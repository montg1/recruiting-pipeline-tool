"""
Automated tests for Module 3 — Applicant Tracker API.
Uses an in-memory SQLite database (no PostgreSQL required).
"""

import sys
import os

# Ensure backend directory is on the path
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# --- JSONB → JSON shim for SQLite (must be BEFORE any model import) ---
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):
    SQLiteTypeCompiler.visit_JSONB = SQLiteTypeCompiler.visit_JSON

# --- BigInteger → Integer shim for SQLite autoincrement support ---
from sqlalchemy.dialects.sqlite.base import SQLiteDDLCompiler
_orig_visit_create_column = SQLiteDDLCompiler.visit_create_column.__wrapped__ if hasattr(SQLiteDDLCompiler.visit_create_column, '__wrapped__') else None

import sqlalchemy as sa
_orig_BigInteger = sa.BigInteger

# Patch: when using SQLite, render BigInteger PKs as plain Integer
from sqlalchemy.dialects.sqlite import base as sqlite_base
_orig_get_col_spec = getattr(SQLiteTypeCompiler, 'visit_big_integer', None)
if not hasattr(SQLiteTypeCompiler, '_patched_bigint'):
    def visit_big_integer(self, type_, **kw):
        return "INTEGER"
    SQLiteTypeCompiler.visit_big_integer = visit_big_integer
    SQLiteTypeCompiler._patched_bigint = True

from database import Base, get_db
from main import app
from models.pipeline_stage import PipelineStage
from models.job import Job
from models.user import User

# ---------- Test DB setup (SQLite in-memory) ----------
TEST_DATABASE_URL = "sqlite://"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Enable foreign keys in SQLite
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Create tables
Base.metadata.create_all(bind=engine)

# ---------- Seed data ----------
db = TestingSessionLocal()

# Pipeline stages
stages = [
    PipelineStage(id=1, name="Applied",         order_index=1, is_terminal=False, stage_type="active"),
    PipelineStage(id=2, name="Screening",        order_index=2, is_terminal=False, stage_type="active"),
    PipelineStage(id=3, name="Pre-Screen Call",   order_index=3, is_terminal=False, stage_type="active"),
    PipelineStage(id=4, name="First Interview",   order_index=4, is_terminal=False, stage_type="active"),
    PipelineStage(id=5, name="Offer",             order_index=5, is_terminal=False, stage_type="active"),
    PipelineStage(id=6, name="Hired",             order_index=6, is_terminal=True,  stage_type="success"),
    PipelineStage(id=7, name="Rejected",          order_index=7, is_terminal=True,  stage_type="rejected"),
]
db.add_all(stages)

# A test job
job = Job(id=1, title="Backend Engineer", department="Engineering", status="open")
db.add(job)

db.commit()
db.close()

# ---------- Test client ----------
client = TestClient(app)

passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name} — {detail}")


print("=" * 60)
print("Module 3 — Applicant Tracker API Tests")
print("=" * 60)

# ------------------------------------------------------------------
# 1. GET /stages
# ------------------------------------------------------------------
print("\n--- Pipeline Stages ---")
r = client.get("/api/candidates/stages")
test("GET /stages returns 200", r.status_code == 200)
test("GET /stages returns 7 stages", len(r.json()) == 7, f"got {len(r.json())}")

# ------------------------------------------------------------------
# 2. POST / — Create candidate
# ------------------------------------------------------------------
print("\n--- Create Candidate ---")
r = client.post("/api/candidates/", json={
    "full_name": "Alice Johnson",
    "email": "alice@example.com",
    "phone": "+1234567890",
    "source": "LinkedIn",
})
test("POST / returns 201", r.status_code == 201, f"got {r.status_code}: {r.text}")
data = r.json()
test("Response has id", "id" in data)
test("full_name matches", data.get("full_name") == "Alice Johnson")
test("email matches", data.get("email") == "alice@example.com")
test("is_active is True", data.get("is_active") is True)
alice_id = data.get("id")

# Duplicate email
r = client.post("/api/candidates/", json={
    "full_name": "Alice Duplicate",
    "email": "alice@example.com",
})
test("Duplicate email returns 409", r.status_code == 409, f"got {r.status_code}")

# ------------------------------------------------------------------
# 3. GET / — List candidates
# ------------------------------------------------------------------
print("\n--- List Candidates ---")
# Create a second candidate
client.post("/api/candidates/", json={"full_name": "Bob Smith", "email": "bob@example.com", "source": "Referral"})

