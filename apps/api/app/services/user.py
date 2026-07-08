"""User management service."""

from __future__ import annotations

import math
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security.password import hash_password
from app.models.auth_audit_event import AuditEventType
from app.models.user import User
from app.repositories.audit import AuditRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.schemas.user import UserCreate, UserListResponse, UserReadSlim, UserUpdate
from app.services.base import BaseService


class UserService(BaseService):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self._users = UserRepository(session)
        self._roles = RoleRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._sessions = UserSessionRepository(session)
        self._audit = AuditRepository(session)

    def create(self, data: UserCreate, *, actor_id: uuid.UUID | None = None) -> User:
        email = data.email.lower()
        username = data.username.lower()

        if self._users.email_exists(email):
            raise ConflictError("Email address is already registered.")
        if self._users.username_exists(username):
            raise ConflictError("Username is already taken.")

        roles = self._roles.get_by_ids(data.role_ids) if data.role_ids else []

        user = User(
            email=email,
            username=username,
            full_name=data.full_name,
            password_hash=hash_password(data.password),
        )
        user.roles = roles
        self.session.add(user)
        self.session.flush()

        self._audit.log(
            AuditEventType.USER_CREATED,
            user_id=user.id,
            actor_id=actor_id,
            metadata={"email": email, "username": username},
        )
        self.session.commit()
        return user

    def update(
        self, user_id: uuid.UUID, data: UserUpdate, *, actor_id: uuid.UUID | None = None
    ) -> User:
        user = self._users.get_active(user_id)
        if user is None:
            raise NotFoundError("User not found.")

        if data.email is not None:
            email = data.email.lower()
            if self._users.email_exists(email, exclude_id=user_id):
                raise ConflictError("Email address is already registered.")
            user.email = email

        if data.username is not None:
            username = data.username.lower()
            if self._users.username_exists(username, exclude_id=user_id):
                raise ConflictError("Username is already taken.")
            user.username = username

        if data.full_name is not None:
            user.full_name = data.full_name
        if data.avatar_url is not None:
            user.avatar_url = data.avatar_url

        self._audit.log(
            AuditEventType.USER_UPDATED,
            user_id=user.id,
            actor_id=actor_id,
        )
        self.session.commit()
        return user

    def disable(self, user_id: uuid.UUID, *, actor_id: uuid.UUID | None = None) -> User:
        user = self._users.get_active(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        if actor_id and user_id == actor_id:
            raise ConflictError("Cannot disable your own account.")

        user.is_active = False
        self._refresh_tokens.revoke_all_for_user(user_id)
        self._sessions.deactivate_all_for_user(user_id)
        self._audit.log(
            AuditEventType.USER_DISABLED, user_id=user_id, actor_id=actor_id
        )
        self.session.commit()
        return user

    def enable(self, user_id: uuid.UUID, *, actor_id: uuid.UUID | None = None) -> User:
        user = self._users.get(user_id)
        if user is None or user.is_deleted:
            raise NotFoundError("User not found.")

        user.is_active = True
        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        self._audit.log(
            AuditEventType.USER_ENABLED, user_id=user_id, actor_id=actor_id
        )
        self.session.commit()
        return user

    def soft_delete(self, user_id: uuid.UUID, *, actor_id: uuid.UUID | None = None) -> None:
        user = self._users.get_active(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        if actor_id and user_id == actor_id:
            raise ConflictError("Cannot delete your own account.")

        self._users.soft_delete(user)
        self._refresh_tokens.revoke_all_for_user(user_id)
        self._sessions.deactivate_all_for_user(user_id)
        self._audit.log(
            AuditEventType.USER_DELETED, user_id=user_id, actor_id=actor_id
        )
        self.session.commit()

    def assign_roles(
        self,
        user_id: uuid.UUID,
        role_ids: list[uuid.UUID],
        *,
        actor_id: uuid.UUID | None = None,
    ) -> User:
        user = self._users.get_active(user_id)
        if user is None:
            raise NotFoundError("User not found.")

        roles = self._roles.get_by_ids(role_ids)
        user.roles = roles

        self._audit.log(
            AuditEventType.ROLE_ASSIGNED,
            user_id=user_id,
            actor_id=actor_id,
            metadata={"role_ids": [str(r) for r in role_ids]},
        )
        self.session.commit()
        return user

    def list_users(
        self,
        *,
        q: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> UserListResponse:
        items, total = self._users.search(
            q=q, is_active=is_active, page=page, page_size=page_size
        )
        pages = max(1, math.ceil(total / page_size))
        return UserListResponse(
            items=[UserReadSlim.model_validate(u) for u in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    def get_user(self, user_id: uuid.UUID) -> User:
        user = self._users.get_active(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user
