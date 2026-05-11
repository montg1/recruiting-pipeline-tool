"""
Candidate model — people in the recruiting funnel.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    full_name    = Column(String(128), nullable=False)
    email        = Column(String(255), nullable=False, unique=True)
    phone        = Column(String(32), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    source       = Column(String(64), nullable=True, doc="'LinkedIn' | 'Referral' | 'n8n_scrape' | …")
    resume_path  = Column(String(512), nullable=True, doc="Filesystem path or S3 key")
    resume_text  = Column(Text, nullable=True, doc="Parsed plaintext — Module 2 input")
    parsed_data  = Column(JSONB, nullable=True, doc="Normalized JSON from n8n scraper (Module 1)")
    is_active    = Column(Boolean, nullable=False, default=True, doc="Soft-delete flag")
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # --- relationships ---
    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Candidate {self.full_name!r}>"
