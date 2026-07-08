"""AlertService — create, query, and manage WatchlistAlert records."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.case_assignment import CaseAssignment
from app.models.evidence import Evidence
from app.models.user import User
from app.models.watchlist import Watchlist
from app.models.watchlist_alert import AlertStatus, WatchlistAlert
from app.schemas.watchlist import (
    AlertStats,
    WatchlistAlertListResponse,
    WatchlistAlertRead,
)
from app.services.watchlist_matching import MatchResult


def _accessible_case_ids(user: User, db: Session) -> list[uuid.UUID]:
    stmt = select(Case.id).where(
        (Case.is_private.is_(False))
        | (Case.owner_id == user.id)
        | (
            Case.id.in_(
                select(CaseAssignment.case_id).where(
                    CaseAssignment.user_id == user.id
                )
            )
        )
    )
    return list(db.execute(stmt).scalars())


def _to_alert_read(
    alert: WatchlistAlert,
    db: Session,
    actor: User,
    accessible_ids: list[uuid.UUID],
) -> WatchlistAlertRead:
    watchlist_name = None
    if alert.watchlist_id:
        wl = db.get(Watchlist, alert.watchlist_id)
        watchlist_name = wl.name if wl else None

    evidence_filename = None
    if alert.evidence_id:
        ev = db.get(Evidence, alert.evidence_id)
        evidence_filename = ev.original_filename if ev else None

    case_ref = None
    case = db.get(Case, alert.case_id)
    if case:
        case_ref = case.reference_number

    cross_count = len(alert.cross_case_ids or [])
    # User can "see" a cross-case alert if they have access to at least one of
    # the related cases
    cross_accessible = any(
        uuid.UUID(cid) in accessible_ids
        for cid in (alert.cross_case_ids or [])
    )

    return WatchlistAlertRead(
        id=alert.id,
        watchlist_id=alert.watchlist_id,
        watchlist_entry_id=alert.watchlist_entry_id,
        evidence_id=alert.evidence_id,
        case_id=alert.case_id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        matched_value=alert.matched_value,
        matched_entity_type=alert.matched_entity_type,
        confidence=alert.confidence,
        status=alert.status,
        is_cross_case=alert.is_cross_case,
        cross_case_count=cross_count,
        cross_case_accessible=cross_accessible,
        alert_metadata=dict(alert.alert_metadata or {}),
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
        watchlist_name=watchlist_name,
        evidence_filename=evidence_filename,
        case_reference=case_ref,
    )


class AlertService:
    def __init__(self, db: Session, actor: User) -> None:
        self.db = db
        self.actor = actor

    # ── Bulk create from matching results ─────────────────────────────────────

    def create_from_matches(
        self,
        matches: list[MatchResult],
        evidence_id: uuid.UUID,
        case_id: uuid.UUID,
    ) -> list[WatchlistAlert]:
        created: list[WatchlistAlert] = []
        for m in matches:
            alert = WatchlistAlert(
                watchlist_id=m.watchlist_id,
                watchlist_entry_id=m.watchlist_entry_id,
                evidence_id=evidence_id,
                case_id=case_id,
                alert_type=m.alert_type,
                severity=m.severity,
                title=m.title[:500],
                description=m.description,
                matched_value=m.matched_value,
                matched_entity_type=m.matched_entity_type,
                confidence=m.confidence,
                status=AlertStatus.NEW.value,
                is_cross_case=m.is_cross_case,
                cross_case_ids=m.cross_case_ids,
                alert_metadata=m.metadata,
            )
            self.db.add(alert)
            created.append(alert)

            # Increment hit_count on the matched entry
            if m.watchlist_entry_id:
                from app.models.watchlist import WatchlistEntry
                entry = self.db.get(WatchlistEntry, m.watchlist_entry_id)
                if entry:
                    entry.hit_count += 1

        self.db.flush()
        return created

    # ── Queries ───────────────────────────────────────────────────────────────

    def list_alerts(
        self,
        page: int = 1,
        page_size: int = 20,
        case_id: uuid.UUID | None = None,
        status: str | None = None,
        severity: str | None = None,
        alert_type: str | None = None,
        is_cross_case: bool | None = None,
    ) -> WatchlistAlertListResponse:
        accessible = _accessible_case_ids(self.actor, self.db)
        stmt = select(WatchlistAlert).where(WatchlistAlert.case_id.in_(accessible))

        if case_id is not None:
            stmt = stmt.where(WatchlistAlert.case_id == case_id)
        if status is not None:
            stmt = stmt.where(WatchlistAlert.status == status)
        if severity is not None:
            stmt = stmt.where(WatchlistAlert.severity == severity)
        if alert_type is not None:
            stmt = stmt.where(WatchlistAlert.alert_type == alert_type)
        if is_cross_case is not None:
            stmt = stmt.where(WatchlistAlert.is_cross_case.is_(is_cross_case))

        total = self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        pages = max(1, math.ceil(total / page_size))

        alerts = self.db.execute(
            stmt.order_by(WatchlistAlert.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).scalars().all()

        new_count = self.db.execute(
            select(func.count(WatchlistAlert.id)).where(
                WatchlistAlert.case_id.in_(accessible),
                WatchlistAlert.status == AlertStatus.NEW.value,
            )
        ).scalar_one()
        critical_count = self.db.execute(
            select(func.count(WatchlistAlert.id)).where(
                WatchlistAlert.case_id.in_(accessible),
                WatchlistAlert.severity == "critical",
                WatchlistAlert.status == AlertStatus.NEW.value,
            )
        ).scalar_one()

        return WatchlistAlertListResponse(
            items=[
                _to_alert_read(a, self.db, self.actor, accessible)
                for a in alerts
            ],
            total=total,
            page=page,
            pages=pages,
            new_count=new_count,
            critical_count=critical_count,
        )

    def get_alert(self, alert_id: uuid.UUID) -> WatchlistAlertRead:
        alert = self.db.get(WatchlistAlert, alert_id)
        if alert is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Alert not found")
        accessible = _accessible_case_ids(self.actor, self.db)
        if alert.case_id not in accessible:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Access denied")
        return _to_alert_read(alert, self.db, self.actor, accessible)

    # ── Status transitions ────────────────────────────────────────────────────

    def _transition(
        self, alert_id: uuid.UUID, new_status: str, **fields: object
    ) -> WatchlistAlertRead:
        alert = self.db.get(WatchlistAlert, alert_id)
        if alert is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Alert not found")
        accessible = _accessible_case_ids(self.actor, self.db)
        if alert.case_id not in accessible:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Access denied")
        alert.status = new_status
        for k, v in fields.items():
            setattr(alert, k, v)
        self.db.flush()
        self.db.refresh(alert)
        return _to_alert_read(alert, self.db, self.actor, accessible)

    def acknowledge(self, alert_id: uuid.UUID) -> WatchlistAlertRead:
        return self._transition(
            alert_id,
            AlertStatus.ACKNOWLEDGED.value,
            acknowledged_at=datetime.now(timezone.utc),
            acknowledged_by_id=self.actor.id,
        )

    def resolve(self, alert_id: uuid.UUID) -> WatchlistAlertRead:
        return self._transition(
            alert_id,
            AlertStatus.RESOLVED.value,
            resolved_at=datetime.now(timezone.utc),
            resolved_by_id=self.actor.id,
        )

    def dismiss(self, alert_id: uuid.UUID) -> WatchlistAlertRead:
        return self._transition(alert_id, AlertStatus.DISMISSED.value)

    # ── Statistics ────────────────────────────────────────────────────────────

    def get_stats(self, case_id: uuid.UUID | None = None) -> AlertStats:
        accessible = _accessible_case_ids(self.actor, self.db)
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        base = WatchlistAlert.case_id.in_(accessible)
        if case_id:
            def base_filter(s):  # type: ignore[return]
                return s.where(WatchlistAlert.case_id == case_id)
        else:
            def base_filter(s):  # type: ignore[return]
                return s.where(base)

        def count(extra=None):
            s = select(func.count(WatchlistAlert.id))
            s = base_filter(s)
            if extra is not None:
                s = s.where(extra)
            return self.db.execute(s).scalar_one()

        return AlertStats(
            total=count(),
            new_count=count(WatchlistAlert.status == AlertStatus.NEW.value),
            acknowledged_count=count(
                WatchlistAlert.status == AlertStatus.ACKNOWLEDGED.value
            ),
            resolved_count=count(
                WatchlistAlert.status == AlertStatus.RESOLVED.value
            ),
            dismissed_count=count(
                WatchlistAlert.status == AlertStatus.DISMISSED.value
            ),
            critical_count=count(WatchlistAlert.severity == "critical"),
            high_count=count(WatchlistAlert.severity == "high"),
            cross_case_count=count(WatchlistAlert.is_cross_case.is_(True)),
            alerts_today=count(WatchlistAlert.created_at >= today),
            alerts_this_week=count(WatchlistAlert.created_at >= week_ago),
        )