r = client.get("/api/candidates/")
test("GET / returns 200", r.status_code == 200)
test("GET / returns 2 candidates", len(r.json()) == 2, f"got {len(r.json())}")

# Filter by source
r = client.get("/api/candidates/?source=LinkedIn")
test("Filter source=LinkedIn returns 1", len(r.json()) == 1)

# Search by name
r = client.get("/api/candidates/?search=bob")
test("Search 'bob' returns 1", len(r.json()) == 1)
test("Search result is Bob", r.json()[0]["full_name"] == "Bob Smith")

# ------------------------------------------------------------------
# 4. GET /{id} — Get candidate detail
# ------------------------------------------------------------------
print("\n--- Get Candidate Detail ---")
r = client.get(f"/api/candidates/{alice_id}")
test("GET /{id} returns 200", r.status_code == 200)
test("Detail has applications list", "applications" in r.json())

r = client.get("/api/candidates/9999")
test("GET /9999 returns 404", r.status_code == 404)

# ------------------------------------------------------------------
# 5. PUT /{id} — Update candidate
# ------------------------------------------------------------------
print("\n--- Update Candidate ---")
r = client.put(f"/api/candidates/{alice_id}", json={"phone": "+9876543210", "source": "Referral"})
test("PUT /{id} returns 200", r.status_code == 200, f"got {r.status_code}: {r.text}")
test("Phone updated", r.json()["phone"] == "+9876543210")
test("Source updated", r.json()["source"] == "Referral")
test("Name unchanged", r.json()["full_name"] == "Alice Johnson")

# ------------------------------------------------------------------
# 6. POST /{id}/applications — Apply to a job
# ------------------------------------------------------------------
print("\n--- Create Application ---")
r = client.post(f"/api/candidates/{alice_id}/applications", json={"job_id": 1})
test("POST /applications returns 201", r.status_code == 201, f"got {r.status_code}: {r.text}")
app_data = r.json()
test("Application has id", "id" in app_data)
test("Stage defaults to Applied (1)", app_data.get("current_stage_id") == 1)
test("current_stage nested object present", app_data.get("current_stage") is not None)
test("current_stage name is Applied", app_data["current_stage"]["name"] == "Applied")
app_id = app_data["id"]

# Duplicate application
r = client.post(f"/api/candidates/{alice_id}/applications", json={"job_id": 1})
test("Duplicate application returns 409", r.status_code == 409, f"got {r.status_code}")

# ------------------------------------------------------------------
# 7. PATCH /{id}/applications/{app_id}/stage — Drag-and-drop
# ------------------------------------------------------------------
print("\n--- Update Stage (Drag-and-Drop) ---")
r = client.patch(
    f"/api/candidates/{alice_id}/applications/{app_id}/stage",
    json={"stage_id": 2, "kanban_position": 0, "note": "Looks promising"},
)
test("PATCH /stage returns 200", r.status_code == 200, f"got {r.status_code}: {r.text}")
test("Stage updated to Screening (2)", r.json()["current_stage_id"] == 2)
test("Stage name is Screening", r.json()["current_stage"]["name"] == "Screening")
test("Kanban position updated", r.json()["kanban_position"] == 0)

# Move to rejected
r = client.patch(
    f"/api/candidates/{alice_id}/applications/{app_id}/stage",
    json={"stage_id": 7, "note": "Not enough experience"},
)
test("Move to Rejected returns 200", r.status_code == 200)
test("Stage is Rejected (7)", r.json()["current_stage_id"] == 7)
test("rejected_reason set", r.json()["rejected_reason"] == "Not enough experience")

# Verify detail shows application with updated stage
r = client.get(f"/api/candidates/{alice_id}")
test("Detail shows updated stage", r.json()["applications"][0]["current_stage_id"] == 7)

# ------------------------------------------------------------------
# 8. DELETE /{id} — Soft delete
# ------------------------------------------------------------------
print("\n--- Delete Candidate (Soft) ---")
r = client.delete(f"/api/candidates/{alice_id}")
test("DELETE returns 204", r.status_code == 204, f"got {r.status_code}")

r = client.get(f"/api/candidates/{alice_id}")
test("GET after delete returns 404", r.status_code == 404)

r = client.get("/api/candidates/")
test("List no longer includes deleted", len(r.json()) == 1)

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)

if failed > 0:
    sys.exit(1)
