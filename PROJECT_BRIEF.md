# Project Brief: Recruiting Pipeline Tool (Hybrid Architecture: FastAPI + n8n)

## Overview
A Full Stack Recruiting Pipeline Tool designed for HR teams. This project utilizes a **Hybrid Architecture**: 
1. **Core Backend (FastAPI):** Handles business logic, database management, AI Resume Scoring (Mod 2), and Interview Scheduling (Mod 4).
2. **Automation Microservice (n8n):** Handles the messy data scraping and normalization process via Webhooks (Mod 1).

## Tech Stack
- **Frontend:** Vue 3 (Vite), Tailwind CSS, Vue Router
- **Core Backend:** FastAPI (Python), SQLAlchemy ORM
- **Database:** PostgreSQL
- **Automation Service:** n8n (for Webhooks, HTTP Scraping, and AI Normalization)
- **AI Integration:** Claude API (Anthropic)
- **Calendar Integration:** Google Calendar API (Google Meet)

## Project Structure
```text
recruiting-pipeline-tool/
├── frontend/
│   ├── src/ components, views, services
├── backend/
│   ├── api/ (candidates.py, resumes.py, interviews.py, scraper_webhook.py)
│   ├── models/ (Candidate, Job, Interview)
│   ├── schemas/ 
│   └── services/ (claude_ai.py, google_meet.py)
└── n8n_workflows/
    └── Candidate_Scraper_Workflow.json (Exported n8n workflow)
```

## Module Requirements

### Module 1: Candidate Data Scraper (n8n Microservice)
- **Flow:** Frontend sends URL/Text to FastAPI -> FastAPI forwards payload to **n8n Webhook**.
- **n8n Logic:** Scrape raw text -> Send to Claude API Node to normalize into JSON -> Return JSON to FastAPI via Webhook Response.
- **UI:** Show a "Preview" for HR to review/edit before saving to the Tracker.

### Module 2: AI Resume Screener (FastAPI Core)
- Upload PDF/Text resumes. Link to specific JD.
- **FastAPI Logic:** Parse PDF, call Claude API directly via Python to score (0-10) on Skills, Experience, Culture. Include reasoning.
- **Output:** Score card with "Prescreen questions".

### Module 3: Applicant Tracker (FastAPI Core)
- CRUD for Candidates.
- Pipeline Stages: Applied -> Screening -> Pre-Screen Call -> First Interview -> Offer -> Hired/Rejected.
- UI: Kanban board with Drag-and-drop.

### Module 4: Interview Scheduler (FastAPI Core)
- Automated Google Meet creation.
- Conflict detection (prevent double-booking) handled in FastAPI.
- Auto-update status in Applicant Tracker.

## Evaluation Focus
- **Architecture (30%):** Demonstrating the ability to separate concerns (Heavy lifting in FastAPI, Data munging in n8n).
- **Code Quality (30%):** Clean FastAPI codebase.
- **UX (25%):** Smooth HR workflow.
- **AI Integration (15%):** Effective prompting in both n8n and Python.
