"""
Pydantic schemas for Interview request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Interview schemas
# ---------------------------------------------------------------------------

class InterviewCreate(BaseModel):
    """Body for POST /interviews — schedule a new interview."""
    application_id: int
    scheduled_at: datetime
    duration_minutes: int = 30
    interviewer_id: Optional[int] = None


class InterviewUpdate(BaseModel):
    """Body for PUT /interviews/{id} — reschedule or update an interview."""
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    interviewer_id: Optional[int] = None
    status: Optional[str] = None
    feedback: Optional[str] = None


class InterviewResponse(BaseModel):
    """Serialised interview returned from the API."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    scheduled_at: datetime
    duration_minutes: int
    google_meet_link: Optional[str] = None
    google_event_id: Optional[str] = None
    interviewer_id: Optional[int] = None
    status: str
    feedback: Optional[str] = None
    created_at: datetime
