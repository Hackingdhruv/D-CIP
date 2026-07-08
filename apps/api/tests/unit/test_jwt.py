"""Unit tests for JWT token utilities."""

from __future__ import annotations

import time

import pytest

from app.core.security.jwt import (
    TokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_create_and_decode_access_token() -> None:
    token = create_access_token("user-123")
    payload = decode_token(token, expected_type=TokenType.ACCESS)
    assert payload["sub"] == "user-123"
    assert payload["type"] == TokenType.ACCESS.value


def test_create_and_decode_refresh_token() -> None:
    token = create_refresh_token("user-456")
    payload = decode_token(token, expected_type=TokenType.REFRESH)
    assert payload["sub"] == "user-456"
    assert payload["type"] == TokenType.REFRESH.value


def test_access_token_has_jti() -> None:
    token = create_access_token("u")
    payload = decode_token(token)
    assert "jti" in payload and payload["jti"]


def test_wrong_type_raises_token_error() -> None:
    access = create_access_token("u")
    with pytest.raises(TokenError, match="refresh"):
        decode_token(access, expected_type=TokenType.REFRESH)


def test_tampered_token_raises_token_error() -> None:
    token = create_access_token("u")
    tampered = token[:-4] + "XXXX"
    with pytest.raises(TokenError):
        decode_token(tampered)


def test_extra_claims_are_preserved() -> None:
    token = create_access_token("u", extra_claims={"roles": ["admin"], "email": "a@b.com"})
    payload = decode_token(token)
    assert payload["roles"] == ["admin"]
    assert payload["email"] == "a@b.com"


def test_decode_without_type_check_passes() -> None:
    token = create_access_token("u")
    payload = decode_token(token)
    assert payload["sub"] == "u"
