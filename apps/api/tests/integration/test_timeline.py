"""Integration tests for the Investigation Timeline endpoints.

These mirror the AI-engine integration tests: the service layer is mocked so the
tests exercise routing, permission guards, and response shaping without a live
database.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
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
from app.schemas.timeline import (
    TimelineAnalysisResponse,
    TimelineListResponse,
    TimelineStatsResponse,
)


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


def _make_user(permissions: list[str] | None = None) -> User:
    r = Role(name="Investigator", slug="investigator", is_system=False)
    r.id = uuid.uuid4()
    r.permissions = [_make_permission(*p.split(":")) for p in (permissions or [])]
    r.created_at = datetime.now(timezone.utc)
    r.updated_at = datetime.now(timezone.utc)

    u = User(
        email="inv@example.com",
        username="inv",
        full_name="Test Investigator",
        password_hash=hash_password("Test@1234!"),
    )
    u.id = uuid.uuid4()
    u.roles = [r]
    u.refresh_tokens = []
    u.password_reset_tokens = []
    u.sessions = []
    u.audit_events = []
    u.avatar_url = None
    u.last_login_at = None
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    return u


@contextmanager
def _as_user(app: FastAPI, user: User):
    app.dependency_overrides[_get_current_user] = lambda: user
    try:
        yield
    finally:
        app.dependency_overrides.pop(_get_current_user, None)


_CASE_ID = uuid.uuid4()
_BASE = f"/api/v1/cases/{_CASE_ID}/timeline"
_PATCH = "app.api.v1.routes.timeline.TimelineService"


def _empty_list() -> TimelineListResponse:
    return TimelineListResponse(items=[], total=0, page=1, page_size=100, pages=1)


# ── Auth guards ──────────────────────────────────────────────────────────────────

class TestTimelineAuth:
    def test_list_without_auth_returns_401(self, client: TestClient) -> None:
        assert client.get(_BASE).status_code == 401

    def test_list_without_permission_returns_403(self, app: FastAPI, client: TestClient) -> None:
        with _as_user(app, _make_user(permissions=[])):
            assert client.get(_BASE).status_code == 403

    def test_create_requires_write(self, app: FastAPI, client: TestClient) -> None:
        with _as_user(app, _make_user(permissions=["timeline:read"])):
            res = client.post(_BASE, json={"event_type": "meeting", "title": "X"})
        assert res.status_code == 403

    def test_merge_requires_manage(self, app: FastAPI, client: TestClient) -> None:
        with _as_user(app, _make_user(permissions=["timeline:read", "timeline:write"])):
            res = client.post(
                f"{_BASE}/merge",
                json={"primary_id": str(uuid.uuid4()), "merge_ids": [str(uuid.uuid4())]},
            )
        assert res.status_code == 403


# ── List / stats / analysis ──────────────────────────────────────────────────────

class TestTimelineRead:
    def test_list_returns_response(self, app: FastAPI, client: TestClient) -> None:
        with _as_user(app, _make_user(permissions=["timeline:read"])):
            with patch(_PATCH) as MockSvc:
                MockSvc.return_value.list_events.return_value = _empty_list()
                res = client.get(_BASE)
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 0 and "items" in body

    def test_stats_returns_response(self, app: FastAPI, client: TestClient) -> None:
        stats = TimelineStatsResponse(
            total_events=0, verified=0, pinned=0, bookmarked=0,
            ai_generated=0, manual=0, by_category={}, by_type={}, by_source={},
        )
        with _as_user(app, _make_user(permissions=["timeline:read"])):
            with patch(_PATCH) as MockSvc:
                MockSvc.return_value.stats.return_value = stats
                res = client.get(f"{_BASE}/stats")
        assert res.status_code == 200
        assert res.json()["totalEvents"] == 0

    def test_analysis_returns_response(self, app: FastAPI, client: TestClient) -> None:
        analysis = TimelineAnalysisResponse(
            analyzed_events=0, gaps=[], conflicts=[], duplicates=[],
            clusters=[], inactivity=[], groups=[],
        )
        with _as_user(app, _make_user(permissions=["timeline:read"])):
            with patch(_PATCH) as MockSvc:
                MockSvc.return_value.analyze.return_value = analysis
                res = client.get(f"{_BASE}/analysis")
        assert res.status_code == 200
        assert res.json()["analyzedEvents"] == 0


# ── Export ───────────────────────────────────────────────────────────────────────

class TestTimelineExport:
    def test_export_json(self, app: FastAPI, client: TestClient) -> None:
        with _as_user(app, _make_user(permissions=["timeline:read"])):
            with patch(_PATCH) as MockSvc:
                MockSvc.return_value.export.return_value = (
                    b'{"events": []}', "application/json", "timeline.json",
                )
                res = client.get(f"{_BASE}/export?format=json")
        assert res.status_code == 200
        assert "attachment" in res.headers.get("content-disposition", "")


# ── Create ───────────────────────────────────────────────────────────────────────

class TestTimelineCreate:
    def test_create_event_invokes_service(self, app: FastAPI, client: TestClient) -> None:
        from app.models.timeline_event import TimelineEvent

        event = TimelineEvent(
            case_id=_CASE_ID,
            source_type="manual",
            event_type="meeting",
            category="communication",
            title="Kickoff meeting",
            confidence=1.0,
            verification_status="verified",
            tags=[],
            entities=[],
            attachments=[],
        )
        event.id = uuid.uuid4()
        event.is_pinned = False
        event.is_bookmarked = False
        event.is_merged = False
        event.created_at = datetime.now(timezone.utc)
        event.updated_at = datetime.now(timezone.utc)

        with _as_user(app, _make_user(permissions=["timeline:write"])):
            with patch(_PATCH) as MockSvc:
                MockSvc.return_value.create_event.return_value = event
                res = client.post(
                    _BASE,
                    json={"event_type": "meeting", "title": "Kickoff meeting"},
                )
        assert res.status_code == 201
        assert res.json()["title"] == "Kickoff meeting"
