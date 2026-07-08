"""Role repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.role import Role
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    model = Role

    def get_by_slug(self, slug: str) -> Role | None:
        stmt = (
            select(Role)
            .where(Role.slug == slug)
            .options(selectinload(Role.permissions))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_with_permissions(self, role_id: uuid.UUID) -> Role | None:
        stmt = (
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permissions))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(self) -> list[Role]:
        stmt = (
            select(Role)
            .order_by(Role.name)
            .options(selectinload(Role.permissions))
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_by_ids(self, ids: list[uuid.UUID]) -> list[Role]:
        if not ids:
            return []
        stmt = select(Role).where(Role.id.in_(ids))
        return list(self.session.execute(stmt).scalars().all())

    def slug_exists(self, slug: str, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Role.id).where(Role.slug == slug)
        if exclude_id:
            stmt = stmt.where(Role.id != exclude_id)
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def name_exists(self, name: str, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Role.id).where(Role.name == name)
        if exclude_id:
            stmt = stmt.where(Role.id != exclude_id)
        return self.session.execute(stmt).scalar_one_or_none() is not None
