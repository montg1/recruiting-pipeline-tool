"""
Recruiting Pipeline Tool — FastAPI Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Recruiting Pipeline Tool",
    description="API for managing recruitment pipeline, AI resume screening, and interview scheduling.",
    version="0.1.0",
)

# CORS — allow Vue dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Recruiting Pipeline Tool API is running."}


# -------------------------------------------------------------------
# Register routers
# -------------------------------------------------------------------
from api.candidates import router as candidates_router

app.include_router(candidates_router, prefix="/api/candidates", tags=["Candidates"])

from api.scraper import router as scraper_router

app.include_router(scraper_router, prefix="/api/scraper", tags=["Scraper (n8n)"])

# Uncomment as each module is implemented:
from api.resumes import router as resumes_router

app.include_router(resumes_router, prefix="/api/resumes", tags=["Resumes (AI Screener)"])

from api.jobs import router as jobs_router

app.include_router(jobs_router, prefix="/api/jobs", tags=["Jobs"])

# from api.interviews import router as interviews_router
# app.include_router(interviews_router, prefix="/api/interviews", tags=["Interviews"])


