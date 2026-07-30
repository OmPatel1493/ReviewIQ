"""Security primitives: JWTs, token encryption, and OAuth state tokens.

Kept dependency-free of FastAPI/DB so it's trivially unit-testable and reusable.

* **JWT** — our own stateless session token. Signed with `JWT_SECRET` (HS256); any
  API instance can verify it without a shared session store.
* **Fernet encryption** — the GitHub access token is a bearer credential to a user's
  repos, so we never store it in plaintext. Fernet gives authenticated symmetric
  encryption (AES-128-CBC + HMAC) with a simple API.
* **OAuth state** — a short-lived signed token round-tripped through GitHub to defeat
  CSRF on the callback. Because it's signed, we need no server-side storage.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

settings = get_settings()

_ACCESS = "access"
_STATE = "oauth_state"


# --------------------------------------------------------------------- JWT --
def create_access_token(
    subject: str,
    *,
    expires_minutes: int | None = None,
    token_type: str = _ACCESS,
    extra: dict[str, Any] | None = None,
) -> str:
    """Sign a JWT for `subject` (usually the user id)."""
    now = datetime.now(UTC)
    expire = now + timedelta(
        minutes=expires_minutes
        if expires_minutes is not None
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode & verify a JWT (signature + expiry). Raises `jwt.PyJWTError` on failure."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# ---------------------------------------------------- token encryption ----
def encrypt_token(raw: str) -> str:
    return Fernet(settings.fernet_key).encrypt(raw.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Raises `cryptography.fernet.InvalidToken` if the ciphertext was tampered with."""
    return Fernet(settings.fernet_key).decrypt(encrypted.encode()).decode()


# ------------------------------------------------------- OAuth CSRF state --
def create_state_token() -> str:
    """A short-lived, signed value to detect a forged/late OAuth callback."""
    return create_access_token(
        subject=uuid.uuid4().hex, expires_minutes=10, token_type=_STATE
    )


def verify_state_token(token: str) -> bool:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return False
    return payload.get("type") == _STATE


__all__ = [
    "InvalidToken",
    "create_access_token",
    "decode_token",
    "encrypt_token",
    "decrypt_token",
    "create_state_token",
    "verify_state_token",
]
