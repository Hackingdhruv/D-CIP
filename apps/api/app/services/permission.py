"""Permission service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.repositories.permission import PermissionRepository
from app.services.base import BaseService


class PermissionService(BaseService):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self._permissions = PermissionRepository(session)

    def get_all(self) -> list[Permission]:
        return self._permissions.list_all()
