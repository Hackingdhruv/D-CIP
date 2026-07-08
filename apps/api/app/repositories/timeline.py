"""Timeline event + comment repositories."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.timeline_event import TimelineEvent
from app.models.timeline_event_comment import TimelineEventComment
from app.repositories.base import BaseRepository

_SORT_COLUMNS = {
    "event_timestamp": TimelineEvent.event_timestamp,
    "created_at": TimelineEvent.created_at,
    "confidence": TimelineEvent.confidence,
    "title": TimelineEvent.title,
}


class TimelineEventRepository(BaseRepository[TimelineEvent]):
    model = TimelineEvent

    # ── Lookups ────────────────────────────────────────────────────────────────

    def get_for_case(
        self, event_id: uuid.UUID, case_id: uuid.UUID
    ) -> TimelineEvent | None:
        return self.session.execute(
            select(TimelineEvent).where(
                TimelineEvent.id == event_id,
                TimelineEvent.case_id == case_id,
                TimelineEvent.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def existing_origin_ids(self, case_id: uuid.UUID) -> set[uuid.UUID]:
        """Origin extraction ids already ingested into the canonical timeline."""
        rows = self.session.execute(
            select(TimelineEvent.origin_event_id).where(
                TimelineEvent.case_id == case_id,
                TimelineEvent.origin_event_id.is_not(None),
            )
        ).scalars()
        return {r for r in rows if r is not None}

    # ── Filtered query builder ───────────────────────────────────────────────────

    def _filtered(
        self,
        case_id: uuid.UUID,
        *,
        q: str | None = None,
        event_types: list[str] | None = None,
        categories: list[str] | None = None,
        source_types: list[str] | None = None,
        verification: list[str] | None = None,
        tag: str | None = None,
        min_confidence: float | None = None,
        max_confidence: float | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        is_pinned: bool | None = None,
        is_bookmarked: bool | None = None,
        include_merged: bool = False,
        include_undated: bool = True,
    ):
        stmt = select(TimelineEvent).where(
            TimelineEvent.case_id == case_id,
            TimelineEvent.deleted_at.is_(None),
        )
        if not include_merged:
            stmt = stmt.where(TimelineEvent.is_merged.is_(False))
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    TimelineEvent.title.ilike(like),
                    TimelineEvent.description.ilike(like),
                    TimelineEvent.source_text.ilike(like),
                )
            )
        if event_types:
            stmt = stmt.where(TimelineEvent.event_type.in_(event_types))
        if categories:
            stmt = stmt.where(TimelineEvent.category.in_(categories))
        if source_types:
            stmt = stmt.where(TimelineEvent.source_type.in_(source_types))
        if verification:
            stmt = stmt.where(TimelineEvent.verification_status.in_(verification))
        if tag:
            stmt = stmt.where(TimelineEvent.tags.contains([tag]))
        if min_confidence is not None:
            stmt = stmt.where(TimelineEvent.confidence >= min_confidence)
        if max_confidence is not None:
            stmt = stmt.where(TimelineEvent.confidence <= max_confidence)
        if date_from is not None:
            stmt = stmt.where(TimelineEvent.event_timestamp >= date_from)
        if date_to is not None:
            stmt = stmt.where(TimelineEvent.event_timestamp <= date_to)
        if not include_undated and (date_from is not None or date_to is not None):
            stmt = stmt.where(TimelineEvent.event_timestamp.is_not(None))
        if is_pinned is not None:
            stmt = stmt.where(TimelineEvent.is_pinned.is_(is_pinned))
        if is_bookmarked is not None:
            stmt = stmt.where(TimelineEvent.is_bookmarked.is_(is_bookmarked))
        return stmt

    def list_for_case(
        self,
        case_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 100,
        sort_by: str = "event_timestamp",
        sort_dir: str = "asc",
        **filters,
    ) -> tuple[list[TimelineEvent], int]:
        stmt = self._filtered(case_id, **filters)

        total: int = self.session.execute(
            select(func.count()).select_from(stmt.subquery())
        ).scalar_one()

        column = _SORT_COLUMNS.get(sort_by, TimelineEvent.event_timestamp)
        if sort_dir == "desc":
            order = column.desc().nulls_last()
        else:
            order = column.asc().nulls_last()

        items = list(
            self.session.execute(
                stmt.order_by(order, TimelineEvent.created_at.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).scalars()
        )
        return items, total

    def all_for_case(
        self, case_id: uuid.UUID, *, include_merged: bool = False, cap: int = 5000
    ) -> list[TimelineEvent]:
        """All (capped) events for a case — used by analysis and export."""
        stmt = self._filtered(case_id, include_merged=include_merged)
        return list(
            self.session.execute(
                stmt.order_by(TimelineEvent.event_timestamp.asc().nulls_last()).limit(cap)
            ).scalars()
        )

    # ── Stats ────────────────────────────────────────────────────────────────────

    def count_for_case(self, case_id: uuid.UUID) -> int:
        return self.session.execute(
            select(func.count()).where(
                TimelineEvent.case_id == case_id,
                TimelineEvent.deleted_at.is_(None),
                TimelineEvent.is_merged.is_(False),
            )
        ).scalar_one()

    # ── Mutations ────────────────────────────────────────────────────────────────

    def soft_delete(self, event: TimelineEvent) -> None:
        from datetime import timezone

        event.deleted_at = datetime.now(timezone.utc)
        self.session.flush()


class TimelineCommentRepository(BaseRepository[TimelineEventComment]):
    model = TimelineEventComment

    def list_for_event(self, event_id: uuid.UUID) -> list[TimelineEventComment]:
        return list(
            self.session.execute(
                select(TimelineEventComment)
                .where(TimelineEventComment.event_id == event_id)
                .order_by(TimelineEventComment.created_at.asc())
            ).scalars()
        )

    def add_comment(
        self, event_id: uuid.UUID, *, author_id: uuid.UUID | None, body: str
    ) -> TimelineEventComment:
        comment = TimelineEventComment(
            event_id=event_id, author_id=author_id, body=body
        )
        self.session.add(comment)
        self.session.flush()
        return comment
