"""
Source adapters for Module 1 candidate discovery.

Each adapter turns parsed JD criteria into a list of candidate *leads* from one
source. They all share the SourceAdapter interface so the orchestrator
(`services.jd_search`) can fan out across sources without knowing their
internals — add a new source = add one adapter and register it here.
"""

from services.sources.base import Candidate, SourceAdapter
from services.sources.github import GithubAdapter
from services.sources.linkedin_xray import LinkedinXrayAdapter

# Registry — the orchestrator iterates over these.
# Order is irrelevant; results are merged + deduped downstream.
ADAPTERS: dict[str, SourceAdapter] = {
    "github": GithubAdapter(),
    "linkedin": LinkedinXrayAdapter(),
}

__all__ = ["Candidate", "SourceAdapter", "GithubAdapter", "LinkedinXrayAdapter", "ADAPTERS"]
