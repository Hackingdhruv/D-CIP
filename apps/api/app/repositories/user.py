"""User repository."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        stmt = (
            select(User)
            .where(User.email == email.lower(), User.deleted_at.is_(None))
            .options(selectinload(User.roles))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_username(self, username: str) -> User | None:
        stmt = (
            select(User)
            .where(User.username == username.lower(), User.deleted_at.is_(None))
            .options(selectinload(User.roles))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_active(self, user_id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .options(selectinload(User.roles))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_many_active(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, User]:
        """Fetch multiple active users in a single query. Returns a mapping of id→User."""
        if not user_ids:
            return {}
        stmt = (
            select(User)
            .where(User.id.in_(user_ids), User.deleted_at.is_(None))
            .options(selectinload(User.roles))
        )
        rows = self.session.execute(stmt).scalars().all()
        return {u.id: u for u in rows}

    def search(
        self,
        *,
        q: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        base = select(User).where(User.deleted_at.is_(None))
        if q:
            term = f"%{q.lower()}%"
            base = base.where(
                or_(
                    func.lower(User.email).like(term),
                    func.lower(User.username).like(term),
                    func.lower(User.full_name).like(term),
                )
            )
        if is_active is not None:
            base = base.where(User.is_active == is_active)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.session.execute(count_stmt).scalar_one()

        offset = (page - 1) * page_size
        stmt = (
            base.order_by(User.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .options(selectinload(User.roles))
        )
        items = list(self.session.execute(stmt).scalars().all())
        return items, total

    def increment_failed_attempts(self, user: User) -> None:
        user.failed_login_attempts += 1
        self.session.flush()

    def reset_failed_attempts(self, user: User) -> None:
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None
        self.session.flush()

    def lock(self, user: User, until: datetime) -> None:
        user.is_locked = True
        user.locked_until = until
        self.session.flush()

    def record_login(self, user: User) -> None:
        user.last_login_at = datetime.now(tz=timezone.utc)
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None
        self.session.flush()

    def soft_delete(self, user: User) -> None:
        user.deleted_at = datetime.now(tz=timezone.utc)
        user.is_active = False
        self.session.flush()

    def email_exists(self, email: str, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(User.id).where(
            User.email == email.lower(), User.deleted_at.is_(None)
        )
        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def username_exists(self, username: str, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(User.id).where(
            User.username == username.lower(), User.deleted_at.is_(None)
        )
        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)
        return self.session.execute(stmt).scalar_one_or_none() is not None
