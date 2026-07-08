"""Rate limiting framework.

A configured ``slowapi`` limiter is created here and wired into the app in
``main.py``. Per-route limits can later be applied with the ``@limiter.limit``
decorator; a permissive global default is active when rate limiting is enabled.
The limiter keys on the client's remote address.

Storage defaults to in-memory (``memory://``) so the API and tests run without
Redis. Set ``RATE_LIMIT_STORAGE_URI`` to the Redis URL for multi-process
deployments where limits must be shared across workers.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default] if settings.rate_limit_enabled else [],
    storage_uri=settings.rate_limit_storage_uri,
    enabled=settings.rate_limit_enabled,
)
