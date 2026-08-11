"""Ask-AI API schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class AskRequest(BaseModel):
    repository_id: uuid.UUID
    question: str = Field(
        min_length=1,
        max_length=2000,
        examples=["What tests should I write for the auth module?"],
    )
    top_k: int | None = Field(
        default=None, ge=1, le=20, description="How many code snippets to ground the answer in."
    )


class AskSource(BaseModel):
    """A code snippet the answer was grounded in."""

    model_config = ConfigDict(from_attributes=True)

    file_path: str
    start_line: int
    end_line: int
    score: float


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[AskSource]
