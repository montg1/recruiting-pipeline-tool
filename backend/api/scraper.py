"""
Module 1 — Candidate Data Scraper API.

Two flows:
  • JD-driven discovery (the core requirement): a JD/criteria goes in, the system
    generates queries, scrapes/searches multiple sources, AI-ranks the leads, and
    returns a shortlist for HR review — persisted to candidate_searches (staging).
    HR then approves selected leads, promoting them into the Applicant Tracker.
  • Legacy single-URL/text extraction via the n8n webhook (kept as a manual
    fallback for sources that can't be auto-discovered, e.g. a Facebook post).
"""

import logging
import os
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.application import Application
from models.application_stage_history import ApplicationStageHistory
from models.candidate import Candidate
from models.candidate_search import CandidateSearch
from models.job import Job
from schemas.scraper import (
    ApproveRequest,
    ApproveResponse,
    ApproveResultItem,
    CandidateSearchResponse,
    SearchFromJDRequest,
)
from services import jd_search

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Scraper"])  # mounted at /api/scraper in main.py

DEFAULT_APPLIED_STAGE_ID = 1


# ===================================================================
# JD-driven discovery (Module 1 core)
# ===================================================================

@router.post("/search-from-jd", response_model=CandidateSearchResponse,
             summary="Find & rank candidates from a JD across multiple sources")
def search_from_jd(payload: SearchFromJDRequest, db: Session = Depends(get_db)):
    """Parse a JD into criteria, discover leads across sources, AI-rank them,
    and persist the shortlist as a candidate_searches run for HR review."""
    job: Job | None = None
    jd_text = payload.jd_text
    explicit_jd = bool(payload.jd_text)  # caller sent fresh JD text → re-parse, don't reuse cache
    cached_criteria = None

    if payload.job_id is not None:
        job = db.query(Job).filter(Job.id == payload.job_id).first()
        if not job:
            raise HTTPException(404, f"Job {payload.job_id} not found.")
        # fall back to the job's stored JD text if none was sent
        if not jd_text:
            jd_text = "\n\n".join(filter(None, [job.title, job.description, job.requirements]))
        # reuse a prior parse only when the caller didn't supply their own JD text
        if not explicit_jd:
            cached_criteria = job.parsed_criteria

    if not jd_text and not cached_criteria:
        raise HTTPException(400, "Provide jd_text or a job_id with a stored description.")

    try:
        run = jd_search.search_from_jd(
            jd_text=jd_text or "",
            sources=payload.sources,
            per_source=payload.per_source,
            criteria=cached_criteria,
            deep=payload.deep,
            deep_limit=payload.deep_limit,
        )
    except Exception as e:
        logger.exception("search_from_jd failed")
        raise HTTPException(502, f"Search pipeline failed: {e}")

    # cache the freshly parsed criteria back onto the job (refresh if we re-parsed)
    if job is not None and cached_criteria is None:
        job.parsed_criteria = run["criteria"]

    search = CandidateSearch(
        job_id=payload.job_id,
        criteria=run["criteria"],
        sources=run["sources"],
        queries=run["queries"],  # actual query string each adapter sent
        results=run["results"],
        result_count=run["result_count"],
        status=run["status"],
    )
    db.add(search)
    db.commit()
    db.refresh(search)
    return search


@router.get("/searches/{search_id}", response_model=CandidateSearchResponse,
            summary="Fetch a saved search run")
def get_search(search_id: int, db: Session = Depends(get_db)):
    search = db.query(CandidateSearch).filter(CandidateSearch.id == search_id).first()
    if not search:
        raise HTTPException(404, "Search not found.")
    return search


@router.get("/searches", response_model=list[CandidateSearchResponse],
            summary="List search runs (optionally by job)")
