"""
ResumeScore model — AI-generated scoring from Claude (Module 2).

overall_score is a computed column in PostgreSQL (GENERATED ALWAYS AS …).
In SQLAlchemy we map it as a read-only property instead.
"""

from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from database import Base


class ResumeScore(Base):
    __tablename__ = "resume_scores"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    application_id      = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    skills_score        = Column(Numeric(3, 1), nullable=True)
    experience_score    = Column(Numeric(3, 1), nullable=True)
    culture_score       = Column(Numeric(3, 1), nullable=True)
    # overall_score is a PostgreSQL generated column — we treat it as read-only here
    overall_score       = Column(Numeric(3, 1), nullable=True, doc="Computed: avg of the three scores (DB-generated)")
    reasoning           = Column(Text, nullable=True)
    prescreen_questions = Column(JSONB, nullable=True)
    model_version       = Column(String(64), nullable=True)
    scored_at           = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # --- relationships ---
    application = relationship("Application", back_populates="resume_scores")

    @hybrid_property
    def computed_overall(self):
        """Python-side fallback for the DB-generated overall_score."""
        scores = [s for s in (self.skills_score, self.experience_score, self.culture_score) if s is not None]
        return sum(scores) / len(scores) if scores else None

    def __repr__(self):
        return f"<ResumeScore app={self.application_id} overall={self.overall_score}>"
