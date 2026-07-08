"""Integration tests for Alert and Notification API endpoints."""

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
from app.schemas.watchlist import (
    AlertNotificationRead,
    AlertStats,
    NotificationCount,
    NotificationListResponse,
    WatchlistAlertListResponse,
    WatchlistAlertRead,
)
from app.services.alert_service import AlertService
from app.services.notification_service import NotificationService


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app() -> FastAPI:
    return create_app()


@pytest.fixture(scope="module")
def client(app: FastAPI) -> TestClient:
    with TestClient(app) as c:
        yield c


def _now():
    return datetime.now(timezone.utc)


def _make_permission(name: str) -> Permission:
    resource, action = name.split(":")
    p = Permission(resource=resource, action=action)
    p.id = uuid.uuid4()
    return p


def _make_role(permissions: list[str]) -> Role:
    r = Role(name="Investigator", slug="investigator", is_system=True)
    r.id = uuid.uuid4()
    r.permissions = [_make_permission(p) for p in permissions]
    r.created_at = _now()
    r.updated_at = _now()
    return r


def _make_user(permissions: list[str] | None = None) -> User:
    perms = permissions or ["alert:read", "alert:write", "watchlist:read"]
    u = User(
        email="investigator@example.com",
        username="investigator",
        full_name="Test Investigator",
        password_hash=hash_password("Test@1234!"),
    )
    u.id = uuid.uuid4()
    u.roles = [_make_role(perms)]
    u.refresh_tokens = []
    u.password_reset_tokens = []
    u.sessions = []
    u.audit_events = []
    u.avatar_url = None
    u.is_active = True
    u.is_locked = False
    u.deleted_at = None
    u.locked_until = None
    u.last_login_at = None
    u.failed_login_attempts = 0
    u.created_at = _now()
    u.updated_at = _now()
    return u


@contextmanager
def _as_user(app: FastAPI, user: User):
    app.dependency_overrides[_get_current_user] = lambda: user
    try:
        yield
    finally:
        app.dependency_overrides.pop(_get_current_user, None)


def _mock_alert_read() -> WatchlistAlertRead:
    return WatchlistAlertRead(
        id=uuid.uuid4(),
        watchlist_id=uuid.uuid4(),
        watchlist_entry_id=uuid.uuid4(),
        evidence_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        alert_type="exact_match",
        severity="high",
        title="Watchlist hit: suspect@evil.org",
        description="Email matched watchlist",
        matched_value="suspect@evil.org",
        matched_entity_type="email",
        confidence=1.0,
        status="new",
        is_cross_case=False,
        cross_case_count=0,
        cross_case_accessible=False,
        alert_metadata={},
        acknowledged_at=None,
        resolved_at=None,
        created_at=_now(),
        updated_at=_now(),
        watchlist_name="Suspect Emails",
        evidence_filename="document.pdf",
        case_reference="CASE-2026-001",
    )


# ── GET /alerts/stats ─────────────────────────────────────────────────────────

