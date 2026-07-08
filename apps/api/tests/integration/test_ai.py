"""Integration tests for AI Intelligence Engine endpoints."""

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


_CASE_ID = uuid.uuid4()
_AI_BASE = f"/api/v1/cases/{_CASE_ID}/ai"


# ── Auth guards ────────────────────────────────────────────────────────────────

class TestAiAuth:
    def test_summary_without_auth_returns_401(self, client: TestClient) -> None:
        res = client.get(f"{_AI_BASE}/summary")
        assert res.status_code == 401

    def test_entities_without_auth_returns_401(self, client: TestClient) -> None:
        res = client.get(f"{_AI_BASE}/entities")
        assert res.status_code == 401

    def test_chat_without_auth_returns_401(self, client: TestClient) -> None:
        res = client.post(f"{_AI_BASE}/chat", json={"message": "Hello"})
        assert res.status_code == 401

    def test_summary_without_permission_returns_403(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=[])
        with _as_user(app, user):
            res = client.get(f"{_AI_BASE}/summary")
        assert res.status_code == 403


# ── Case summary ───────────────────────────────────────────────────────────────

class TestCaseSummary:
    def test_get_summary_returns_null_when_none(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["evidence:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.ai.AIIntelligenceService") as MockSvc:
                MockSvc.return_value.get_case_summary.return_value = None
                res = client.get(f"{_AI_BASE}/summary")
        assert res.status_code == 200
        assert res.json() is None

    def test_regenerate_returns_404_for_missing_case(
        self, app: FastAPI, client: TestClient
    ) -> None:
        from app.core.exceptions import NotFoundError
        user = _make_user(permissions=["evidence:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.ai.AIIntelligenceService") as MockSvc:
                MockSvc.return_value.regenerate_case_summary.side_effect = NotFoundError("not found")
                res = client.post(f"{_AI_BASE}/summary/regenerate")
        assert res.status_code == 404


# ── Entities ───────────────────────────────────────────────────────────────────

class TestEntities:
    def test_list_entities_returns_response(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["evidence:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.ai.AIIntelligenceService") as MockSvc:
                MockSvc.return_value.list_entities.return_value = ([], 0)
                res = client.get(f"{_AI_BASE}/entities")
        assert res.status_code == 200
        body = res.json()
        assert "items" in body
        assert body["total"] == 0


# ── Keywords ───────────────────────────────────────────────────────────────────

class TestKeywords:
    def test_list_keywords_returns_response(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["evidence:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.ai.AIIntelligenceService") as MockSvc:
                MockSvc.return_value.list_keywords.return_value = ([], 0)
                res = client.get(f"{_AI_BASE}/keywords")
        assert res.status_code == 200
        assert res.json()["total"] == 0


# ── Timeline ───────────────────────────────────────────────────────────────────

class TestTimeline:
    def test_list_timeline_returns_response(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["evidence:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.ai.AIIntelligenceService") as MockSvc:
                MockSvc.return_value.list_timeline.return_value = ([], 0)
                res = client.get(f"{_AI_BASE}/timeline")
        assert res.status_code == 200
        assert res.json()["total"] == 0


# ── Chat ───────────────────────────────────────────────────────────────────────

class TestChat:
    def test_chat_returns_ai_message(
        self, app: FastAPI, client: TestClient
    ) -> None:
        from app.models.ai_chat_message import AiChatMessage

        user = _make_user(permissions=["evidence:read"])
        reply = AiChatMessage(
            case_id=_CASE_ID,
            role="assistant",
            content="AI is not configured.",
            evidence_references=[],
        )
        reply.id = uuid.uuid4()
        reply.user_id = None
        reply.model_used = None
        reply.created_at = datetime.now(timezone.utc)

        with _as_user(app, user):
            with patch("app.api.v1.routes.ai.AIIntelligenceService") as MockSvc:
                MockSvc.return_value.chat.return_value = reply
                res = client.post(f"{_AI_BASE}/chat", json={"message": "Summarize the case."})
        assert res.status_code == 200
        body = res.json()
        assert body["role"] == "assistant"

    def test_chat_validates_empty_message(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["evidence:read"])
        with _as_user(app, user):
            res = client.post(f"{_AI_BASE}/chat", json={"message": ""})
        assert res.status_code == 422


# ── Search ─────────────────────────────────────────────────────────────────────

class TestSearch:
    def test_search_returns_response(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["evidence:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.ai.AIIntelligenceService") as MockSvc:
                MockSvc.return_value.search_evidence.return_value = []
                res = client.get(f"{_AI_BASE}/search?q=fraud")
        assert res.status_code == 200
        body = res.json()
        assert body["query"] == "fraud"
        assert body["results"] == []


# ── Processing status ──────────────────────────────────────────────────────────

class TestProcessingStatus:
    def test_processing_status_returns_list(
        self, app: FastAPI, client: TestClient
    ) -> None:
        user = _make_user(permissions=["evidence:read"])
        with _as_user(app, user):
            with patch("app.api.v1.routes.ai.AIIntelligenceService") as MockSvc:
                MockSvc.return_value.get_processing_status.return_value = []
                res = client.get(f"{_AI_BASE}/processing-status")
        assert res.status_code == 200
        assert res.json() == []
