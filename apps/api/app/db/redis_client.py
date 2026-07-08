"""Redis client factory.

A lazily-initialised, process-wide client is used for caching, sessions, and
(via Celery) queueing. Decoded responses keep call sites working with ``str``.
"""

from __future__ import annotations

import redis

from app.core.config import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Return the shared Redis client, creating it on first use."""
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def check_connection() -> None:
    """Ping Redis to verify connectivity."""
    get_redis().ping()
