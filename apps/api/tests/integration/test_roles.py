"""Integration tests for role management endpoints."""

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
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User


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


def _make_role(name: str = "Test Role", is_system: bool = False) -> Role:
    from datetime import datetime, timezone
    r = Role(name=name, slug=name.lower().replace(" ", "_"), description="Test role")
    r.id = uuid.uuid4()
    r.is_system = is_system
    r.permissions = []
    r.created_at = datetime.now(timezone.utc)
    r.updated_at = datetime.now(timezone.utc)
    return r


def _admin_user(*, permissions: list[str] = ["role:manage", "user:manage"]) -> User:
    from app.models.role import Role as R

    u = User(
        email="admin@dcip.local",
        username="admin",
        full_name="System Administrator",
        password_hash=hash_password("Admin@1234!"),
    )
    u.id = uuid.uuid4()
    admin_role = R(name="Administrator", slug="administrator", is_system=True)
    admin_role.id = uuid.uuid4()
    admin_role.permissions = [_make_permission(*p.split(":")) for p in permissions]
    u.roles = [admin_role]
    u.refresh_tokens = []
    u.password_reset_tokens = []
    u.sessions = []
    u.audit_events = []
    return u


@contextmanager
def _as_user(app: FastAPI, user: User):
    app.dependency_overrides[_get_current_user] = lambda: user
    try:
        yield
    finally:
        app.dependency_overrides.pop(_get_current_user, None)


class TestRolesEndpoints:
    def test_list_roles_without_auth_returns_401(self, client: TestClient) -> None:
        res = client.get("/api/v1/roles")
        assert res.status_code == 401

    def test_list_roles_returns_list(self, app: FastAPI, client: TestClient) -> None:
        admin = _admin_user()
        with _as_user(app, admin):
            with patch("app.api.v1.routes.roles.RoleService") as MockSvc:
                MockSvc.return_value.get_all.return_value = [_make_role()]
                res = client.get("/api/v1/roles")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_create_role_missing_name_returns_422(
        self, app: FastAPI, client: TestClient
    ) -> None:
        admin = _admin_user()
        with _as_user(app, admin):
            res = client.post("/api/v1/roles", json={})
        assert res.status_code == 422

    def test_delete_system_role_returns_403(
        self, app: FastAPI, client: TestClient
    ) -> None:
        admin = _admin_user()
        with _as_user(app, admin):
            with patch("app.api.v1.routes.roles.RoleService") as MockSvc:
                from app.core.exceptions import PermissionDeniedError
                MockSvc.return_value.delete.side_effect = PermissionDeniedError(
                    "System roles cannot be deleted."
                )
                res = client.delete(f"/api/v1/roles/{uuid.uuid4()}")
        assert res.status_code == 403
