# RecruitPipe — AI-Powered Recruiting Pipeline Tool

A full-stack recruiting pipeline tool for HR teams. Combines a **FastAPI** core backend with an **n8n** automation microservice for a clean separation between business logic and data-munging workflows.

**Live Demo:** [frontend-sigma-seven-85.vercel.app](https://frontend-sigma-seven-85.vercel.app)
**Backend API:** [recruiting-pipeline-tool.onrender.com](https://recruiting-pipeline-tool.onrender.com)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        HR User (Browser)                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              Frontend  (Vue 3 + Vite + Tailwind CSS)            │
│                    Deployed on Vercel                           │
│                                                                 │
│  /           → Kanban Pipeline Board (drag & drop)              │
│  /scraper    → Candidate Data Scraper (URL / raw text)          │
│  /cv-screener → AI Resume Screener (PDF upload)                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP / REST  (/api/*)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│             Core Backend  (FastAPI + SQLAlchemy)                │
│                    Deployed on Render                           │
│                                                                 │
│  Module 1 → /api/scraper/extract      (proxy to n8n)            │
│  Module 2 → /api/resumes/screen       (PDF parse → n8n → AI)    │
│  Module 3 → /api/candidates/*         (full CRUD + Kanban)      │
│  Module 4 → /api/interviews/*         (scheduling + conflicts)  │
│             /api/jobs/                                          │
└───────────┬────────────────────────┬────────────────────────────┘
            │                        │
            ▼                        ▼
┌───────────────────┐    ┌───────────────────────────────────────┐
│  PostgreSQL DB    │    │      n8n Automation Cloud             │
│  (Supabase)       │    │                                       │
│                   │    │  Workflow 1: Scrape URL → Claude AI   │
│  9 tables         │    │             → normalize JSON          │
│  (candidates,     │    │  Workflow 2: PDF text + JD → Claude   │
│   applications,   │    │             → score JSON              │
│   interviews,     │    │  Workflow 3: Create Google Calendar   │
│   ...)            │    │             event → return Meet link  │
└───────────────────┘    └───────────────────────────────────────┘
```

### Architecture Decision: Why FastAPI + n8n?

| Concern | Where it lives | Why |
|---|---|---|
| Business logic, CRUD, validation | **FastAPI** | Python is fast to write, easy to test, type-safe via Pydantic |
| Web scraping & HTML parsing | **n8n** | Scraping is brittle; isolating it means backend never breaks when LinkedIn changes its DOM |
| Claude AI prompting for resumes | **n8n** | Non-engineers can edit the prompt in the n8n UI without touching Python code |
| Google Calendar / Meet creation | **n8n** | OAuth token management and API retries are handled visually, not in code |
| Conflict detection & DB writes | **FastAPI** | Requires transactional guarantees that n8n cannot provide |

The FastAPI backend is the **source of truth** for all data. n8n is a **stateless processing microservice** — it receives a payload, does work, and returns a result. It never writes to the database directly.

---

## Project Structure

```
recruiting-pipeline-tool/
├── frontend/                        # Vue 3 + Vite + Tailwind CSS
│   ├── src/
│   │   ├── views/
│   │   │   ├── DashboardView.vue    # Kanban board
│   │   │   ├── ScraperView.vue      # Module 1 UI
│   │   │   └── CVUploadView.vue     # Module 2 UI
│   │   ├── components/
│   │   │   ├── CandidateCard.vue    # Draggable Kanban card
│   │   │   ├── CandidateModal.vue   # Slide-over detail / edit / delete
│   │   │   ├── AddCandidateModal.vue
│   │   │   └── ScoreCard.vue        # AI evaluation display
│   │   ├── stores/pipeline.js       # Pinia store (stages + candidates)
│   │   ├── services/api.js          # Axios instance
│   │   └── router/index.js
│   ├── vercel.json                  # SPA routing + API proxy rewrite
│   └── .env.example
│
├── backend/                         # FastAPI (Python 3.12)
│   ├── api/
│   │   ├── candidates.py            # Module 3 — full CRUD + stage PATCH
│   │   ├── resumes.py               # Module 2 — PDF upload → n8n
│   │   ├── scraper.py               # Module 1 — URL/text → n8n
│   │   ├── interviews.py            # Module 4 — scheduling + conflicts
│   │   └── jobs.py                  # Job listings
│   ├── models/                      # SQLAlchemy ORM models (9 tables)
│   │   ├── candidate.py
│   │   ├── application.py           # The Kanban "card" entity
│   │   ├── application_stage_history.py
│   │   ├── interview.py
│   │   ├── resume_score.py
│   │   ├── job.py
│   │   ├── pipeline_stage.py
│   │   ├── user.py
│   │   └── application_note.py
│   ├── schemas/                     # Pydantic request/response schemas
│   ├── services/
│   │   ├── claude_ai.py             # Anthropic SDK helper
│   │   └── google_meet.py           # Google Calendar helper
│   ├── database.py                  # SQLAlchemy engine (Supabase pooler aware)
│   ├── config.py                    # pydantic-settings
│   ├── main.py                      # FastAPI app + CORS + router registration
│   ├── init_db.py                   # One-time DB schema creation script
│   ├── seed_supabase.py             # Seeds pipeline stages + sample jobs
│   ├── dev_server.py                # Local SQLite dev server with seed data
│   ├── schema.sql                   # Raw SQL schema reference
│   └── requirements.txt
│
├── n8n_workflows/
│   └── Candidate_Scraper_Workflow.json
│
├── .github/workflows/ci.yml         # GitHub Actions: test + build on push
└── .gitignore                       # test/ folder excluded from git
```

---

## Modules

### Module 1 — Candidate Data Scraper
HR pastes a LinkedIn URL or raw profile text. FastAPI forwards it to an **n8n webhook** which scrapes the page, feeds the raw text to Claude AI for normalization, and returns structured JSON (name, skills, experience). HR reviews and edits the result before saving.

### Module 2 — AI Resume Screener
HR uploads a PDF CV and selects a job position. FastAPI extracts the text with **PyPDF2**, fetches the job description from the DB, and forwards both to **n8n** where Claude AI scores the candidate 0–10 on Skills, Experience, and Culture fit. Returns a scorecard with reasoning and prescreen interview questions.

### Module 3 — Applicant Tracker (Kanban)
Full CRUD for candidates and their applications. The pipeline stages are:
`Applied → Screening → Pre-Screen Call → First Interview → Offer → Hired / Rejected`

Drag-and-drop on the Kanban board calls `PATCH /api/candidates/{id}/applications/{app_id}/stage`, which records the transition in `application_stage_history` for a full audit trail.

### Module 4 — Interview Scheduler
HR schedules interviews directly from a candidate's modal. FastAPI checks for **booking conflicts** (no double-booking an interviewer), then fires an n8n webhook that creates a Google Calendar event and returns a Google Meet link. The application stage auto-updates to reflect the scheduled interview.

---

## Database Schema

9 tables in PostgreSQL (Supabase):

| Table | Purpose |
|---|---|
| `pipeline_stages` | Kanban column definitions (order, type, terminal flag) |
| `candidates` | Core candidate records with JSONB `parsed_data` |
| `applications` | The Kanban card — links candidate ↔ job ↔ stage. `UNIQUE(candidate_id, job_id)` |
| `application_stage_history` | Immutable audit trail of every stage transition |
| `jobs` | Open job requisitions with description and requirements |
| `interviews` | Scheduled interviews with Google Meet links and conflict detection support |
| `resume_scores` | AI scores (skills / experience / culture) with JSONB prescreen questions |
| `application_notes` | Free-form recruiter comments per application |
| `users` | Recruiter and hiring manager accounts |

---

## Local Development Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- A Supabase project (or any PostgreSQL database)
- n8n cloud account (or self-hosted)

### 1. Clone the repo

```bash
git clone https://github.com/montg1/recruiting-pipeline-tool.git
cd recruiting-pipeline-tool
```

### 2. Backend

```bash
cd backend

# Create and activate virtual environment
py -3.12 -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and fill in your values (see below)

# Create DB tables (run once against your Supabase DB)
python init_db.py

# Seed pipeline stages and sample jobs
python seed_supabase.py

# Start the backend
uvicorn main:app --reload --port 8000
```

**`backend/.env` variables:**

```env
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_PASSWORD@aws-1-region.pooler.supabase.com:5432/postgres
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
N8N_WEBHOOK_URL=https://your-n8n-instance.app.n8n.cloud/webhook/YOUR_WEBHOOK_ID
GOOGLE_CREDENTIALS_PATH=credentials.json
```

> For Supabase: use port **5432** (direct connection) for the backend. The pooler port 6543 breaks SQLAlchemy's `joinedload` queries.

**Local dev without Supabase (SQLite):**

```bash
python dev_server.py   # Starts on port 8000 with 10 seeded candidates
```

### 3. Frontend

```bash
cd frontend

npm install

# Set the backend URL
cp .env.example .env
# For local dev the Vite proxy handles /api automatically — no changes needed

npm run dev   # http://localhost:5173
```

**`frontend/.env` variables:**

```env
# Leave blank to use Vite's built-in /api proxy (points to localhost:8000)
# Or set to your live backend for direct connection:
# VITE_API_URL=https://recruiting-pipeline-tool.onrender.com/api
VITE_API_URL=/api
```

---

## Deployment

### Frontend → Vercel

The repo is connected to Vercel via GitHub integration. Every push to `master` triggers an automatic deployment.

- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Environment Variable:** `VITE_API_URL=https://recruiting-pipeline-tool.onrender.com/api`

The `frontend/vercel.json` rewrites `/api/*` to the Render backend and configures SPA routing.

### Backend → Render (Free Tier)

1. Go to Render Dashboard → **New Web Service** → connect GitHub repo
2. Set **Root Directory** to `backend`
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. **Instance Type:** Free
6. Add environment variables: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `N8N_WEBHOOK_URL`

### Database → Supabase

Run `init_db.py` once from your local machine to create all tables, then `seed_supabase.py` to populate pipeline stages and seed jobs.

---

## CI/CD

GitHub Actions runs on every push to `master` and every pull request:

- **Backend:** runs `test_candidates.py` (37 assertions against SQLite in-memory DB)
- **Frontend:** runs `npm run build` to catch compile errors

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3, Vite, Tailwind CSS v4, Pinia, Vue Router, Axios |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic v2, Uvicorn |
| Database | PostgreSQL via Supabase |
| AI | Claude API (Anthropic) via n8n nodes |
| Automation | n8n (webhooks, Claude AI node, Google Calendar node) |
| PDF Parsing | PyPDF2 |
| Hosting | Vercel (frontend), Render (backend), Supabase (database) |
| CI/CD | GitHub Actions |
