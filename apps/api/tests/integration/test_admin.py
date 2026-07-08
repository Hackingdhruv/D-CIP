"""Integration tests for Enterprise Administration API endpoints."""

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
from app.schemas.admin import (
    AdminOverviewStats,
    AdminUserListResponse,
    AiConfigRead,
    AiUsageStats,
    AuditSearchResponse,
    AuditStats,
    RecommendationsResponse,
    SecurityOverview,
    SessionListResponse,
    StorageOverview,
    SystemHealthResponse,
)
from app.services.admin_service import AdminService


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app() -> FastAPI:
    return create_app()


@pytest.fixture(scope="module")
def client(app: FastAPI) -> TestClient:
    with TestClient(app) as c:
        yield c


# ── Factories ─────────────────────────────────────────────────────────────────

def _make_permission(resource: str, action: str) -> Permission:
    p = Permission(resource=resource, action=action)
    p.id = uuid.uuid4()
    return p


def _make_role(permissions: list[str]) -> Role:
    r = Role(name="Admin", slug="administrator", is_system=True)
    r.id = uuid.uuid4()
    r.permissions = [_make_permission(*p.split(":")) for p in permissions]
    r.created_at = datetime.now(timezone.utc)
    r.updated_at = datetime.now(timezone.utc)
    return r


def _make_admin_user(permissions: list[str] | None = None) -> User:
    perms = permissions or ["admin:read", "admin:write"]
    u = User(
        email="sysadmin@example.com",
        username="sysadmin",
        full_name="System Administrator",
        password_hash=hash_password("Test@1234!"),
    )
    u.id = uuid.uuid4()
    u.roles = [_make_role(perms)]
    u.refresh_tokens = []
    u.password_reset_tokens = []
    u.sessions = []
    u.audit_events = []
    u.avatar_url = None
    u.last_login_at = None
    u.is_locked = False
    u.failed_login_attempts = 0
    u.locked_until = None
    u.deleted_at = None
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    return u


def _make_readonly_user() -> User:
    return _make_admin_user(["admin:read"])


def _make_no_perm_user() -> User:
    u = _make_admin_user([])
    u.roles = []
    return u


@contextmanager
def _as_user(app: FastAPI, user: User):
    app.dependency_overrides[_get_current_user] = lambda: user
    try:
        yield
    finally:
        app.dependency_overrides.pop(_get_current_user, None)


def _make_stats() -> AdminOverviewStats:
    return AdminOverviewStats(
        total_users=100,
        active_users=90,
        locked_users=2,
        inactive_users=10,
        total_roles=5,
        total_permissions=18,
        active_sessions=45,
        audit_events_today=150,
        failed_logins_24h=3,
        evidence_items=1200,
        total_cases=55,
        system_status="healthy",
        generated_at=datetime.now(timezone.utc),
    )


# ── Overview ──────────────────────────────────────────────────────────────────

