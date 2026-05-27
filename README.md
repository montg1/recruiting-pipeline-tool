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
│  /scraper    → Candidate Discovery (JD → ranked shortlist)      │
│  /cv-screener → AI Resume Screener (PDF upload)                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP / REST  (/api/*)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│             Core Backend  (FastAPI + SQLAlchemy)                │
│                    Deployed on Render                           │
│                                                                 │
│  Module 1 → /api/scraper/search-from-jd  (JD → discover → rank) │
│             discovery: GitHub API + LinkedIn X-ray (ZenRows)    │
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
│                   │    │  Module 1 AI: parse JD + rank         │
│  10 tables        │    │             (Claude via AI Agent)     │
│  (candidates,     │    │  Module 2: PDF text + JD → Claude     │
│   applications,   │    │             → score JSON              │
│   candidate_      │    │  Module 4: Create Google Calendar     │
│   searches, ...)  │    │             event → return Meet link  │
└───────────────────┘    └───────────────────────────────────────┘
```

### Architecture Decision: Why FastAPI + n8n?

| Concern | Where it lives | Why |
|---|---|---|
| Business logic, CRUD, validation | **FastAPI** | Python is fast to write, easy to test, type-safe via Pydantic |
| Candidate discovery (GitHub API, LinkedIn X-ray) | **FastAPI adapters** | One file per source; merge/dedup/graceful-degradation are easier to test in Python |
| Claude AI prompting (JD parse, ranking, resume scoring) | **n8n** | Non-engineers can edit prompts in the n8n AI-Agent UI without touching code; provider is swappable (`LLM_PROVIDER`) |
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
│   │   ├── scraper.py               # Module 1 — search-from-jd / approve / extract
│   │   ├── interviews.py            # Module 4 — scheduling + conflicts
│   │   └── jobs.py                  # Job listings
│   ├── models/                      # SQLAlchemy ORM models (10 tables)
│   │   ├── candidate.py
│   │   ├── candidate_search.py      # Module 1 staging (discovered leads)
│   │   ├── application.py           # The Kanban "card" entity
│   │   ├── application_stage_history.py
│   │   ├── interview.py
│   │   ├── resume_score.py
│   │   ├── job.py                   # + parsed_criteria (cached JD parse)
│   │   ├── pipeline_stage.py
│   │   ├── user.py
│   │   └── application_note.py
│   ├── schemas/                     # Pydantic request/response schemas (incl. scraper.py)
│   ├── services/
│   │   ├── claude_ai.py             # LLM helper — provider switch (anthropic/ollama/n8n)
│   │   ├── jd_search.py             # Module 1 orchestrator (parse → discover → rank)
│   │   ├── sources/                 # Source adapters: base, github, linkedin_xray
│   │   └── google_meet.py           # Google Calendar helper
│   ├── migrations/                  # SQL migrations (001 — Module 1 staging)
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
│   ├── Module1_AI_Workflow.json     # Module 1 AI: parse_jd + rank (AI Agent + Claude)
│   └── Candidate_Scraper_Workflow.json
│
├── .github/workflows/ci.yml         # GitHub Actions: test + build on push
└── .gitignore                       # test/ folder excluded from git
```

---

## Modules

### Module 1 — Candidate Data Scraper (JD-driven Discovery)

> **Status: Working.** Give it a Job Description (Thai or English) and the system auto-generates search queries, finds candidates across multiple sources, AI-ranks them by fit, and presents a shortlist for HR to review and approve into the pipeline — **human-in-the-loop**, not data entry.

#### Pipeline (6 steps)

```
JD / criteria
  → 1. parse_jd        (LLM)      JD → { position, skills, min_years, location }
  → 2. build queries   (adapter)  per-source search strings, generated automatically
  → 3. discover        (adapter)  GitHub + LinkedIn → leads (merged + deduped)
  → 4. rank            (LLM)      match_score 0-100 + verdict + reasons + missing
  → 5. staging                    saved to candidate_searches (shortlist)
  → 6. HR review → approve        promoted to candidates + applications (Kanban)
```

#### Source strategy (tested empirically)

| Source | Method | Login? | Status |
|---|---|---|---|
| **GitHub** | Official Search Users API + profile enrich | No | ✅ reliable — best for engineering roles |
| **LinkedIn** | ZenRows Universal API + Google X-ray + JSON-LD | No | ✅ works — name + headline from search snippets |
| **JobsDB / JobThai** | Resume DB behind employer login | Yes | ⚠️ not indexed publicly — X-ray returns job ads, not people |
| **Facebook groups** | ZenRows refuses the domain (`REQS001`) | Yes | ❌ auto-scrape impossible → manual paste only |

Each source is a **Source Adapter** (`backend/services/sources/`) implementing `search()` + `build_query()`. Add a new source = add one file and register it in `ADAPTERS`. Discovery (web data-collection) lives in **FastAPI**, not n8n — only the LLM steps are delegated.

#### AI provider switch (`LLM_PROVIDER`)

`parse_jd` and `rank` run through a pluggable provider — same prompts, different transport:

| value | behaviour |
|---|---|
| `n8n` | delegate to the n8n AI-Agent workflow (prompts live in n8n) — **production** |
| `anthropic` | FastAPI calls the Claude API directly (needs `ANTHROPIC_API_KEY`) |
| `ollama` | local model (e.g. `gemma4:e4b`), no API key — for keyless local testing |

#### Why a staging table?

Scraped leads usually have **no email**, but `candidates.email` is `UNIQUE NOT NULL`. So leads are held in **`candidate_searches`** until HR approves them; on approval they're promoted into `candidates` + `applications` (a deterministic placeholder email is synthesized and flagged for HR to fill).

#### Endpoints

| method | path | purpose |
|---|---|---|
| POST | `/api/scraper/search-from-jd` | JD → discover → rank → save shortlist |
| GET | `/api/scraper/searches/{id}` | fetch a saved search run |
| POST | `/api/scraper/approve` | promote selected leads into the pipeline |
| POST | `/api/scraper/extract` | *(legacy)* single URL/text → n8n normalize — manual paste fallback |

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

10 tables in PostgreSQL (Supabase):

| Table | Purpose |
|---|---|
| `pipeline_stages` | Kanban column definitions (order, type, terminal flag) |
| `candidates` | Core candidate records with JSONB `parsed_data` |
| `candidate_searches` | Module 1 staging — a search run + ranked shortlist of leads (pre-approval) |
| `applications` | The Kanban card — links candidate ↔ job ↔ stage. `UNIQUE(candidate_id, job_id)` |
| `application_stage_history` | Immutable audit trail of every stage transition |
| `jobs` | Open job requisitions with description, requirements, and JSONB `parsed_criteria` |
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
GOOGLE_CREDENTIALS_PATH=credentials.json
N8N_WEBHOOK_URL=https://your-n8n-instance.app.n8n.cloud/webhook/YOUR_WEBHOOK_ID

# Module 1 — candidate discovery
ZENROWS_API_KEY=your_zenrows_key            # LinkedIn X-ray
GITHUB_TOKEN=                               # optional — raises GitHub API rate limit

# Module 1 — AI provider: "n8n" | "anthropic" | "ollama"
LLM_PROVIDER=n8n
N8N_AI_WEBHOOK_URL=https://your-n8n.app.n8n.cloud/webhook/recruitpipe-ai
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx      # used when LLM_PROVIDER=anthropic
# OLLAMA_BASE_URL=http://localhost:11434    # used when LLM_PROVIDER=ollama
# OLLAMA_MODEL=gemma4:e4b
```

> Module 1 adds the `candidate_searches` table and a `jobs.parsed_criteria` column. Apply once: run `backend/migrations/001_module1_candidate_search.sql` against your DB (idempotent). The n8n AI workflow is `n8n_workflows/Module1_AI_Workflow.json` — import it and set `N8N_AI_WEBHOOK_URL`.

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
6. Add environment variables: `DATABASE_URL`, `N8N_WEBHOOK_URL`, `ZENROWS_API_KEY`, `LLM_PROVIDER`, `N8N_AI_WEBHOOK_URL` (+ `ANTHROPIC_API_KEY` or `GITHUB_TOKEN` as needed)

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
| AI | Claude (via n8n AI Agent) · pluggable with Anthropic SDK / local Ollama |
| Candidate discovery | GitHub Search API · LinkedIn X-ray via ZenRows |
| Automation | n8n (webhooks, AI Agent + Claude, Google Calendar node) |
| PDF Parsing | PyPDF2 |
| Hosting | Vercel (frontend), Render (backend), Supabase (database) |
| CI/CD | GitHub Actions |
