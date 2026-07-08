"""Role management service."""

from __future__ import annotations

import re
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models.auth_audit_event import AuditEventType
from app.models.role import Role
from app.repositories.audit import AuditRepository
from app.repositories.permission import PermissionRepository
from app.repositories.role import RoleRepository
from app.schemas.role import RoleCreate, RoleUpdate
from app.services.base import BaseService


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


class RoleService(BaseService):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self._roles = RoleRepository(session)
        self._permissions = PermissionRepository(session)
        self._audit = AuditRepository(session)

    def create(self, data: RoleCreate, *, actor_id: uuid.UUID | None = None) -> Role:
        slug = _slugify(data.name)
        if self._roles.name_exists(data.name):
            raise ConflictError("A role with that name already exists.")
        if self._roles.slug_exists(slug):
            raise ConflictError("A role with that slug already exists.")

        permissions = self._permissions.get_by_ids(data.permission_ids)

        role = Role(name=data.name, slug=slug, description=data.description)
        role.permissions = permissions
        self.session.add(role)
        self.session.flush()

        self._audit.log(
            AuditEventType.ROLE_CREATED,
            actor_id=actor_id,
            metadata={"role_name": data.name},
        )
        self.session.commit()
        return role

    def update(
        self, role_id: uuid.UUID, data: RoleUpdate, *, actor_id: uuid.UUID | None = None
    ) -> Role:
        role = self._roles.get_with_permissions(role_id)
        if role is None:
            raise NotFoundError("Role not found.")

        if data.name is not None:
            if self._roles.name_exists(data.name, exclude_id=role_id):
                raise ConflictError("A role with that name already exists.")
            role.name = data.name
            role.slug = _slugify(data.name)

        if data.description is not None:
            role.description = data.description

        self._audit.log(
            AuditEventType.ROLE_UPDATED, actor_id=actor_id, metadata={"role_id": str(role_id)}
        )
        self.session.commit()
        return role

    def delete(self, role_id: uuid.UUID, *, actor_id: uuid.UUID | None = None) -> None:
        role = self._roles.get(role_id)
        if role is None:
            raise NotFoundError("Role not found.")
        if role.is_system:
            raise PermissionDeniedError("System roles cannot be deleted.")

        self.session.delete(role)
        self._audit.log(
            AuditEventType.ROLE_DELETED, actor_id=actor_id, metadata={"role_id": str(role_id)}
        )
        self.session.commit()

    def assign_permissions(
        self,
        role_id: uuid.UUID,
        permission_ids: list[uuid.UUID],
        *,
        actor_id: uuid.UUID | None = None,
    ) -> Role:
        role = self._roles.get_with_permissions(role_id)
        if role is None:
            raise NotFoundError("Role not found.")

        permissions = self._permissions.get_by_ids(permission_ids)
        role.permissions = permissions

        self._audit.log(
            AuditEventType.PERMISSION_CHANGED,
            actor_id=actor_id,
            metadata={
                "role_id": str(role_id),
                "permission_ids": [str(p) for p in permission_ids],
            },
        )
        self.session.commit()
        return role

    def get_all(self) -> list[Role]:
        return self._roles.list_all()

    def get(self, role_id: uuid.UUID) -> Role:
        role = self._roles.get_with_permissions(role_id)
        if role is None:
            raise NotFoundError("Role not found.")
        return role
