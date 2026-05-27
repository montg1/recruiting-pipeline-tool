"""
LinkedIn source adapter — Track A (public, no login).

LinkedIn blocks direct fetches (HTTP 999) and walls People Search behind login.
The robust workaround is a search-engine "X-ray": ask Google for
`site:linkedin.com/in <keywords> <location>` via ZenRows (which bypasses the
anti-bot proxy), then read name + headline straight from the result snippets —
no profile visit, no login, no ban risk.

`deep_fetch()` (opt-in) pulls a single public profile's JSON-LD for richer data
when an HR user explicitly drills into one lead.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import quote_plus

import httpx

from config import settings
from services.sources.base import Candidate, SourceAdapter

logger = logging.getLogger(__name__)

ZENROWS = "https://api.zenrows.com/v1/"

# country (lowercased) -> LinkedIn locale subdomain
_TLD = {"thailand": "th", "th": "th", "singapore": "sg", "malaysia": "my",
        "japan": "jp", "india": "in", "united kingdom": "uk", "uk": "uk"}

_PROFILE_RE = re.compile(r'href="(https?://[a-z]{2,3}\.linkedin\.com/in/[A-Za-z0-9\-]+)[^"]*"')
_H3_RE = re.compile(r"<h3[^>]*>(.*?)</h3>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")


class LinkedinXrayAdapter(SourceAdapter):
    name = "linkedin"

    def _zen_get(self, target_url: str, timeout: float = 90.0, attempts: int = 2) -> Optional[str]:
        # ZenRows renders Google through a proxy — a single call routinely takes
        # 15-60s, so give it room and retry once on a timeout/transient error.
        key = getattr(settings, "zenrows_api_key", "") or ""
        if not key:
            logger.warning("LinkedIn adapter: ZENROWS_API_KEY not set — skipping")
            return None
        for attempt in range(1, attempts + 1):
            try:
                with httpx.Client(timeout=timeout) as client:
                    r = client.get(ZENROWS, params={
                        "apikey": key,
                        "url": target_url,
                        "js_render": "true",
                        "premium_proxy": "true",
                    })
                    if r.status_code == 200:
                        return r.text
                    logger.warning("ZenRows returned %s (attempt %d/%d)", r.status_code, attempt, attempts)
            except Exception as e:
                logger.warning("ZenRows request failed (attempt %d/%d): %s", attempt, attempts, e)
        return None

    def build_query(self, criteria: dict[str, Any]) -> str:
        country = (criteria.get("location_country") or criteria.get("location") or "").lower()
        tld = _TLD.get(country.split(",")[0].strip(), "www")
        kws = self._keywords(criteria)[:4]
        kw_clause = " OR ".join(f'"{k}"' for k in kws) if kws else ""
        loc = criteria.get("location") or criteria.get("location_country") or ""
        loc = re.split(r"[(,/]", loc)[0].strip()  # drop cruft like "Bangkok (Hybrid Working…)"
        q = f"site:{tld}.linkedin.com/in"
        if kw_clause:
            q += f" ({kw_clause})"
        if loc:
            q += f" {loc}"
        return q

    def search(self, criteria: dict[str, Any], limit: int = 10) -> list[Candidate]:
        query = self.build_query(criteria)
        google = f"https://www.google.com/search?q={quote_plus(query)}&num=20&hl=en"
        html = self._zen_get(google)
        if not html:
            return []

        out: list[Candidate] = []
        seen: set[str] = set()
        for m in _PROFILE_RE.finditer(html):
            url = m.group(1)
            if url in seen:
                continue
            seen.add(url)

            # grab the nearest result title after this anchor: "Name - Headline ..."
            window = html[m.start():m.start() + 1500]
            h3 = _H3_RE.search(window)
            title = _TAG_RE.sub("", h3.group(1)).strip() if h3 else ""
            title = _clean(title)
            name, headline = _split_title(title) if title else (None, None)

            out.append(Candidate(
                full_name=name or url.rsplit("/", 1)[-1].replace("-", " ").title(),
                source="LinkedIn",
                profile_url=url,
                headline=headline,
                raw={"snippet_title": title, "query": query},
            ))
            if len(out) >= limit:
                break
        return out

    # --- opt-in deep extraction (one profile) ---

    def enrich(self, candidate: Candidate) -> None:
        """Deep-fetch the profile's JSON-LD and fill location/experience/education in place."""
        if not candidate.profile_url:
            return
        try:
            data = self.deep_fetch(candidate.profile_url)
        except Exception as e:
            logger.warning("enrich failed for %s: %s", candidate.profile_url, e)
            return
        if not data:
            return
        if data.get("location") and not candidate.location:
            candidate.location = data["location"]
        works = [w for w in (data.get("worksFor") or []) if w]
        if works and not candidate.experience_summary:
            candidate.experience_summary = "; ".join(works)
        edu = [e for e in (data.get("education") or []) if e]
        if edu and not candidate.education_summary:
            candidate.education_summary = "; ".join(edu)
        candidate.raw["deep_fetched"] = True

    def deep_fetch(self, profile_url: str) -> dict[str, Any]:
        """Pull richer fields from a public profile's JSON-LD. Best-effort."""
        html = self._zen_get(profile_url)
        if not html:
            return {}
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        if not m:
            return {}
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return {}
        graph = data.get("@graph", [data])
        person = next((n for n in graph if n.get("@type") == "Person"), graph[0] if graph else {})
        addr = person.get("address") or {}
        return {
            "name": person.get("name"),
            "location": addr.get("addressLocality"),
            "worksFor": [w.get("name") for w in person.get("worksFor", []) if isinstance(w, dict)],
            "education": [e.get("name") for e in person.get("alumniOf", []) if isinstance(e, dict)],
        }


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("&amp;", "&")).strip()


def _split_title(title: str) -> tuple[str, Optional[str]]:
    """Google titles look like 'Jane Doe - AI Engineer | Foo'. Split on the first dash."""
    parts = re.split(r"\s[-–—]\s", title, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return title.strip(), None
