"""Password hashing utilities built on bcrypt.

bcrypt operates on bytes and silently truncates inputs beyond 72 bytes, so we
encode explicitly and guard the length. Hashes are stored as UTF-8 strings.
"""

from __future__ import annotations

import bcrypt

# Work factor. 12 is a sensible default balancing security and latency.
_ROUNDS = 12
_MAX_BYTES = 72


def _encode(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(encoded) > _MAX_BYTES:
        raise ValueError("Password exceeds the 72-byte bcrypt limit.")
    return encoded


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash for the given plaintext password."""
    return bcrypt.hashpw(_encode(password), bcrypt.gensalt(rounds=_ROUNDS)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Return True if the plaintext password matches the stored hash."""
    try:
        return bcrypt.checkpw(_encode(password), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def needs_rehash(hashed: str) -> bool:
    """Return True if a stored hash uses a weaker work factor than current."""
    try:
        cost = int(hashed.split("$")[2])
    except (IndexError, ValueError):
        return True
    return cost < _ROUNDS
