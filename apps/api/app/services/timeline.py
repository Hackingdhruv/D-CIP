"""Timeline service — the Investigation Timeline Intelligence Engine.

Aggregates curated timeline events from every source, lets investigators manage
them (create/edit/verify/pin/merge/split/comment), runs the deterministic
analysis engine with an optional AI narrative, and exports the reconstruction.

The canonical store is :class:`TimelineEvent`. AI-extracted events produced by
the processing pipeline live in :class:`EvidenceTimelineEvent`; this service
*ingests* them into the canonical store (idempotently, keyed on the origin id)
so the timeline tab shows a single, deduplicated chronology while the raw
extraction history remains intact and auditable.
"""

from __future__ import annotations

import csv
import io
import json
import math
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.case_activity import CaseActivity  # noqa: F401  (ensures mapper config)
from app.models.evidence import Evidence
from app.models.evidence_timeline_event import EvidenceTimelineEvent
from app.models.timeline_event import (
    TimelineEvent,
    TimelineEventType,
    TimelineSourceType,
    TimelineVerificationStatus,
    category_for_event_type,
)
from app.models.user import User
from app.repositories.case import CaseActivityRepository, CaseRepository
from app.repositories.timeline import (
    TimelineCommentRepository,
    TimelineEventRepository,
)
from app.schemas.timeline import (
    TimelineEventCreate,
    TimelineEventUpdate,
    TimelineListResponse,
    TimelineStatsResponse,
)
from app.services import timeline_analysis as analysis
from app.services.base import BaseService

_VALID_VERIFICATION = {s.value for s in TimelineVerificationStatus}
_AI_SOURCE_TYPES = {
    TimelineSourceType.AI_EXTRACTION.value,
    TimelineSourceType.OCR.value,
    TimelineSourceType.EXIF.value,
    TimelineSourceType.EMAIL.value,
    TimelineSourceType.FILE_METADATA.value,
}


