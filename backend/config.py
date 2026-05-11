"""
Application configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/recruiting_db"

    # Claude AI
    anthropic_api_key: str = ""

    # Google Calendar
    google_credentials_path: str = "credentials.json"

    class Config:
        env_file = ".env"


settings = Settings()
