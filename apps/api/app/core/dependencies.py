"""Shared FastAPI dependencies.

Provides injectable access to configuration, the database session, infrastructure
clients, and authentication guards (current user, permission checks).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

import redis
from fastapi import Cookie, Depends, Header
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.db.redis_client import get_redis
from app.db.session import get_session


def settings_dependency() -> Settings:
    return get_settings()


def db_session() -> Iterator[Session]:
    yield from get_session()


def redis_client() -> redis.Redis:
    return get_redis()


SettingsDep = Annotated[Settings, Depends(settings_dependency)]
SessionDep = Annotated[Session, Depends(db_session)]
RedisDep = Annotated[redis.Redis, Depends(redis_client)]


# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------

def _extract_token(
    access_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> str:
    """Extract a bearer token from cookie or Authorization header."""
    if access_token:
        return access_token
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    raise AuthenticationError("Authentication required.")


def _get_current_user(
    session: Session = Depends(db_session),
    token: str = Depends(_extract_token),
):
    from app.services.auth import AuthService

    svc = AuthService(session)
    return svc.get_current_user(token)


CurrentUserDep = Annotated[object, Depends(_get_current_user)]


def RequirePermission(permission: str):
    """Dependency factory that enforces a specific permission on the current user."""

    def _check(user=Depends(_get_current_user)) -> object:
        if permission not in user.permissions:
            raise PermissionDeniedError(
                f"You do not have the required permission: {permission}"
            )
        return user

    return Depends(_check)
