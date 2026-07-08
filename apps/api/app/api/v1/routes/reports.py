"""Investigation Report Intelligence Engine — API routes.

All endpoints require at minimum evidence:read permission. Generating and
publishing reports additionally require report:write and report:publish.

Route prefix: /api/v1/cases/{case_id}/reports
Global list:  /api/v1/reports
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.dependencies import RequirePermission, SessionDep
from app.models.user import User
from app.schemas.report import (
    CreateReportRequest,
    GenerateReportRequest,
    ReportListItem,
    ReportRead,
    TemplateDescriptor,
    ReportTypeDescriptor,
)
from app.services.report_export import (
    export_docx,
    export_html,
    export_json,
    export_pdf,
    _file_hash,
)
from app.services.report_service import ReportService

router = APIRouter(tags=["reports"])

_READ = RequirePermission("evidence:read")
_WRITE = RequirePermission("report:write")
_PUBLISH = RequirePermission("report:publish")


# ── Metadata endpoints ─────────────────────────────────────────────────────────

@router.get("/report-templates", response_model=list[TemplateDescriptor])
def list_templates(current_user: User = _READ):
    """Return all available report templates with their default sections."""
    return ReportService.get_available_templates()


@router.get("/report-types", response_model=list[ReportTypeDescriptor])
def list_report_types(current_user: User = _READ):
    """Return all supported report types."""
    return ReportService.get_report_types()


# ── Case-scoped report CRUD ────────────────────────────────────────────────────

@router.post(
    "/cases/{case_id}/reports",
    response_model=ReportRead,
    status_code=201,
)
def create_report(
    case_id: uuid.UUID,
    body: CreateReportRequest,
    session: SessionDep,
    current_user: User = _WRITE,
) -> ReportRead:
    """Create a report configuration (does not generate content yet)."""
    svc = ReportService(session, current_user)
    report = svc.create(case_id, body)
    return _to_read(report)


@router.get("/cases/{case_id}/reports", response_model=list[ReportListItem])
def list_reports(
    case_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> list[ReportListItem]:
    """List all non-deleted reports for a case."""
    svc = ReportService(session, current_user)
    reports = svc.list_for_case(case_id)
    return [_to_list_item(r) for r in reports]


@router.get("/cases/{case_id}/reports/{report_id}", response_model=ReportRead)
def get_report(
    case_id: uuid.UUID,
    report_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> ReportRead:
    svc = ReportService(session, current_user)
    return _to_read(svc.get(case_id, report_id))


@router.delete("/cases/{case_id}/reports/{report_id}", status_code=204)
def delete_report(
    case_id: uuid.UUID,
    report_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _WRITE,
) -> None:
    ReportService(session, current_user).delete(case_id, report_id)


# ── Generation & versioning ────────────────────────────────────────────────────

@router.post("/cases/{case_id}/reports/{report_id}/generate", response_model=ReportRead)
def generate_report(
    case_id: uuid.UUID,
    report_id: uuid.UUID,
    session: SessionDep,
    body: GenerateReportRequest | None = None,
    current_user: User = _WRITE,
) -> ReportRead:
    """Collect all case data and populate sections_content."""
    svc = ReportService(session, current_user)
    return _to_read(svc.generate(case_id, report_id, body))


@router.post("/cases/{case_id}/reports/{report_id}/publish", response_model=ReportRead)
def publish_report(
    case_id: uuid.UUID,
    report_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _PUBLISH,
) -> ReportRead:
    """Mark a ready report as officially published (requires report:publish)."""
    svc = ReportService(session, current_user)
    return _to_read(svc.publish(case_id, report_id))


@router.post(
    "/cases/{case_id}/reports/{report_id}/version",
    response_model=ReportRead,
    status_code=201,
)
def new_version(
    case_id: uuid.UUID,
    report_id: uuid.UUID,
    session: SessionDep,
    body: GenerateReportRequest | None = None,
    current_user: User = _WRITE,
) -> ReportRead:
    """Create a new version of an existing report (parent_report_id is set)."""
    svc = ReportService(session, current_user)
    return _to_read(svc.create_new_version(case_id, report_id, body))


# ── Export endpoints ───────────────────────────────────────────────────────────

@router.get("/cases/{case_id}/reports/{report_id}/export/pdf")
def export_pdf_endpoint(
    case_id: uuid.UUID,
    report_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> Response:
    svc = ReportService(session, current_user)
    report = svc.get(case_id, report_id)
    data = export_pdf(report)
    svc.record_export(report.id, "pdf", len(data), _file_hash(data))
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-v{report.version}.pdf"'},
    )


@router.get("/cases/{case_id}/reports/{report_id}/export/docx")
def export_docx_endpoint(
    case_id: uuid.UUID,
    report_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> Response:
    svc = ReportService(session, current_user)
    report = svc.get(case_id, report_id)
    data = export_docx(report)
    svc.record_export(report.id, "docx", len(data), _file_hash(data))
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="report-v{report.version}.docx"'},
    )


@router.get("/cases/{case_id}/reports/{report_id}/export/html")
def export_html_endpoint(
    case_id: uuid.UUID,
    report_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> Response:
    svc = ReportService(session, current_user)
    report = svc.get(case_id, report_id)
    data = export_html(report)
    svc.record_export(report.id, "html", len(data), _file_hash(data))
    return Response(
        content=data,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="report-v{report.version}.html"'},
    )


@router.get("/cases/{case_id}/reports/{report_id}/export/json")
def export_json_endpoint(
    case_id: uuid.UUID,
    report_id: uuid.UUID,
    session: SessionDep,
    current_user: User = _READ,
) -> Response:
    svc = ReportService(session, current_user)
    report = svc.get(case_id, report_id)
    data = export_json(report)
    svc.record_export(report.id, "json", len(data), _file_hash(data))
    return Response(
        content=data,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="report-v{report.version}.json"'},
    )


# ── Global reports listing (cross-case, RBAC scoped) ─────────────────────────

@router.get("/reports", response_model=list[ReportListItem])
def list_all_reports(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = _READ,
) -> list[ReportListItem]:
    """List reports across all accessible cases (RBAC-filtered)."""
    from sqlalchemy import or_, select
    from app.models.case import Case
    from app.models.case_assignment import CaseAssignment
    from app.models.report import InvestigationReport

    assigned_subq = (
        select(CaseAssignment.case_id)
        .where(CaseAssignment.user_id == current_user.id)
        .scalar_subquery()
    )
    accessible = (
        select(Case.id)
        .where(
            Case.deleted_at.is_(None),
            or_(
                Case.is_private.is_(False),
                Case.owner_id == current_user.id,
                Case.id.in_(assigned_subq),
            ),
        )
        .scalar_subquery()
    )

    reports = (
        session.query(InvestigationReport)
        .filter(
            InvestigationReport.case_id.in_(accessible),
            InvestigationReport.deleted_at.is_(None),
        )
        .order_by(InvestigationReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [_to_list_item(r) for r in reports]


# ── Schema helpers ─────────────────────────────────────────────────────────────

def _to_read(r) -> ReportRead:
    from app.schemas.report import ReportExportRead
    return ReportRead(
        id=r.id,
        case_id=r.case_id,
        report_type=r.report_type,
        template=r.template,
        title=r.title,
        status=r.status,
        version=r.version,
        content_hash=r.content_hash,
        parent_report_id=r.parent_report_id,
        sections_config=r.sections_config,
        report_filters=r.report_filters,
        sections_content=r.sections_content,
        generation_error=r.generation_error,
        generated_by_id=r.generated_by_id,
        approved_by_id=r.approved_by_id,
        generated_at=r.generated_at,
        published_at=r.published_at,
        created_at=r.created_at,
        updated_at=r.updated_at,
        exports=[
            ReportExportRead(
                id=ex.id,
                report_id=ex.report_id,
                format=ex.format,
                file_size=ex.file_size,
                file_hash=ex.file_hash,
                generated_by_id=ex.generated_by_id,
                created_at=ex.created_at,
            )
            for ex in (r.exports or [])
        ],
    )


def _to_list_item(r) -> ReportListItem:
    return ReportListItem(
        id=r.id,
        case_id=r.case_id,
        report_type=r.report_type,
        template=r.template,
        title=r.title,
        status=r.status,
        version=r.version,
        content_hash=r.content_hash,
        parent_report_id=r.parent_report_id,
        generated_by_id=r.generated_by_id,
        generated_at=r.generated_at,
        published_at=r.published_at,
        created_at=r.created_at,
        export_count=len(r.exports) if r.exports else 0,
    )
