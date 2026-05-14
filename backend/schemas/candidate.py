"""
Pydantic schemas for Candidate request/response validation.
"""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, EmailStr, ConfigDict


# ---------------------------------------------------------------------------
# Candidate schemas
# ---------------------------------------------------------------------------

class CandidateCreate(BaseModel):
    """Body for POST /candidates — create a new candidate."""
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    source: Optional[str] = None


class CandidateUpdate(BaseModel):
    """Body for PUT /candidates/{id} — update candidate details.
    All fields optional so the client only sends what changed."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    source: Optional[str] = None
    resume_path: Optional[str] = None
    resume_text: Optional[str] = None
    parsed_data: Optional[dict[str, Any]] = None


class CandidateResponse(BaseModel):
    """Serialised candidate returned from the API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    source: Optional[str] = None
    resume_path: Optional[str] = None
    resume_text: Optional[str] = None
    parsed_data: Optional[dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Application (Kanban card) schemas
# ---------------------------------------------------------------------------

class ApplicationCreate(BaseModel):
    """Body for POST /candidates/{id}/applications — apply candidate to a job."""
    job_id: int
    stage_id: Optional[int] = None          # defaults to "Applied" (id=1) if omitted
    assigned_to: Optional[int] = None


class StageUpdate(BaseModel):
    """Body for PATCH /candidates/{id}/applications/{app_id}/stage
    — used by the frontend drag-and-drop."""
    stage_id: int
    kanban_position: Optional[int] = None   # vertical order in the new column
    moved_by: Optional[int] = None          # user id who performed the move
    note: Optional[str] = None              # optional transition note


class PipelineStageResponse(BaseModel):
    """Serialised pipeline stage."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    order_index: int
    is_terminal: bool
    stage_type: str
    color_hex: Optional[str] = None


class ApplicationResponse(BaseModel):
    """Serialised application (Kanban card) returned from the API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    job_id: int
    current_stage_id: int
    current_stage: Optional[PipelineStageResponse] = None
    applied_at: datetime
    rejected_reason: Optional[str] = None
    kanban_position: int
    assigned_to: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Interview data (from the most recent scheduled interview)
    google_meet_link: Optional[str] = None
    next_interview_at: Optional[datetime] = None


class CandidateDetailResponse(CandidateResponse):
    """Extended response that nests applications for detail views."""
    applications: list[ApplicationResponse] = []
