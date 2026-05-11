# Project Brief: Recruiting Pipeline Tool (3-Day Build)

## Overview
A Full Stack Recruiting Pipeline Tool designed for HR teams to manage the recruitment process, score resumes using AI, and schedule interviews automatically.

## Tech Stack
- **Frontend:** Vue 3 (Vite), Tailwind CSS, Vue Router, Pinia
- **Backend:** FastAPI (Python), SQLAlchemy ORM
- **Database:** PostgreSQL
- **AI Integration:** Claude API (Anthropic)
- **Calendar Integration:** Google Calendar API (Google Meet)

## Project Structure
```text
recruiting-pipeline-tool/
├── frontend/
│   ├── src/
│   │   ├── components/ (UI Components: ScoreCard, CandidateCard, etc.)
│   │   ├── views/ (Dashboard, CandidateDetail, Upload)
│   │   ├── services/ (API Calls)
│   │   └── store/ (State Management for Pipeline)
├── backend/
│   ├── api/ (Endpoints for Candidates, Resumes, Interviews)
│   ├── models/ (SQLAlchemy: Candidate, Job, Interview)
│   ├── schemas/ (Pydantic models)
│   └── services/ (Claude AI logic, Google Calendar logic, PDF parsing)
```

## Module Requirements

### Module 1: AI Resume Screener
- Upload PDF/Text resumes.
- Link candidates to specific Job Descriptions (JD).
- **AI Scoring:** Use Claude API to score (0-10) on:
    1. Skills fit
    2. Experience fit
    3. Culture/Communication fit
- **Output:** Structured score card with reasoning and "Prescreen questions".

### Module 2: Applicant Tracker (Priority 1)
- CRUD for Candidates (Name, Email, Phone, Source, Date).
- Pipeline Stages: Applied -> Screening -> Pre-Screen Call -> First Interview -> Offer -> Hired/Rejected.
- UI: Kanban or List view with Drag-and-drop or Stage-switching capability.
- Filtering by stage, position, or source.

### Module 3: Interview Scheduler
- Automated Google Meet creation.
- Conflict detection (prevent double-booking).
- Attach "Prescreen questions" from Module 1 into the calendar description.
- Status sync with Applicant Tracker.

## Development Guidelines
- **Clean Code:** Use clear naming conventions.
- **Architecture:** Keep business logic in `services/` and keep `api/` routes clean.
- **UX:** Focus on a simple, intuitive flow for HR users.
```
