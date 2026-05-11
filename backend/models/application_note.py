"""
ApplicationNote model — free-form recruiter comments on an application.
"""

from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


class ApplicationNote(Base):
    __tablename__ = "application_notes"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    author_id      = Column(Integer, ForeignKey("users.id"), nullable=True)
    body           = Column(Text, nullable=False)
    created_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # --- relationships ---
    application = relationship("Application", back_populates="notes")
    author      = relationship("User", back_populates="notes")

    def __repr__(self):
        return f"<ApplicationNote app={self.application_id} by={self.author_id}>"
