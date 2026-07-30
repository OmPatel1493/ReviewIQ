"""Auth-related API schemas (the public contract; distinct from ORM models)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    """The safe, public view of a user — note there is NO token field here."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    github_id: int
    login: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    created_at: datetime


class LoginUrlResponse(BaseModel):
    authorize_url: str