class TestAdminStats:
    def test_returns_200_for_admin_read(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user), patch.object(AdminService, "get_overview_stats", return_value=_make_stats()):
            resp = client.get("/api/v1/admin/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "totalUsers" in data
        assert data["totalUsers"] == 100
        assert data["systemStatus"] == "healthy"

    def test_returns_403_without_permission(self, client: TestClient, app: FastAPI):
        user = _make_no_perm_user()
        with _as_user(app, user):
            resp = client.get("/api/v1/admin/stats")
        assert resp.status_code == 403


# ── Identity Administration ───────────────────────────────────────────────────

class TestAdminUsers:
    def _list_response(self) -> AdminUserListResponse:
        return AdminUserListResponse(items=[], total=0, page=1, page_size=25, pages=1)

    def test_list_users_200(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user), patch.object(AdminService, "list_users", return_value=self._list_response()):
            resp = client.get("/api/v1/admin/users")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] == 0

    def test_list_users_403_no_perm(self, client: TestClient, app: FastAPI):
        user = _make_no_perm_user()
        with _as_user(app, user):
            resp = client.get("/api/v1/admin/users")
        assert resp.status_code == 403

    def test_get_user_404_for_missing(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user), patch.object(AdminService, "get_user", return_value=None):
            resp = client.get(f"/api/v1/admin/users/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_lock_requires_admin_write(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()  # only admin:read
        with _as_user(app, user):
            resp = client.post(f"/api/v1/admin/users/{uuid.uuid4()}/lock", json={"durationMinutes": 30})
        assert resp.status_code == 403

    def test_lock_user_404_for_missing(self, client: TestClient, app: FastAPI):
        user = _make_admin_user()
        with _as_user(app, user), patch.object(AdminService, "lock_user", return_value=None):
            resp = client.post(
                f"/api/v1/admin/users/{uuid.uuid4()}/lock",
                json={"durationMinutes": 30},
            )
        assert resp.status_code == 404

    def test_unlock_user_404_for_missing(self, client: TestClient, app: FastAPI):
        user = _make_admin_user()
        with _as_user(app, user), patch.object(AdminService, "unlock_user", return_value=None):
            resp = client.post(f"/api/v1/admin/users/{uuid.uuid4()}/unlock")
        assert resp.status_code == 404

    def test_force_password_reset_404_for_missing(self, client: TestClient, app: FastAPI):
        user = _make_admin_user()
        with _as_user(app, user), patch.object(AdminService, "force_password_reset", return_value=False):
            resp = client.post(f"/api/v1/admin/users/{uuid.uuid4()}/force-password-reset")
        assert resp.status_code == 404

    def test_force_password_reset_204_when_found(self, client: TestClient, app: FastAPI):
        user = _make_admin_user()
        with _as_user(app, user), patch.object(AdminService, "force_password_reset", return_value=True):
            resp = client.post(f"/api/v1/admin/users/{uuid.uuid4()}/force-password-reset")
        assert resp.status_code == 204


# ── Sessions ──────────────────────────────────────────────────────────────────

class TestSessions:
    def _list_response(self) -> SessionListResponse:
        return SessionListResponse(items=[], total=0, page=1, page_size=50, pages=1)

    def test_list_sessions_200(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user), patch.object(AdminService, "list_sessions", return_value=self._list_response()):
            resp = client.get("/api/v1/admin/sessions")
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_revoke_session_404(self, client: TestClient, app: FastAPI):
        user = _make_admin_user()
        with _as_user(app, user), patch.object(AdminService, "revoke_session", return_value=False):
            resp = client.delete(f"/api/v1/admin/sessions/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_revoke_session_204(self, client: TestClient, app: FastAPI):
        user = _make_admin_user()
        with _as_user(app, user), patch.object(AdminService, "revoke_session", return_value=True):
            resp = client.delete(f"/api/v1/admin/sessions/{uuid.uuid4()}")
        assert resp.status_code == 204


# ── Audit Center ──────────────────────────────────────────────────────────────

class TestAudit:
    def _search_response(self) -> AuditSearchResponse:
        return AuditSearchResponse(items=[], total=0, page=1, page_size=50, pages=1)

    def _stats(self) -> AuditStats:
        from app.schemas.admin import AuditStatItem
        return AuditStats(
            total_events=500,
            events_today=20,
            events_this_week=150,
            breakdown=[AuditStatItem(event_type="login_success", count=300)],
            generated_at=datetime.now(timezone.utc),
        )

    def test_audit_search_200(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user), patch.object(AdminService, "search_audit", return_value=self._search_response()):
            resp = client.get("/api/v1/admin/audit")
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_audit_stats_200(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user), patch.object(AdminService, "get_audit_stats", return_value=self._stats()):
            resp = client.get("/api/v1/admin/audit/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["totalEvents"] == 500
        assert len(data["breakdown"]) == 1

    def test_audit_requires_admin_read(self, client: TestClient, app: FastAPI):
        user = _make_no_perm_user()
        with _as_user(app, user):
            resp = client.get("/api/v1/admin/audit")
        assert resp.status_code == 403


# ── Security Center ───────────────────────────────────────────────────────────

class TestSecurity:
    def _overview(self) -> SecurityOverview:
        return SecurityOverview(
            locked_users_count=2,
            inactive_users_count=5,
            failed_logins_24h=8,
            active_sessions=40,
            expired_sessions_24h=3,
            top_failed_logins=[],
            locked_users=[],
            recent_suspicious_ips=["1.2.3.4"],
            generated_at=datetime.now(timezone.utc),
        )

    def test_security_overview_200(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user), patch.object(AdminService, "get_security_overview", return_value=self._overview()):
            resp = client.get("/api/v1/admin/security")
        assert resp.status_code == 200
        data = resp.json()
        assert data["lockedUsersCount"] == 2
        assert data["recentSuspiciousIps"] == ["1.2.3.4"]


# ── System Health ─────────────────────────────────────────────────────────────

class TestSystemHealth:
    def _health(self) -> SystemHealthResponse:
        from app.schemas.admin import ServiceHealthDetail
        svc = ServiceHealthDetail(name="PostgreSQL", status="healthy", latency_ms=1.2, message=None, version=None, last_check=datetime.now(timezone.utc))
        return SystemHealthResponse(services=[svc], queues=[], workers=[], overall_status="healthy", generated_at=datetime.now(timezone.utc))

    def test_health_200(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user), patch.object(AdminService, "get_system_health", return_value=self._health()):
            resp = client.get("/api/v1/admin/system/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overallStatus"] == "healthy"
        assert len(data["services"]) == 1
        assert data["services"][0]["name"] == "PostgreSQL"

    def test_recommendations_200(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        recs = RecommendationsResponse(
            recommendations=[],
            critical_count=0,
            warning_count=0,
            info_count=0,
            generated_at=datetime.now(timezone.utc),
        )
        with _as_user(app, user), patch.object(AdminService, "get_recommendations", return_value=recs):
            resp = client.get("/api/v1/admin/system/recommendations")
        assert resp.status_code == 200
        assert resp.json()["criticalCount"] == 0


# ── AI Administration ─────────────────────────────────────────────────────────

class TestAiAdmin:
    def _config(self) -> AiConfigRead:
        return AiConfigRead(
            provider="openai",
            model="gpt-4o-mini",
            embedding_model="text-embedding-3-small",
            max_tokens=2048,
            temperature=0.1,
            api_base="https://api.openai.com/v1",
            api_key_configured=True,
            ocr_enabled=True,
        )

    def _stats(self) -> AiUsageStats:
        return AiUsageStats(
            total_messages=500,
            messages_today=20,
            messages_this_week=100,
            messages_this_month=400,
            models_used=[],
            avg_messages_per_case=9.1,
            top_users=[],
            generated_at=datetime.now(timezone.utc),
        )

    def test_ai_config_200(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user), patch.object(AdminService, "get_ai_config", return_value=self._config()):
            resp = client.get("/api/v1/admin/ai/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "openai"
        assert data["apiKeyConfigured"] is True

    def test_ai_stats_200(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user), patch.object(AdminService, "get_ai_usage_stats", return_value=self._stats()):
            resp = client.get("/api/v1/admin/ai/stats")
        assert resp.status_code == 200
        assert resp.json()["totalMessages"] == 500


# ── Storage Center ────────────────────────────────────────────────────────────

class TestStorage:
    def _overview(self) -> StorageOverview:
        return StorageOverview(
            total_used_bytes=1_000_000_000,
            total_file_count=500,
            evidence_bytes=1_000_000_000,
            evidence_count=500,
            by_type=[],
            growth_last_7_days=50_000_000,
            growth_last_30_days=200_000_000,
            warning_threshold_pct=80,
            used_pct=45.3,
            largest_files=[],
            generated_at=datetime.now(timezone.utc),
        )

    def test_storage_200(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user), patch.object(AdminService, "get_storage_overview", return_value=self._overview()):
            resp = client.get("/api/v1/admin/storage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["totalUsedBytes"] == 1_000_000_000
        assert data["usedPct"] == 45.3


# ── Configuration Center ──────────────────────────────────────────────────────

class TestConfig:
    def _entries(self):
        from app.schemas.admin import ConfigEntry
        return [ConfigEntry(
            key="session_timeout_minutes",
            value="60",
            description="Session timeout",
            is_secret=False,
            updated_at=datetime.now(timezone.utc),
            updated_by_email=None,
        )]

    def test_list_config_200(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user), patch.object(AdminService, "list_config", return_value=self._entries()):
            resp = client.get("/api/v1/admin/config")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["key"] == "session_timeout_minutes"

    def test_get_config_404(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user), patch.object(AdminService, "get_config", return_value=None):
            resp = client.get("/api/v1/admin/config/nonexistent")
        assert resp.status_code == 404

    def test_set_config_requires_admin_write(self, client: TestClient, app: FastAPI):
        user = _make_readonly_user()
        with _as_user(app, user):
            resp = client.put("/api/v1/admin/config/session_timeout_minutes", json={"value": "120"})
        assert resp.status_code == 403

    def test_set_config_200(self, client: TestClient, app: FastAPI):
        user = _make_admin_user()
        entry = self._entries()[0]
        with _as_user(app, user), patch.object(AdminService, "set_config", return_value=entry):
            resp = client.put(
                "/api/v1/admin/config/session_timeout_minutes",
                json={"value": "120"},
            )
        assert resp.status_code == 200
        assert resp.json()["key"] == "session_timeout_minutes"
