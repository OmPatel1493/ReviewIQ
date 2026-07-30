"""ORM models package.

Importing every model here has a purpose beyond convenience: SQLAlchemy only knows
about a table once its class is imported, and Alembic autogenerate diffs the live DB
against `Base.metadata`. If a model isn't imported, its table silently won't appear
in migrations. So this file is the single import point that guarantees the whole
schema is registered.
"""

from app.models.activity_log import ActivityLog
from app.models.base import Base
from app.models.code_chunk import CodeChunk
from app.models.finding import Finding
from app.models.job import Job
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.review import Review
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Repository",
    "PullRequest",
    "Review",
    "Finding",
    "CodeChunk",
    "Job",
    "ActivityLog",
]