def test_get_alert_stats_returns_200(app, client):
    user = _make_user()
    stats = AlertStats(
        total=10, new_count=3, acknowledged_count=4, resolved_count=2,
        dismissed_count=1, critical_count=2, high_count=5, cross_case_count=1,
        alerts_today=3, alerts_this_week=8,
    )
    with _as_user(app, user), patch.object(AlertService, "get_stats", return_value=stats):
        resp = client.get("/api/v1/alerts/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    assert data["newCount"] == 3


# ── GET /alerts ───────────────────────────────────────────────────────────────

def test_list_alerts_returns_200(app, client):
    user = _make_user()
    response_obj = WatchlistAlertListResponse(
        items=[_mock_alert_read()],
        total=1, page=1, pages=1, new_count=1, critical_count=0,
    )
    with _as_user(app, user), patch.object(AlertService, "list_alerts", return_value=response_obj):
        resp = client.get("/api/v1/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["alertType"] == "exact_match"


def test_list_alerts_403_no_permission(app, client):
    user = _make_user(permissions=["watchlist:read"])
    with _as_user(app, user):
        resp = client.get("/api/v1/alerts")
    assert resp.status_code == 403


# ── GET /alerts/{id} ──────────────────────────────────────────────────────────

def test_get_alert_by_id_returns_200(app, client):
    user = _make_user()
    alert = _mock_alert_read()
    with _as_user(app, user), patch.object(AlertService, "get_alert", return_value=alert):
        resp = client.get(f"/api/v1/alerts/{alert.id}")
    assert resp.status_code == 200
    assert resp.json()["severity"] == "high"


def test_get_alert_by_id_returns_404(app, client):
    user = _make_user()
    from fastapi import HTTPException
    with _as_user(app, user), patch.object(
        AlertService, "get_alert",
        side_effect=HTTPException(status_code=404, detail="Alert not found"),
    ):
        resp = client.get(f"/api/v1/alerts/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── POST /alerts/{id}/acknowledge ─────────────────────────────────────────────

def test_acknowledge_alert_returns_200(app, client):
    user = _make_user()
    alert = _mock_alert_read()
    ack = WatchlistAlertRead(**{**alert.model_dump(), "status": "acknowledged", "acknowledged_at": _now()})
    with _as_user(app, user), patch.object(AlertService, "acknowledge", return_value=ack):
        resp = client.post(f"/api/v1/alerts/{alert.id}/acknowledge")
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"


# ── POST /alerts/{id}/resolve ─────────────────────────────────────────────────

def test_resolve_alert_returns_200(app, client):
    user = _make_user()
    alert = _mock_alert_read()
    resolved = WatchlistAlertRead(**{**alert.model_dump(), "status": "resolved", "resolved_at": _now()})
    with _as_user(app, user), patch.object(AlertService, "resolve", return_value=resolved):
        resp = client.post(f"/api/v1/alerts/{alert.id}/resolve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


# ── POST /alerts/{id}/dismiss ─────────────────────────────────────────────────

def test_dismiss_alert_returns_200(app, client):
    user = _make_user()
    alert = _mock_alert_read()
    dismissed = WatchlistAlertRead(**{**alert.model_dump(), "status": "dismissed"})
    with _as_user(app, user), patch.object(AlertService, "dismiss", return_value=dismissed):
        resp = client.post(f"/api/v1/alerts/{alert.id}/dismiss")
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"


# ── Notification endpoints ────────────────────────────────────────────────────

def _mock_notification() -> AlertNotificationRead:
    return AlertNotificationRead(
        id=uuid.uuid4(),
        alert_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        title="New alert: suspect@evil.org matched watchlist",
        message="Entity matched watchlist 'Suspect Emails'",
        level="error",
        is_read=False,
        is_archived=False,
        read_at=None,
        created_at=_now(),
    )


def test_get_notification_count_returns_200(app, client):
    user = _make_user()
    count = NotificationCount(unread_count=5)
    with _as_user(app, user), patch.object(NotificationService, "get_count", return_value=count):
        resp = client.get("/api/v1/notifications/count")
    assert resp.status_code == 200
    assert resp.json()["unreadCount"] == 5


def test_list_notifications_returns_200(app, client):
    user = _make_user()
    response_obj = NotificationListResponse(
        items=[_mock_notification()],
        total=1,
        unread_count=1,
    )
    with _as_user(app, user), patch.object(NotificationService, "list_notifications", return_value=response_obj):
        resp = client.get("/api/v1/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["unreadCount"] == 1


def test_mark_all_read_returns_200(app, client):
    user = _make_user()
    with _as_user(app, user), patch.object(NotificationService, "mark_all_read", return_value=3):
        resp = client.post("/api/v1/notifications/read-all")
    assert resp.status_code == 200
    assert resp.json()["marked_read"] == 3


def test_archive_notification_returns_200(app, client):
    user = _make_user()
    with _as_user(app, user), patch.object(NotificationService, "archive", return_value=None):
        resp = client.post(f"/api/v1/notifications/{uuid.uuid4()}/archive")
    assert resp.status_code == 200


def test_delete_notification_returns_204(app, client):
    user = _make_user()
    with _as_user(app, user), patch.object(NotificationService, "delete", return_value=None):
        resp = client.delete(f"/api/v1/notifications/{uuid.uuid4()}")
    assert resp.status_code == 204


# ── RBAC: cross-case alert inaccessible ──────────────────────────────────────

def test_cross_case_alert_inaccessible_cases_not_revealed(app, client):
    user = _make_user()
    alert = WatchlistAlertRead(
        id=uuid.uuid4(),
        watchlist_id=None,
        watchlist_entry_id=None,
        evidence_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        alert_type="cross_case_match",
        severity="high",
        title="Cross-case match detected",
        description="Entity appears in another case",
        matched_value="suspect@evil.org",
        matched_entity_type="email",
        confidence=1.0,
        status="new",
        is_cross_case=True,
        cross_case_count=2,
        cross_case_accessible=False,
        alert_metadata={},
        acknowledged_at=None,
        resolved_at=None,
        created_at=_now(),
        updated_at=_now(),
    )
    with _as_user(app, user), patch.object(AlertService, "get_alert", return_value=alert):
        resp = client.get(f"/api/v1/alerts/{alert.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["crossCaseAccessible"] is False
    assert data["crossCaseCount"] == 2
