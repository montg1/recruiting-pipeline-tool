"""
Dev server — runs FastAPI with in-memory SQLite and seed data.
Usage: python dev_server.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# Patch SQLite to support JSONB + BigInteger before any model import
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):
    SQLiteTypeCompiler.visit_JSONB = SQLiteTypeCompiler.visit_JSON
if not hasattr(SQLiteTypeCompiler, "_patched_bigint"):
    def visit_big_integer(self, type_, **kw):
        return "INTEGER"
    SQLiteTypeCompiler.visit_big_integer = visit_big_integer
    SQLiteTypeCompiler._patched_bigint = True

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models.pipeline_stage import PipelineStage
from models.job import Job
from models.user import User
from models.candidate import Candidate
from models.application import Application
from models.application_stage_history import ApplicationStageHistory

# --- SQLite engine ---
engine = create_engine("sqlite:///", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@event.listens_for(engine, "connect")
def _fk(conn, _):
    conn.cursor().execute("PRAGMA foreign_keys=ON")

def override_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_db
Base.metadata.create_all(bind=engine)

# --- Seed ---
db = TestSession()

stages = [
    PipelineStage(id=1, name="Applied",        order_index=1, is_terminal=False, stage_type="active",   color_hex="#3B82F6"),
    PipelineStage(id=2, name="Screening",       order_index=2, is_terminal=False, stage_type="active",   color_hex="#8B5CF6"),
    PipelineStage(id=3, name="Pre-Screen Call",  order_index=3, is_terminal=False, stage_type="active",   color_hex="#EC4899"),
    PipelineStage(id=4, name="First Interview",  order_index=4, is_terminal=False, stage_type="active",   color_hex="#F97316"),
    PipelineStage(id=5, name="Offer",            order_index=5, is_terminal=False, stage_type="active",   color_hex="#14B8A6"),
    PipelineStage(id=6, name="Hired",            order_index=6, is_terminal=True,  stage_type="success",  color_hex="#22C55E"),
    PipelineStage(id=7, name="Rejected",         order_index=7, is_terminal=True,  stage_type="rejected", color_hex="#EF4444"),
]
db.add_all(stages)

job = Job(id=1, title="Backend Engineer", department="Engineering", status="open")
db.add(job)

# Seed candidates across various stages
seed = [
    {"name": "Somchai Prasert",     "email": "somchai@email.com",     "source": "LinkedIn",  "stage": 1},
    {"name": "Naree Thongsuk",      "email": "naree@email.com",      "source": "Referral",  "stage": 1},
    {"name": "Patchara Wongchai",   "email": "patchara@email.com",   "source": "LinkedIn",  "stage": 2},
    {"name": "Arisa Kittisak",      "email": "arisa@email.com",      "source": "Job Board", "stage": 2},
    {"name": "Thanakorn Srisuk",    "email": "thanakorn@email.com",  "source": "LinkedIn",  "stage": 3},
    {"name": "Wipada Chaiwat",      "email": "wipada@email.com",     "source": "Referral",  "stage": 4},
    {"name": "Kritsana Meechai",    "email": "kritsana@email.com",   "source": "n8n_scrape","stage": 4},
    {"name": "Siriporn Lertpanya",  "email": "siriporn@email.com",   "source": "LinkedIn",  "stage": 5},
    {"name": "Natthawut Jaidee",    "email": "natthawut@email.com",  "source": "Referral",  "stage": 6},
    {"name": "Kanokporn Suthep",    "email": "kanokporn@email.com",  "source": "Job Board", "stage": 7},
]

for i, s in enumerate(seed, start=1):
    c = Candidate(id=i, full_name=s["name"], email=s["email"], source=s["source"])
    db.add(c)
    db.flush()
    a = Application(id=i, candidate_id=i, job_id=1, current_stage_id=s["stage"], kanban_position=0)
    db.add(a)
    db.flush()
    h = ApplicationStageHistory(application_id=i, from_stage_id=None, to_stage_id=s["stage"])
    db.add(h)

db.commit()
db.close()

print(f"\nSeeded {len(seed)} candidates across {len(stages)} stages")
print("Starting dev server at http://localhost:8000 ...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
