"""Semantic search API schemas (the request/response boundary types)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    """A natural-language query scoped to one connected repository."""

    repository_id: uuid.UUID
    query: str = Field(
        min_length=1,
        max_length=1000,
        examples=["where is JWT auth implemented?"],
    )
    # Optional per-request override; falls back to settings.SEARCH_TOP_K.
    limit: int | None = Field(
        default=None, ge=1, le=50, description="Max results to return."
    )


class SearchResultItem(BaseModel):
    """One matching code chunk, ranked by semantic similarity."""

    model_config = ConfigDict(from_attributes=True)

    file_path: str
    start_line: int
    end_line: int
    content: str
    score: float


class SearchResponse(BaseModel):
    repository_id: uuid.UUID
    query: str
    results: list[SearchResultItem]
