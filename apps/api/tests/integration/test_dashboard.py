"""Integration tests for the Dashboard API endpoints."""

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
from app.schemas.dashboard import (
    ExecutiveDashboard,
    IntelligenceDashboard,
    InvestigatorDashboard,
    OperationsDashboard,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app() -> FastAPI:
    return create_app()


@pytest.fixture(scope="module")
def client(app: FastAPI) -> TestClient:
    with TestClient(app) as c:
        yield c


# ── Factories ──────────────────────────────────────────────────────────────────

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
        email="dash@example.com",
        username="dashuser",
        full_name="Dashboard User",
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


@contextmanager
def _as_user(app: FastAPI, user: User):
    app.dependency_overrides[_get_current_user] = lambda: user
    try:
        yield
    finally:
        app.dependency_overrides.pop(_get_current_user, None)


# ── Shared mock data ───────────────────────────────────────────────────────────

def _exec_dashboard_data() -> dict:
    return dict(
        active_cases=5, high_priority_cases=2, closed_cases=10, total_cases=20,
        evidence_uploaded_today=3, total_evidence=150,
        reports_generated=8, reports_published=4,
        ai_queue_size=2, avg_investigation_days=14.5,
        status_breakdown=dict(draft=1, open=2, in_progress=3, under_review=1, on_hold=0, closed=10, archived=3),
        priority_breakdown=dict(low=5, medium=10, high=4, critical=1),
        cases_opened_last_30_days=[],
        evidence_uploaded_last_30_days=[],
        investigator_workload=[],
        recently_active_cases=[],
        generated_at=datetime.now(timezone.utc),
    )


# ── Authentication guard tests ─────────────────────────────────────────────────

class TestDashboardAuth:
    def test_executive_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard/executive")
        assert resp.status_code == 401

    def test_intelligence_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard/intelligence")
        assert resp.status_code == 401

    def test_operations_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard/operations")
        assert resp.status_code == 401

    def test_investigator_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard/investigator")
        assert resp.status_code == 401


# ── Permission guard tests ─────────────────────────────────────────────────────

class TestDashboardPermissions:
    def test_executive_requires_evidence_read(self, app, client):
        user = _make_user([])  # no permissions
        with _as_user(app, user):
            resp = client.get("/api/v1/dashboard/executive")
        assert resp.status_code == 403

    def test_intelligence_requires_evidence_read(self, app, client):
        user = _make_user([])
        with _as_user(app, user):
            resp = client.get("/api/v1/dashboard/intelligence")
        assert resp.status_code == 403

    def test_operations_requires_evidence_read(self, app, client):
        user = _make_user([])
        with _as_user(app, user):
            resp = client.get("/api/v1/dashboard/operations")
        assert resp.status_code == 403

    def test_investigator_requires_evidence_read(self, app, client):
        user = _make_user([])
        with _as_user(app, user):
            resp = client.get("/api/v1/dashboard/investigator")
        assert resp.status_code == 403


# ── Executive endpoint ────────────────────────────────────────────────────────

class TestExecutiveDashboard:
    def test_returns_200_with_permission(self, app, client):
        user = _make_user(["evidence:read"])
        with patch("app.api.v1.routes.dashboard.DashboardService") as MockSvc:
            MockSvc.return_value.get_executive.return_value = ExecutiveDashboard(
                **_exec_dashboard_data()
            )
            with _as_user(app, user):
                resp = client.get("/api/v1/dashboard/executive")
        assert resp.status_code == 200

    def test_response_has_expected_fields(self, app, client):
        user = _make_user(["evidence:read"])
        with patch("app.api.v1.routes.dashboard.DashboardService") as MockSvc:
            MockSvc.return_value.get_executive.return_value = ExecutiveDashboard(
                **_exec_dashboard_data()
            )
            with _as_user(app, user):
                data = client.get("/api/v1/dashboard/executive").json()
        assert "activeCases" in data
        assert "highPriorityCases" in data
        assert "statusBreakdown" in data
        assert "priorityBreakdown" in data
        assert "investigatorWorkload" in data
        assert "recentlyActiveCases" in data

    def test_response_camel_case(self, app, client):
        user = _make_user(["evidence:read"])
        with patch("app.api.v1.routes.dashboard.DashboardService") as MockSvc:
            MockSvc.return_value.get_executive.return_value = ExecutiveDashboard(
                **_exec_dashboard_data()
            )
            with _as_user(app, user):
                data = client.get("/api/v1/dashboard/executive").json()
        # Check camelCase (snake_case would fail here)
        assert "avgInvestigationDays" in data


# ── Intelligence endpoint ──────────────────────────────────────────────────────

def _intel_dashboard_data() -> dict:
    return dict(
        entity_distribution=[],
        top_organizations=[], top_devices=[], top_persons=[],
        evidence_type_distribution=[],
        ai_confidence_distribution=[
            dict(bucket="0.0–0.5", count=0),
            dict(bucket="0.5–0.7", count=5),
            dict(bucket="0.7–0.9", count=12),
            dict(bucket="0.9–1.0", count=30),
        ],
        top_keywords=[],
        timeline_heatmap=[],
        avg_entities_per_case=2.4,
        total_unique_entities=88,
        generated_at=datetime.now(timezone.utc),
    )


class TestIntelligenceDashboard:
    def test_returns_200_with_permission(self, app, client):
        user = _make_user(["evidence:read"])
        with patch("app.api.v1.routes.dashboard.DashboardService") as MockSvc:
            MockSvc.return_value.get_intelligence.return_value = IntelligenceDashboard(
                **_intel_dashboard_data()
            )
            with _as_user(app, user):
                resp = client.get("/api/v1/dashboard/intelligence")
        assert resp.status_code == 200

    def test_confidence_buckets_in_response(self, app, client):
        user = _make_user(["evidence:read"])
        with patch("app.api.v1.routes.dashboard.DashboardService") as MockSvc:
            MockSvc.return_value.get_intelligence.return_value = IntelligenceDashboard(
                **_intel_dashboard_data()
            )
            with _as_user(app, user):
                data = client.get("/api/v1/dashboard/intelligence").json()
        assert "aiConfidenceDistribution" in data
        assert len(data["aiConfidenceDistribution"]) == 4


# ── Operations endpoint ───────────────────────────────────────────────────────

def _ops_dashboard_data() -> dict:
    return dict(
        services=[
            dict(name="PostgreSQL", status="healthy", latency_ms=1.2, message=None),
            dict(name="Redis", status="down", latency_ms=None, message="Connection refused"),
        ],
        queues=[dict(name="celery", pending=3, active=0)],
        evidence_by_status={"completed": 100, "failed": 2},
        failed_processing_24h=2,
        processing_stats=dict(avg_ocr_seconds=None, avg_ai_seconds=None, avg_total_seconds=4.2, throughput_per_hour=None),
        storage=dict(used_bytes=1_048_576, file_count=42),
        generated_at=datetime.now(timezone.utc),
    )


class TestOperationsDashboard:
    def test_returns_200_with_permission(self, app, client):
        user = _make_user(["evidence:read"])
        with patch("app.api.v1.routes.dashboard.DashboardService") as MockSvc:
            MockSvc.return_value.get_operations.return_value = OperationsDashboard(
                **_ops_dashboard_data()
            )
            with _as_user(app, user):
                resp = client.get("/api/v1/dashboard/operations")
        assert resp.status_code == 200

    def test_services_in_response(self, app, client):
        user = _make_user(["evidence:read"])
        with patch("app.api.v1.routes.dashboard.DashboardService") as MockSvc:
            MockSvc.return_value.get_operations.return_value = OperationsDashboard(
                **_ops_dashboard_data()
            )
            with _as_user(app, user):
                data = client.get("/api/v1/dashboard/operations").json()
        assert "services" in data
        assert len(data["services"]) == 2
        names = [s["name"] for s in data["services"]]
        assert "PostgreSQL" in names

    def test_down_service_included(self, app, client):
        user = _make_user(["evidence:read"])
        with patch("app.api.v1.routes.dashboard.DashboardService") as MockSvc:
            MockSvc.return_value.get_operations.return_value = OperationsDashboard(
                **_ops_dashboard_data()
            )
            with _as_user(app, user):
                data = client.get("/api/v1/dashboard/operations").json()
        statuses = {s["name"]: s["status"] for s in data["services"]}
        assert statuses["Redis"] == "down"


# ── Investigator endpoint ─────────────────────────────────────────────────────

def _inv_dashboard_data() -> dict:
    return dict(
        assigned_cases=[],
        open_tasks=[],
        recent_notes=[],
        recent_evidence=[],
        productivity=dict(
            cases_active=3,
            cases_closed_30d=1,
            tasks_completed_30d=5,
            evidence_items_uploaded_30d=12,
            notes_created_30d=4,
        ),
        generated_at=datetime.now(timezone.utc),
    )


class TestInvestigatorDashboard:
    def test_returns_200_with_permission(self, app, client):
        user = _make_user(["evidence:read"])
        with patch("app.api.v1.routes.dashboard.DashboardService") as MockSvc:
            MockSvc.return_value.get_investigator.return_value = InvestigatorDashboard(
                **_inv_dashboard_data()
            )
            with _as_user(app, user):
                resp = client.get("/api/v1/dashboard/investigator")
        assert resp.status_code == 200

    def test_productivity_in_response(self, app, client):
        user = _make_user(["evidence:read"])
        with patch("app.api.v1.routes.dashboard.DashboardService") as MockSvc:
            MockSvc.return_value.get_investigator.return_value = InvestigatorDashboard(
                **_inv_dashboard_data()
            )
            with _as_user(app, user):
                data = client.get("/api/v1/dashboard/investigator").json()
        assert "productivity" in data
        assert "casesActive" in data["productivity"]
        assert data["productivity"]["casesActive"] == 3

    def test_empty_lists_serialised_correctly(self, app, client):
        user = _make_user(["evidence:read"])
        with patch("app.api.v1.routes.dashboard.DashboardService") as MockSvc:
            MockSvc.return_value.get_investigator.return_value = InvestigatorDashboard(
                **_inv_dashboard_data()
            )
            with _as_user(app, user):
                data = client.get("/api/v1/dashboard/investigator").json()
        assert data["assignedCases"] == []
        assert data["openTasks"] == []
