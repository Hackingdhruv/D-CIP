"""Unit tests for AuthService business logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security.password import hash_password
from app.models.user import User
from app.services.auth import AuthService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(
    *,
    email: str = "analyst@dcip.local",
    password: str = "Test@1234!",
    is_active: bool = True,
    is_locked: bool = False,
    failed_login_attempts: int = 0,
) -> User:
    u = User(
        email=email,
        username="analyst",
        full_name="Test Analyst",
        password_hash=hash_password(password),
        is_active=is_active,
        is_locked=is_locked,
        failed_login_attempts=failed_login_attempts,
    )
    u.id = uuid.uuid4()
    u.roles = []
    u.refresh_tokens = []
    u.password_reset_tokens = []
    u.sessions = []
    u.audit_events = []
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    return u


def _make_service() -> tuple[AuthService, MagicMock]:
    """Return (service, mock_session). Bypasses __init__ to avoid real DB."""
    db = MagicMock()
    db.commit = MagicMock()
    db.add = MagicMock()
    db.flush = MagicMock()
    svc = AuthService.__new__(AuthService)
    svc.session = db
    return svc, db


def _wire_login_repos(svc: AuthService, user: User | None) -> None:
    svc._users = MagicMock()
    svc._users.get_by_email = MagicMock(return_value=user)
    svc._users.get_active = MagicMock(return_value=user)
    svc._users.increment_failed_attempts = MagicMock()
    svc._users.lock = MagicMock()
    svc._users.record_login = MagicMock()
    svc._refresh_tokens = MagicMock()
    svc._refresh_tokens.create = MagicMock(return_value=MagicMock(jti="jti", token="rt"))
    svc._sessions = MagicMock()
    svc._sessions.create = MagicMock(return_value=MagicMock())
    svc._audit = MagicMock()
    svc._audit.log = MagicMock()
    svc._reset_tokens = MagicMock()


# ── Login ─────────────────────────────────────────────────────────────────────

class TestAuthServiceLogin:
    def test_unknown_email_raises_authentication_error(self) -> None:
        svc, _ = _make_service()
        _wire_login_repos(svc, None)
        with pytest.raises(AuthenticationError):
            svc.login(email="nobody@dcip.local", password="Test@1234!")

    def test_wrong_password_raises_authentication_error(self) -> None:
        user = _make_user()
        svc, _ = _make_service()
        _wire_login_repos(svc, user)
        with pytest.raises(AuthenticationError):
            svc.login(email=user.email, password="WrongPass@1!")

    def test_inactive_user_raises_authentication_error(self) -> None:
        user = _make_user(is_active=False)
        svc, _ = _make_service()
        _wire_login_repos(svc, user)
        with pytest.raises(AuthenticationError):
            svc.login(email=user.email, password="Test@1234!")

    def test_locked_user_raises_with_locked_message(self) -> None:
        from datetime import timedelta
        user = _make_user(is_locked=True)
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
        svc, _ = _make_service()
        _wire_login_repos(svc, user)
        with pytest.raises(AuthenticationError, match="locked"):
            svc.login(email=user.email, password="Test@1234!")

    def test_successful_login_returns_access_refresh_user(self) -> None:
        user = _make_user()
        svc, _ = _make_service()
        _wire_login_repos(svc, user)
        with (
            patch("app.services.auth.create_access_token", return_value="access-tok"),
            patch("app.services.auth.create_refresh_token", return_value="refresh-tok"),
        ):
            access, refresh, returned_user = svc.login(
                email=user.email,
                password="Test@1234!",
                ip_address="127.0.0.1",
                user_agent="pytest",
            )
        assert access == "access-tok"
        assert refresh == "refresh-tok"
        assert returned_user is user

    def test_successful_login_calls_record_login(self) -> None:
        user = _make_user(failed_login_attempts=3)
        svc, _ = _make_service()
        _wire_login_repos(svc, user)
        with (
            patch("app.services.auth.create_access_token", return_value="at"),
            patch("app.services.auth.create_refresh_token", return_value="rt"),
        ):
            svc.login(email=user.email, password="Test@1234!")
        svc._users.record_login.assert_called_once()


# ── Change Password ────────────────────────────────────────────────────────────

class TestChangePassword:
    def _wire(self, svc: AuthService) -> None:
        svc._refresh_tokens = MagicMock()
        svc._refresh_tokens.revoke_all_for_user = MagicMock()
        svc._audit = MagicMock()
        svc._audit.log = MagicMock()

    def test_wrong_current_raises_authentication_error(self) -> None:
        user = _make_user(password="Test@1234!")
        svc, _ = _make_service()
        self._wire(svc)
        with pytest.raises(AuthenticationError):
            svc.change_password(user, "WrongCurrent!1", "NewPass@9!")

    def test_same_as_current_raises_conflict(self) -> None:
        user = _make_user(password="Test@1234!")
        svc, _ = _make_service()
        self._wire(svc)
        with pytest.raises(ConflictError):
            svc.change_password(user, "Test@1234!", "Test@1234!")

    def test_success_updates_password_hash(self) -> None:
        user = _make_user(password="Test@1234!")
        old_hash = user.password_hash
        svc, _ = _make_service()
        self._wire(svc)
        svc.change_password(user, "Test@1234!", "NewPass@9!")
        assert user.password_hash != old_hash

    def test_success_revokes_all_refresh_tokens(self) -> None:
        user = _make_user(password="Test@1234!")
        svc, _ = _make_service()
        self._wire(svc)
        svc.change_password(user, "Test@1234!", "NewPass@9!")
        svc._refresh_tokens.revoke_all_for_user.assert_called_once_with(user.id)


# ── Forgot / Reset Password ───────────────────────────────────────────────────

class TestForgotResetPassword:
    def test_forgot_unknown_email_returns_none_silently(self) -> None:
        svc, _ = _make_service()
        svc._users = MagicMock()
        svc._users.get_by_email = MagicMock(return_value=None)
        svc._audit = MagicMock()
        svc._audit.log = MagicMock()
        result = svc.forgot_password(email="ghost@dcip.local")
        assert result is None

    def test_reset_invalid_token_raises(self) -> None:
        svc, _ = _make_service()
        svc._reset_tokens = MagicMock()
        svc._reset_tokens.get_valid_by_hash = MagicMock(return_value=None)
        svc._audit = MagicMock()
        svc._audit.log = MagicMock()
        with pytest.raises(AuthenticationError):
            svc.reset_password(raw_token="invalid-token", new_password="NewPass@9!")

    def test_reset_valid_token_updates_password(self) -> None:
        user = _make_user(password="Test@1234!")
        old_hash = user.password_hash
        tok = MagicMock()
        tok.user_id = user.id
        svc, _ = _make_service()
        svc._reset_tokens = MagicMock()
        svc._reset_tokens.get_valid_by_hash = MagicMock(return_value=tok)
        svc._reset_tokens.mark_used = MagicMock()
        svc._users = MagicMock()
        svc._users.get_active = MagicMock(return_value=user)
        svc._refresh_tokens = MagicMock()
        svc._refresh_tokens.revoke_all_for_user = MagicMock()
        svc._sessions = MagicMock()
        svc._sessions.deactivate_all_for_user = MagicMock()
        svc._audit = MagicMock()
        svc._audit.log = MagicMock()
        svc.reset_password(raw_token="valid-token", new_password="NewPass@9!")
        assert user.password_hash != old_hash
        svc._reset_tokens.mark_used.assert_called_once_with(tok)
