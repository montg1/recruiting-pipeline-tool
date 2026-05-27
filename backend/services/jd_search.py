"""
Module 1 orchestrator — JD → ranked shortlist.

Ties the pieces together:
  1. parse_jd     (Claude)        raw JD → structured criteria
  2. discover     (adapters)      criteria → leads from each source, merged + deduped
  3. rank         (Claude)        leads → fit score + reasons, sorted

Network/AI failures degrade gracefully: a dead source contributes nothing, and
if ranking fails the leads are still returned unscored.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from services import claude_ai
from services.sources import ADAPTERS
from services.sources.base import Candidate

logger = logging.getLogger(__name__)


def _enrich_leads(leads: list[Candidate], limit: int) -> None:
    """Deep-fetch the top LinkedIn leads (in place) to add location/experience/
    education before ranking. Parallelized — each ZenRows fetch is ~15s."""
    targets = [c for c in leads if c.source == "LinkedIn" and c.profile_url][:limit]
    if not targets:
        return
    enrich = ADAPTERS["linkedin"].enrich  # adapters never raise
    with ThreadPoolExecutor(max_workers=min(5, len(targets))) as ex:
        list(ex.map(enrich, targets))
    logger.info("deep-fetched %d LinkedIn leads", len(targets))


def discover(criteria: dict[str, Any], sources: Optional[list[str]] = None,
             per_source: int = 10) -> tuple[list[Candidate], dict[str, str]]:
    """Fan out across the chosen source adapters and merge + dedup the leads.

    Returns (leads, queries) where `queries` maps each source to the actual
    query string it sent — surfaced so callers can record/show what was searched.
    """
    chosen = sources or list(ADAPTERS.keys())
    merged: dict[str, Candidate] = {}
    queries: dict[str, str] = {}

    for name in chosen:
        adapter = ADAPTERS.get(name)
        if not adapter:
            logger.warning("Unknown source %r — skipping", name)
            continue
        queries[name] = adapter.build_query(criteria)
        leads = adapter.search(criteria, limit=per_source)  # adapters never raise
        logger.info("source %s [%s] returned %d leads", name, queries[name], len(leads))
        for lead in leads:
            key = lead.dedup_key()
            # first source wins; could merge fields later if useful
            merged.setdefault(key, lead)

    return list(merged.values()), queries


def search_from_jd(
    jd_text: str,
    sources: Optional[list[str]] = None,
    per_source: int = 10,
    criteria: Optional[dict[str, Any]] = None,
    deep: bool = False,
    deep_limit: int = 5,
) -> dict[str, Any]:
    """Full pipeline. Returns a dict ready to persist into candidate_searches.

    Pass `criteria` to skip the parse step (e.g. reuse a job's cached parse).
    `deep=True` deep-fetches the top LinkedIn leads for richer ranking (slower).
    """
    if criteria is None:
        criteria = claude_ai.parse_jd(jd_text)

    leads, queries = discover(criteria, sources=sources, per_source=per_source)

    if deep and leads:
        _enrich_leads(leads, deep_limit)

    # rank (best-effort) and fold scores back onto the leads.
    # If Claude is unavailable, still return the discovered leads — unranked —
    # rather than failing the whole search.
    rank_failed = False
    rankings: list[dict[str, Any]] = []
    if leads:
        try:
            rankings = claude_ai.rank_candidates(criteria, [c.to_dict() for c in leads])
        except Exception as e:
            logger.warning("ranking unavailable, returning unranked leads: %s", e)
            rank_failed = True
    # coerce ids to int — some models return "id" as a string, which would
    # otherwise miss the lookup and leave every lead unranked.
    by_id: dict[int, dict[str, Any]] = {}
    for r in rankings:
        try:
            by_id[int(r.get("id"))] = r
        except (TypeError, ValueError):
            continue
    ranked_results: list[dict[str, Any]] = []

    for i, lead in enumerate(leads):
        r = by_id.get(i, {})
        item = lead.to_dict()
        item.update({
            "match_score": r.get("match_score", 0),
            "verdict": r.get("verdict", "Unranked"),
            "reasons": r.get("reasons", []),
            "missing": r.get("missing", []),
            "status": "pending",  # HR review state: pending | approved | rejected
        })
        ranked_results.append(item)

    ranked_results.sort(key=lambda x: x["match_score"], reverse=True)

    # 'completed' = found + ranked; 'partial' = found but unranked (Claude down) or nothing found
    status = "completed" if (leads and not rank_failed) else "partial"
    return {
        "criteria": criteria,
        "sources": sources or list(ADAPTERS.keys()),
        "queries": queries,
        "results": ranked_results,
        "result_count": len(ranked_results),
        "status": status,
    }
