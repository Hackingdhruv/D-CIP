"""Integration tests for authentication endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.security.password import hash_password
from app.main import create_app
from app.models.user import User


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(create_app()) as c:
        yield c


def _make_user(
    email: str = "investigator@example.com",
    password: str = "Test@1234!",
    is_active: bool = True,
    is_locked: bool = False,
) -> User:
    from datetime import datetime, timezone
    u = User(
        email=email,
        username="investigator",
        full_name="Test Investigator",
        password_hash=hash_password(password),
        is_active=is_active,
        is_locked=is_locked,
    )
    u.id = uuid.uuid4()
    u.roles = []
    u.refresh_tokens = []
    u.password_reset_tokens = []
    u.sessions = []
    u.audit_events = []
    u.avatar_url = None
    u.last_login_at = None
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    return u


# ── Login ──────────────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_returns_422_for_missing_fields(self, client: TestClient) -> None:
        res = client.post("/api/v1/auth/login", json={})
        assert res.status_code == 422

    def test_login_with_invalid_email_returns_422(self, client: TestClient) -> None:
        res = client.post("/api/v1/auth/login", json={"email": "not-email", "password": "pw"})
        assert res.status_code == 422

    def test_login_wrong_credentials_returns_401(self, client: TestClient) -> None:
        with patch("app.api.v1.routes.auth.AuthService") as MockSvc:
            from app.core.exceptions import AuthenticationError
            MockSvc.return_value.login.side_effect = AuthenticationError("Invalid email or password.")
            res = client.post(
                "/api/v1/auth/login",
                json={"email": "noone@example.com", "password": "Wrong@1!"},
            )
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "authentication_required"

    def test_login_success_sets_user_in_response(self, client: TestClient) -> None:
        user = _make_user()
        with patch("app.api.v1.routes.auth.AuthService") as MockSvc:
            MockSvc.return_value.login.return_value = (
                "fake-access-token",
                "fake-refresh-token",
                user,
            )
            res = client.post(
                "/api/v1/auth/login",
                json={"email": "investigator@example.com", "password": "Test@1234!"},
            )
        assert res.status_code == 200
        body = res.json()
        assert "user" in body
        assert body["tokenType"] == "bearer"


# ── Forgot Password ────────────────────────────────────────────────────────────

class TestForgotPassword:
    def test_forgot_password_always_returns_200(self, client: TestClient) -> None:
        with patch("app.api.v1.routes.auth.AuthService") as MockSvc:
            MockSvc.return_value.forgot_password.return_value = None
            res = client.post(
                "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
            )
        assert res.status_code == 200
        assert "message" in res.json()

    def test_forgot_password_invalid_email_returns_422(self, client: TestClient) -> None:
        res = client.post("/api/v1/auth/forgot-password", json={"email": "not-an-email"})
        assert res.status_code == 422


# ── Reset Password ─────────────────────────────────────────────────────────────

class TestResetPassword:
    def test_reset_password_missing_fields_returns_422(self, client: TestClient) -> None:
        res = client.post("/api/v1/auth/reset-password", json={"token": "tok"})
        assert res.status_code == 422

    def test_reset_password_weak_password_returns_422(self, client: TestClient) -> None:
        res = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "tok", "new_password": "weak"},
        )
        assert res.status_code == 422

    def test_reset_password_invalid_token_returns_401(self, client: TestClient) -> None:
        with patch("app.api.v1.routes.auth.AuthService") as MockSvc:
            from app.core.exceptions import AuthenticationError
            MockSvc.return_value.reset_password.side_effect = AuthenticationError("Invalid token.")
            res = client.post(
                "/api/v1/auth/reset-password",
                json={"token": "bad-token", "new_password": "NewPass@1!"},
            )
        assert res.status_code == 401


# ── Protected endpoints ────────────────────────────────────────────────────────

class TestProtectedEndpoints:
    def test_get_me_without_auth_returns_401(self, client: TestClient) -> None:
        res = client.get("/api/v1/me")
        assert res.status_code == 401
