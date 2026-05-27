"""
Application configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/recruiting_db"

    # LLM provider — "anthropic" (prod) or "ollama" (local, no API key, for testing)
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e4b"

    # Module 1 — Candidate discovery
    zenrows_api_key: str = ""        # ZenRows Universal API key (LinkedIn X-ray + deep fetch)
    github_token: str = ""           # optional — raises GitHub API rate limit (60→5000/hr)

    # Google Calendar
    google_credentials_path: str = "credentials.json"

    # n8n Automation
    n8n_webhook_url: str = "http://localhost:5678/webhook"
    n8n_interview_webhook_url: str = "http://localhost:5678/webhook-interview"
    # AI microservice: when LLM_PROVIDER=n8n, parse_jd/rank are delegated here
    # (n8n owns the prompts + the Claude call). FastAPI sends only raw inputs.
    n8n_ai_webhook_url: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
