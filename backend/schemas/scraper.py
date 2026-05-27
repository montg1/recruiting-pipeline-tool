"""
Pydantic schemas for Module 1 — JD-driven candidate search & approval.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Search from JD
# ---------------------------------------------------------------------------

class SearchFromJDRequest(BaseModel):
    """Body for POST /scraper/search-from-jd."""
    jd_text: Optional[str] = Field(None, description="Raw job description text")
    job_id: Optional[int] = Field(None, description="Existing job to search for / attach results to")
    sources: Optional[list[str]] = Field(None, description='Subset of sources, e.g. ["github", "linkedin"]')
    per_source: int = Field(10, ge=1, le=25, description="Max leads per source")
    deep: bool = Field(False, description="Deep-fetch top LinkedIn profiles for richer ranking (slower)")
    deep_limit: int = Field(5, ge=1, le=10, description="Max LinkedIn profiles to deep-fetch when deep=True")


class LeadResult(BaseModel):
    """One ranked lead inside a search's results array."""
    full_name: str
    source: str
    profile_url: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    skills: list[str] = []
    experience_summary: Optional[str] = None
    education_summary: Optional[str] = None
    match_score: int = 0
    verdict: str = "Unranked"
    reasons: list[str] = []
    missing: list[str] = []
    status: str = "pending"          # pending | approved | rejected
    raw: dict[str, Any] = {}


class CandidateSearchResponse(BaseModel):
    """Serialised candidate_searches row."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: Optional[int] = None
    criteria: Optional[dict[str, Any]] = None
    sources: Optional[list[str]] = None
    queries: Optional[dict[str, str]] = None     # actual query string sent per source
    results: list[LeadResult] = []
    result_count: int
    status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Approve leads → pipeline
# ---------------------------------------------------------------------------

class ApproveLead(BaseModel):
    """One lead the HR user approved (possibly edited in the preview)."""
    full_name: str
    email: Optional[str] = None            # synthesized if missing (see endpoint)
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    source: Optional[str] = None
    profile_url: Optional[str] = None
    skills: list[str] = []
    experience_summary: Optional[str] = None
    education_summary: Optional[str] = None
    match_score: Optional[int] = None
    reasons: list[str] = []


class ApproveRequest(BaseModel):
    """Body for POST /scraper/approve — promote selected leads into the tracker."""
    job_id: int = Field(..., description="Job to create applications under")
    leads: list[ApproveLead] = Field(..., min_length=1)
    search_id: Optional[int] = Field(None, description="Mark these leads approved in this search run")


class ApproveResultItem(BaseModel):
    full_name: str
    candidate_id: Optional[int] = None
    application_id: Optional[int] = None
    status: str                            # 'created' | 'duplicate' | 'error'
    detail: Optional[str] = None


class ApproveResponse(BaseModel):
    created: int
    skipped: int
    items: list[ApproveResultItem]
