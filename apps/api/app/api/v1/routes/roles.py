"""Role management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.core.dependencies import RequirePermission, SessionDep
from app.schemas.role import AssignPermissionsRequest, RoleCreate, RoleRead, RoleUpdate
from app.services.role import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])

_MANAGE = RequirePermission("user:manage")


@router.get("", response_model=list[RoleRead], summary="List all roles")
def list_roles(
    session: SessionDep,
    _= _MANAGE,
) -> list[RoleRead]:
    svc = RoleService(session)
    return [RoleRead.model_validate(r) for r in svc.get_all()]


@router.post(
    "", response_model=RoleRead, status_code=status.HTTP_201_CREATED, summary="Create role"
)
def create_role(
    body: RoleCreate,
    session: SessionDep,
    current_user= _MANAGE,
) -> RoleRead:
    svc = RoleService(session)
    role = svc.create(body, actor_id=current_user.id)
    return RoleRead.model_validate(role)


@router.get("/{role_id}", response_model=RoleRead, summary="Get role")
def get_role(
    role_id: uuid.UUID,
    session: SessionDep,
    _= _MANAGE,
) -> RoleRead:
    svc = RoleService(session)
    return RoleRead.model_validate(svc.get(role_id))


@router.put("/{role_id}", response_model=RoleRead, summary="Update role")
def update_role(
    role_id: uuid.UUID,
    body: RoleUpdate,
    session: SessionDep,
    current_user= _MANAGE,
) -> RoleRead:
    svc = RoleService(session)
    return RoleRead.model_validate(svc.update(role_id, body, actor_id=current_user.id))


@router.delete(
    "/{role_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete role"
)
def delete_role(
    role_id: uuid.UUID,
    session: SessionDep,
    current_user= _MANAGE,
) -> None:
    svc = RoleService(session)
    svc.delete(role_id, actor_id=current_user.id)


@router.put(
    "/{role_id}/permissions",
    response_model=RoleRead,
    summary="Assign permissions to role",
)
def assign_permissions(
    role_id: uuid.UUID,
    body: AssignPermissionsRequest,
    session: SessionDep,
    current_user= _MANAGE,
) -> RoleRead:
    svc = RoleService(session)
    role = svc.assign_permissions(role_id, body.permission_ids, actor_id=current_user.id)
    return RoleRead.model_validate(role)
