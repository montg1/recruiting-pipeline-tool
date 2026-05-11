"""
Lookup table for pipeline stages (Kanban columns).

Seeded rows:
  Applied → Screening → Pre-Screen Call → First Interview → Offer → Hired / Rejected
"""

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship

from database import Base


class PipelineStage(Base):
    __tablename__ = "pipeline_stages"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(64), nullable=False, unique=True)
    order_index = Column(Integer, nullable=False, doc="Column order on the Kanban board")
    is_terminal = Column(Boolean, nullable=False, default=False)
    stage_type  = Column(String(16), nullable=False, doc="'active' | 'success' | 'rejected'")
    color_hex   = Column(String(7), nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # --- relationships ---
    applications = relationship("Application", back_populates="current_stage", foreign_keys="Application.current_stage_id")

    def __repr__(self):
        return f"<PipelineStage {self.name!r}>"
