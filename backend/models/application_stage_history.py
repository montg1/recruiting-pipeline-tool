"""
ApplicationStageHistory model — audit trail for stage transitions.

Rows are created by a PostgreSQL trigger (trg_log_stage_change)
or explicitly by the application layer.
"""

from sqlalchemy import Column, BigInteger, Integer, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


class ApplicationStageHistory(Base):
    __tablename__ = "application_stage_history"

    id             = Column(BigInteger, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    from_stage_id  = Column(Integer, ForeignKey("pipeline_stages.id"), nullable=True, doc="NULL on first entry")
    to_stage_id    = Column(Integer, ForeignKey("pipeline_stages.id"), nullable=False)
    moved_by       = Column(Integer, ForeignKey("users.id"), nullable=True)
    note           = Column(Text, nullable=True)
    moved_at       = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # --- relationships ---
    application = relationship("Application", back_populates="stage_history")
    from_stage  = relationship("PipelineStage", foreign_keys=[from_stage_id])
    to_stage    = relationship("PipelineStage", foreign_keys=[to_stage_id])
    moved_by_user = relationship("User", foreign_keys=[moved_by])

    def __repr__(self):
        return f"<StageHistory app={self.application_id} {self.from_stage_id}→{self.to_stage_id}>"
