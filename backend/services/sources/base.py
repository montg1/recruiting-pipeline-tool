"""
Source adapter contract.

`Candidate` is the normalized lead shape every adapter must return. Most fields
are optional because discovery sources expose wildly different amounts of data
(GitHub gives a bio; a LinkedIn search snippet gives only name + headline).
Downstream code (ranking, dedup, approval) only relies on this shape.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class Candidate:
    """A discovered lead — NOT yet a pipeline candidate."""
    full_name: str
    source: str                                  # 'GitHub' | 'LinkedIn' | ...
    profile_url: Optional[str] = None
    headline: Optional[str] = None               # one-line role/summary
    location: Optional[str] = None
    email: Optional[str] = None
    skills: list[str] = field(default_factory=list)
    experience_summary: Optional[str] = None
    education_summary: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)  # source-specific extras

    def dedup_key(self) -> str:
        """Identity for cross-source dedup: prefer the profile URL path, else name."""
        if self.profile_url:
            # normalize: strip scheme/host/query, lowercase the path
            m = re.search(r"(?:linkedin\.com/in/|github\.com/)([^/?#]+)", self.profile_url, re.I)
            if m:
                return f"{self.source.lower()}:{m.group(1).lower()}"
            return self.profile_url.split("?")[0].rstrip("/").lower()
        normalized_name = re.sub(r"\s+", " ", self.full_name).strip().lower()
        return f"name:{normalized_name}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SourceAdapter(ABC):
    """One discovery source. Implementations must be import-safe (no network at
    construction) and must never raise — return [] on failure so one dead source
    can't sink the whole search."""

    name: str = "base"

    @abstractmethod
    def search(self, criteria: dict[str, Any], limit: int = 10) -> list[Candidate]:
        """Turn parsed JD criteria into a list of leads. Best-effort; swallow errors."""
        raise NotImplementedError

    def build_query(self, criteria: dict[str, Any]) -> str:
        """The actual query string this adapter sends for the given criteria.
        Surfaced so the orchestrator can record/show what was searched."""
        return ""

    def enrich(self, candidate: Candidate) -> None:
        """Optionally deep-fetch and fill in more fields for one lead, in place.
        Default no-op (e.g. GitHub already returns full data from its API)."""
        return

    # --- shared helpers ---

    @staticmethod
    def _keywords(criteria: dict[str, Any]) -> list[str]:
        """Flatten the most useful query terms out of parsed criteria."""
        terms: list[str] = []
        for key in ("role_keywords", "must_have_skills"):
            terms += [t for t in (criteria.get(key) or []) if t]
        if criteria.get("position"):
            terms.insert(0, criteria["position"])
        # de-dupe preserving order
        seen, out = set(), []
        for t in terms:
            k = t.lower()
            if k not in seen:
                seen.add(k)
                out.append(t)
        return out
