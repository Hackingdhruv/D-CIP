"""Authentication service."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.security.jwt import TokenError, TokenType, create_access_token, create_refresh_token, decode_token
from app.core.security.password import hash_password, needs_rehash, verify_password
from app.models.auth_audit_event import AuditEventType
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.audit import AuditRepository
from app.repositories.password_reset import PasswordResetRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.services.base import BaseService

logger = get_logger(__name__)

_MAX_FAILED_ATTEMPTS = 5
_LOCK_DURATION_MINUTES = 15
_RESET_TOKEN_EXPIRE_MINUTES = 60
_SESSION_EXPIRE_MINUTES = 10080  # 7 days


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class AuthService(BaseService):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._reset_tokens = PasswordResetRepository(session)
        self._sessions = UserSessionRepository(session)
        self._audit = AuditRepository(session)

    def login(
        self,
        email: str,
        password: str,
        *,
        remember_me: bool = False,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str, User]:
        """Authenticate a user. Returns (access_token, refresh_token, user)."""
        user = self._users.get_by_email(email)
        if user is None:
            self._audit.log(
                AuditEventType.LOGIN_FAILED,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"email": email, "reason": "user_not_found"},
            )
            self.session.commit()
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            self._audit.log(
                AuditEventType.LOGIN_FAILED,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"reason": "account_inactive"},
            )
            self.session.commit()
            raise AuthenticationError("Account is disabled.")

        now = datetime.now(tz=timezone.utc)
        if user.is_locked and user.locked_until and user.locked_until > now:
            remaining = int((user.locked_until - now).total_seconds() / 60)
            self._audit.log(
                AuditEventType.LOGIN_FAILED,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"reason": "account_locked"},
            )
            self.session.commit()
            raise AuthenticationError(
                f"Account locked. Try again in {remaining} minute(s)."
            )

        if not verify_password(password, user.password_hash):
            self._users.increment_failed_attempts(user)
            if user.failed_login_attempts >= _MAX_FAILED_ATTEMPTS:
                locked_until = now + timedelta(minutes=_LOCK_DURATION_MINUTES)
                self._users.lock(user, locked_until)
                self._audit.log(
                    AuditEventType.ACCOUNT_LOCKED,
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            self._audit.log(
                AuditEventType.LOGIN_FAILED,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"attempts": user.failed_login_attempts},
            )
            self.session.commit()
            raise AuthenticationError("Invalid email or password.")

        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        self._users.record_login(user)

        role_slugs = [r.slug for r in user.roles]
        # Access tokens are always short-lived regardless of remember_me.
        # remember_me only extends the refresh token (30 days vs 7 days).
        access_token = create_access_token(
            str(user.id),
            extra_claims={"roles": role_slugs, "email": user.email},
        )
        raw_refresh, refresh_token_record = self._create_refresh_token(
            user, ip_address=ip_address, user_agent=user_agent, remember_me=remember_me
        )

        self._create_session(user, ip_address=ip_address, user_agent=user_agent, remember_me=remember_me)

        self._audit.log(
            AuditEventType.LOGIN_SUCCESS,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.commit()
        return access_token, raw_refresh, user

    def refresh(
        self,
        raw_refresh_token: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str, User]:
        """Rotate refresh token. Returns (new_access_token, new_refresh_token, user)."""
        try:
            payload = decode_token(raw_refresh_token, expected_type=TokenType.REFRESH)
        except TokenError:
            raise AuthenticationError("Invalid or expired refresh token.")

        jti = payload.get("jti", "")
        stored = self._refresh_tokens.get_by_jti(jti)
        if stored is None or stored.is_revoked:
            raise AuthenticationError("Refresh token has been revoked.")

        now = datetime.now(tz=timezone.utc)
        if stored.expires_at < now:
            raise AuthenticationError("Refresh token has expired.")

        self._refresh_tokens.revoke(stored)

        user = self._users.get_active(stored.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User account is inactive.")

        role_slugs = [r.slug for r in user.roles]
        new_access = create_access_token(
            str(user.id), extra_claims={"roles": role_slugs, "email": user.email}
        )
        new_raw_refresh, _ = self._create_refresh_token(
            user, ip_address=ip_address, user_agent=user_agent
        )

        self._audit.log(
            AuditEventType.TOKEN_REFRESHED,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.commit()
        return new_access, new_raw_refresh, user

    def logout(
        self,
        raw_refresh_token: str | None,
        user_id: uuid.UUID,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        if raw_refresh_token:
            try:
                payload = decode_token(raw_refresh_token, expected_type=TokenType.REFRESH)
                jti = payload.get("jti", "")
                stored = self._refresh_tokens.get_by_jti(jti)
                if stored and not stored.is_revoked:
                    self._refresh_tokens.revoke(stored)
            except TokenError:
                pass

        self._sessions.deactivate_all_for_user(user_id)
        self._audit.log(
            AuditEventType.LOGOUT,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.commit()

    def forgot_password(
        self, email: str, *, ip_address: str | None = None
    ) -> str | None:
        """Initiate password reset. Returns raw token (only in dev; production sends email)."""
        user = self._users.get_by_email(email)
        if user is None:
            return None

        self._reset_tokens.invalidate_all_for_user(user.id)

        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=_RESET_TOKEN_EXPIRE_MINUTES)

        reset = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
        )
        self.session.add(reset)
        self._audit.log(
            AuditEventType.PASSWORD_RESET_REQUESTED,
            user_id=user.id,
            ip_address=ip_address,
        )
        self.session.commit()

        if settings.debug:
            logger.info("Password reset token for %s: %s", email, raw_token)

        return raw_token

    def reset_password(
        self,
        raw_token: str,
        new_password: str,
        *,
        ip_address: str | None = None,
    ) -> None:
        token_hash = _hash_token(raw_token)
        reset = self._reset_tokens.get_valid_by_hash(token_hash)
        if reset is None:
            raise AuthenticationError("Invalid or expired password reset token.")

        user = self._users.get_active(reset.user_id)
        if user is None:
            raise AuthenticationError("User not found.")

        user.password_hash = hash_password(new_password)
        self._reset_tokens.mark_used(reset)
        self._refresh_tokens.revoke_all_for_user(user.id)
        self._sessions.deactivate_all_for_user(user.id)

        self._audit.log(
            AuditEventType.PASSWORD_RESET_COMPLETED,
            user_id=user.id,
            ip_address=ip_address,
        )
        self.session.commit()

    def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
        *,
        ip_address: str | None = None,
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect.")

        if verify_password(new_password, user.password_hash):
            raise ConflictError("New password must differ from the current password.")

        user.password_hash = hash_password(new_password)
        self._refresh_tokens.revoke_all_for_user(user.id)

        self._audit.log(
            AuditEventType.PASSWORD_CHANGED,
            user_id=user.id,
            ip_address=ip_address,
        )
        self.session.commit()

    def get_current_user(self, access_token: str) -> User:
        """Validate access token and return the associated user."""
        try:
            payload = decode_token(access_token, expected_type=TokenType.ACCESS)
        except TokenError as exc:
            raise AuthenticationError(str(exc))

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationError("Token missing subject.")

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise AuthenticationError("Invalid token subject.")

        user = self._users.get_active(user_id)
        if user is None:
            raise AuthenticationError("User not found.")
        if not user.is_active:
            raise AuthenticationError("Account is disabled.")

        return user

    def _create_refresh_token(
        self,
        user: User,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        remember_me: bool = False,
    ) -> tuple[str, RefreshToken]:
        raw_token = secrets.token_urlsafe(64)
        role_slugs = [r.slug for r in user.roles]
        # 30 days for "remember me", 7 days default
        refresh_expire = timedelta(days=30) if remember_me else timedelta(minutes=settings.refresh_token_expire_minutes)
        jwt_refresh = create_refresh_token(
            str(user.id), extra_claims={"roles": role_slugs}, expires_delta=refresh_expire
        )
        try:
            payload = decode_token(jwt_refresh, expected_type=TokenType.REFRESH)
            jti = payload["jti"]
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        except TokenError:
            jti = uuid.uuid4().hex
            exp = datetime.now(tz=timezone.utc) + timedelta(
                minutes=settings.refresh_token_expire_minutes
            )

        token_hash = _hash_token(jwt_refresh)
        record = RefreshToken(
            jti=jti,
            user_id=user.id,
            token_hash=token_hash,
            expires_at=exp,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(record)
        self.session.flush()
        return jwt_refresh, record

    def _create_session(
        self,
        user: User,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        remember_me: bool = False,
    ) -> UserSession:
        session_token = secrets.token_urlsafe(32)
        session_expire = timedelta(days=30) if remember_me else timedelta(minutes=_SESSION_EXPIRE_MINUTES)
        expires_at = datetime.now(tz=timezone.utc) + session_expire
        session = UserSession(
            user_id=user.id,
            session_token=session_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )
        self.session.add(session)
        self.session.flush()
        return session
