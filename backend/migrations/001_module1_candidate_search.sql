-- ============================================================
-- Migration 001 — Module 1 (Candidate Data Scraper)
-- Idempotent: safe to run more than once.
--   • jobs.parsed_criteria  — cached AI parse of the JD
--   • candidate_searches    — staging for JD-driven discovery results
-- ============================================================

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS parsed_criteria JSONB;

CREATE TABLE IF NOT EXISTS candidate_searches (
    id            SERIAL PRIMARY KEY,
    job_id        INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    criteria      JSONB,
    sources       JSONB,
    queries       JSONB,
    results       JSONB NOT NULL DEFAULT '[]',
    result_count  INTEGER NOT NULL DEFAULT 0,
    status        VARCHAR(16) NOT NULL DEFAULT 'completed',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_candidate_searches_job ON candidate_searches(job_id);
