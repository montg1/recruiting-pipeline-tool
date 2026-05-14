"""
Module 2 — AI Resume Screener API

Accepts a PDF upload + job_id, extracts text, calls Claude for scoring,
and returns a structured evaluation.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
import json

from database import get_db
from config import settings
from models.job import Job

router = APIRouter()


# ---------- PDF Text Extraction ----------
def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF using PyPDF2."""
    from PyPDF2 import PdfReader
    import io

    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    full_text = "\n\n".join(pages).strip()
    if not full_text:
        raise ValueError("Could not extract any text from the PDF.")
    return full_text


# ---------- Claude AI Scoring via n8n ----------


async def score_resume_with_n8n(
    resume_text: str,
    job_title: str,
    job_description: str,
    job_requirements: str,
) -> dict:
    """Send extracted resume text and job details to n8n webhook for Claude scoring."""
    import httpx

    webhook_url = settings.n8n_webhook_url
    if not webhook_url:
        raise HTTPException(
            status_code=500,
            detail="N8N_WEBHOOK_URL is not configured."
        )

    payload = {
        "type": "resume_screen",
        "job_title": job_title,
        "job_description": job_description or "Not provided",
        "job_requirements": job_requirements or "Not provided",
        "resume_text": resume_text[:8000] # Limit to avoid massive payloads
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"n8n webhook error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to n8n webhook: {str(e)}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="n8n returned invalid JSON.")


# ---------- API Endpoint ----------
@router.post("/screen", summary="Screen a resume against a job description using Claude AI")
async def screen_resume(
    file: UploadFile = File(..., description="PDF resume file"),
    job_id: int = Form(..., description="Job ID to match against"),
    db: Session = Depends(get_db),
):
    """
    1. Accepts a PDF file upload and job_id
    2. Extracts text from the PDF
    3. Fetches the job description from the database
    4. Calls Claude AI for scoring
    5. Returns the structured evaluation
    """

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Read file
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")

    # Extract text
    try:
        resume_text = extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=422, detail=f"Failed to parse the PDF file: {str(e)}")

    # Fetch job from DB
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with id {job_id} not found.")

    # Call n8n webhook
    evaluation = await score_resume_with_n8n(
        resume_text=resume_text,
        job_title=job.title,
        job_description=job.description,
        job_requirements=job.requirements,
    )

    # Return the evaluation with metadata
    return {
        "job_id": job_id,
        "job_title": job.title,
        "resume_filename": file.filename,
        "resume_text_length": len(resume_text),
        "evaluation": evaluation,
    }
