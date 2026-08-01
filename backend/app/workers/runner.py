"""Async runner bridging a (sync) Celery task to our async indexing code.

A Celery task is a normal sync function, but our DB/vector work is async, so the task
calls `asyncio.run(run_index_job(...))`. We create a **dedicated** async engine here
(with `NullPool`) rather than reusing the app's global engine, because each task runs
in its own fresh event loop and asyncpg connections are bound to the loop that made
them — a fresh engine avoids cross-loop reuse bugs.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.logging import get_logger
from app.modules.auth.security import decrypt_token
from app.modules.indexing.service import IndexingService
from app.repositories.job_repository import JobRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.user_repository import UserRepository

settings = get_settings()
logger = get_logger(__name__)


async def run_index_job(
    *, job_id: str, repo_id: str, celery_task_id: str | None = None
) -> dict[str, Any]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    job_uuid = uuid.UUID(job_id)
    repo_uuid = uuid.UUID(repo_id)

    try:
        async with session_factory() as db:
            jobs = JobRepository(db)
            await jobs.mark_running(job_uuid, celery_task_id)
            await db.commit()

            service = IndexingService(db)
            try:
                repo = await RepositoryRepository(db).get(repo_uuid)
                if repo is None:
                    raise ValueError(f"repository {repo_id} not found")

                # The owner's OAuth token lets us clone private repos.
                owner = await UserRepository(db).get(repo.owner_id)
                token = (
                    decrypt_token(owner.github_access_token)
                    if owner and owner.github_access_token
                    else None
                )

                result = await service.index_repository(repo_uuid, token=token)
                await jobs.mark_succeeded(job_uuid, result)
                await db.commit()
                return result
            except Exception as exc:
                await db.rollback()
                await jobs.mark_failed(job_uuid, str(exc))
                await db.commit()
                logger.exception("Index job %s failed", job_id)
                raise
            finally:
                await service.aclose()
    finally:
        await engine.dispose()
