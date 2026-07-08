"""WatchlistService — CRUD for watchlists, entries, and statistics."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.case_assignment import CaseAssignment
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistEntry
from app.models.watchlist_alert import WatchlistAlert
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistEntryCreate,
    WatchlistEntryListResponse,
    WatchlistEntryRead,
    WatchlistEntryUpdate,
    WatchlistListResponse,
    WatchlistRead,
    WatchlistStats,
    WatchlistUpdate,
)


def _normalize(value: str) -> str:
    return value.strip().lower()


def _accessible_case_ids(user: User, db: Session) -> list[uuid.UUID]:
    """Return case IDs visible to this user (same RBAC pattern as dashboard)."""
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


def _to_watchlist_read(wl: Watchlist, db: Session) -> WatchlistRead:
    entry_count = db.execute(
        select(func.count(WatchlistEntry.id)).where(
            WatchlistEntry.watchlist_id == wl.id,
            WatchlistEntry.is_active.is_(True),
        )
    ).scalar_one()
    alert_count = db.execute(
        select(func.count(WatchlistAlert.id)).where(
            WatchlistAlert.watchlist_id == wl.id
        )
    ).scalar_one()
    email = None
    if wl.created_by_id is not None:
        user = db.get(User, wl.created_by_id)
        email = user.email if user else None
    return WatchlistRead(
        id=wl.id,
        name=wl.name,
        description=wl.description,
        watchlist_type=wl.watchlist_type,
        is_active=wl.is_active,
        case_id=wl.case_id,
        created_by_id=wl.created_by_id,
        created_by_email=email,
        entry_count=entry_count,
        alert_count=alert_count,
        created_at=wl.created_at,
        updated_at=wl.updated_at,
    )


class WatchlistService:
    def __init__(self, db: Session, actor: User) -> None:
        self.db = db
        self.actor = actor

    # ── Watchlist CRUD ────────────────────────────────────────────────────────

    def list_watchlists(
        self,
        page: int = 1,
        page_size: int = 20,
        watchlist_type: str | None = None,
        is_active: bool | None = None,
        case_id: uuid.UUID | None = None,
        include_global: bool = True,
    ) -> WatchlistListResponse:
        stmt = select(Watchlist)
        if watchlist_type:
            stmt = stmt.where(Watchlist.watchlist_type == watchlist_type)
        if is_active is not None:
            stmt = stmt.where(Watchlist.is_active.is_(is_active))
        if case_id is not None:
            if include_global:
                stmt = stmt.where(
                    (Watchlist.case_id == case_id) | (Watchlist.case_id.is_(None))
                )
            else:
                stmt = stmt.where(Watchlist.case_id == case_id)
        elif not include_global:
            stmt = stmt.where(Watchlist.case_id.is_not(None))

        total = self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()
        pages = max(1, math.ceil(total / page_size))
        items = self.db.execute(
            stmt.order_by(Watchlist.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).scalars().all()
        return WatchlistListResponse(
            items=[_to_watchlist_read(w, self.db) for w in items],
            total=total,
            page=page,
            pages=pages,
        )

    def get_watchlist(self, watchlist_id: uuid.UUID) -> Watchlist:
        wl = self.db.get(Watchlist, watchlist_id)
        if wl is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Watchlist not found")
        return wl

    def get_watchlist_read(self, watchlist_id: uuid.UUID) -> WatchlistRead:
        return _to_watchlist_read(self.get_watchlist(watchlist_id), self.db)

    def create_watchlist(self, data: WatchlistCreate) -> WatchlistRead:
        wl = Watchlist(
            name=data.name,
            description=data.description,
            watchlist_type=data.watchlist_type,
            is_active=data.is_active,
            case_id=data.case_id,
            created_by_id=self.actor.id,
        )
        self.db.add(wl)
        self.db.flush()
        self.db.refresh(wl)
        return _to_watchlist_read(wl, self.db)

    def update_watchlist(
        self, watchlist_id: uuid.UUID, data: WatchlistUpdate
    ) -> WatchlistRead:
        wl = self.get_watchlist(watchlist_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(wl, field, value)
        self.db.flush()
        self.db.refresh(wl)
        return _to_watchlist_read(wl, self.db)

    def delete_watchlist(self, watchlist_id: uuid.UUID) -> None:
        wl = self.get_watchlist(watchlist_id)
        self.db.delete(wl)
        self.db.flush()

    # ── Entry CRUD ────────────────────────────────────────────────────────────

    def list_entries(self, watchlist_id: uuid.UUID) -> WatchlistEntryListResponse:
        self.get_watchlist(watchlist_id)  # ensures 404 if missing
        stmt = (
            select(WatchlistEntry)
            .where(WatchlistEntry.watchlist_id == watchlist_id)
            .order_by(WatchlistEntry.created_at.desc())
        )
        entries = self.db.execute(stmt).scalars().all()
        return WatchlistEntryListResponse(
            items=[WatchlistEntryRead.model_validate(e) for e in entries],
            total=len(entries),
        )

    def add_entry(
        self, watchlist_id: uuid.UUID, data: WatchlistEntryCreate
    ) -> WatchlistEntryRead:
        self.get_watchlist(watchlist_id)
        entry = WatchlistEntry(
            watchlist_id=watchlist_id,
            value=data.value,
            normalized_value=_normalize(data.value),
            is_regex=data.is_regex,
            description=data.description,
            created_by_id=self.actor.id,
        )
        self.db.add(entry)
        self.db.flush()
        self.db.refresh(entry)
        return WatchlistEntryRead.model_validate(entry)

    def update_entry(
        self, entry_id: uuid.UUID, data: WatchlistEntryUpdate
    ) -> WatchlistEntryRead:
        entry = self.db.get(WatchlistEntry, entry_id)
        if entry is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Watchlist entry not found")
        updates = data.model_dump(exclude_unset=True)
        if "value" in updates:
            entry.value = updates.pop("value")
            entry.normalized_value = _normalize(entry.value)
        for field, value in updates.items():
            setattr(entry, field, value)
        self.db.flush()
        self.db.refresh(entry)
        return WatchlistEntryRead.model_validate(entry)

    def delete_entry(self, entry_id: uuid.UUID) -> None:
        entry = self.db.get(WatchlistEntry, entry_id)
        if entry is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Watchlist entry not found")
        self.db.delete(entry)
        self.db.flush()

    # ── Statistics ────────────────────────────────────────────────────────────

    def get_stats(self) -> WatchlistStats:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        total = self.db.execute(select(func.count(Watchlist.id))).scalar_one()
        active = self.db.execute(
            select(func.count(Watchlist.id)).where(Watchlist.is_active.is_(True))
        ).scalar_one()
        entries = self.db.execute(
            select(func.count(WatchlistEntry.id)).where(
                WatchlistEntry.is_active.is_(True)
            )
        ).scalar_one()
        total_alerts = self.db.execute(
            select(func.count(WatchlistAlert.id))
        ).scalar_one()
        today_alerts = self.db.execute(
            select(func.count(WatchlistAlert.id)).where(
                WatchlistAlert.created_at >= today_start
            )
        ).scalar_one()
        week_alerts = self.db.execute(
            select(func.count(WatchlistAlert.id)).where(
                WatchlistAlert.created_at >= week_start
            )
        ).scalar_one()

        # Top 5 watchlists by alert count
        top_rows = self.db.execute(
            select(
                Watchlist.id,
                Watchlist.name,
                func.count(WatchlistAlert.id).label("cnt"),
            )
            .outerjoin(WatchlistAlert, WatchlistAlert.watchlist_id == Watchlist.id)
            .group_by(Watchlist.id, Watchlist.name)
            .order_by(func.count(WatchlistAlert.id).desc())
            .limit(5)
        ).all()
        top_hit = [
            {"id": str(r.id), "name": r.name, "alert_count": r.cnt}
            for r in top_rows
        ]

        return WatchlistStats(
            total_watchlists=total,
            active_watchlists=active,
            total_entries=entries,
            total_alerts=total_alerts,
            alerts_today=today_alerts,
            alerts_this_week=week_alerts,
            top_hit_watchlists=top_hit,
        )

    # ── Active watchlists for matching engine ─────────────────────────────────

    def get_active_watchlists_for_case(
        self, case_id: uuid.UUID
    ) -> list[Watchlist]:
        """Return all active global watchlists plus case-specific ones."""
        stmt = (
            select(Watchlist)
            .where(
                Watchlist.is_active.is_(True),
                (Watchlist.case_id == case_id) | (Watchlist.case_id.is_(None)),
            )
        )
        return list(self.db.execute(stmt).scalars())
