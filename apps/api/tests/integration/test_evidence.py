"""Integration tests for evidence management endpoints."""

from __future__ import annotations

import io
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.dependencies import _get_current_user
from app.core.security.password import hash_password
from app.main import create_app
from app.models.evidence import Evidence, EvidenceStatus
from app.models.user import User as UserModel
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
    r = Role(name="Analyst", slug="analyst", is_system=False)
    r.id = uuid.uuid4()
    r.permissions = [_make_permission(*p.split(":")) for p in permissions]
    r.created_at = datetime.now(timezone.utc)
    r.updated_at = datetime.now(timezone.utc)
    return r


def _make_user(permissions: list[str] | None = None) -> User:
    u = User(
        email="analyst@example.com",
        username="analyst",
        full_name="Test Analyst",
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


def _make_evidence(case_id: uuid.UUID, uploaded_by: User) -> Evidence:
    """Build a real Evidence model instance — same pattern as test_cases._make_case."""
    eid = uuid.uuid4()
    ev = Evidence(
        case_id=case_id,
        original_filename="evidence.pdf",
        storage_path=f"evidence/{case_id}/{eid}.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_extension="pdf",
        sha256_hash="a" * 64,
        uploaded_by_id=uploaded_by.id,
    )
    ev.id = eid
    ev.status = EvidenceStatus.COMPLETED.value
    ev.tags = []
    ev.priority = "medium"
    ev.is_starred = False
    ev.source = None
    ev.classification = None
    ev.notes = None
    ev.is_starred = False
    ev.deleted_at = None
    ev.processing_error = None
    ev.processing_started_at = None
    ev.processing_completed_at = None
    ev.extracted_metadata = {}
    ev.created_at = datetime.now(timezone.utc)
    ev.updated_at = datetime.now(timezone.utc)

    # Wire the relationship to a controlled mock — same as test_cases uses for owner
    uploader = MagicMock(spec=User)
    uploader.id = uploaded_by.id
    uploader.full_name = uploaded_by.full_name
    uploader.email = uploaded_by.email
    uploader.username = uploaded_by.username
    uploader.avatar_url = None
    uploader.is_active = True
    uploader.is_locked = False
    uploader.last_login_at = None
    uploader.created_at = datetime.now(timezone.utc)
    uploader.roles = []
    ev.uploaded_by = uploader
    return ev


@contextmanager
def _as_user(app: FastAPI, user: User):
    app.dependency_overrides[_get_current_user] = lambda: user
    try:
        yield
    finally:
        app.dependency_overrides.pop(_get_current_user, None)


_CASE_ID = uuid.uuid4()
_EVIDENCE_PATH = f"/api/v1/cases/{_CASE_ID}/evidence"


# ── Auth / permission guards ───────────────────────────────────────────────────

class TestEvidenceAuth:
    def test_list_without_auth_returns_401(self, client: TestClient) -> None:
        res = client.get(_EVIDENCE_PATH)
        assert res.status_code == 401

    def test_list_without_permission_returns_403(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=[])
        with _as_user(app, user):
            res = client.get(_EVIDENCE_PATH)
        assert res.status_code == 403

    def test_upload_without_permission_returns_403(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["evidence:read"])  # read only
        with _as_user(app, user):
            res = client.post(
                _EVIDENCE_PATH,
                files={"files": ("test.txt", b"hello", "text/plain")},
            )
        assert res.status_code == 403

    def test_delete_without_permission_returns_403(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["evidence:read", "evidence:update"])
        with _as_user(app, user):
            res = client.delete(f"{_EVIDENCE_PATH}/{uuid.uuid4()}")
        assert res.status_code == 403


# ── List evidence ──────────────────────────────────────────────────────────────

class TestListEvidence:
    def test_list_returns_response(self, app: FastAPI, client: TestClient) -> None:
        user = _make_user(permissions=["evidence:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.evidence.EvidenceService") as MockSvc:
                from app.schemas.evidence import EvidenceListResponse
                MockSvc.return_value.list_evidence.return_value = EvidenceListResponse(
                    items=[], total=0, page=1, page_size=50, pages=1
                )
                res = client.get(_EVIDENCE_PATH)
        assert res.status_code == 200
        body = res.json()
        assert "items" in body
        assert body["total"] == 0


# ── Get evidence ───────────────────────────────────────────────────────────────

class TestGetEvidence:
    def test_not_found_returns_404(self, app: FastAPI, client: TestClient) -> None:
        from app.core.exceptions import NotFoundError
        user = _make_user(permissions=["evidence:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.evidence.EvidenceService") as MockSvc:
                MockSvc.return_value.get.side_effect = NotFoundError("Not found")
                res = client.get(f"{_EVIDENCE_PATH}/{uuid.uuid4()}")
        assert res.status_code == 404

    def test_get_returns_evidence(self, app: FastAPI, client: TestClient) -> None:
        user = _make_user(permissions=["evidence:read"])
        ev = _make_evidence(_CASE_ID, user)
        with _as_user(app, user):
            with patch("app.api.v1.routes.evidence.EvidenceService") as MockSvc:
                MockSvc.return_value.get.return_value = ev
                res = client.get(f"{_EVIDENCE_PATH}/{ev.id}")
        assert res.status_code == 200
        body = res.json()
        assert body["sha256Hash"] == "a" * 64


# ── Delete evidence ────────────────────────────────────────────────────────────

class TestDeleteEvidence:
    def test_delete_returns_204(self, app: FastAPI, client: TestClient) -> None:
        user = _make_user(permissions=["evidence:delete"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.evidence.EvidenceService") as MockSvc:
                MockSvc.return_value.delete.return_value = None
                res = client.delete(f"{_EVIDENCE_PATH}/{uuid.uuid4()}")
        assert res.status_code == 204


# ── Update evidence ────────────────────────────────────────────────────────────

class TestUpdateEvidence:
    def test_update_returns_evidence(self, app: FastAPI, client: TestClient) -> None:
        user = _make_user(permissions=["evidence:update"])
        ev = _make_evidence(_CASE_ID, user)
        ev.tags = ["financial"]
        with _as_user(app, user):
            with patch("app.api.v1.routes.evidence.EvidenceService") as MockSvc:
                MockSvc.return_value.update.return_value = ev
                res = client.put(
                    f"{_EVIDENCE_PATH}/{ev.id}",
                    json={"tags": ["financial"]},
                )
        assert res.status_code == 200

    def test_update_without_permission_returns_403(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["evidence:read"])
        with _as_user(app, user):
            res = client.put(
                f"{_EVIDENCE_PATH}/{uuid.uuid4()}",
                json={"tags": ["financial"]},
            )
        assert res.status_code == 403


# ── Verify hash ────────────────────────────────────────────────────────────────

class TestVerifyEvidence:
    def test_verify_returns_result(self, app: FastAPI, client: TestClient) -> None:
        user = _make_user(permissions=["evidence:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.evidence.EvidenceService") as MockSvc:
                MockSvc.return_value.verify_hash.return_value = {
                    "matches": True,
                    "original_hash": "a" * 64,
                    "computed_hash": "a" * 64,
                }
                res = client.post(f"{_EVIDENCE_PATH}/{uuid.uuid4()}/verify")
        assert res.status_code == 200
        body = res.json()
        assert body["matches"] is True


# ── Chain of custody ───────────────────────────────────────────────────────────

class TestCustodyLog:
    def test_custody_returns_list(self, app: FastAPI, client: TestClient) -> None:
        user = _make_user(permissions=["evidence:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.evidence.EvidenceService") as MockSvc:
                MockSvc.return_value.get_custody.return_value = ([], 0)
                res = client.get(f"{_EVIDENCE_PATH}/{uuid.uuid4()}/custody")
        assert res.status_code == 200
        assert isinstance(res.json(), list)


# ── Preview ────────────────────────────────────────────────────────────────────

class TestPreviewEvidence:
    def test_preview_unavailable_for_unknown(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["evidence:read"])
        ev = _make_evidence(_CASE_ID, user)
        ev.mime_type = "application/octet-stream"
        ev.file_extension = "bin"
        with _as_user(app, user):
            with patch("app.api.v1.routes.evidence.EvidenceService") as MockSvc:
                with patch("app.api.v1.routes.evidence.Path") as MockPath:
                    MockSvc.return_value.get.return_value = ev
                    # Simulate file not found in storage
                    mock_path = MagicMock()
                    mock_path.exists.return_value = False
                    MockPath.return_value.__truediv__ = lambda s, o: mock_path
                    res = client.get(f"{_EVIDENCE_PATH}/{ev.id}/preview")
        assert res.status_code == 200
        assert res.json()["type"] == "unavailable"
