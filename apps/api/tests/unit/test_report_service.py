"""Unit tests for ReportService business logic."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.case import Case, CaseStatus
from app.models.report import InvestigationReport
from app.models.user import User
from app.schemas.report import CreateReportRequest, GenerateReportRequest, ReportFilters, SectionConfig
from app.services.report_export import _file_hash, export_html, export_json
from app.services.report_service import ReportService, get_template_sections


# ── Factories ─────────────────────────────────────────────────────────────────

def _user(permissions: list[str] | None = None) -> User:
    u = User(
        email="analyst@example.com",
        username="analyst",
        full_name="Test Analyst",
        password_hash="$2b$12$fake",
    )
    u.id = uuid.uuid4()
    u.refresh_tokens = []
    u.password_reset_tokens = []
    u.sessions = []
    u.audit_events = []
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    if permissions:
        role = MagicMock()
        role.permissions = [
            MagicMock(**{"resource": p.split(":")[0], "action": p.split(":")[1]})
            for p in permissions
        ]
        u.roles = [role]
    else:
        u.roles = []
    return u


def _case(owner_id: uuid.UUID | None = None) -> MagicMock:
    """Return a mock Case (task_count etc. are computed properties, can't be set)."""
    c = MagicMock(spec=Case)
    c.id = uuid.uuid4()
    c.owner_id = owner_id or uuid.uuid4()
    c.is_private = False
    c.deleted_at = None
    c.created_at = datetime.now(timezone.utc)
    c.updated_at = datetime.now(timezone.utc)
    return c


def _report(case_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> InvestigationReport:
    r = InvestigationReport(
        case_id=case_id,
        report_type=kwargs.get("report_type", "detailed"),
        template=kwargs.get("template", "professional"),
        title=kwargs.get("title", "Test Report"),
        status=kwargs.get("status", "draft"),
        sections_config=kwargs.get("sections_config", []),
        report_filters=kwargs.get("report_filters", {}),
        sections_content=kwargs.get("sections_content", {}),
        generated_by_id=user_id,
    )
    r.id = uuid.uuid4()
    r.version = kwargs.get("version", 1)
    r.parent_report_id = kwargs.get("parent_report_id", None)
    r.content_hash = kwargs.get("content_hash", None)
    r.generation_error = None
    r.approved_by_id = None
    r.published_at = None
    r.generated_at = None
    r.deleted_at = None
    r.exports = []
    r.created_at = datetime.now(timezone.utc)
    r.updated_at = datetime.now(timezone.utc)
    return r


def _mock_session(reports: list | None = None, case: Case | None = None):
    session = MagicMock()
    # .query(...).filter(...).first() → case
    # .query(...).filter(...).all() → reports
    q_mock = MagicMock()
    session.query.return_value = q_mock
    q_mock.filter.return_value = q_mock
    q_mock.order_by.return_value = q_mock
    q_mock.first.return_value = case
    q_mock.all.return_value = reports or []
    q_mock.count.return_value = len(reports) if reports else 0
    return session


# ── Template tests ─────────────────────────────────────────────────────────────

class TestGetTemplateSections:
    def test_professional_has_cover_and_toc(self):
        secs = get_template_sections("professional")
        types = [s["type"] for s in secs]
        assert "cover" in types
        assert "table_of_contents" in types

    def test_executive_summary_is_short(self):
        secs = get_template_sections("executive_summary")
        assert len(secs) == 3

    def test_unknown_template_falls_back_to_professional(self):
        secs = get_template_sections("nonexistent_template_xyz")
        types = [s["type"] for s in secs]
        assert "cover" in types

    def test_all_sections_have_required_keys(self):
        for tmpl in ("professional", "police", "cyber", "incident_response", "executive_summary", "custom"):
            for sec in get_template_sections(tmpl):
                assert "type" in sec
                assert "title" in sec
                assert "order_index" in sec
                assert "enabled" in sec

    def test_police_has_chain_of_custody(self):
        secs = get_template_sections("police")
        types = [s["type"] for s in secs]
        assert "chain_of_custody" in types

    def test_cyber_has_ai_findings(self):
        secs = get_template_sections("cyber")
        types = [s["type"] for s in secs]
        assert "ai_findings" in types


# ── ReportService.create ───────────────────────────────────────────────────────

class TestReportServiceCreate:
    def test_create_uses_template_sections_when_none_provided(self):
        user = _user(["report:write"])
        case = _case(owner_id=user.id)
        session = _mock_session(case=case)

        svc = ReportService(session=session, current_user=user)
        req = CreateReportRequest(
            report_type="detailed",
            template="executive_summary",
            title="My Report",
        )
        svc.create(case.id, req)

        call_args = session.add.call_args[0][0]
        assert call_args.template == "executive_summary"
        # Cover page always present in executive_summary template
        section_types = [s["type"] for s in call_args.sections_config]
        assert "cover" in section_types

    def test_create_respects_custom_sections_config(self):
        user = _user(["report:write"])
        case = _case(owner_id=user.id)
        session = _mock_session(case=case)

        custom_sections = [
            SectionConfig(type="cover", title="Cover", order_index=0, enabled=True),
            SectionConfig(type="timeline", title="Timeline", order_index=1, enabled=True),
        ]
        req = CreateReportRequest(
            report_type="timeline",
            template="professional",
            title="Timeline Report",
            sections_config=custom_sections,
        )
        svc = ReportService(session=session, current_user=user)
        svc.create(case.id, req)

        call_args = session.add.call_args[0][0]
        assert len(call_args.sections_config) == 2
        assert call_args.sections_config[1]["type"] == "timeline"

    def test_create_sets_draft_status(self):
        user = _user(["report:write"])
        case = _case(owner_id=user.id)
        session = _mock_session(case=case)

        req = CreateReportRequest(
            report_type="executive",
            template="executive_summary",
            title="Exec Summary",
        )
        svc = ReportService(session=session, current_user=user)
        svc.create(case.id, req)

        report = session.add.call_args[0][0]
        assert report.status == "draft"
        assert report.sections_content == {}

    def test_create_raises_on_inaccessible_case(self):
        user = _user(["report:write"])
        session = _mock_session(case=None)

        req = CreateReportRequest(
            report_type="detailed",
            template="professional",
            title="Forbidden",
        )
        svc = ReportService(session=session, current_user=user)
        with pytest.raises(NotFoundError):
            svc.create(uuid.uuid4(), req)


# ── ReportService.publish ──────────────────────────────────────────────────────

class TestReportServicePublish:
    def test_publish_ready_report_succeeds(self):
        user = _user(["report:publish"])
        case = _case(owner_id=user.id)
        r = _report(case.id, user.id, status="ready")

        session = _mock_session(case=case)
        session.query.return_value.filter.return_value.first.return_value = r

        svc = ReportService(session=session, current_user=user)
        result = svc.publish(case.id, r.id)

        assert result.status == "published"
        assert result.approved_by_id == user.id
        assert result.published_at is not None

    def test_publish_draft_report_raises(self):
        user = _user(["report:publish"])
        case = _case(owner_id=user.id)
        r = _report(case.id, user.id, status="draft")

        session = _mock_session(case=case)
        session.query.return_value.filter.return_value.first.return_value = r

        svc = ReportService(session=session, current_user=user)
        with pytest.raises(PermissionDeniedError):
            svc.publish(case.id, r.id)


# ── ReportService.delete ──────────────────────────────────────────────────────

class TestReportServiceDelete:
    def test_delete_sets_deleted_at(self):
        user = _user(["report:write"])
        case = _case(owner_id=user.id)
        r = _report(case.id, user.id, status="draft")

        session = _mock_session(case=case)
        session.query.return_value.filter.return_value.first.return_value = r

        svc = ReportService(session=session, current_user=user)
        svc.delete(case.id, r.id)

        assert r.deleted_at is not None

    def test_delete_nonexistent_raises(self):
        user = _user(["report:write"])
        case = _case(owner_id=user.id)

        session = _mock_session(case=case)
        session.query.return_value.filter.return_value.first.return_value = None

        svc = ReportService(session=session, current_user=user)
        with pytest.raises(NotFoundError):
            svc.delete(case.id, uuid.uuid4())


# ── ReportService.create_new_version ──────────────────────────────────────────

class TestReportServiceVersioning:
    def test_new_version_bumps_version_number(self):
        user = _user(["report:write"])
        case = _case(owner_id=user.id)
        parent = _report(case.id, user.id, status="published", version=1)

        session = _mock_session(case=case)
        session.query.return_value.filter.return_value.first.return_value = parent

        svc = ReportService(session=session, current_user=user)
        svc.create_new_version(case.id, parent.id)

        added = session.add.call_args[0][0]
        assert added.version == 2
        assert added.parent_report_id == parent.id
        assert added.status == "draft"

    def test_new_version_inherits_parent_title(self):
        user = _user(["report:write"])
        case = _case(owner_id=user.id)
        parent = _report(case.id, user.id, status="published", title="Original Title")

        session = _mock_session(case=case)
        session.query.return_value.filter.return_value.first.return_value = parent

        svc = ReportService(session=session, current_user=user)
        svc.create_new_version(case.id, parent.id)

        added = session.add.call_args[0][0]
        assert added.title == "Original Title"


# ── Export layer tests ────────────────────────────────────────────────────────

class TestExportLayer:
    def _make_report(self) -> InvestigationReport:
        user_id = uuid.uuid4()
        case_id = uuid.uuid4()
        r = _report(case_id, user_id, title="Export Test Report")
        r.sections_content = {
            "executive_summary": {
                "title": "Executive Summary",
                "is_ai_generated": True,
                "disclaimer": "AI-generated content requires investigator review.",
                "summary": "The evidence points to a coordinated intrusion.",
            },
            "case_overview": {
                "title": "Case Overview",
                "is_ai_generated": False,
                "content": "Case opened on 2026-01-01.",
            },
        }
        r.case = MagicMock()
        r.case.reference_number = "CASE-2026-EXPO"
        r.case.title = "Export Test Case"
        r.generated_at = datetime.now(timezone.utc)
        return r

    def test_json_export_contains_required_fields(self):
        r = self._make_report()
        data = export_json(r)
        import json as _json
        obj = _json.loads(data)
        assert obj["title"] == "Export Test Report"
        assert "sections_content" in obj
        assert "content_hash" in obj

    def test_json_export_is_utf8_bytes(self):
        r = self._make_report()
        data = export_json(r)
        assert isinstance(data, bytes)
        data.decode("utf-8")  # should not raise

    def test_html_export_contains_title(self):
        r = self._make_report()
        html = export_html(r).decode("utf-8")
        assert "Export Test Report" in html

    def test_html_export_labels_ai_sections(self):
        r = self._make_report()
        html = export_html(r).decode("utf-8")
        assert "AI" in html or "ai" in html.lower()

    def test_html_export_includes_disclaimer(self):
        r = self._make_report()
        html = export_html(r).decode("utf-8")
        assert "disclaimer" in html.lower() or "AI" in html

    def test_file_hash_is_sha256(self):
        data = b"test payload"
        h = _file_hash(data)
        assert h == hashlib.sha256(data).hexdigest()
        assert len(h) == 64


# ── Content hash immutability ──────────────────────────────────────────────────

class TestContentHash:
    def test_same_content_produces_same_hash(self):
        content = {"section": {"data": "value", "is_ai_generated": False}}
        import json as _json
        raw = _json.dumps(content, sort_keys=True).encode()
        h1 = hashlib.sha256(raw).hexdigest()
        h2 = hashlib.sha256(raw).hexdigest()
        assert h1 == h2

    def test_different_content_produces_different_hash(self):
        import json as _json
        c1 = _json.dumps({"section": {"data": "value1"}}, sort_keys=True).encode()
        c2 = _json.dumps({"section": {"data": "value2"}}, sort_keys=True).encode()
        assert hashlib.sha256(c1).hexdigest() != hashlib.sha256(c2).hexdigest()


# ── Static methods ────────────────────────────────────────────────────────────

class TestStaticDescriptors:
    def test_get_available_templates_returns_six(self):
        templates = ReportService.get_available_templates()
        assert len(templates) == 6
        keys = [t["key"] for t in templates]
        assert "professional" in keys
        assert "custom" in keys

    def test_get_report_types_returns_nine(self):
        types = ReportService.get_report_types()
        assert len(types) == 9
        keys = [t["key"] for t in types]
        assert "executive" in keys
        assert "chain_of_custody" in keys
        assert "ai_findings" in keys

    def test_report_types_have_default_template(self):
        for t in ReportService.get_report_types():
            assert "default_template" in t
            assert t["default_template"] in (
                "executive_summary", "professional", "police"
            )
