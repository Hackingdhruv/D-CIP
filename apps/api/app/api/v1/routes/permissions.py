"""Permission listing endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import RequirePermission, SessionDep
from app.schemas.permission import PermissionRead
from app.services.permission import PermissionService

router = APIRouter(prefix="/permissions", tags=["permissions"])

_MANAGE = RequirePermission("user:manage")


@router.get("", response_model=list[PermissionRead], summary="List all permissions")
def list_permissions(
    session: SessionDep,
    _= _MANAGE,
) -> list[PermissionRead]:
    svc = PermissionService(session)
    return [PermissionRead.model_validate(p) for p in svc.get_all()]
