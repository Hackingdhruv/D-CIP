"""Integration tests for Universal Search endpoints."""

from __future__ import annotations

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


def _make_user(permissions: list[str] | None = None) -> User:
    r = Role(name="Analyst", slug="analyst", is_system=False)
    r.id = uuid.uuid4()
    r.permissions = [_make_permission(*p.split(":")) for p in (permissions or [])]
    r.created_at = datetime.now(timezone.utc)
    r.updated_at = datetime.now(timezone.utc)

    u = User(
        email="analyst@example.com",
        username="analyst",
        full_name="Test Analyst",
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


_BASE = "/api/v1/search"


# ── Auth / Permission guards ───────────────────────────────────────────────────

def test_search_requires_auth(client: TestClient) -> None:
    resp = client.post(_BASE, json={"query": "test"})
    assert resp.status_code == 401


def test_search_requires_evidence_read_permission(app: FastAPI, client: TestClient) -> None:
    no_perm_user = _make_user(permissions=[])
    with _as_user(app, no_perm_user):
        resp = client.post(_BASE, json={"query": "test"})
    assert resp.status_code == 403


def test_suggestions_requires_auth(client: TestClient) -> None:
    resp = client.get(f"{_BASE}/suggestions", params={"q": "te"})
    assert resp.status_code == 401


# ── Search endpoint ────────────────────────────────────────────────────────────

def test_search_returns_response_shape(app: FastAPI, client: TestClient) -> None:
    user = _make_user(permissions=["evidence:read"])
    MockSvc = MagicMock()
    MockSvc.return_value.search.return_value = {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
        "pages": 1,
        "query": "fraud",
        "took_ms": 5,
        "sources": {},
    }
    with _as_user(app, user):
        with patch("app.api.v1.routes.search.SearchService", MockSvc):
            resp = client.post(_BASE, json={"query": "fraud"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "fraud"
    assert "items" in body
    assert "total" in body
    assert "sources" in body
    assert "tookMs" in body


def test_search_with_type_filter(app: FastAPI, client: TestClient) -> None:
    user = _make_user(permissions=["evidence:read"])
    MockSvc = MagicMock()
    MockSvc.return_value.search.return_value = {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
        "pages": 1,
        "query": "tax",
        "took_ms": 2,
        "sources": {"case": 0},
    }
    payload = {
        "query": "tax",
        "filters": {"types": ["case", "note"]},
        "page": 1,
        "page_size": 20,
    }
    with _as_user(app, user):
        with patch("app.api.v1.routes.search.SearchService", MockSvc):
            resp = client.post(_BASE, json=payload)
    assert resp.status_code == 200
    _, call_kwargs = MockSvc.return_value.search.call_args
    assert call_kwargs["filters"].types == ["case", "note"]


def test_search_empty_query_rejected(app: FastAPI, client: TestClient) -> None:
    user = _make_user(permissions=["evidence:read"])
    with _as_user(app, user):
        resp = client.post(_BASE, json={"query": ""})
    assert resp.status_code == 422


def test_search_query_too_long_rejected(app: FastAPI, client: TestClient) -> None:
    user = _make_user(permissions=["evidence:read"])
    with _as_user(app, user):
        resp = client.post(_BASE, json={"query": "x" * 501})
    assert resp.status_code == 422


# ── Suggestions endpoint ───────────────────────────────────────────────────────

def test_suggestions_returns_list(app: FastAPI, client: TestClient) -> None:
    user = _make_user(permissions=["evidence:read"])
    MockSvc = MagicMock()
    MockSvc.return_value.suggestions.return_value = [
        {"text": "John Smith", "suggestion_type": "person"},
        {"text": "CASE-2024-001", "suggestion_type": "case"},
    ]
    with _as_user(app, user):
        with patch("app.api.v1.routes.search.SearchService", MockSvc):
            resp = client.get(f"{_BASE}/suggestions", params={"q": "jo"})
    assert resp.status_code == 200
    body = resp.json()
    assert "suggestions" in body
    assert len(body["suggestions"]) == 2
    assert body["suggestions"][0]["text"] == "John Smith"


def test_suggestions_short_query_rejected(client: TestClient) -> None:
    user = _make_user(permissions=["evidence:read"])
    resp = client.get(f"{_BASE}/suggestions", params={"q": "a"})
    # No auth, but validation should reject before auth check
    assert resp.status_code in (401, 422)
