"""Permission repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.permission import Permission
from app.repositories.base import BaseRepository


class PermissionRepository(BaseRepository[Permission]):
    model = Permission

    def get_by_codename(self, resource: str, action: str) -> Permission | None:
        stmt = select(Permission).where(
            Permission.resource == resource, Permission.action == action
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.resource, Permission.action)
        return list(self.session.execute(stmt).scalars().all())

    def get_by_ids(self, ids: list[uuid.UUID]) -> list[Permission]:
        if not ids:
            return []
        stmt = select(Permission).where(Permission.id.in_(ids))
        return list(self.session.execute(stmt).scalars().all())
