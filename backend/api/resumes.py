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


# ---------- Claude AI Scoring ----------
SCORING_PROMPT = """You are an expert HR recruiter and resume screener.

**Job Title:** {job_title}

**Job Description:**
{job_description}

**Job Requirements:**
{job_requirements}

**Candidate Resume Text:**
{resume_text}

---

Evaluate this candidate for the job above. You MUST return ONLY valid JSON (no markdown, no explanation outside JSON). Use this exact schema:

{{
  "skills_score": <number 0-10>,
  "experience_score": <number 0-10>,
  "culture_score": <number 0-10>,
  "overall_score": <number 0-10>,
  "reasoning": "<2-4 sentence summary of your evaluation>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>"],
  "prescreen_questions": [
    "<question 1 to ask in phone screen>",
    "<question 2>",
    "<question 3>"
  ]
}}

Scoring guide:
- skills_score: How well do the candidate's technical skills match the requirements?
- experience_score: How relevant is their work experience to this role?
- culture_score: Based on communication style, interests, and overall presentation.
- overall_score: Weighted average (skills 40%, experience 40%, culture 20%).

Return ONLY the JSON object. No markdown fences, no extra text."""


async def score_resume_with_claude(
    resume_text: str,
    job_title: str,
    job_description: str,
    job_requirements: str,
) -> dict:
    """Call Claude API to score the resume against the job description."""
    import anthropic

    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY is not configured."
        )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = SCORING_PROMPT.format(
        job_title=job_title,
        job_description=job_description or "Not provided",
        job_requirements=job_requirements or "Not provided",
        resume_text=resume_text[:8000],  # Limit to avoid token overflow
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_response = message.content[0].text.strip()

    # Parse the JSON response from Claude
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown fences if Claude wrapped it
        import re
        match = re.search(r'\{[\s\S]*\}', raw_response)
        if match:
            return json.loads(match.group())
        raise HTTPException(
            status_code=500,
            detail=f"Claude returned invalid JSON: {raw_response[:300]}"
        )


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
    except Exception:
        raise HTTPException(status_code=422, detail="Failed to parse the PDF file.")

    # Fetch job from DB
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with id {job_id} not found.")

    # Call Claude
    evaluation = await score_resume_with_claude(
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
