"""
Job model — open requisitions / job descriptions.
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


class Job(Base):
    __tablename__ = "jobs"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    title        = Column(String(128), nullable=False)
    department   = Column(String(64), nullable=True)
    description  = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    status       = Column(String(16), nullable=False, default="open", doc="'open' | 'on_hold' | 'closed'")
    owner_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # --- relationships ---
    owner        = relationship("User", back_populates="owned_jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Job {self.title!r}>"
