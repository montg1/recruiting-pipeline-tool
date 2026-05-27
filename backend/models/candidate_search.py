"""
CandidateSearch model — Module 1 staging.

One row = one "search from JD" run. Stores the ranked shortlist of *leads*
discovered across sources (GitHub, LinkedIn, …) BEFORE any HR approval.
Approved leads are promoted into Candidate + Application; the rest live here
only. Kept out of `candidates` because scraped leads usually lack an email
(candidates.email is NOT NULL UNIQUE) and aren't pipeline members yet.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


class CandidateSearch(Base):
    __tablename__ = "candidate_searches"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    job_id       = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True,
                          doc="The JD (job requisition) this search was run for")
    criteria     = Column(JSONB, nullable=True, doc="Snapshot of parsed criteria used for this run")
    sources      = Column(JSONB, nullable=True, doc='Adapters that ran, e.g. ["github", "linkedin"]')
    queries      = Column(JSONB, nullable=True, doc="Actual query string sent to each source")
    results      = Column(JSONB, nullable=False, default=list,
                          doc="Ranked leads incl. match_score / reasons / status")
    result_count = Column(Integer, nullable=False, default=0)
    status       = Column(String(16), nullable=False, default="completed",
                          doc="'completed' | 'partial' | 'failed'")
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # --- relationships ---
    job = relationship("Job")

    def __repr__(self):
        return f"<CandidateSearch id={self.id} job={self.job_id} results={self.result_count}>"
