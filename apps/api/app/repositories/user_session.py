"""User session repository."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.models.user_session import UserSession
from app.repositories.base import BaseRepository


class UserSessionRepository(BaseRepository[UserSession]):
    model = UserSession

    def get_active_by_token(self, session_token: str) -> UserSession | None:
        now = datetime.now(tz=timezone.utc)
        stmt = select(UserSession).where(
            UserSession.session_token == session_token,
            UserSession.is_active.is_(True),
            UserSession.expires_at > now,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def touch(self, session: UserSession) -> None:
        session.last_active_at = datetime.now(tz=timezone.utc)
        self.session.flush()

    def deactivate(self, session: UserSession) -> None:
        session.is_active = False
        self.session.flush()

    def deactivate_all_for_user(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.is_active.is_(True))
            .values(is_active=False)
        )
        self.session.execute(stmt)
        self.session.flush()

    def list_active_for_user(self, user_id: uuid.UUID) -> list[UserSession]:
        now = datetime.now(tz=timezone.utc)
        stmt = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_active.is_(True),
            UserSession.expires_at > now,
        )
        return list(self.session.execute(stmt).scalars().all())
