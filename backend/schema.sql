-- ============================================================
-- Recruiting Pipeline Tool — Database Schema (PostgreSQL)
-- Module 3: Applicant Tracker (with hooks for Modules 1, 2, 4)
-- ============================================================

-- ---------- Lookup: Pipeline Stages ----------
CREATE TABLE pipeline_stages (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(64) NOT NULL UNIQUE,
    order_index  INTEGER     NOT NULL,                 -- column order on kanban
    is_terminal  BOOLEAN     NOT NULL DEFAULT FALSE,
    stage_type   VARCHAR(16) NOT NULL,                 -- 'active' | 'success' | 'rejected'
    color_hex    VARCHAR(7),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO pipeline_stages (name, order_index, is_terminal, stage_type) VALUES
  ('Applied',          1, FALSE, 'active'),
  ('Screening',        2, FALSE, 'active'),
  ('Pre-Screen Call',  3, FALSE, 'active'),
  ('First Interview',  4, FALSE, 'active'),
  ('Offer',            5, FALSE, 'active'),
  ('Hired',            6, TRUE,  'success'),
  ('Rejected',         7, TRUE,  'rejected');

-- ---------- Users (recruiters / hiring managers) ----------
CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) NOT NULL UNIQUE,
    full_name   VARCHAR(128) NOT NULL,
    role        VARCHAR(32)  NOT NULL,                 -- 'recruiter' | 'hiring_manager' | 'admin'
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ---------- Jobs (open requisitions) ----------
CREATE TABLE jobs (
    id            SERIAL PRIMARY KEY,
    title         VARCHAR(128) NOT NULL,
    department    VARCHAR(64),
    description   TEXT,
    requirements  TEXT,
    status        VARCHAR(16)  NOT NULL DEFAULT 'open',  -- 'open' | 'on_hold' | 'closed'
    owner_id      INTEGER REFERENCES users(id),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ---------- Candidates (people) ----------
CREATE TABLE candidates (
    id            SERIAL PRIMARY KEY,
    full_name     VARCHAR(128) NOT NULL,
    email         VARCHAR(255) NOT NULL UNIQUE,
    phone         VARCHAR(32),
    linkedin_url  VARCHAR(255),
    source        VARCHAR(64),                          -- 'LinkedIn' | 'Referral' | 'n8n_scrape' | ...
    resume_path   VARCHAR(512),                         -- filesystem path or S3 key
    resume_text   TEXT,                                 -- parsed plaintext (Module 2 input)
    parsed_data   JSONB,                                -- normalized JSON from n8n scraper (Module 1)
    is_active     BOOLEAN     NOT NULL DEFAULT TRUE,    -- soft delete flag
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_candidates_active     ON candidates(is_active);
CREATE INDEX idx_candidates_parsed_gin ON candidates USING GIN (parsed_data);

-- ---------- Applications (THE Kanban card — Module 3) ----------
-- One row = one candidate's pipeline for one job.
CREATE TABLE applications (
    id                SERIAL PRIMARY KEY,
    candidate_id      INTEGER NOT NULL REFERENCES candidates(id)      ON DELETE CASCADE,
    job_id            INTEGER NOT NULL REFERENCES jobs(id)            ON DELETE CASCADE,
    current_stage_id  INTEGER NOT NULL REFERENCES pipeline_stages(id),
    applied_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rejected_reason   VARCHAR(255),                                   -- set when current stage = Rejected
    kanban_position   INTEGER NOT NULL DEFAULT 0,                     -- vertical order inside a column
    assigned_to       INTEGER REFERENCES users(id),
    is_active         BOOLEAN     NOT NULL DEFAULT TRUE,              -- soft delete flag
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (candidate_id, job_id)                                     -- can't apply to same job twice
);
CREATE INDEX idx_applications_stage     ON applications(current_stage_id);
CREATE INDEX idx_applications_job       ON applications(job_id);
CREATE INDEX idx_applications_candidate ON applications(candidate_id);
CREATE INDEX idx_applications_active    ON applications(is_active);

-- ---------- Stage history (audit trail, time-in-stage metrics) ----------
CREATE TABLE application_stage_history (
    id              BIGSERIAL PRIMARY KEY,
    application_id  INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    from_stage_id   INTEGER REFERENCES pipeline_stages(id),       -- NULL on first entry
    to_stage_id     INTEGER NOT NULL REFERENCES pipeline_stages(id),
    moved_by        INTEGER REFERENCES users(id),
    note            TEXT,
    moved_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_stage_history_app ON application_stage_history(application_id);

-- ---------- Resume scores (Module 2) ----------
CREATE TABLE resume_scores (
    id                  SERIAL PRIMARY KEY,
    application_id      INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    skills_score        NUMERIC(3,1) CHECK (skills_score     BETWEEN 0 AND 10),
    experience_score    NUMERIC(3,1) CHECK (experience_score BETWEEN 0 AND 10),
    culture_score       NUMERIC(3,1) CHECK (culture_score    BETWEEN 0 AND 10),
    overall_score       NUMERIC(3,1) GENERATED ALWAYS AS
                        ((skills_score + experience_score + culture_score) / 3) STORED,
    reasoning           TEXT,
    prescreen_questions JSONB,
    model_version       VARCHAR(64),
    scored_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------- Interviews (Module 4) ----------
CREATE TABLE interviews (
    id                SERIAL PRIMARY KEY,
    application_id    INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    scheduled_at      TIMESTAMPTZ NOT NULL,
    duration_minutes  INTEGER     NOT NULL DEFAULT 30,
    google_meet_link  VARCHAR(255),
    google_event_id   VARCHAR(255),                                  -- Google Calendar event ID (for update/delete)
    interviewer_id    INTEGER REFERENCES users(id),
    status            VARCHAR(16) NOT NULL DEFAULT 'scheduled',     -- 'scheduled' | 'completed' | 'cancelled'
    feedback          TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_interviews_scheduled   ON interviews(scheduled_at);
CREATE INDEX idx_interviews_application ON interviews(application_id);
-- Conflict detection: query (interviewer_id, scheduled_at, scheduled_at + duration_minutes) overlap.

-- ---------- Notes (free-form recruiter comments) ----------
CREATE TABLE application_notes (
    id              SERIAL PRIMARY KEY,
    application_id  INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    author_id       INTEGER REFERENCES users(id),
    body            TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Optional: trigger to auto-write stage_history on stage change
-- ============================================================
CREATE OR REPLACE FUNCTION log_stage_change() RETURNS TRIGGER AS $$
BEGIN
  IF NEW.current_stage_id IS DISTINCT FROM OLD.current_stage_id THEN
    INSERT INTO application_stage_history (application_id, from_stage_id, to_stage_id, moved_by)
    VALUES (NEW.id, OLD.current_stage_id, NEW.current_stage_id, NEW.assigned_to);
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_log_stage_change
  AFTER UPDATE OF current_stage_id ON applications
  FOR EACH ROW EXECUTE FUNCTION log_stage_change();
