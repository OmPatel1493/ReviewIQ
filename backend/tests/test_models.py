"""Phase 1 — schema-shape tests that need no database.

These assert the *structure* of the ORM metadata (tables, keys, enums) and that it
compiles to valid PostgreSQL DDL. Live round-trip behaviour (inserts, cascades) is
verified separately against a real Postgres; keeping these DB-free means the suite
stays fast and green in CI without a database service.
"""

from __future__ import annotations

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.models import Base
from app.models.enums import FindingCategory, Severity

EXPECTED_TABLES = {
    "users",
    "repositories",
    "pull_requests",
    "reviews",
    "findings",
    "code_chunks",
    "jobs",
    "activity_logs",
}


def test_all_tables_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


@pytest.mark.parametrize("table_name", sorted(EXPECTED_TABLES))
def test_each_table_compiles_to_postgres_ddl(table_name: str) -> None:
    table = Base.metadata.tables[table_name]
    ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
    assert f'CREATE TABLE {table_name}' in ddl


def test_relationships_and_cascades_declared() -> None:
    from app.models import Repository, User

    # User → repositories relationship exists and cascades deletes.
    rel = User.__mapper__.relationships["repositories"]
    assert rel.mapper.class_ is Repository
    assert "delete-orphan" in rel.cascade


def test_foreign_keys_use_naming_convention() -> None:
    # The metadata naming convention should produce predictable FK names.
    fks = list(Base.metadata.tables["repositories"].foreign_keys)
    assert any(fk.constraint.name == "fk_repositories_owner_id_users" for fk in fks)


def test_enum_values_are_stable() -> None:
    # These string values are persisted and surfaced in the API/UI — pin them.
    assert [s.value for s in Severity] == ["low", "medium", "high", "critical"]
    assert FindingCategory.SECURITY.value == "security"
