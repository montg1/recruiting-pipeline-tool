"""
Module 4 — Interview Scheduling API

Routes
------
  POST   /                  Schedule a new interview (with conflict detection + n8n webhook)
  GET    /                  List interviews (filterable by application_id, interviewer_id, status)
  GET    /{interview_id}    Get a single interview
  PUT    /{interview_id}    Reschedule / update an interview (pings n8n to update Calendar event)
  DELETE /{interview_id}    Cancel an interview (pings n8n to delete Calendar event, reverts stage)

Hybrid Architecture:
  FastAPI handles validation, conflict detection, and DB writes.
  n8n handles Google Calendar event creation/update/deletion and returns meet links.
"""

from datetime import timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from database import get_db
from config import settings
from models.interview import Interview
from models.application import Application
from models.candidate import Candidate
from models.resume_score import ResumeScore
from models.pipeline_stage import PipelineStage
from schemas.interview import InterviewCreate, InterviewUpdate, InterviewResponse

router = APIRouter()

# Stage IDs — match seeded pipeline_stages
FIRST_INTERVIEW_STAGE_ID = 4  # "First Interview"
SCREENING_STAGE_ID = 2        # "Screening" (fallback on cancel)


# ===================================================================
# Helpers
# ===================================================================

def _check_overlap(
    db: Session,
    interviewer_id: int,
    start: "datetime",
    duration: int,
    exclude_id: Optional[int] = None,
):
    """Check if the interviewer has a conflicting interview at the proposed time.

    Two interviews overlap when:
        existing.start < proposed.end  AND  proposed.start < existing.end
    """
    from sqlalchemy import text

    proposed_end = start + timedelta(minutes=duration)

    query = db.query(Interview).filter(
        Interview.interviewer_id == interviewer_id,
        Interview.status == "scheduled",
        # existing starts before proposed ends
        Interview.scheduled_at < proposed_end,
        # existing ends after proposed starts
        # Use raw SQL for interval calculation: scheduled_at + (duration_minutes * interval '1 minute')
        text("scheduled_at + (duration_minutes * interval '1 minute') > :proposed_start"),
    ).params(proposed_start=start)

    if exclude_id is not None:
        query = query.filter(Interview.id != exclude_id)

    return query.first()


async def _call_n8n_interview_webhook(action: str, payload: dict) -> dict:
    """Send interview data to n8n webhook for Google Calendar integration."""
    webhook_url = settings.n8n_interview_webhook_url
    if not webhook_url or webhook_url.startswith("http://localhost:5678"):
        # n8n not configured — return placeholder data
        return {
            "google_meet_link": None,
            "google_event_id": None,
            "status": "no_n8n_configured",
        }

    payload["action"] = action  # "create" | "update" | "delete"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            result = response.json()
            # Handle n8n array response format
            if isinstance(result, list) and len(result) > 0:
                result = result[0].get("output", result[0]) if "output" in result[0] else result[0]
            return result
    except httpx.HTTPStatusError as e:
        print(f"n8n interview webhook error ({action}): {e.response.status_code} {e.response.text}")
        return {"google_meet_link": None, "google_event_id": None, "error": str(e)}
    except Exception as e:
        print(f"n8n interview webhook failed ({action}): {e}")
        return {"google_meet_link": None, "google_event_id": None, "error": str(e)}


def _get_prescreen_questions(db: Session, application_id: int) -> list:
    """Fetch prescreen questions from resume_scores for this application."""
    score = (
        db.query(ResumeScore)
        .filter(ResumeScore.application_id == application_id)
        .order_by(ResumeScore.scored_at.desc())
        .first()
    )
    if score and score.prescreen_questions:
        return score.prescreen_questions if isinstance(score.prescreen_questions, list) else []

    # Fallback: check candidate.parsed_data for AI evaluation
    app = db.query(Application).options(joinedload(Application.candidate)).filter(Application.id == application_id).first()
    if app and app.candidate and app.candidate.parsed_data:
        ai_eval = app.candidate.parsed_data.get("ai_evaluation", {})
        return ai_eval.get("prescreen_questions", [])

    return []


