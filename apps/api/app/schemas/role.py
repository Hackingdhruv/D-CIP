"""Role schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.permission import PermissionRead


class RoleBase(BaseSchema):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class RoleCreate(RoleBase):
    permission_ids: list[uuid.UUID] = Field(default_factory=list)


class RoleUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None


class RoleRead(BaseSchema):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    is_system: bool
    permissions: list[PermissionRead]
    created_at: datetime
    updated_at: datetime


class RoleReadSlim(BaseSchema):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    is_system: bool


class AssignPermissionsRequest(BaseSchema):
    permission_ids: list[uuid.UUID]


class AssignRolesRequest(BaseSchema):
    role_ids: list[uuid.UUID]