class TimelineService(BaseService):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self._events = TimelineEventRepository(session)
        self._comments = TimelineCommentRepository(session)
        self._cases = CaseRepository(session)
        self._activity = CaseActivityRepository(session)

    # ── Case guard ───────────────────────────────────────────────────────────────

    def _require_case(self, case_id: uuid.UUID):
        case = self._cases.get_active(case_id)
        if not case:
            raise NotFoundError(f"Case {case_id} not found.")
        return case

    # ── List / get ───────────────────────────────────────────────────────────────

    def list_events(
        self,
        case_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 100,
        sort_by: str = "event_timestamp",
        sort_dir: str = "asc",
        **filters,
    ) -> TimelineListResponse:
        self._require_case(case_id)
        items, total = self._events.list_for_case(
            case_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            **filters,
        )
        from app.schemas.timeline import TimelineEventRead

        return TimelineListResponse(
            items=[TimelineEventRead.model_validate(e) for e in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=max(1, math.ceil(total / page_size)),
        )

    def get_event(self, event_id: uuid.UUID, case_id: uuid.UUID) -> TimelineEvent:
        event = self._events.get_for_case(event_id, case_id)
        if not event:
            raise NotFoundError("Timeline event not found.")
        return event

    # ── Create / update / delete ─────────────────────────────────────────────────

    def create_event(
        self, case_id: uuid.UUID, data: TimelineEventCreate, actor: User
    ) -> TimelineEvent:
        self._require_case(case_id)

        # Validate evidence belongs to the case if supplied.
        if data.evidence_id is not None:
            ev = self.session.get(Evidence, data.evidence_id)
            if ev is None or ev.case_id != case_id or ev.deleted_at is not None:
                raise ValidationError("Evidence does not belong to this case.")

        category = data.category or category_for_event_type(data.event_type)
        event = TimelineEvent(
            case_id=case_id,
            evidence_id=data.evidence_id,
            source_type=TimelineSourceType.MANUAL.value,
            event_type=data.event_type,
            category=category,
            title=data.title,
            description=data.description,
            event_timestamp=data.event_timestamp,
            event_end_timestamp=data.event_end_timestamp,
            timezone_name=data.timezone_name,
            confidence=data.confidence,
            verification_status=TimelineVerificationStatus.VERIFIED.value,
            color=data.color,
            tags=data.tags or [],
            entities=data.entities or [],
            location=data.location,
            attachments=data.attachments or [],
            source_reference=data.source_reference,
            created_by_id=actor.id,
        )
        self.session.add(event)
        self.session.flush()
        self._log(case_id, actor.id, "timeline.event_created", f"Added timeline event: {data.title}")
        self.session.commit()
        self.session.refresh(event)
        return event

    def update_event(
        self,
        event_id: uuid.UUID,
        case_id: uuid.UUID,
        data: TimelineEventUpdate,
        actor: User,
    ) -> TimelineEvent:
        event = self.get_event(event_id, case_id)
        payload = data.model_dump(exclude_unset=True)
        for field, value in payload.items():
            setattr(event, field, value)
        # Keep category coherent if the type changed but category was not set.
        if "event_type" in payload and "category" not in payload:
            event.category = category_for_event_type(event.event_type)
        self.session.flush()
        self._log(case_id, actor.id, "timeline.event_updated", f"Edited timeline event: {event.title}")
        self.session.commit()
        self.session.refresh(event)
        return event

    def delete_event(
        self, event_id: uuid.UUID, case_id: uuid.UUID, actor: User
    ) -> None:
        event = self.get_event(event_id, case_id)
        self._events.soft_delete(event)
        self._log(case_id, actor.id, "timeline.event_deleted", f"Removed timeline event: {event.title}")
        self.session.commit()

    # ── Flags ────────────────────────────────────────────────────────────────────

    def set_pinned(
        self, event_id: uuid.UUID, case_id: uuid.UUID, pinned: bool, actor: User
    ) -> TimelineEvent:
        event = self.get_event(event_id, case_id)
        event.is_pinned = pinned
        self.session.commit()
        self.session.refresh(event)
        return event

    def set_bookmarked(
        self, event_id: uuid.UUID, case_id: uuid.UUID, bookmarked: bool, actor: User
    ) -> TimelineEvent:
        event = self.get_event(event_id, case_id)
        event.is_bookmarked = bookmarked
        self.session.commit()
        self.session.refresh(event)
        return event

    def set_verification(
        self, event_id: uuid.UUID, case_id: uuid.UUID, status: str, actor: User
    ) -> TimelineEvent:
        if status not in _VALID_VERIFICATION:
            raise ValidationError(f"Invalid verification status: {status}")
        event = self.get_event(event_id, case_id)
        event.verification_status = status
        self.session.flush()
        self._log(
            case_id, actor.id, "timeline.event_verified",
            f"Marked timeline event '{event.title}' as {status}",
        )
        self.session.commit()
        self.session.refresh(event)
        return event

    # ── Merge / split ────────────────────────────────────────────────────────────

    def merge_events(
        self,
        case_id: uuid.UUID,
        primary_id: uuid.UUID,
        merge_ids: list[uuid.UUID],
        actor: User,
    ) -> TimelineEvent:
        primary = self.get_event(primary_id, case_id)
        merged = 0
        for mid in merge_ids:
            if mid == primary_id:
                continue
            child = self._events.get_for_case(mid, case_id)
            if not child:
                continue
            child.is_merged = True
            child.merged_into_id = primary_id
            # Fold child tags into the primary for discoverability.
            primary.tags = sorted(set((primary.tags or []) + (child.tags or [])))
            merged += 1
        if merged == 0:
            raise ValidationError("No valid events to merge.")
        self.session.flush()
        self._log(
            case_id, actor.id, "timeline.events_merged",
            f"Merged {merged} event(s) into '{primary.title}'",
        )
        self.session.commit()
        self.session.refresh(primary)
        return primary

    def split_event(
        self, event_id: uuid.UUID, case_id: uuid.UUID, actor: User
    ) -> int:
        """Un-merge: restore every child currently merged into *event_id*."""
        from sqlalchemy import select

        children = list(
            self.session.execute(
                select(TimelineEvent).where(
                    TimelineEvent.case_id == case_id,
                    TimelineEvent.merged_into_id == event_id,
                    TimelineEvent.deleted_at.is_(None),
                )
            ).scalars()
        )
        for child in children:
            child.is_merged = False
            child.merged_into_id = None
        self.session.flush()
        self._log(
            case_id, actor.id, "timeline.event_split",
            f"Split {len(children)} event(s) back out",
        )
        self.session.commit()
        return len(children)

    # ── Comments ─────────────────────────────────────────────────────────────────

    def list_comments(self, event_id: uuid.UUID, case_id: uuid.UUID):
        self.get_event(event_id, case_id)
        return self._comments.list_for_event(event_id)

    def add_comment(
        self, event_id: uuid.UUID, case_id: uuid.UUID, body: str, actor: User
    ):
        self.get_event(event_id, case_id)
        comment = self._comments.add_comment(event_id, author_id=actor.id, body=body)
        self.session.commit()
        self.session.refresh(comment)
        return comment

    # ── Stats ────────────────────────────────────────────────────────────────────

    def stats(self, case_id: uuid.UUID) -> TimelineStatsResponse:
        self._require_case(case_id)
        events = self._events.all_for_case(case_id)
        by_cat: dict[str, int] = {}
        by_type: dict[str, int] = {}
        by_source: dict[str, int] = {}
        verified = pinned = bookmarked = ai_gen = manual = undated = 0
        timestamps: list[datetime] = []
        for e in events:
            by_cat[e.category] = by_cat.get(e.category, 0) + 1
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
            by_source[e.source_type] = by_source.get(e.source_type, 0) + 1
            if e.verification_status == TimelineVerificationStatus.VERIFIED.value:
                verified += 1
            if e.is_pinned:
                pinned += 1
            if e.is_bookmarked:
                bookmarked += 1
            if e.source_type in _AI_SOURCE_TYPES:
                ai_gen += 1
            if e.source_type == TimelineSourceType.MANUAL.value:
                manual += 1
            if e.event_timestamp is None:
                undated += 1
            else:
                timestamps.append(e.event_timestamp)
        return TimelineStatsResponse(
            total_events=len(events),
            verified=verified,
            pinned=pinned,
            bookmarked=bookmarked,
            ai_generated=ai_gen,
            manual=manual,
            by_category=by_cat,
            by_type=by_type,
            by_source=by_source,
            earliest=min(timestamps) if timestamps else None,
            latest=max(timestamps) if timestamps else None,
            undated=undated,
        )

    # ── Analysis ─────────────────────────────────────────────────────────────────

    def analyze(self, case_id: uuid.UUID, *, use_ai: bool = True):
        case = self._require_case(case_id)
        events = self._events.all_for_case(case_id)
        rows = [
            analysis.AnalysisEvent(
                id=e.id,
                timestamp=e.event_timestamp,
                event_type=e.event_type,
                title=e.title,
                category=e.category,
            )
            for e in events
        ]
        result = analysis.analyze(rows)

        narrative: str | None = None
        model_used: str | None = None
        if use_ai and events:
            try:
                from app.services.ai_provider import generate_timeline_analysis

                digest = [
                    {
                        "timestamp": e.event_timestamp.isoformat()
                        if e.event_timestamp
                        else None,
                        "type": e.event_type,
                        "title": e.title,
                        "evidence": e.evidence.original_filename
                        if e.evidence
                        else None,
                    }
                    for e in events
                ]
                findings = {
                    "gaps": len(result.gaps),
                    "conflicts": len(result.conflicts),
                    "duplicates": len(result.duplicates),
                    "clusters": len(result.clusters),
                    "inactivity_periods": len(result.inactivity),
                }
                ai = generate_timeline_analysis(case.title, findings, digest)
                if ai:
                    narrative = ai.narrative
                    model_used = ai.model_used
            except Exception:
                narrative = None

        return self._analysis_to_schema(result, narrative, model_used)

    @staticmethod
    def _analysis_to_schema(result, narrative, model_used):
        from app.schemas.timeline import (
            TimelineAnalysisResponse,
            TimelineCluster,
            TimelineConflict,
            TimelineDuplicate,
            TimelineGap,
            TimelineGroup,
            TimelineInactivity,
        )

        return TimelineAnalysisResponse(
            analyzed_events=result.analyzed_events,
            gaps=[
                TimelineGap(
                    start=g.start,
                    end=g.end,
                    duration_hours=g.duration_hours,
                    before_event_id=g.before_event_id,
                    after_event_id=g.after_event_id,
                )
                for g in result.gaps
            ],
            conflicts=[
                TimelineConflict(kind=c.kind, description=c.description, event_ids=c.event_ids)
                for c in result.conflicts
            ],
            duplicates=[
                TimelineDuplicate(description=d.description, event_ids=d.event_ids)
                for d in result.duplicates
            ],
            clusters=[
                TimelineCluster(
                    start=c.start,
                    end=c.end,
                    event_count=c.event_count,
                    span_minutes=c.span_minutes,
                    event_ids=c.event_ids,
                    label=c.label,
                )
                for c in result.clusters
            ],
            inactivity=[
                TimelineInactivity(
                    start=i.start, end=i.end, duration_hours=i.duration_hours
                )
                for i in result.inactivity
            ],
            groups=[
                TimelineGroup(key=g.key, label=g.label, event_ids=g.event_ids)
                for g in result.groups
            ],
            narrative=narrative,
            model_used=model_used,
        )

    # ── Export ───────────────────────────────────────────────────────────────────

    def export(self, case_id: uuid.UUID, fmt: str) -> tuple[bytes, str, str]:
        """Return ``(content, media_type, filename)`` for *fmt* in {json,csv,pdf}."""
        case = self._require_case(case_id)
        events = self._events.all_for_case(case_id)
        fmt = fmt.lower()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        base = f"timeline_{case.reference_number}_{stamp}"

        if fmt == "json":
            payload = {
                "case": {"id": str(case.id), "reference": case.reference_number, "title": case.title},
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "event_count": len(events),
                "events": [self._event_to_dict(e) for e in events],
            }
            return (
                json.dumps(payload, indent=2, default=str).encode("utf-8"),
                "application/json",
                f"{base}.json",
            )

        if fmt == "csv":
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(
                [
                    "timestamp", "end_timestamp", "event_type", "category",
                    "title", "description", "confidence", "verification",
                    "source_type", "evidence", "tags",
                ]
            )
            for e in events:
                writer.writerow(
                    [
                        e.event_timestamp.isoformat() if e.event_timestamp else "",
                        e.event_end_timestamp.isoformat() if e.event_end_timestamp else "",
                        e.event_type,
                        e.category,
                        e.title,
                        (e.description or "").replace("\n", " "),
                        e.confidence,
                        e.verification_status,
                        e.source_type,
                        e.evidence.original_filename if e.evidence else "",
                        "|".join(e.tags or []),
                    ]
                )
            return buf.getvalue().encode("utf-8"), "text/csv", f"{base}.csv"

        if fmt == "pdf":
            from app.services.pdf_export import render_text_pdf

            lines: list[str] = [
                f"Case: {case.title} ({case.reference_number})",
                f"Events: {len(events)}",
                "",
            ]
            for e in events:
                ts = e.event_timestamp.strftime("%Y-%m-%d %H:%M") if e.event_timestamp else "undated"
                lines.append(f"[{ts}] {e.event_type.upper()} — {e.title}")
                meta = f"    confidence={e.confidence:.2f} status={e.verification_status} source={e.source_type}"
                if e.evidence:
                    meta += f" evidence={e.evidence.original_filename}"
                lines.append(meta)
                if e.description:
                    lines.append(f"    {e.description}")
                lines.append("")
            content = render_text_pdf(f"Investigation Timeline — {case.title}", lines)
            return content, "application/pdf", f"{base}.pdf"

        raise ValidationError(f"Unsupported export format: {fmt}")

    @staticmethod
    def _event_to_dict(e: TimelineEvent) -> dict:
        return {
            "id": str(e.id),
            "event_type": e.event_type,
            "category": e.category,
            "title": e.title,
            "description": e.description,
            "event_timestamp": e.event_timestamp.isoformat() if e.event_timestamp else None,
            "event_end_timestamp": e.event_end_timestamp.isoformat()
            if e.event_end_timestamp
            else None,
            "confidence": e.confidence,
            "verification_status": e.verification_status,
            "source_type": e.source_type,
            "evidence_id": str(e.evidence_id) if e.evidence_id else None,
            "tags": e.tags or [],
            "entities": e.entities or [],
            "location": e.location,
            "is_pinned": e.is_pinned,
            "is_bookmarked": e.is_bookmarked,
        }

    # ── Ingest from the AI extraction store ──────────────────────────────────────

    def ingest_from_extraction(
        self, case_id: uuid.UUID, evidence_id: uuid.UUID | None = None, *, commit: bool = True
    ) -> int:
        """Mirror new EvidenceTimelineEvent rows into the canonical timeline.

        Idempotent: events already ingested (matched by ``origin_event_id``) are
        skipped, so this is safe to call after every pipeline run or on demand.
        Returns the number of newly created canonical events.
        """
        from sqlalchemy import select

        stmt = select(EvidenceTimelineEvent).where(
            EvidenceTimelineEvent.case_id == case_id
        )
        if evidence_id is not None:
            stmt = stmt.where(EvidenceTimelineEvent.evidence_id == evidence_id)
        raw_events = list(self.session.execute(stmt).scalars())

        already = self._events.existing_origin_ids(case_id)
        created = 0
        ev_cache: dict[uuid.UUID, Evidence | None] = {}
        for raw in raw_events:
            if raw.id in already:
                continue
            if raw.evidence_id not in ev_cache:
                ev_cache[raw.evidence_id] = self.session.get(Evidence, raw.evidence_id)
            ev = ev_cache.get(raw.evidence_id)
            event_type = raw.event_type or TimelineEventType.UNKNOWN.value
            attachments = (
                [{"evidence_id": str(ev.id), "filename": ev.original_filename}]
                if ev
                else []
            )
            self.session.add(
                TimelineEvent(
                    case_id=case_id,
                    evidence_id=raw.evidence_id,
                    origin_event_id=raw.id,
                    source_type=TimelineSourceType.AI_EXTRACTION.value,
                    event_type=event_type,
                    category=category_for_event_type(event_type),
                    title=raw.event_title,
                    description=raw.description,
                    event_timestamp=raw.event_timestamp,
                    confidence=raw.confidence,
                    verification_status=TimelineVerificationStatus.UNVERIFIED.value,
                    source_text=raw.source_text,
                    attachments=attachments,
                )
            )
            created += 1
        if created:
            self.session.flush()
            if commit:
                self.session.commit()
        return created

    def record_evidence_event(
        self,
        case_id: uuid.UUID,
        evidence: Evidence,
        *,
        event_type: str,
        title: str,
        timestamp: datetime,
        commit: bool = True,
    ) -> TimelineEvent:
        """Record an evidence lifecycle event (uploaded/processed) on the timeline."""
        event = TimelineEvent(
            case_id=case_id,
            evidence_id=evidence.id,
            source_type=TimelineSourceType.EVIDENCE_METADATA.value,
            event_type=event_type,
            category=category_for_event_type(event_type),
            title=title,
            event_timestamp=timestamp,
            confidence=1.0,
            verification_status=TimelineVerificationStatus.VERIFIED.value,
            attachments=[
                {"evidence_id": str(evidence.id), "filename": evidence.original_filename}
            ],
        )
        self.session.add(event)
        self.session.flush()
        if commit:
            self.session.commit()
        return event

    # ── Internal ─────────────────────────────────────────────────────────────────

    def _log(
        self, case_id: uuid.UUID, actor_id: uuid.UUID | None, action: str, description: str
    ) -> None:
        try:
            self._activity.log(case_id, action, description, actor_id=actor_id)
        except Exception:
            # Activity logging must never break the primary operation.
            pass
