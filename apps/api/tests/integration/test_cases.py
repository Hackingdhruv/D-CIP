"""Integration tests for case management endpoints."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.dependencies import _get_current_user
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.security.password import hash_password
from app.main import create_app
from app.models.case import Case, CaseStatus
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app() -> FastAPI:
    return create_app()


@pytest.fixture(scope="module")
def client(app: FastAPI) -> TestClient:
    with TestClient(app) as c:
        yield c


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_permission(resource: str, action: str) -> Permission:
    p = Permission(resource=resource, action=action)
    p.id = uuid.uuid4()
    return p


def _make_role(permissions: list[str]) -> Role:
    r = Role(name="Investigator", slug="investigator", is_system=False)
    r.id = uuid.uuid4()
    r.permissions = [_make_permission(*p.split(":")) for p in permissions]
    r.created_at = datetime.now(timezone.utc)
    r.updated_at = datetime.now(timezone.utc)
    return r


def _make_user(permissions: list[str] | None = None) -> User:
    u = User(
        email="investigator@example.com",
        username="investigator",
        full_name="Test Investigator",
        password_hash=hash_password("Test@1234!"),
    )
    u.id = uuid.uuid4()
    u.roles = [_make_role(permissions)] if permissions else []
    u.refresh_tokens = []
    u.password_reset_tokens = []
    u.sessions = []
    u.audit_events = []
    u.avatar_url = None
    u.last_login_at = None
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    return u


def _make_case(owner_id: uuid.UUID) -> Case:
    c = Case(
        reference_number="CASE-2026-0001",
        title="Test Investigation",
        status=CaseStatus.OPEN.value,
        priority="medium",
        is_private=False,
        is_starred=False,
        owner_id=owner_id,
        created_by_id=owner_id,
    )
    c.id = uuid.uuid4()
    c.tags = []
    c.description = None
    c.category = None
    c.assignments = []
    c.tasks = []
    c.notes = []
    c.closed_at = None
    c.archived_at = None
    c.deleted_at = None
    c.created_at = datetime.now(timezone.utc)
    c.updated_at = datetime.now(timezone.utc)
    # Set owner + created_by as proper User objects
    c.owner = MagicMock(spec=User)
    c.owner.id = owner_id
    c.owner.full_name = "Test Investigator"
    c.owner.email = "investigator@example.com"
    c.owner.username = "investigator"
    c.owner.avatar_url = None
    c.owner.is_active = True
    c.owner.is_locked = False
    c.owner.last_login_at = None
    c.owner.created_at = datetime.now(timezone.utc)
    c.owner.roles = []
    c.created_by = c.owner
    return c


@contextmanager
def _as_user(app: FastAPI, user: User):
    app.dependency_overrides[_get_current_user] = lambda: user
    try:
        yield
    finally:
        app.dependency_overrides.pop(_get_current_user, None)


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestCasesEndpoints:
    def test_list_cases_without_auth_returns_401(self, client: TestClient) -> None:
        res = client.get("/api/v1/cases")
        assert res.status_code == 401

    def test_list_cases_without_permission_returns_403(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=[])  # no case:read
        with _as_user(app, user):
            res = client.get("/api/v1/cases")
        assert res.status_code == 403

    def test_list_cases_returns_list(self, app: FastAPI, client: TestClient) -> None:
        user = _make_user(permissions=["case:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.cases.CaseService") as MockSvc:
                from app.schemas.case import CaseListResponse
                MockSvc.return_value.list_cases.return_value = CaseListResponse(
                    items=[], total=0, page=1, page_size=20, pages=1
                )
                res = client.get("/api/v1/cases")
        assert res.status_code == 200
        body = res.json()
        assert "items" in body
        assert body["total"] == 0

    def test_create_case_without_permission_returns_403(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["case:read"])  # only read, not create
        with _as_user(app, user):
            res = client.post("/api/v1/cases", json={"title": "Test"})
        assert res.status_code == 403

    def test_create_case_missing_title_returns_422(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["case:create"])
        with _as_user(app, user):
            res = client.post("/api/v1/cases", json={})
        assert res.status_code == 422

    def test_create_case_success(self, app: FastAPI, client: TestClient) -> None:
        user = _make_user(permissions=["case:create"])
        case = _make_case(owner_id=user.id)
        with _as_user(app, user):
            with patch("app.api.v1.routes.cases.CaseService") as MockSvc:
                MockSvc.return_value.create.return_value = case
                res = client.post("/api/v1/cases", json={"title": "New Investigation"})
        assert res.status_code == 201
        body = res.json()
        assert body["referenceNumber"] == "CASE-2026-0001"
        assert body["title"] == "Test Investigation"

    def test_get_case_not_found_returns_404(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["case:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.cases.CaseService") as MockSvc:
                MockSvc.return_value.get.side_effect = NotFoundError("Case not found.")
                res = client.get(f"/api/v1/cases/{uuid.uuid4()}")
        assert res.status_code == 404

    def test_get_case_private_denied_returns_403(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["case:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.cases.CaseService") as MockSvc:
                MockSvc.return_value.get.side_effect = PermissionDeniedError(
                    "Private case."
                )
                res = client.get(f"/api/v1/cases/{uuid.uuid4()}")
        assert res.status_code == 403

    def test_delete_case_requires_permission(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["case:read", "case:update"])
        with _as_user(app, user):
            res = client.delete(f"/api/v1/cases/{uuid.uuid4()}")
        assert res.status_code == 403

    def test_create_task_missing_title_returns_422(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["case:read", "case:update"])
        with _as_user(app, user):
            res = client.post(f"/api/v1/cases/{uuid.uuid4()}/tasks", json={})
        assert res.status_code == 422

    def test_create_note_missing_title_returns_422(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["case:read", "case:update"])
        with _as_user(app, user):
            res = client.post(f"/api/v1/cases/{uuid.uuid4()}/notes", json={})
        assert res.status_code == 422

    def test_assign_users_requires_case_assign_permission(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["case:read", "case:update"])
        with _as_user(app, user):
            res = client.put(
                f"/api/v1/cases/{uuid.uuid4()}/assignments",
                json={"assignments": []},
            )
        assert res.status_code == 403
