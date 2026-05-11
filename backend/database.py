"""
Database engine and session configuration.

Uses psycopg2 (sync) driver with SQLAlchemy 2.0-style declarative base.
Connection parameters are loaded from config.Settings (reads .env).
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,       # verify connections before handing them out
    pool_size=5,              # reasonable default for a dev/small-prod DB
    max_overflow=10,
    echo=False,               # set True for SQL debug logging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def get_db():
    """FastAPI dependency that yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
