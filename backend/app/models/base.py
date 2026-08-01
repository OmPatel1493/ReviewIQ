"""Declarative base, metadata naming convention, and shared mixins.

Two things here are load-bearing for a clean, maintainable schema:

1. **Naming convention** on the `MetaData`. Without it, databases auto-generate
   constraint/index names that differ between engines and are unstable, which makes
   Alembic autogenerate noisy and `ALTER`/`DROP` migrations painful. Pinning the
   convention means every index/FK/unique/PK/check has a predictable name.

2. **Mixins** (`UUIDMixin`, `TimestampMixin`) so every table gets a UUID primary key
   and audit timestamps without repeating boilerplate.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Stable, predictable names for every constraint/index across the whole schema.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all ORM models. `Base.metadata` is what Alembic diffs against."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDMixin:
    """A UUID v4 primary key.

    UUIDs (vs auto-increment ints) avoid leaking row counts, don't collide across
    services/shards, and can be generated app-side before an INSERT (handy for
    linking related rows in one unit of work).
    """

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """`created_at` / `updated_at`, maintained by the database clock.

    We use `TIMESTAMPTZ` (timezone-aware) everywhere: timestamps are stored as UTC
    with an offset, which avoids a whole class of naive-vs-aware bugs — including
    inserting GitHub's timezone-aware timestamps.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
