"""User management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import RequirePermission, SessionDep
from app.schemas.role import AssignRolesRequest
from app.schemas.user import UserCreate, UserListResponse, UserRead, UserUpdate
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])

_MANAGE = RequirePermission("user:manage")


@router.get("", response_model=UserListResponse, summary="List users")
def list_users(
    session: SessionDep,
    _= _MANAGE,
    q: str | None = Query(default=None, description="Search term"),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> UserListResponse:
    svc = UserService(session)
    return svc.list_users(q=q, is_active=is_active, page=page, page_size=page_size)


@router.post(
    "", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="Create user"
)
def create_user(
    body: UserCreate,
    session: SessionDep,
    current_user= _MANAGE,
) -> UserRead:
    svc = UserService(session)
    user = svc.create(body, actor_id=current_user.id)
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead, summary="Get user")
def get_user(
    user_id: uuid.UUID,
    session: SessionDep,
    _= _MANAGE,
) -> UserRead:
    svc = UserService(session)
    user = svc.get_user(user_id)
    return UserRead.model_validate(user)


@router.put("/{user_id}", response_model=UserRead, summary="Update user")
def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    session: SessionDep,
    current_user= _MANAGE,
) -> UserRead:
    svc = UserService(session)
    user = svc.update(user_id, body, actor_id=current_user.id)
    return UserRead.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete user",
)
def delete_user(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user= _MANAGE,
) -> None:
    svc = UserService(session)
    svc.soft_delete(user_id, actor_id=current_user.id)


@router.post(
    "/{user_id}/enable",
    response_model=UserRead,
    summary="Enable user",
)
def enable_user(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user= _MANAGE,
) -> UserRead:
    svc = UserService(session)
    user = svc.enable(user_id, actor_id=current_user.id)
    return UserRead.model_validate(user)


@router.post(
    "/{user_id}/disable",
    response_model=UserRead,
    summary="Disable user",
)
def disable_user(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user= _MANAGE,
) -> UserRead:
    svc = UserService(session)
    user = svc.disable(user_id, actor_id=current_user.id)
    return UserRead.model_validate(user)


@router.post(
    "/{user_id}/unlock",
    response_model=UserRead,
    summary="Unlock a locked user account",
)
def unlock_user(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user= _MANAGE,
) -> UserRead:
    svc = UserService(session)
    user = svc.enable(user_id, actor_id=current_user.id)
    return UserRead.model_validate(user)


@router.put("/{user_id}/roles", response_model=UserRead, summary="Assign roles to user")
def assign_roles(
    user_id: uuid.UUID,
    body: AssignRolesRequest,
    session: SessionDep,
    current_user= _MANAGE,
) -> UserRead:
    svc = UserService(session)
    user = svc.assign_roles(user_id, body.role_ids, actor_id=current_user.id)
    return UserRead.model_validate(user)