# ===================================================================
# POST / — Schedule a new interview
# ===================================================================

@router.post("/", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def schedule_interview(payload: InterviewCreate, db: Session = Depends(get_db)):
    """Schedule a new interview.

    1. Validates the application exists
    2. Checks for interviewer time conflicts (409 if overlap)
    3. Fetches prescreen questions from Module 2
    4. Calls n8n webhook to create Google Calendar event
    5. Saves interview record with meet link
    6. Advances application stage to 'First Interview'
    """

    # Validate application exists
    application = (
        db.query(Application)
        .options(joinedload(Application.candidate), joinedload(Application.job))
        .filter(Application.id == payload.application_id, Application.is_active == True)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    # --- Conflict Detection ---
    if payload.interviewer_id:
        conflict = _check_overlap(
            db,
            interviewer_id=payload.interviewer_id,
            start=payload.scheduled_at,
            duration=payload.duration_minutes,
        )
        if conflict:
            conflict_end = conflict.scheduled_at + timedelta(minutes=conflict.duration_minutes)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Interviewer has a conflicting interview "
                    f"from {conflict.scheduled_at.isoformat()} to {conflict_end.isoformat()} "
                    f"(Interview #{conflict.id})."
                ),
            )

    # --- Fetch prescreen questions ---
    prescreen_questions = _get_prescreen_questions(db, payload.application_id)

    # --- Call n8n for Google Calendar ---
    n8n_payload = {
        "candidate_name": application.candidate.full_name,
        "candidate_email": application.candidate.email,
        "job_title": application.job.title if application.job else "Unknown",
        "scheduled_at": payload.scheduled_at.isoformat(),
        "duration_minutes": payload.duration_minutes,
        "prescreen_questions": prescreen_questions,
    }

    n8n_result = await _call_n8n_interview_webhook("create", n8n_payload)

    # --- Save interview ---
    interview = Interview(
        application_id=payload.application_id,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        interviewer_id=payload.interviewer_id,
        google_meet_link=n8n_result.get("google_meet_link"),
        google_event_id=n8n_result.get("google_event_id"),
        status="scheduled",
    )
    db.add(interview)

    # --- Advance stage to First Interview ---
    first_interview_stage = (
        db.query(PipelineStage).filter(PipelineStage.id == FIRST_INTERVIEW_STAGE_ID).first()
    )
    if first_interview_stage and application.current_stage_id < FIRST_INTERVIEW_STAGE_ID:
        application.current_stage_id = FIRST_INTERVIEW_STAGE_ID

    db.commit()
    db.refresh(interview)
    return interview


# ===================================================================
# GET / — List interviews
# ===================================================================

