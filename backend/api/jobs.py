"""
Jobs API — list open job positions for the CV screener dropdown.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.job import Job

router = APIRouter()


@router.get("/", summary="List all open jobs")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.status == "open").all()
    return [
        {
            "id": j.id,
            "title": j.title,
            "department": j.department,
            "description": j.description,
            "requirements": j.requirements,
        }
        for j in jobs
    ]
