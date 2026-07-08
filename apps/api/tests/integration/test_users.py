"""Integration tests for user management endpoints."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.dependencies import _get_current_user
from app.core.security.password import hash_password
from app.main import create_app
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission


@pytest.fixture(scope="module")
def app() -> FastAPI:
    return create_app()


@pytest.fixture(scope="module")
def client(app: FastAPI) -> TestClient:
    with TestClient(app) as c:
        yield c


def _make_permission(resource: str, action: str) -> Permission:
    p = Permission(resource=resource, action=action)
    p.id = uuid.uuid4()
    return p


def _make_role(slug: str, *, perms: list[str]) -> Role:
    r = Role(name=slug.title(), slug=slug, is_system=False)
    r.id = uuid.uuid4()
    r.permissions = [_make_permission(*p.split(":")) for p in perms]
    return r


def _admin_user(*, permissions: list[str] = ["user:manage"]) -> User:
    u = User(
        email="admin@dcip.local",
        username="admin",
        full_name="System Administrator",
        password_hash=hash_password("Admin@1234!"),
    )
    u.id = uuid.uuid4()
    u.roles = [_make_role("administrator", perms=permissions)]
    u.refresh_tokens = []
    u.password_reset_tokens = []
    u.sessions = []
    u.audit_events = []
    return u


@contextmanager
def _as_user(app: FastAPI, user: User):
    """Override the current-user dependency for the duration of the block."""
    app.dependency_overrides[_get_current_user] = lambda: user
    try:
        yield
    finally:
        app.dependency_overrides.pop(_get_current_user, None)


class TestUsersEndpoints:
    def test_list_users_without_auth_returns_401(self, client: TestClient) -> None:
        res = client.get("/api/v1/users")
        assert res.status_code == 401

    def test_list_users_without_permission_returns_403(
        self, app: FastAPI, client: TestClient
    ) -> None:
        no_perms_user = _admin_user(permissions=[])
        with _as_user(app, no_perms_user):
            res = client.get("/api/v1/users")
        assert res.status_code == 403

    def test_create_user_missing_fields_returns_422(
        self, app: FastAPI, client: TestClient
    ) -> None:
        admin = _admin_user()
        with _as_user(app, admin):
            res = client.post("/api/v1/users", json={})
        assert res.status_code == 422

    def test_create_user_weak_password_returns_422(
        self, app: FastAPI, client: TestClient
    ) -> None:
        admin = _admin_user()
        with _as_user(app, admin):
            res = client.post(
                "/api/v1/users",
                json={
                    "email": "new@dcip.local",
                    "username": "newuser",
                    "full_name": "New User",
                    "password": "weak",
                },
            )
        assert res.status_code == 422

    def test_get_nonexistent_user_returns_404(
        self, app: FastAPI, client: TestClient
    ) -> None:
        admin = _admin_user()
        with _as_user(app, admin):
            with patch("app.api.v1.routes.users.UserService") as MockSvc:
                from app.core.exceptions import NotFoundError
                MockSvc.return_value.get_user.side_effect = NotFoundError("User not found.")
                res = client.get(f"/api/v1/users/{uuid.uuid4()}")
        assert res.status_code == 404