def list_searches(
    job_id: int | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(CandidateSearch)
    if job_id is not None:
        q = q.filter(CandidateSearch.job_id == job_id)
    return q.order_by(CandidateSearch.created_at.desc()).limit(limit).all()


# ===================================================================
# Approve leads → Applicant Tracker (human-in-the-loop)
# ===================================================================

@router.post("/approve", response_model=ApproveResponse,
             summary="Promote HR-approved leads into the pipeline")
def approve_leads(payload: ApproveRequest, db: Session = Depends(get_db)):
    """Create a Candidate + Application for each approved lead.

    Scraped leads often lack an email (candidates.email is NOT NULL UNIQUE), so a
    deterministic placeholder is synthesized and flagged in parsed_data for HR to
    fill later. Existing candidates (by email) are reused, not duplicated.
    """
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(404, f"Job {payload.job_id} not found.")

    items: list[ApproveResultItem] = []
    created = skipped = 0

    for lead in payload.leads:
        try:
            email = lead.email or _placeholder_email(lead)
            candidate = db.query(Candidate).filter(Candidate.email == email).first()

            if candidate is None:
                candidate = Candidate(
                    full_name=lead.full_name,
                    email=email,
                    phone=lead.phone,
                    linkedin_url=lead.linkedin_url or (
                        lead.profile_url if lead.profile_url and "linkedin.com" in lead.profile_url else None
                    ),
                    source=lead.source or "scraper",
                    parsed_data={
                        "skills": lead.skills,
                        "experience": lead.experience_summary,
                        "education": lead.education_summary,
                        "profile_url": lead.profile_url,
                        "module1_match_score": lead.match_score,
                        "module1_reasons": lead.reasons,
                        "needs_contact_info": lead.email is None,
                    },
                )
                db.add(candidate)
                db.flush()  # get candidate.id

            # one application per (candidate, job)
            existing_app = (
                db.query(Application)
                .filter(Application.candidate_id == candidate.id, Application.job_id == payload.job_id)
                .first()
            )
            if existing_app:
                skipped += 1
                items.append(ApproveResultItem(
                    full_name=lead.full_name, candidate_id=candidate.id,
                    application_id=existing_app.id, status="duplicate",
                    detail="Already applied to this job.",
                ))
                continue

            application = Application(
                candidate_id=candidate.id,
                job_id=payload.job_id,
                current_stage_id=DEFAULT_APPLIED_STAGE_ID,
            )
            db.add(application)
            db.flush()
            db.add(ApplicationStageHistory(
                application_id=application.id,
                from_stage_id=None,
                to_stage_id=DEFAULT_APPLIED_STAGE_ID,
            ))
            created += 1
            items.append(ApproveResultItem(
                full_name=lead.full_name, candidate_id=candidate.id,
                application_id=application.id, status="created",
            ))
        except Exception as e:  # isolate per-lead failures
            logger.exception("approve failed for %s", lead.full_name)
            items.append(ApproveResultItem(full_name=lead.full_name, status="error", detail=str(e)))

    # mark approved leads in the originating search run (if provided)
    if payload.search_id is not None:
        _mark_approved(db, payload.search_id, payload.leads)

    db.commit()
    return ApproveResponse(created=created, skipped=skipped, items=items)


def _placeholder_email(lead) -> str:
    """Deterministic stand-in email so a contact-less lead can still be stored."""
    handle = ""
    if lead.profile_url:
        m = re.search(r"(?:/in/|github\.com/)([^/?#]+)", lead.profile_url)
        handle = m.group(1) if m else ""
    if not handle:
        handle = re.sub(r"[^a-z0-9]+", ".", lead.full_name.lower()).strip(".")
    src = (lead.source or "lead").lower()
    return f"{handle}.{src}@lead.recruitpipe.local"


def _mark_approved(db: Session, search_id: int, leads) -> None:
    search = db.query(CandidateSearch).filter(CandidateSearch.id == search_id).first()
    if not search or not search.results:
        return
    approved_urls = {l.profile_url for l in leads if l.profile_url}
    approved_names = {l.full_name for l in leads}
    new_results = []
    for r in search.results:
        if r.get("profile_url") in approved_urls or r.get("full_name") in approved_names:
            r = {**r, "status": "approved"}
        new_results.append(r)
    search.results = new_results  # reassign so SQLAlchemy flags the JSONB column dirty


# ===================================================================
# Legacy: single URL/text extraction via n8n (manual fallback)
# ===================================================================

class ScraperRequest(BaseModel):
    input_type: str = Field(..., description="'url' or 'text'")
    payload: str = Field(..., description="The URL or raw text to scrape")


@router.post("/extract", summary="Extract one candidate via the n8n webhook (manual fallback)")
async def extract_candidate_data(request: ScraperRequest):
    """Forward a single URL/text to the n8n webhook for scraping + normalization.
    Used for manual sources (e.g. a pasted Facebook job-seeking post)."""
    if request.input_type not in ["url", "text"]:
        raise HTTPException(status_code=400, detail="input_type must be 'url' or 'text'")

    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    if not webhook_url:
        raise HTTPException(status_code=500, detail="N8N_WEBHOOK_URL environment variable is not set")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                webhook_url,
                json={"input_type": request.input_type, "payload": request.payload},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"n8n webhook error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to communicate with n8n webhook: {str(e)}")
