"""Tests for password hashing and JWT utilities."""

from __future__ import annotations

import pytest

from app.core.security import (
    TokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_access_token_round_trip() -> None:
    token = create_access_token("user-123", extra_claims={"org": "acme"})
    payload = decode_token(token, expected_type=TokenType.ACCESS)
    assert payload["sub"] == "user-123"
    assert payload["org"] == "acme"
    assert payload["type"] == "access"


def test_refresh_token_type_is_enforced() -> None:
    token = create_refresh_token("user-123")
    with pytest.raises(TokenError):
        decode_token(token, expected_type=TokenType.ACCESS)


def test_invalid_token_raises() -> None:
    with pytest.raises(TokenError):
        decode_token("not-a-real-token")
