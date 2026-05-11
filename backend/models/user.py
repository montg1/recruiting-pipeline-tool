"""
User model — recruiters, hiring managers, and admins.
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    email     = Column(String(255), nullable=False, unique=True)
    full_name = Column(String(128), nullable=False)
    role      = Column(String(32), nullable=False, doc="'recruiter' | 'hiring_manager' | 'admin'")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # --- relationships ---
    owned_jobs   = relationship("Job", back_populates="owner")
    assignments  = relationship("Application", back_populates="assigned_user", foreign_keys="Application.assigned_to")
    interviews   = relationship("Interview", back_populates="interviewer")
    notes        = relationship("ApplicationNote", back_populates="author")

    def __repr__(self):
        return f"<User {self.email!r}>"
