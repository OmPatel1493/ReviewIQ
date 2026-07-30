"""`get_current_user` — the FastAPI dependency that guards protected routes.

Accepts the JWT from either an httpOnly cookie (browser/SPA) or an
`Authorization: Bearer` header (API clients/scripts), verifies it, and loads the
user. Any failure results in a clean 401 — handlers just declare
`user: User = Depends(get_current_user)` and can assume a valid, present user.
"""

from __future__ import annotations

import uuid

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.models import User
from app.modules.auth.security import decode_token
from app.repositories.user_repository import UserRepository

settings = get_settings()

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def _extract_token(request: Request) -> str | None:
    header = request.headers.get("Authorization")
    if header and header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get(settings.COOKIE_NAME)


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    token = _extract_token(request)
    if not token:
        raise _UNAUTHENTICATED

    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise _UNAUTHENTICATED from None

    if payload.get("type") != "access":
        raise _UNAUTHENTICATED

    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        raise _UNAUTHENTICATED from None

    user = await UserRepository(db).get(user_id)
    if user is None:
        raise _UNAUTHENTICATED
    return user
