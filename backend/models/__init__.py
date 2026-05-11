"""
SQLAlchemy ORM models — import every model here so that
``Base.metadata`` sees them all when creating / migrating tables.
"""

from models.pipeline_stage import PipelineStage          # noqa: F401
from models.user import User                              # noqa: F401
from models.job import Job                                # noqa: F401
from models.candidate import Candidate                    # noqa: F401
from models.application import Application                # noqa: F401
from models.application_stage_history import ApplicationStageHistory  # noqa: F401
from models.resume_score import ResumeScore               # noqa: F401
from models.interview import Interview                    # noqa: F401
from models.application_note import ApplicationNote       # noqa: F401
