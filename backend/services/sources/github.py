"""
GitHub source adapter — Track A (public, official API, no scraping).

Uses GitHub's Search Users API to find developers by location + keyword, then
enriches the top results via GET /users/{login} for name/bio/company. Ideal for
engineering JDs. Optional GITHUB_TOKEN raises the rate limit (60→5000/hr).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from config import settings
from services.sources.base import Candidate, SourceAdapter

logger = logging.getLogger(__name__)

API = "https://api.github.com"

# Map common skills/keywords to GitHub `language:` qualifiers for sharper results.
_LANGUAGE_HINTS = {
    "python": "Python", "fastapi": "Python", "django": "Python", "flask": "Python",
    "javascript": "JavaScript", "node": "JavaScript", "node.js": "JavaScript",
    "typescript": "TypeScript", "react": "TypeScript", "vue": "Vue",
    "go": "Go", "golang": "Go", "rust": "Rust", "java": "Java",
    "c#": "C#", ".net": "C#", "php": "PHP", "ruby": "Ruby",
}


class GithubAdapter(SourceAdapter):
    name = "github"

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/vnd.github+json", "User-Agent": "recruitpipe"}
        token = getattr(settings, "github_token", "") or ""
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def build_query(self, criteria: dict[str, Any]) -> str:
        parts: list[str] = ["type:user"]  # exclude organizations/clubs from results
        country = criteria.get("location_country") or criteria.get("location")
        if country:
            # GitHub location is free-text; quote multiword values
            loc = country.split(",")[0].strip()
            parts.append(f'location:"{loc}"' if " " in loc else f"location:{loc}")

        # pick at most one language qualifier from skills
        for kw in self._keywords(criteria):
            lang = _LANGUAGE_HINTS.get(kw.lower())
            if lang:
                parts.append(f"language:{lang}")
                break

        # one free-text keyword (bio/name match)
        kws = self._keywords(criteria)
        if kws:
            # avoid using the position phrase verbatim (too sparse on GitHub); use a skill term
            free = next((k for k in kws if k.lower() not in _LANGUAGE_HINTS), kws[0])
            parts.append(free.split()[0])  # single token keeps the query loose

        return " ".join(parts).strip() or "location:Thailand"

    def search(self, criteria: dict[str, Any], limit: int = 10) -> list[Candidate]:
        query = self.build_query(criteria)
        try:
            with httpx.Client(timeout=20.0, headers=self._headers()) as client:
                resp = client.get(
                    f"{API}/search/users",
                    params={"q": query, "per_page": min(limit, 20)},
                )
                resp.raise_for_status()
                items = resp.json().get("items", [])[:limit]

                out: list[Candidate] = []
                for it in items:
                    login = it.get("login")
                    detail = self._fetch_user(client, login)
                    out.append(self._to_candidate(it, detail))
                return out
        except Exception as e:  # never sink the whole search on one source
            logger.warning("GitHub adapter failed for query %r: %s", query, e)
            return []

    def _fetch_user(self, client: httpx.Client, login: str) -> dict[str, Any]:
        try:
            r = client.get(f"{API}/users/{login}")
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return {}

    @staticmethod
    def _to_candidate(item: dict[str, Any], detail: dict[str, Any]) -> Candidate:
        login = item.get("login", "")
        return Candidate(
            full_name=detail.get("name") or login,
            source="GitHub",
            profile_url=item.get("html_url"),
            headline=detail.get("bio"),
            location=detail.get("location"),
            email=detail.get("email"),  # only if the user made it public
            experience_summary=(
                f"{detail.get('company') or ''} · public repos: {detail.get('public_repos', 0)} "
                f"· followers: {detail.get('followers', 0)}"
            ).strip(" ·"),
            raw={
                "login": login,
                "blog": detail.get("blog"),
                "company": detail.get("company"),
                "public_repos": detail.get("public_repos"),
                "followers": detail.get("followers"),
            },
        )
