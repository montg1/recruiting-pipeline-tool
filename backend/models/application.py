"""
Application model — the Kanban card (Module 3).

One row = one candidate's pipeline journey for one job.
The composite UNIQUE(candidate_id, job_id) prevents duplicate applications.
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


class Application(Base):
    __tablename__ = "applications"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id     = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    job_id           = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    current_stage_id = Column(Integer, ForeignKey("pipeline_stages.id"), nullable=False)
    applied_at       = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    rejected_reason  = Column(String(255), nullable=True, doc="Set when stage = Rejected")
    kanban_position  = Column(Integer, nullable=False, default=0, doc="Vertical order inside a Kanban column")
    assigned_to      = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active        = Column(Boolean, nullable=False, default=True, doc="Soft-delete flag")
    created_at       = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # --- constraints ---
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_candidate_job"),
    )

    # --- relationships ---
    candidate      = relationship("Candidate", back_populates="applications")
    job            = relationship("Job", back_populates="applications")
    current_stage  = relationship("PipelineStage", back_populates="applications", foreign_keys=[current_stage_id])
    assigned_user  = relationship("User", back_populates="assignments", foreign_keys=[assigned_to])
    stage_history  = relationship("ApplicationStageHistory", back_populates="application", cascade="all, delete-orphan",
                                  order_by="ApplicationStageHistory.moved_at")
    resume_scores  = relationship("ResumeScore", back_populates="application", cascade="all, delete-orphan")
    interviews     = relationship("Interview", back_populates="application", cascade="all, delete-orphan")
    notes          = relationship("ApplicationNote", back_populates="application", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Application candidate={self.candidate_id} job={self.job_id} stage={self.current_stage_id}>"
