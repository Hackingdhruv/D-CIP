"""Dashboard aggregation service.

All queries are RBAC-scoped to cases the current user can access.
Expensive aggregations use optimised SQL (COUNT / GROUP BY) — no full
row loads.  Health probes run with sub-second timeouts to keep the
Operations endpoint fast.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Integer,
    cast,
    distinct,
    extract,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.case_assignment import CaseAssignment
from app.models.case_note import CaseNote
from app.models.case_task import CaseTask
from app.models.evidence import Evidence
from app.models.evidence_entity import EvidenceEntity
from app.models.evidence_keyword import EvidenceKeyword
from app.models.report import InvestigationReport
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.schemas.dashboard import (
    CasePriorityBreakdown,
    CaseStatusBreakdown,
    ConfidenceBucket,
    DateCount,
    EntityDistributionItem,
    EvidenceTypeItem,
    ExecutiveDashboard,
    IntelligenceDashboard,
    InvestigatorDashboard,
    InvestigatorWorkload,
    MyCase,
    MyEvidence,
    MyNote,
    MyTask,
    OperationsDashboard,
    ProcessingStats,
    ProductivityMetrics,
    QueueInfo,
    RecentCaseSummary,
    ServiceHealth,
    StorageStats,
    TopEntity,
    TopKeyword,
)


# ── RBAC helper ────────────────────────────────────────────────────────────────

def _accessible_case_ids(session: Session, user: User):
    """Subquery: IDs of all cases the user can see (mirrors search/report pattern)."""
    assigned_subq = (
        select(CaseAssignment.case_id)
        .where(CaseAssignment.user_id == user.id)
        .scalar_subquery()
    )
    return (
        select(Case.id)
        .where(
            Case.deleted_at.is_(None),
            or_(
                Case.is_private.is_(False),
                Case.owner_id == user.id,
                Case.id.in_(assigned_subq),
            ),
        )
        .scalar_subquery()
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _now() - timedelta(days=n)


# ── Executive Dashboard ────────────────────────────────────────────────────────

class DashboardService:

    def __init__(self, session: Session, user: User) -> None:
        self.db = session
        self.user = user
        self._accessible = None  # cached per request

    def _accessible_ids(self):
        if self._accessible is None:
            self._accessible = _accessible_case_ids(self.db, self.user)
        return self._accessible

    # ── Executive ─────────────────────────────────────────────────────────────

    def get_executive(self) -> ExecutiveDashboard:
        accessible = self._accessible_ids()
        now = _now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # ── Case counters ──────────────────────────────────────────────────────
        active_statuses = ("open", "in_progress", "under_review", "on_hold")
        closed_statuses = ("closed", "archived")

        total_cases = self.db.execute(
            select(func.count()).select_from(Case)
            .where(Case.id.in_(accessible))
        ).scalar() or 0

        active_cases = self.db.execute(
            select(func.count()).select_from(Case)
            .where(Case.id.in_(accessible), Case.status.in_(active_statuses))
        ).scalar() or 0

        high_priority_cases = self.db.execute(
            select(func.count()).select_from(Case)
            .where(
                Case.id.in_(accessible),
                Case.status.in_(active_statuses),
                Case.priority.in_(("high", "critical")),
            )
        ).scalar() or 0

        closed_cases = self.db.execute(
            select(func.count()).select_from(Case)
            .where(Case.id.in_(accessible), Case.status.in_(closed_statuses))
        ).scalar() or 0

        # ── Status / priority breakdown ────────────────────────────────────────
        rows = self.db.execute(
            select(Case.status, func.count().label("n"))
            .where(Case.id.in_(accessible))
            .group_by(Case.status)
        ).all()
        status_map: dict[str, int] = {r.status: r.n for r in rows}

        rows_p = self.db.execute(
            select(Case.priority, func.count().label("n"))
            .where(Case.id.in_(accessible))
            .group_by(Case.priority)
        ).all()
        priority_map: dict[str, int] = {r.priority: r.n for r in rows_p}

        # ── Daily new cases (last 30 days) ─────────────────────────────────────
        cutoff_30 = _days_ago(30)
        daily_cases_rows = self.db.execute(
            select(
                func.date_trunc("day", Case.created_at).label("day"),
                func.count().label("n"),
            )
            .where(Case.id.in_(accessible), Case.created_at >= cutoff_30)
            .group_by(text("day"))
            .order_by(text("day"))
        ).all()
        cases_opened_30d = [
            DateCount(date=r.day.strftime("%Y-%m-%d"), count=r.n)
            for r in daily_cases_rows
        ]

        # ── Evidence counters ──────────────────────────────────────────────────
        total_evidence = self.db.execute(
            select(func.count()).select_from(Evidence)
            .where(Evidence.case_id.in_(accessible))
        ).scalar() or 0

        evidence_today = self.db.execute(
            select(func.count()).select_from(Evidence)
            .where(
                Evidence.case_id.in_(accessible),
                Evidence.created_at >= today_start,
            )
        ).scalar() or 0

        ai_queue_statuses = ("ai_queue", "ocr_queue", "metadata_extraction", "hashing")
        ai_queue_size = self.db.execute(
            select(func.count()).select_from(Evidence)
            .where(
                Evidence.case_id.in_(accessible),
                Evidence.status.in_(ai_queue_statuses),
            )
        ).scalar() or 0

        # ── Daily evidence uploads (last 30 days) ──────────────────────────────
        daily_ev_rows = self.db.execute(
            select(
                func.date_trunc("day", Evidence.created_at).label("day"),
                func.count().label("n"),
            )
            .where(
                Evidence.case_id.in_(accessible),
                Evidence.created_at >= cutoff_30,
            )
            .group_by(text("day"))
            .order_by(text("day"))
        ).all()
        ev_uploaded_30d = [
            DateCount(date=r.day.strftime("%Y-%m-%d"), count=r.n)
            for r in daily_ev_rows
        ]

        # ── Reports ────────────────────────────────────────────────────────────
        reports_generated = self.db.execute(
            select(func.count()).select_from(InvestigationReport)
            .where(
                InvestigationReport.case_id.in_(accessible),
                InvestigationReport.deleted_at.is_(None),
                InvestigationReport.status != "draft",
            )
        ).scalar() or 0

        reports_published = self.db.execute(
            select(func.count()).select_from(InvestigationReport)
            .where(
                InvestigationReport.case_id.in_(accessible),
                InvestigationReport.deleted_at.is_(None),
                InvestigationReport.status == "published",
            )
        ).scalar() or 0

        # ── Average investigation duration (closed cases) ──────────────────────
        avg_result = self.db.execute(
            select(
                func.avg(
                    extract("epoch", Case.closed_at - Case.created_at) / 86400
                ).label("avg_days")
            )
            .where(
                Case.id.in_(accessible),
                Case.closed_at.is_not(None),
            )
        ).scalar()
        avg_investigation_days = round(float(avg_result), 1) if avg_result else 0.0

        # ── Investigator workload ──────────────────────────────────────────────
        # Count active cases and open tasks per user who owns cases accessible to viewer
        workload_rows = self.db.execute(
            select(
                User.id.label("user_id"),
                User.full_name.label("full_name"),
                func.count(distinct(Case.id)).filter(
                    Case.status.in_(active_statuses)
                ).label("active_case_count"),
            )
            .join(Case, Case.owner_id == User.id)
            .where(Case.id.in_(accessible))
            .group_by(User.id, User.full_name)
            .order_by(func.count(distinct(Case.id)).filter(
                Case.status.in_(active_statuses)
            ).desc())
            .limit(10)
        ).all()

        # Open tasks per user
        open_task_map: dict[str, int] = {}
        if workload_rows:
            uid_list = [r.user_id for r in workload_rows]
            task_rows = self.db.execute(
                select(
                    CaseTask.assignee_id.label("uid"),
                    func.count().label("n"),
                )
                .join(Case, CaseTask.case_id == Case.id)
                .where(
                    Case.id.in_(accessible),
                    CaseTask.status.in_(("pending", "in_progress")),
                    CaseTask.assignee_id.in_(uid_list),
                )
                .group_by(CaseTask.assignee_id)
            ).all()
            open_task_map = {str(r.uid): r.n for r in task_rows if r.uid}

        workload = [
            InvestigatorWorkload(
                user_id=str(r.user_id),
                full_name=r.full_name,
                active_case_count=r.active_case_count or 0,
                open_task_count=open_task_map.get(str(r.user_id), 0),
            )
            for r in workload_rows
        ]

        # ── Recently active cases ──────────────────────────────────────────────
        recent_rows = self.db.execute(
            select(
                Case.id, Case.reference_number, Case.title,
                Case.status, Case.priority, Case.updated_at,
            )
            .where(Case.id.in_(accessible))
            .order_by(Case.updated_at.desc())
            .limit(8)
        ).all()
        recently_active = [
            RecentCaseSummary(
                id=str(r.id),
                reference_number=r.reference_number,
                title=r.title,
                status=r.status,
                priority=r.priority,
                updated_at=r.updated_at,
            )
            for r in recent_rows
        ]

        return ExecutiveDashboard(
            active_cases=active_cases,
            high_priority_cases=high_priority_cases,
            closed_cases=closed_cases,
            total_cases=total_cases,
            evidence_uploaded_today=evidence_today,
            total_evidence=total_evidence,
            reports_generated=reports_generated,
            reports_published=reports_published,
            ai_queue_size=ai_queue_size,
            avg_investigation_days=avg_investigation_days,
            status_breakdown=CaseStatusBreakdown(
                draft=status_map.get("draft", 0),
                open=status_map.get("open", 0),
                in_progress=status_map.get("in_progress", 0),
                under_review=status_map.get("under_review", 0),
                on_hold=status_map.get("on_hold", 0),
                closed=status_map.get("closed", 0),
                archived=status_map.get("archived", 0),
            ),
            priority_breakdown=CasePriorityBreakdown(
                low=priority_map.get("low", 0),
                medium=priority_map.get("medium", 0),
                high=priority_map.get("high", 0),
                critical=priority_map.get("critical", 0),
            ),
            cases_opened_last_30_days=cases_opened_30d,
            evidence_uploaded_last_30_days=ev_uploaded_30d,
            investigator_workload=workload,
            recently_active_cases=recently_active,
            generated_at=now,
        )

    # ── Intelligence ───────────────────────────────────────────────────────────

    def get_intelligence(self) -> IntelligenceDashboard:
        accessible = self._accessible_ids()
        now = _now()
        cutoff_30 = _days_ago(30)

        # ── Entity distribution ────────────────────────────────────────────────
        entity_rows = self.db.execute(
            select(
                EvidenceEntity.entity_type.label("etype"),
                func.count().label("n"),
            )
            .where(EvidenceEntity.case_id.in_(accessible))
            .group_by(EvidenceEntity.entity_type)
            .order_by(func.count().desc())
        ).all()
        entity_dist = [
            EntityDistributionItem(entity_type=r.etype, count=r.n)
            for r in entity_rows
        ]

        # ── Top organizations ──────────────────────────────────────────────────
        top_orgs = self._top_entities(accessible, "organization")
        top_devices = self._top_entities(accessible, "device")
        top_persons = self._top_entities(accessible, "person")

        # ── Evidence type distribution ─────────────────────────────────────────
        ev_type_rows = self.db.execute(
            select(
                Evidence.mime_type.label("mime"),
                func.count().label("n"),
            )
            .where(Evidence.case_id.in_(accessible))
            .group_by(Evidence.mime_type)
            .order_by(func.count().desc())
            .limit(15)
        ).all()
        ev_type_dist = [
            EvidenceTypeItem(
                mime_type=r.mime,
                label=_mime_label(r.mime),
                count=r.n,
            )
            for r in ev_type_rows
        ]

        # ── AI confidence distribution ─────────────────────────────────────────
        # Buckets: 0.0-0.5, 0.5-0.7, 0.7-0.9, 0.9-1.0
        bucket_cases = [
            ("0.0–0.5", 0.0, 0.5),
            ("0.5–0.7", 0.5, 0.7),
            ("0.7–0.9", 0.7, 0.9),
            ("0.9–1.0", 0.9, 1.001),
        ]
        confidence_dist: list[ConfidenceBucket] = []
        for label, lo, hi in bucket_cases:
            n = self.db.execute(
                select(func.count()).select_from(EvidenceEntity)
                .where(
                    EvidenceEntity.case_id.in_(accessible),
                    EvidenceEntity.confidence >= lo,
                    EvidenceEntity.confidence < hi,
                )
            ).scalar() or 0
            confidence_dist.append(ConfidenceBucket(bucket=label, count=n))

        # ── Top keywords ───────────────────────────────────────────────────────
        kw_rows = self.db.execute(
            select(
                EvidenceKeyword.keyword.label("kw"),
                func.sum(EvidenceKeyword.score).label("total_score"),
                func.count().label("occ"),
            )
            .where(EvidenceKeyword.case_id.in_(accessible))
            .group_by(EvidenceKeyword.keyword)
            .order_by(func.sum(EvidenceKeyword.score).desc())
            .limit(20)
        ).all()
        top_keywords = [
            TopKeyword(
                keyword=r.kw,
                total_score=round(float(r.total_score), 3),
                occurrence_count=r.occ,
            )
            for r in kw_rows
        ]

        # ── Timeline heatmap (last 30 days) ───────────────────────────────────
        heatmap_rows = self.db.execute(
            select(
                func.date_trunc("day", TimelineEvent.event_timestamp).label("day"),
                func.count().label("n"),
            )
            .where(
                TimelineEvent.case_id.in_(accessible),
                TimelineEvent.event_timestamp.is_not(None),
                TimelineEvent.event_timestamp >= cutoff_30,
            )
            .group_by(text("day"))
            .order_by(text("day"))
        ).all()
        heatmap = [
            DateCount(date=r.day.strftime("%Y-%m-%d"), count=r.n)
            for r in heatmap_rows
        ]

        # ── Relationship density proxy ─────────────────────────────────────────
        total_unique = self.db.execute(
            select(func.count(distinct(EvidenceEntity.normalized_value)))
            .where(EvidenceEntity.case_id.in_(accessible))
        ).scalar() or 0

        case_count = self.db.execute(
            select(func.count()).select_from(Case)
            .where(Case.id.in_(accessible))
        ).scalar() or 1
        avg_entities = round(total_unique / max(case_count, 1), 1)

        return IntelligenceDashboard(
            entity_distribution=entity_dist,
            top_organizations=top_orgs,
            top_devices=top_devices,
            top_persons=top_persons,
            evidence_type_distribution=ev_type_dist,
            ai_confidence_distribution=confidence_dist,
            top_keywords=top_keywords,
            timeline_heatmap=heatmap,
            avg_entities_per_case=avg_entities,
            total_unique_entities=total_unique,
            generated_at=now,
        )

    def _top_entities(self, accessible, entity_type: str, limit: int = 10) -> list[TopEntity]:
        rows = self.db.execute(
            select(
                EvidenceEntity.normalized_value.label("val"),
                func.count().label("occ"),
                func.avg(EvidenceEntity.confidence).label("avg_conf"),
            )
            .where(
                EvidenceEntity.case_id.in_(accessible),
                EvidenceEntity.entity_type == entity_type,
            )
            .group_by(EvidenceEntity.normalized_value)
            .order_by(func.count().desc())
            .limit(limit)
        ).all()
        return [
            TopEntity(
                value=r.val,
                entity_type=entity_type,
                occurrence_count=r.occ,
                avg_confidence=round(float(r.avg_conf), 3) if r.avg_conf else 0.0,
            )
            for r in rows
        ]

    # ── Operations ─────────────────────────────────────────────────────────────

    def get_operations(self) -> OperationsDashboard:
        """Probe all infrastructure services and return health + queue stats."""
        now = _now()
        services: list[ServiceHealth] = []

        # PostgreSQL
        services.append(self._probe_postgres())

        # Redis
        try:
            from app.db.redis_client import get_redis
            r = get_redis()
            t0 = time.monotonic()
            r.ping()
            lat = round((time.monotonic() - t0) * 1000, 1)
            services.append(ServiceHealth(name="Redis", status="healthy", latency_ms=lat))
        except Exception as exc:
            services.append(ServiceHealth(name="Redis", status="down", message=str(exc)[:120]))

        # Neo4j
        try:
            from app.db.neo4j_client import get_driver
            t0 = time.monotonic()
            get_driver().verify_connectivity()
            lat = round((time.monotonic() - t0) * 1000, 1)
            services.append(ServiceHealth(name="Neo4j", status="healthy", latency_ms=lat))
        except Exception as exc:
            services.append(ServiceHealth(name="Neo4j", status="down", message=str(exc)[:120]))

        # OpenSearch
        try:
            from app.db.opensearch_client import get_client as get_opensearch_client
            t0 = time.monotonic()
            client = get_opensearch_client()
            info = client.info()
            lat = round((time.monotonic() - t0) * 1000, 1)
            version = info.get("version", {}).get("number", "?")
            services.append(
                ServiceHealth(name="OpenSearch", status="healthy", latency_ms=lat, message=f"v{version}")
            )
        except Exception as exc:
            services.append(ServiceHealth(name="OpenSearch", status="down", message=str(exc)[:120]))

        # Celery / Redis queues
        queues: list[QueueInfo] = []
        try:
            from app.db.redis_client import get_redis
            r = get_redis()
            for q_name in ("celery", "default", "high", "low"):
                length = r.llen(q_name)
                queues.append(QueueInfo(name=q_name, pending=length or 0))
            services.append(ServiceHealth(name="Celery", status="healthy", message="Queue accessible"))
        except Exception as exc:
            services.append(ServiceHealth(name="Celery", status="unknown", message=str(exc)[:120]))

        # Evidence by status
        ev_status_rows = self.db.execute(
            select(Evidence.status, func.count().label("n"))
            .group_by(Evidence.status)
        ).all()
        ev_by_status = {r.status: r.n for r in ev_status_rows}

        # Failed processing in last 24h
        failed_24h = self.db.execute(
            select(func.count()).select_from(Evidence)
            .where(
                Evidence.status == "failed",
                Evidence.updated_at >= _days_ago(1),
            )
        ).scalar() or 0

        # Processing stats
        proc_result = self.db.execute(
            select(
                func.avg(
                    extract("epoch", Evidence.processing_completed_at - Evidence.processing_started_at)
                ).label("avg_total"),
            )
            .where(
                Evidence.processing_started_at.is_not(None),
                Evidence.processing_completed_at.is_not(None),
            )
        ).first()
        avg_total = float(proc_result.avg_total) if proc_result and proc_result.avg_total else None

        # Storage stats
        storage_result = self.db.execute(
            select(
                func.coalesce(func.sum(Evidence.file_size), 0).label("total_bytes"),
                func.count().label("file_count"),
            )
        ).first()
        storage = StorageStats(
            used_bytes=int(storage_result.total_bytes) if storage_result else 0,
            file_count=int(storage_result.file_count) if storage_result else 0,
        )

        return OperationsDashboard(
            services=services,
            queues=queues,
            evidence_by_status=ev_by_status,
            failed_processing_24h=failed_24h,
            processing_stats=ProcessingStats(avg_total_seconds=avg_total),
            storage=storage,
            generated_at=now,
        )

    def _probe_postgres(self) -> ServiceHealth:
        try:
            t0 = time.monotonic()
            self.db.execute(text("SELECT 1"))
            lat = round((time.monotonic() - t0) * 1000, 1)
            return ServiceHealth(name="PostgreSQL", status="healthy", latency_ms=lat)
        except Exception as exc:
            return ServiceHealth(name="PostgreSQL", status="down", message=str(exc)[:120])

    # ── Investigator ───────────────────────────────────────────────────────────

    def get_investigator(self) -> InvestigatorDashboard:
        """Personalised dashboard for the logged-in user."""
        now = _now()
        cutoff_30 = _days_ago(30)
        uid = self.user.id
        active_statuses = ("open", "in_progress", "under_review", "on_hold")

        # Accessible cases WHERE I am the owner OR assigned to me
        my_case_subq = (
            select(Case.id)
            .join(CaseAssignment, CaseAssignment.case_id == Case.id, isouter=True)
            .where(
                Case.deleted_at.is_(None),
                or_(
                    Case.owner_id == uid,
                    CaseAssignment.user_id == uid,
                ),
            )
            .distinct()
            .scalar_subquery()
        )

        # ── Assigned / owned cases ─────────────────────────────────────────────
        case_rows = self.db.execute(
            select(
                Case.id, Case.reference_number, Case.title,
                Case.status, Case.priority, Case.updated_at,
            )
            .where(
                Case.id.in_(my_case_subq),
                Case.status.in_(active_statuses),
            )
            .order_by(Case.updated_at.desc())
            .limit(10)
        ).all()

        my_cases: list[MyCase] = []
        for r in case_rows:
            # count open tasks for this case assigned to me
            task_count = self.db.execute(
                select(func.count()).select_from(CaseTask)
                .where(
                    CaseTask.case_id == r.id,
                    CaseTask.assignee_id == uid,
                    CaseTask.status.in_(("pending", "in_progress")),
                )
            ).scalar() or 0
            my_cases.append(MyCase(
                id=str(r.id),
                reference_number=r.reference_number,
                title=r.title,
                status=r.status,
                priority=r.priority,
                open_task_count=task_count,
                updated_at=r.updated_at,
            ))

        # ── Open tasks assigned to me ──────────────────────────────────────────
        task_rows = self.db.execute(
            select(
                CaseTask.id, CaseTask.case_id, CaseTask.title,
                CaseTask.priority, CaseTask.due_date, CaseTask.status,
                Case.reference_number.label("ref"),
            )
            .join(Case, CaseTask.case_id == Case.id)
            .where(
                CaseTask.assignee_id == uid,
                CaseTask.status.in_(("pending", "in_progress")),
                Case.deleted_at.is_(None),
            )
            .order_by(CaseTask.due_date.asc().nulls_last(), CaseTask.priority.desc())
            .limit(15)
        ).all()

        open_tasks = [
            MyTask(
                id=str(r.id),
                case_id=str(r.case_id),
                case_reference=r.ref,
                title=r.title,
                priority=r.priority,
                due_date=r.due_date,
                status=r.status,
            )
            for r in task_rows
        ]

        # ── Recent notes I wrote ───────────────────────────────────────────────
        note_rows = self.db.execute(
            select(
                CaseNote.id, CaseNote.case_id, CaseNote.title,
                CaseNote.is_pinned, CaseNote.updated_at,
                Case.reference_number.label("ref"),
            )
            .join(Case, CaseNote.case_id == Case.id)
            .where(
                CaseNote.created_by_id == uid,
                Case.deleted_at.is_(None),
            )
            .order_by(CaseNote.updated_at.desc())
            .limit(8)
        ).all()

        recent_notes = [
            MyNote(
                id=str(r.id),
                case_id=str(r.case_id),
                case_reference=r.ref,
                title=r.title,
                is_pinned=r.is_pinned,
                updated_at=r.updated_at,
            )
            for r in note_rows
        ]

        # ── Recent evidence on my cases ────────────────────────────────────────
        ev_rows = self.db.execute(
            select(
                Evidence.id, Evidence.case_id, Evidence.original_filename,
                Evidence.status, Evidence.created_at,
                Case.reference_number.label("ref"),
            )
            .join(Case, Evidence.case_id == Case.id)
            .where(Evidence.case_id.in_(my_case_subq))
            .order_by(Evidence.created_at.desc())
            .limit(8)
        ).all()

        recent_evidence = [
            MyEvidence(
                id=str(r.id),
                case_id=str(r.case_id),
                case_reference=r.ref,
                original_filename=r.original_filename,
                status=r.status,
                created_at=r.created_at,
            )
            for r in ev_rows
        ]

        # ── Productivity metrics ───────────────────────────────────────────────
        cases_active = self.db.execute(
            select(func.count()).select_from(Case)
            .where(
                Case.id.in_(my_case_subq),
                Case.status.in_(active_statuses),
            )
        ).scalar() or 0

        cases_closed_30d = self.db.execute(
            select(func.count()).select_from(Case)
            .where(
                Case.id.in_(my_case_subq),
                Case.closed_at >= cutoff_30,
            )
        ).scalar() or 0

        tasks_completed_30d = self.db.execute(
            select(func.count()).select_from(CaseTask)
            .where(
                CaseTask.assignee_id == uid,
                CaseTask.status == "completed",
                CaseTask.updated_at >= cutoff_30,
            )
        ).scalar() or 0

        evidence_30d = self.db.execute(
            select(func.count()).select_from(Evidence)
            .where(
                Evidence.case_id.in_(my_case_subq),
                Evidence.created_at >= cutoff_30,
            )
        ).scalar() or 0

        notes_30d = self.db.execute(
            select(func.count()).select_from(CaseNote)
            .where(
                CaseNote.created_by_id == uid,
                CaseNote.created_at >= cutoff_30,
            )
        ).scalar() or 0

        return InvestigatorDashboard(
            assigned_cases=my_cases,
            open_tasks=open_tasks,
            recent_notes=recent_notes,
            recent_evidence=recent_evidence,
            productivity=ProductivityMetrics(
                cases_active=cases_active,
                cases_closed_30d=cases_closed_30d,
                tasks_completed_30d=tasks_completed_30d,
                evidence_items_uploaded_30d=evidence_30d,
                notes_created_30d=notes_30d,
            ),
            generated_at=now,
        )


# ── Helpers ────────────────────────────────────────────────────────────────────

_MIME_LABELS: dict[str, str] = {
    "application/pdf": "PDF",
    "image/jpeg": "JPEG Image",
    "image/png": "PNG Image",
    "image/gif": "GIF",
    "image/tiff": "TIFF Image",
    "text/plain": "Text",
    "text/csv": "CSV",
    "text/html": "HTML",
    "application/json": "JSON",
    "application/xml": "XML",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "XLSX",
    "application/msword": "DOC",
    "video/mp4": "MP4 Video",
    "video/quicktime": "MOV Video",
    "audio/mpeg": "MP3 Audio",
    "audio/wav": "WAV Audio",
    "application/zip": "ZIP Archive",
    "application/x-tar": "TAR Archive",
}


def _mime_label(mime: str) -> str:
    if mime in _MIME_LABELS:
        return _MIME_LABELS[mime]
    major = mime.split("/")[0]
    labels = {"image": "Image", "video": "Video", "audio": "Audio", "text": "Text"}
    return labels.get(major, mime)
