"""Unit tests for password hashing utilities."""

from __future__ import annotations

import pytest

from app.core.security.password import hash_password, needs_rehash, verify_password


def test_hash_password_returns_bcrypt_string() -> None:
    hashed = hash_password("Test@1234!")
    assert hashed.startswith("$2b$")


def test_hash_password_produces_unique_salts() -> None:
    h1 = hash_password("Test@1234!")
    h2 = hash_password("Test@1234!")
    assert h1 != h2


def test_verify_password_correct() -> None:
    hashed = hash_password("Test@1234!")
    assert verify_password("Test@1234!", hashed) is True


def test_verify_password_wrong() -> None:
    hashed = hash_password("Test@1234!")
    assert verify_password("WrongPass!", hashed) is False


def test_verify_password_empty_returns_false() -> None:
    hashed = hash_password("Test@1234!")
    assert verify_password("", hashed) is False


def test_hash_password_rejects_long_input() -> None:
    with pytest.raises(ValueError, match="72-byte"):
        hash_password("A" * 73)


def test_needs_rehash_current_cost_returns_false() -> None:
    hashed = hash_password("Test@1234!")
    assert needs_rehash(hashed) is False


def test_needs_rehash_weak_cost_returns_true() -> None:
    import bcrypt
    weak = bcrypt.hashpw(b"Test@1234!", bcrypt.gensalt(rounds=4)).decode()
    assert needs_rehash(weak) is True


def test_needs_rehash_invalid_string_returns_true() -> None:
    assert needs_rehash("not-a-hash") is True
