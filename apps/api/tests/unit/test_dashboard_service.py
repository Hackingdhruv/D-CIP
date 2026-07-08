"""Unit tests for DashboardService — all methods tested with mocked sessions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.user import User
from app.schemas.dashboard import (
    ConfidenceBucket,
    DateCount,
    ExecutiveDashboard,
    IntelligenceDashboard,
    InvestigatorDashboard,
    OperationsDashboard,
    ServiceHealth,
)
from app.services.dashboard_service import DashboardService, _mime_label


# ── Factories ─────────────────────────────────────────────────────────────────

def _user() -> User:
    u = User(
        email="dash@example.com",
        username="dashuser",
        full_name="Dashboard User",
        password_hash="$2b$12$fake",
    )
    u.id = uuid.uuid4()
    u.roles = []
    u.refresh_tokens = []
    u.password_reset_tokens = []
    u.sessions = []
    u.audit_events = []
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    return u


def _mock_session():
    """Return a fully-chained MagicMock session that returns empty scalars/lists by default."""
    session = MagicMock()
    result = MagicMock()
    result.scalar.return_value = 0
    result.all.return_value = []
    result.first.return_value = MagicMock(avg_total=None, total_bytes=0, file_count=0)
    session.execute.return_value = result
    return session


# ── _mime_label helper ────────────────────────────────────────────────────────

class TestMimeLabelHelper:
    def test_known_pdf(self):
        assert _mime_label("application/pdf") == "PDF"

    def test_known_image_jpeg(self):
        assert _mime_label("image/jpeg") == "JPEG Image"

    def test_image_major_fallback(self):
        assert _mime_label("image/webp") == "Image"

    def test_video_major_fallback(self):
        assert _mime_label("video/webm") == "Video"

    def test_unknown_returns_original(self):
        assert _mime_label("application/octet-stream") == "application/octet-stream"


# ── get_executive ─────────────────────────────────────────────────────────────

class TestGetExecutive:
    def _svc(self, session=None) -> DashboardService:
        return DashboardService(session or _mock_session(), _user())

    def test_returns_executive_dashboard_type(self):
        result = self._svc().get_executive()
        assert isinstance(result, ExecutiveDashboard)

    def test_zeroes_when_no_data(self):
        result = self._svc().get_executive()
        assert result.total_cases == 0
        assert result.active_cases == 0
        assert result.evidence_uploaded_today == 0

    def test_generated_at_is_recent(self):
        result = self._svc().get_executive()
        age_seconds = (datetime.now(timezone.utc) - result.generated_at).total_seconds()
        assert abs(age_seconds) < 5

    def test_status_breakdown_has_all_keys(self):
        result = self._svc().get_executive()
        bd = result.status_breakdown
        assert hasattr(bd, 'draft')
        assert hasattr(bd, 'open')
        assert hasattr(bd, 'in_progress')
        assert hasattr(bd, 'closed')

    def test_priority_breakdown_has_all_keys(self):
        result = self._svc().get_executive()
        bd = result.priority_breakdown
        assert hasattr(bd, 'low')
        assert hasattr(bd, 'high')
        assert hasattr(bd, 'critical')

    def test_empty_lists_when_no_data(self):
        result = self._svc().get_executive()
        assert result.cases_opened_last_30_days == []
        assert result.evidence_uploaded_last_30_days == []
        assert result.investigator_workload == []
        assert result.recently_active_cases == []

    def test_avg_investigation_days_defaults_zero(self):
        result = self._svc().get_executive()
        assert result.avg_investigation_days == 0.0

    def test_ai_queue_size_is_non_negative(self):
        result = self._svc().get_executive()
        assert result.ai_queue_size >= 0


# ── get_intelligence ──────────────────────────────────────────────────────────

class TestGetIntelligence:
    def _svc(self) -> DashboardService:
        return DashboardService(_mock_session(), _user())

    def test_returns_intelligence_dashboard_type(self):
        result = self._svc().get_intelligence()
        assert isinstance(result, IntelligenceDashboard)

    def test_confidence_buckets_always_four(self):
        result = self._svc().get_intelligence()
        assert len(result.ai_confidence_distribution) == 4

    def test_confidence_bucket_labels_are_correct(self):
        result = self._svc().get_intelligence()
        labels = [b.bucket for b in result.ai_confidence_distribution]
        assert "0.0–0.5" in labels
        assert "0.9–1.0" in labels

    def test_empty_lists_when_no_data(self):
        result = self._svc().get_intelligence()
        assert result.entity_distribution == []
        assert result.top_keywords == []
        assert result.top_organizations == []

    def test_avg_entities_per_case_defaults_zero(self):
        result = self._svc().get_intelligence()
        assert result.avg_entities_per_case == 0.0

    def test_total_unique_entities_defaults_zero(self):
        result = self._svc().get_intelligence()
        assert result.total_unique_entities == 0

    def test_generated_at_is_recent(self):
        result = self._svc().get_intelligence()
        age = (datetime.now(timezone.utc) - result.generated_at).total_seconds()
        assert abs(age) < 5


# ── get_operations ────────────────────────────────────────────────────────────

class TestGetOperations:
    def test_returns_operations_dashboard_type(self):
        # All external service probes will fail (no real infra) — all ServiceHealth.status == "down"
        result = DashboardService(_mock_session(), _user()).get_operations()
        assert isinstance(result, OperationsDashboard)

    def test_postgresql_always_probed(self):
        result = DashboardService(_mock_session(), _user()).get_operations()
        names = [s.name for s in result.services]
        assert "PostgreSQL" in names

    def test_redis_always_probed(self):
        result = DashboardService(_mock_session(), _user()).get_operations()
        names = [s.name for s in result.services]
        assert "Redis" in names

    def test_neo4j_always_probed(self):
        result = DashboardService(_mock_session(), _user()).get_operations()
        names = [s.name for s in result.services]
        assert "Neo4j" in names

    def test_opensearch_always_probed(self):
        result = DashboardService(_mock_session(), _user()).get_operations()
        names = [s.name for s in result.services]
        assert "OpenSearch" in names

    def test_storage_stats_non_negative(self):
        result = DashboardService(_mock_session(), _user()).get_operations()
        assert result.storage.used_bytes >= 0
        assert result.storage.file_count >= 0

    def test_service_health_has_status_field(self):
        result = DashboardService(_mock_session(), _user()).get_operations()
        for svc in result.services:
            assert svc.status in ("healthy", "degraded", "down", "unknown")

    def test_processing_stats_present(self):
        result = DashboardService(_mock_session(), _user()).get_operations()
        # Ensure object exists (values may be None when no data)
        assert result.processing_stats is not None

    def test_failed_24h_non_negative(self):
        result = DashboardService(_mock_session(), _user()).get_operations()
        assert result.failed_processing_24h >= 0


# ── get_investigator ──────────────────────────────────────────────────────────

class TestGetInvestigator:
    def _svc(self) -> DashboardService:
        return DashboardService(_mock_session(), _user())

    def test_returns_investigator_dashboard_type(self):
        result = self._svc().get_investigator()
        assert isinstance(result, InvestigatorDashboard)

    def test_empty_lists_when_no_data(self):
        result = self._svc().get_investigator()
        assert result.assigned_cases == []
        assert result.open_tasks == []
        assert result.recent_notes == []
        assert result.recent_evidence == []

    def test_productivity_has_all_metrics(self):
        result = self._svc().get_investigator()
        p = result.productivity
        assert p.cases_active >= 0
        assert p.cases_closed_30d >= 0
        assert p.tasks_completed_30d >= 0
        assert p.evidence_items_uploaded_30d >= 0
        assert p.notes_created_30d >= 0

    def test_generated_at_is_recent(self):
        result = self._svc().get_investigator()
        age = (datetime.now(timezone.utc) - result.generated_at).total_seconds()
        assert abs(age) < 5


# ── RBAC subquery ─────────────────────────────────────────────────────────────

class TestRBACSubquery:
    def test_accessible_ids_cached(self):
        """_accessible_ids() must return the same subquery object on repeated calls."""
        svc = DashboardService(_mock_session(), _user())
        q1 = svc._accessible_ids()
        q2 = svc._accessible_ids()
        assert q1 is q2
