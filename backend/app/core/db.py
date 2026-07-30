"""Async database engine and session management.

We use SQLAlchemy 2.0's asyncio support with the `asyncpg` driver so DB calls don't
block FastAPI's event loop. Two objects matter:

* `engine` — a process-wide connection pool (created once).
* `AsyncSessionLocal` — a factory that hands out short-lived sessions (one per request).

`get_db()` is the FastAPI dependency: it yields a session and guarantees cleanup,
committing on success and rolling back on error. Handlers just declare
`db: AsyncSession = Depends(get_db)` and never worry about connection lifecycle.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

# `pool_pre_ping` transparently checks a connection is alive before use, avoiding
# "server closed the connection" errors after idle periods.
engine = create_async_engine(
    settings.database_url,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep attributes usable after commit (common in APIs)
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transactional session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_db() -> bool:
    """Lightweight liveness ping used by the readiness probe (`SELECT 1`)."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
