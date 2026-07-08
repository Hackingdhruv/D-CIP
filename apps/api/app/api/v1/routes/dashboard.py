"""Dashboard API routes — four specialised dashboard views."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import RequirePermission, SessionDep
from app.models.user import User
from app.schemas.dashboard import (
    ExecutiveDashboard,
    IntelligenceDashboard,
    InvestigatorDashboard,
    OperationsDashboard,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

_READ = RequirePermission("evidence:read")


@router.get("/executive", response_model=ExecutiveDashboard)
def get_executive_dashboard(
    session: SessionDep,
    current_user: User = _READ,
) -> ExecutiveDashboard:
    """Platform-wide investigation metrics for leadership / management view."""
    return DashboardService(session, current_user).get_executive()


@router.get("/intelligence", response_model=IntelligenceDashboard)
def get_intelligence_dashboard(
    session: SessionDep,
    current_user: User = _READ,
) -> IntelligenceDashboard:
    """Entity analytics, keyword rankings, confidence distribution, timeline heatmap."""
    return DashboardService(session, current_user).get_intelligence()


@router.get("/operations", response_model=OperationsDashboard)
def get_operations_dashboard(
    session: SessionDep,
    current_user: User = _READ,
) -> OperationsDashboard:
    """Infrastructure health probes, Celery queue status, evidence pipeline stats."""
    return DashboardService(session, current_user).get_operations()


@router.get("/investigator", response_model=InvestigatorDashboard)
def get_investigator_dashboard(
    session: SessionDep,
    current_user: User = _READ,
) -> InvestigatorDashboard:
    """Personalised dashboard — my cases, tasks, notes, evidence, productivity."""
    return DashboardService(session, current_user).get_investigator()
