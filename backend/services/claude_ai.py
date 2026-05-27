"""
LLM integration for Module 1 (Candidate Data Scraper).

Two responsibilities:
  parse_jd(jd_text)             → structured criteria + search keywords
  rank_candidates(criteria, …)  → fit score (0-100) + reasons per lead

Provider-pluggable via settings.llm_provider:
  • "anthropic" (prod) — Claude, with the JD criteria in a cached system block.
  • "ollama"   (local) — e.g. gemma4:e4b, no API key; handy for testing.
The prompts are identical across providers; only the transport differs.

(Module 2's resume scoring will add score_resume() here later.)
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

# Claude model for the anthropic provider (strong reasoning, batch-ranking cost).
ANTHROPIC_MODEL = "claude-sonnet-4-6"

_anthropic_client = None


# ---------------------------------------------------------------------------
# Provider-agnostic completion
# ---------------------------------------------------------------------------

def _complete(system: str, user: str, max_tokens: int = 2048) -> str:
    """Run a single-turn completion through the configured provider. Returns raw text."""
    if settings.llm_provider == "ollama":
        return _complete_ollama(system, user, max_tokens)
    return _complete_anthropic(system, user, max_tokens)


def _complete_anthropic(system: str, user: str, max_tokens: int) -> str:
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic
        _anthropic_client = Anthropic(api_key=settings.anthropic_api_key)
    resp = _anthropic_client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        # cache the system block — it's identical across every lead in a ranking batch
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text


def _complete_ollama(system: str, user: str, max_tokens: int) -> str:
    """Call a local Ollama model. `format: json` constrains output to valid JSON."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2, "num_predict": max_tokens},
    }
    with httpx.Client(timeout=300.0) as client:  # local 8B models can be slow
        r = client.post(url, json=payload)
        r.raise_for_status()
        return r.json()["message"]["content"]


def _call_n8n(payload: dict[str, Any]) -> Any:
    """Delegate an AI task to the n8n webhook (n8n owns the prompts + Claude call).

    FastAPI sends only raw inputs ({task, jd_text} or {task, criteria, candidates});
    n8n runs Claude and returns structured JSON. Tolerant of how n8n wraps its
    response: a bare value, a single-item array, or the model's raw text under a key.
    """
    url = settings.n8n_ai_webhook_url
    if not url:
        raise RuntimeError("LLM_PROVIDER=n8n but N8N_AI_WEBHOOK_URL is not set")
    with httpx.Client(timeout=300.0) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()

    if isinstance(data, list):                    # n8n usually wraps output in an array
        data = data[0] if data else {}
    if isinstance(data, dict):
        # AI Agent puts its result under "output" (other wrappers vary). The value
        # is a string (raw model text) without a Structured Output Parser, or an
        # already-parsed object/array with one — handle both.
        for key in ("output", "text", "content", "result", "json"):
            if key in data:
                v = data[key]
                if isinstance(v, str):
                    return _extract_json(v) if ("{" in v or "[" in v) else v
                if isinstance(v, (dict, list)):
                    return v
    return data


def _extract_json(text: str) -> Any:
    """Pull the first balanced JSON value out of a model response (handles ```json
    fences and trailing prose that smaller local models sometimes emit)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
    if start == -1:
        raise ValueError("no JSON found in response")

    open_ch = text[start]
    close_ch = "}" if open_ch == "{" else "]"
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:i + 1])
    # fall back: try the whole tail
    return json.loads(text[start:])


# ---------------------------------------------------------------------------
# 1. JD → criteria
# ---------------------------------------------------------------------------

_PARSE_SYSTEM = """You are a technical recruiter. Extract structured search criteria from a job description (which may be in Thai or English).

Return ONLY a JSON object with these keys:
- "position": string — the core role title in English (e.g. "AI Automation Engineer")
- "role_keywords": string[] — 3-6 short role/title synonyms recruiters would search (English)
- "must_have_skills": string[] — required hard skills/tools
- "nice_to_have": string[] — bonus skills
- "min_years": number — minimum years of experience (0 if unstated)
- "location": string — city/region as written (English), or "" if remote/unstated
- "location_country": string — country in English (e.g. "Thailand"), or "" if unknown

Keep arrays concise. Translate Thai terms to their common English equivalents."""


def parse_jd(jd_text: str) -> dict[str, Any]:
    """Turn raw JD text into structured criteria used to build source queries."""
    if settings.llm_provider == "n8n":
        criteria = _call_n8n({"task": "parse_jd", "jd_text": jd_text})
        if isinstance(criteria, dict) and isinstance(criteria.get("criteria"), dict):
            criteria = criteria["criteria"]   # tolerate {"criteria": {...}} wrapping
    else:
        criteria = _extract_json(_complete(_PARSE_SYSTEM, f"Job description:\n\n{jd_text}", max_tokens=1024))

    if not isinstance(criteria, dict):
        raise ValueError("parse_jd expected a JSON object")
    criteria.setdefault("position", "")
    criteria.setdefault("role_keywords", [])
    criteria.setdefault("must_have_skills", [])
    criteria.setdefault("nice_to_have", [])
    criteria.setdefault("min_years", 0)
    criteria.setdefault("location", "")
    criteria.setdefault("location_country", "")
    return criteria


# ---------------------------------------------------------------------------
# 2. Leads → ranked shortlist
# ---------------------------------------------------------------------------

_RANK_SYSTEM = """You are screening discovered candidate leads against a role.

For EACH candidate in the user's JSON list, judge fit using ONLY the data given
(name, headline, location, skills, summary). Data is often sparse — score on the
evidence available and say what's missing rather than inventing facts.

Return ONLY a JSON object of the form {"rankings": [ ... ]} where each item is:
- "id": the candidate's "id" from the input
- "match_score": integer 0-100
- "verdict": one of "Strong" | "Possible" | "Weak"
- "reasons": string[] — 1-3 short bullet reasons (Thai is fine), citing the evidence
- "missing": string[] — must-have criteria you couldn't verify from the data

The "rankings" array must have the same length as the input list."""


def rank_candidates(criteria: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score each lead 0-100 against the criteria. Returns a list of ranking dicts."""
    if not candidates:
        return []

    system = _RANK_SYSTEM + "\n\nROLE CRITERIA (the bar to measure against):\n" + json.dumps(criteria, ensure_ascii=False)
    slim = [
        {
            "id": i,
            "full_name": c.get("full_name"),
            "headline": c.get("headline"),
            "location": c.get("location"),
            "skills": c.get("skills"),
            "summary": c.get("experience_summary"),
            "source": c.get("source"),
        }
        for i, c in enumerate(candidates)
    ]

    try:
        if settings.llm_provider == "n8n":
            parsed = _call_n8n({"task": "rank", "criteria": criteria, "candidates": slim})
        else:
            parsed = _extract_json(_complete(system, json.dumps(slim, ensure_ascii=False), max_tokens=4096))
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse ranking response: %s", e)
        return [{"id": i, "match_score": 0, "verdict": "Weak", "reasons": ["ranking failed"], "missing": []}
                for i in range(len(candidates))]

    # accept either a bare array or {"rankings": [...]} (providers differ in JSON mode)
    if isinstance(parsed, dict):
        parsed = parsed.get("rankings") or next((v for v in parsed.values() if isinstance(v, list)), [])
    return parsed if isinstance(parsed, list) else []
