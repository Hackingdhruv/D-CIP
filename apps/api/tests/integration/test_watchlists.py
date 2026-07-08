"""Integration tests for the Watchlist API endpoints."""

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
    WatchlistEntryListResponse,
    WatchlistEntryRead,
    WatchlistListResponse,
    WatchlistRead,
    WatchlistStats,
)
from app.services.watchlist_service import WatchlistService


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
    perms = permissions or ["watchlist:read", "watchlist:write"]
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


def _mock_watchlist_read() -> WatchlistRead:
    return WatchlistRead(
        id=uuid.uuid4(),
        name="Suspect Emails",
        description="Email addresses of interest",
        watchlist_type="email",
        is_active=True,
        case_id=None,
        created_by_id=uuid.uuid4(),
        created_by_email="admin@example.com",
        entry_count=5,
        alert_count=3,
        created_at=_now(),
        updated_at=_now(),
    )


def _mock_entry_read(watchlist_id: uuid.UUID | None = None) -> WatchlistEntryRead:
    return WatchlistEntryRead(
        id=uuid.uuid4(),
        watchlist_id=watchlist_id or uuid.uuid4(),
        value="suspect@criminal.org",
        normalized_value="suspect@criminal.org",
        is_regex=False,
        description=None,
        is_active=True,
        hit_count=2,
        created_by_id=uuid.uuid4(),
        created_at=_now(),
        updated_at=_now(),
    )


# ── GET /watchlists/stats ─────────────────────────────────────────────────────

def test_get_watchlist_stats_returns_200(app, client):
    user = _make_user()
    stats = WatchlistStats(
        total_watchlists=5,
        active_watchlists=4,
        total_entries=20,
        total_alerts=15,
        alerts_today=3,
        alerts_this_week=10,
        top_hit_watchlists=[],
    )
    with _as_user(app, user), patch.object(WatchlistService, "get_stats", return_value=stats):
        resp = client.get("/api/v1/watchlists/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["totalWatchlists"] == 5
    assert data["activeWatchlists"] == 4


# ── GET /watchlists ───────────────────────────────────────────────────────────

def test_list_watchlists_returns_200(app, client):
    user = _make_user()
    response_obj = WatchlistListResponse(
        items=[_mock_watchlist_read()],
        total=1,
        page=1,
        pages=1,
    )
    with _as_user(app, user), patch.object(WatchlistService, "list_watchlists", return_value=response_obj):
        resp = client.get("/api/v1/watchlists")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Suspect Emails"


def test_list_watchlists_403_without_permission(app, client):
    user = _make_user(permissions=["alert:read"])
    with _as_user(app, user):
        resp = client.get("/api/v1/watchlists")
    assert resp.status_code == 403


# ── POST /watchlists ──────────────────────────────────────────────────────────

def test_create_watchlist_returns_201(app, client):
    user = _make_user()
    wl = _mock_watchlist_read()
    with _as_user(app, user), patch.object(WatchlistService, "create_watchlist", return_value=wl):
        resp = client.post(
            "/api/v1/watchlists",
            json={"name": "Suspect Emails", "watchlistType": "email"},
        )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Suspect Emails"


def test_create_watchlist_403_without_write_permission(app, client):
    user = _make_user(permissions=["watchlist:read"])
    with _as_user(app, user):
        resp = client.post(
            "/api/v1/watchlists",
            json={"name": "Test", "watchlistType": "email"},
        )
    assert resp.status_code == 403


# ── GET /watchlists/{id} ──────────────────────────────────────────────────────

def test_get_watchlist_by_id_returns_200(app, client):
    user = _make_user()
    wl = _mock_watchlist_read()
    with _as_user(app, user), patch.object(WatchlistService, "get_watchlist_read", return_value=wl):
        resp = client.get(f"/api/v1/watchlists/{wl.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(wl.id)


def test_get_watchlist_by_id_returns_404(app, client):
    user = _make_user()
    from fastapi import HTTPException
    with _as_user(app, user), patch.object(
        WatchlistService,
        "get_watchlist_read",
        side_effect=HTTPException(status_code=404, detail="Watchlist not found"),
    ):
        resp = client.get(f"/api/v1/watchlists/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── PUT /watchlists/{id} ──────────────────────────────────────────────────────

def test_update_watchlist_returns_200(app, client):
    user = _make_user()
    wl = _mock_watchlist_read()
    with _as_user(app, user), patch.object(WatchlistService, "update_watchlist", return_value=wl):
        resp = client.put(
            f"/api/v1/watchlists/{wl.id}",
            json={"name": "Updated"},
        )
    assert resp.status_code == 200


# ── DELETE /watchlists/{id} ───────────────────────────────────────────────────

def test_delete_watchlist_returns_204(app, client):
    user = _make_user()
    with _as_user(app, user), patch.object(WatchlistService, "delete_watchlist", return_value=None):
        resp = client.delete(f"/api/v1/watchlists/{uuid.uuid4()}")
    assert resp.status_code == 204


# ── GET /watchlists/{id}/entries ──────────────────────────────────────────────

def test_list_entries_returns_200(app, client):
    user = _make_user()
    wl_id = uuid.uuid4()
    response_obj = WatchlistEntryListResponse(
        items=[_mock_entry_read(wl_id)],
        total=1,
    )
    with _as_user(app, user), patch.object(WatchlistService, "list_entries", return_value=response_obj):
        resp = client.get(f"/api/v1/watchlists/{wl_id}/entries")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ── POST /watchlists/{id}/entries ─────────────────────────────────────────────

def test_add_entry_returns_201(app, client):
    user = _make_user()
    wl_id = uuid.uuid4()
    entry = _mock_entry_read(wl_id)
    with _as_user(app, user), patch.object(WatchlistService, "add_entry", return_value=entry):
        resp = client.post(
            f"/api/v1/watchlists/{wl_id}/entries",
            json={"value": "suspect@criminal.org"},
        )
    assert resp.status_code == 201
    assert resp.json()["value"] == "suspect@criminal.org"


# ── DELETE /watchlists/entries/{id} ──────────────────────────────────────────

def test_delete_entry_returns_204(app, client):
    user = _make_user()
    with _as_user(app, user), patch.object(WatchlistService, "delete_entry", return_value=None):
        resp = client.delete(f"/api/v1/watchlists/entries/{uuid.uuid4()}")
    assert resp.status_code == 204
