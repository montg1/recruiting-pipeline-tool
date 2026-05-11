"""
Interview model — scheduled interviews with Google Meet links (Module 4).
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


class Interview(Base):
    __tablename__ = "interviews"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    application_id   = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    scheduled_at     = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=30)
    google_meet_link = Column(String(255), nullable=True)
    google_event_id  = Column(String(255), nullable=True, doc="Google Calendar event ID for update/delete")
    interviewer_id   = Column(Integer, ForeignKey("users.id"), nullable=True)
    status           = Column(String(16), nullable=False, default="scheduled",
                              doc="'scheduled' | 'completed' | 'cancelled'")
    feedback         = Column(Text, nullable=True)
    created_at       = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # --- relationships ---
    application = relationship("Application", back_populates="interviews")
    interviewer = relationship("User", back_populates="interviews")

    def __repr__(self):
        return f"<Interview app={self.application_id} at={self.scheduled_at}>"
