"""
Module 3 — Applicant Tracker: Candidate & Application CRUD endpoints.

Routes
------
Candidates
  POST   /                                    Create candidate
  GET    /                                    List candidates (filtering, pagination)
  GET    /{candidate_id}                      Get candidate detail (with applications)
  PUT    /{candidate_id}                      Update candidate info
  DELETE /{candidate_id}                      Soft-delete candidate

Applications (nested under candidate)
  POST   /{candidate_id}/applications                     Apply to a job
  PATCH  /{candidate_id}/applications/{app_id}/stage      Move stage (drag-and-drop)

Pipeline stages (read-only lookup)
  GET    /stages                              List all pipeline stages
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.candidate import Candidate
from models.application import Application
from models.application_stage_history import ApplicationStageHistory
from models.pipeline_stage import PipelineStage
from schemas.candidate import (
    CandidateCreate,
    CandidateUpdate,
    CandidateResponse,
    CandidateDetailResponse,
    ApplicationCreate,
    ApplicationResponse,
    StageUpdate,
    PipelineStageResponse,
)

router = APIRouter()

DEFAULT_APPLIED_STAGE_ID = 1  # "Applied" stage — first seeded row


# ===================================================================
# Pipeline stages (read-only)
# ===================================================================

@router.get("/stages", response_model=list[PipelineStageResponse])
def list_stages(db: Session = Depends(get_db)):
    """Return all pipeline stages ordered by their Kanban column index."""
    return (
        db.query(PipelineStage)
        .order_by(PipelineStage.order_index)
        .all()
    )


# ===================================================================
# Candidate CRUD
# ===================================================================

@router.post("/", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db)):
    """Create a new candidate record."""
    # Check for duplicate email
    existing = db.query(Candidate).filter(Candidate.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Candidate with email '{payload.email}' already exists.",
        )

    candidate = Candidate(**payload.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/", response_model=list[CandidateResponse])
def list_candidates(
    # --- filters ---
    source: Optional[str] = Query(None, description="Filter by source (e.g. LinkedIn, Referral)"),
    search: Optional[str] = Query(None, description="Search by name or email (case-insensitive)"),
    is_active: bool = Query(True, description="Filter by active status"),
    # --- pagination ---
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List candidates with optional filtering and pagination."""
    query = db.query(Candidate).filter(Candidate.is_active == is_active)

    if source:
        query = query.filter(Candidate.source == source)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            sa_func.lower(Candidate.full_name).like(sa_func.lower(pattern))
            | sa_func.lower(Candidate.email).like(sa_func.lower(pattern))
        )

    query = query.order_by(Candidate.created_at.desc())
    return query.offset(skip).limit(limit).all()


@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Get a single candidate with their applications (Kanban cards)."""
    candidate = (
        db.query(Candidate)
        .options(
            joinedload(Candidate.applications).joinedload(Application.current_stage)
        )
        .filter(Candidate.id == candidate_id, Candidate.is_active == True)  # noqa: E712
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return candidate


@router.put("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    candidate_id: int,
    payload: CandidateUpdate,
    db: Session = Depends(get_db),
):
    """Update candidate details (name, email, phone, etc.)."""
    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id, Candidate.is_active == True)  # noqa: E712
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    # Only update fields that were explicitly sent
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(candidate, field, value)

    db.commit()
    db.refresh(candidate)
    return candidate


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Soft-delete a candidate (sets is_active = False)."""
    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id, Candidate.is_active == True)  # noqa: E712
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    candidate.is_active = False
    # Also deactivate all their applications
    for app in candidate.applications:
        app.is_active = False
    db.commit()
    return None


# ===================================================================
# Application (Kanban card) endpoints
# ===================================================================

@router.post(
    "/{candidate_id}/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_application(
    candidate_id: int,
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
):
    """Apply a candidate to a job — creates a new Kanban card."""
    # Validate candidate exists
    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id, Candidate.is_active == True)  # noqa: E712
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    # Check for duplicate application (same candidate + same job)
    existing = (
        db.query(Application)
        .filter(
            Application.candidate_id == candidate_id,
            Application.job_id == payload.job_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate has already applied to this job.",
        )

    stage_id = payload.stage_id or DEFAULT_APPLIED_STAGE_ID

    # Validate stage exists
    stage = db.query(PipelineStage).filter(PipelineStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=400, detail=f"Pipeline stage {stage_id} not found.")

    application = Application(
        candidate_id=candidate_id,
        job_id=payload.job_id,
        current_stage_id=stage_id,
        assigned_to=payload.assigned_to,
    )
    db.add(application)
    db.flush()  # get application.id for the history row

    # Record initial stage in history
    history = ApplicationStageHistory(
        application_id=application.id,
        from_stage_id=None,  # first entry
        to_stage_id=stage_id,
        moved_by=payload.assigned_to,
    )
    db.add(history)
    db.commit()
    db.refresh(application)

    # Eager-load the stage relationship for the response
    db.refresh(application, attribute_names=["current_stage"])
    return application


@router.patch(
    "/{candidate_id}/applications/{app_id}/stage",
    response_model=ApplicationResponse,
)
def update_application_stage(
    candidate_id: int,
    app_id: int,
    payload: StageUpdate,
    db: Session = Depends(get_db),
):
    """Move an application to a new pipeline stage.

    This is the endpoint the frontend drag-and-drop calls.
    It also records the transition in the stage history audit trail.
    """
    application = (
        db.query(Application)
        .options(joinedload(Application.current_stage))
        .filter(
            Application.id == app_id,
            Application.candidate_id == candidate_id,
            Application.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    # Validate target stage
    new_stage = db.query(PipelineStage).filter(PipelineStage.id == payload.stage_id).first()
    if not new_stage:
        raise HTTPException(status_code=400, detail=f"Pipeline stage {payload.stage_id} not found.")

    old_stage_id = application.current_stage_id

    # --- Update stage ---
    application.current_stage_id = payload.stage_id

    if payload.kanban_position is not None:
        application.kanban_position = payload.kanban_position

    # Set rejected_reason when moving to a rejected stage
    if new_stage.stage_type == "rejected" and payload.note:
        application.rejected_reason = payload.note

    # --- Write audit trail ---
    # Only record if stage actually changed (not just a reorder)
    if old_stage_id != payload.stage_id:
        history = ApplicationStageHistory(
            application_id=app_id,
            from_stage_id=old_stage_id,
            to_stage_id=payload.stage_id,
            moved_by=payload.moved_by,
            note=payload.note,
        )
        db.add(history)

    db.commit()
    db.refresh(application)
    db.refresh(application, attribute_names=["current_stage"])
    return application
