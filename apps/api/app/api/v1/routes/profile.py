"""Current-user profile endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.dependencies import CurrentUserDep, SessionDep
from app.core.exceptions import NotFoundError
from app.repositories.user_session import UserSessionRepository
from app.schemas.session import UserSessionRead
from app.schemas.user import ProfileUpdate, UserRead
from app.services.user import UserService

router = APIRouter(prefix="/me", tags=["profile"])

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 MB
_UPLOADS_DIR = Path("uploads/avatars")


@router.get("", response_model=UserRead, summary="Get my profile")
def get_profile(current_user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(current_user)


@router.put("", response_model=UserRead, summary="Update my profile")
def update_profile(
    body: ProfileUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> UserRead:
    from app.schemas.user import UserUpdate

    svc = UserService(session)
    update_data = UserUpdate(
        full_name=body.full_name,
        avatar_url=body.avatar_url,
    )
    user = svc.update(current_user.id, update_data, actor_id=current_user.id)
    return UserRead.model_validate(user)


@router.post("/avatar", response_model=UserRead, summary="Upload profile avatar")
async def upload_avatar(
    file: UploadFile,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> UserRead:
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, WebP or GIF images are accepted.",
        )

    content = await file.read()
    if len(content) > _MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Avatar must be smaller than 5 MB.",
        )

    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ext = (file.filename or "avatar").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "jpg"
    filename = f"{current_user.id}.{ext}"
    dest = _UPLOADS_DIR / filename
    dest.write_bytes(content)

    avatar_url = f"/uploads/avatars/{filename}"

    from app.schemas.user import UserUpdate
    svc = UserService(session)
    user = svc.update(current_user.id, UserUpdate(avatar_url=avatar_url), actor_id=current_user.id)
    return UserRead.model_validate(user)


@router.get("/sessions", response_model=list[UserSessionRead], summary="List my active sessions")
def list_sessions(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[UserSessionRead]:
    repo = UserSessionRepository(session)
    sessions = repo.list_active_for_user(current_user.id)
    return [UserSessionRead.model_validate(s) for s in sessions]


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a specific session",
)
def revoke_session(
    session_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> None:
    repo = UserSessionRepository(session)
    from sqlalchemy import select
    from app.models.user_session import UserSession
    stmt = select(UserSession).where(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id,
    )
    user_session = session.execute(stmt).scalar_one_or_none()
    if user_session is None:
        raise NotFoundError("Session not found.")
    repo.deactivate(user_session)
    session.commit()


@router.delete(
    "/sessions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke all other sessions",
)
def revoke_all_sessions(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> None:
    repo = UserSessionRepository(session)
    repo.deactivate_all_for_user(current_user.id)
    session.commit()
