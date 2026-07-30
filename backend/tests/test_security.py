"""Unit tests for the auth security primitives (no DB, no network)."""

from __future__ import annotations

import jwt
import pytest

from app.modules.auth.security import (
    InvalidToken,
    create_access_token,
    create_state_token,
    decode_token,
    decrypt_token,
    encrypt_token,
    verify_state_token,
)


def test_jwt_roundtrip_preserves_subject_and_type() -> None:
    token = create_access_token("user-123", extra={"login": "octocat"})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert payload["login"] == "octocat"


def test_expired_jwt_is_rejected() -> None:
    token = create_access_token("user-123", expires_minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_tampered_jwt_is_rejected() -> None:
    token = create_access_token("user-123")
    with pytest.raises(jwt.PyJWTError):
        decode_token(token + "tampered")


def test_token_encryption_roundtrip() -> None:
    secret = "fake-token-value-for-encryption-test"  # noqa: S105 (not a real secret)
    encrypted = encrypt_token(secret)
    assert encrypted != secret  # not stored in plaintext
    assert decrypt_token(encrypted) == secret


def test_decrypt_rejects_tampered_ciphertext() -> None:
    encrypted = encrypt_token("gho_x")
    with pytest.raises(InvalidToken):
        decrypt_token(encrypted[:-2] + "xy")


def test_oauth_state_roundtrip() -> None:
    state = create_state_token()
    assert verify_state_token(state) is True


def test_oauth_state_rejects_garbage_and_wrong_type() -> None:
    assert verify_state_token("not-a-jwt") is False
    # A normal access token must NOT be accepted as a valid state token.
    assert verify_state_token(create_access_token("user-123")) is False