@router.get("/", response_model=list[InterviewResponse])
def list_interviews(
    application_id: Optional[int] = Query(None, description="Filter by application ID"),
    interviewer_id: Optional[int] = Query(None, description="Filter by interviewer ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List interviews with optional filtering."""
    query = db.query(Interview)

    if application_id is not None:
        query = query.filter(Interview.application_id == application_id)
    if interviewer_id is not None:
        query = query.filter(Interview.interviewer_id == interviewer_id)
    if status_filter:
        query = query.filter(Interview.status == status_filter)

    return query.order_by(Interview.scheduled_at.desc()).offset(skip).limit(limit).all()


# ===================================================================
# GET /{id} — Get a single interview
# ===================================================================

@router.get("/{interview_id}", response_model=InterviewResponse)
def get_interview(interview_id: int, db: Session = Depends(get_db)):
    """Get a single interview by ID."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return interview


# ===================================================================
# PUT /{id} — Reschedule / update
# ===================================================================

@router.put("/{interview_id}", response_model=InterviewResponse)
async def update_interview(
    interview_id: int,
    payload: InterviewUpdate,
    db: Session = Depends(get_db),
):
    """Reschedule or update an interview.

    If scheduled_at or duration_minutes change, re-check for conflicts
    and ping n8n to update the Google Calendar event.
    """
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found.")

    if interview.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot update a cancelled interview.")

    # Determine new values
    new_start = payload.scheduled_at or interview.scheduled_at
    new_duration = payload.duration_minutes or interview.duration_minutes
    new_interviewer = payload.interviewer_id if payload.interviewer_id is not None else interview.interviewer_id

    # --- Conflict detection on reschedule ---
    if new_interviewer and (
        payload.scheduled_at or payload.duration_minutes or payload.interviewer_id
    ):
        conflict = _check_overlap(
            db,
            interviewer_id=new_interviewer,
            start=new_start,
            duration=new_duration,
            exclude_id=interview_id,
        )
        if conflict:
            conflict_end = conflict.scheduled_at + timedelta(minutes=conflict.duration_minutes)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Interviewer has a conflicting interview "
                    f"from {conflict.scheduled_at.isoformat()} to {conflict_end.isoformat()} "
                    f"(Interview #{conflict.id})."
                ),
            )

    # --- Update n8n / Google Calendar ---
    time_changed = payload.scheduled_at or payload.duration_minutes
    if time_changed and interview.google_event_id:
        application = (
            db.query(Application)
            .options(joinedload(Application.candidate))
            .filter(Application.id == interview.application_id)
            .first()
        )
        n8n_payload = {
            "google_event_id": interview.google_event_id,
            "candidate_name": application.candidate.full_name if application else "Unknown",
            "scheduled_at": new_start.isoformat(),
            "duration_minutes": new_duration,
        }
        await _call_n8n_interview_webhook("update", n8n_payload)

    # --- Apply updates ---
    if payload.scheduled_at:
        interview.scheduled_at = payload.scheduled_at
    if payload.duration_minutes:
        interview.duration_minutes = payload.duration_minutes
    if payload.interviewer_id is not None:
        interview.interviewer_id = payload.interviewer_id
    if payload.status:
        interview.status = payload.status
    if payload.feedback is not None:
        interview.feedback = payload.feedback

    db.commit()
    db.refresh(interview)
    return interview


# ===================================================================
# DELETE /{id} — Cancel an interview
# ===================================================================

@router.delete("/{interview_id}", status_code=status.HTTP_200_OK)
async def cancel_interview(interview_id: int, db: Session = Depends(get_db)):
    """Cancel an interview.

    1. Marks interview status as 'cancelled'
    2. Pings n8n to delete the Google Calendar event
    3. Reverts the application stage to 'Screening'
    """
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found.")

    if interview.status == "cancelled":
        raise HTTPException(status_code=400, detail="Interview is already cancelled.")

    # --- Delete Google Calendar event via n8n ---
    if interview.google_event_id:
        n8n_payload = {
            "google_event_id": interview.google_event_id,
        }
        await _call_n8n_interview_webhook("delete", n8n_payload)

    # --- Update interview status ---
    interview.status = "cancelled"

    # --- Revert application stage ---
    application = db.query(Application).filter(Application.id == interview.application_id).first()
    if application and application.current_stage_id == FIRST_INTERVIEW_STAGE_ID:
        # Check if there are other active interviews for this application
        other_active = (
            db.query(Interview)
            .filter(
                Interview.application_id == interview.application_id,
                Interview.id != interview_id,
                Interview.status == "scheduled",
            )
            .first()
        )
        if not other_active:
            # No other scheduled interviews — revert to Screening
            application.current_stage_id = SCREENING_STAGE_ID

    db.commit()

    return {
        "message": f"Interview #{interview_id} cancelled.",
        "stage_reverted": application.current_stage_id == SCREENING_STAGE_ID if application else False,
    }
