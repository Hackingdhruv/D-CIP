"""Enterprise Administration service.

Covers all 8 admin modules:
  - Identity Administration (users, sessions, locking, inviting)
  - Audit Center (searchable audit log)
  - Security Center (failed logins, locked users, session analytics)
  - System Operations Center (health probes for all infrastructure)
  - Queue Monitor (Celery queue depths and workers)
  - Storage Center (evidence storage analytics)
  - AI Administration (config + usage stats)
  - Configuration Center (system_config CRUD)

All write operations are audit-logged. Read operations require admin:read.
Write operations require admin:write.
"""

from __future__ import annotations

import math
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import distinct, func, or_, select, text, update
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.security.password import hash_password
from app.models.ai_chat_message import AiChatMessage
from app.models.auth_audit_event import AuthAuditEvent
from app.models.case import Case
from app.models.evidence import Evidence
from app.models.permission import Permission
from app.models.role import Role
from app.models.system_config import SystemConfig
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.admin import (
    AdminOverviewStats,
    AdminUserListResponse,
    AdminUserRead,
    AiConfigRead,
    AiModelStat,
    AiUsageStats,
    AuditEventRead,
    AuditSearchResponse,
    AuditStatItem,
    AuditStats,
    ConfigEntry,
    FailedLoginSummary,
    LargestFile,
    QueueDetail,
    RecommendationsResponse,
    SecurityOverview,
    ServiceHealthDetail,
    SessionListResponse,
    SessionRead,
    StorageBreakdown,
    StorageOverview,
    SystemHealthResponse,
    SystemRecommendation,
    WorkerInfo,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _now() - timedelta(days=n)


def _user_to_admin_read(user: User) -> AdminUserRead:
    return AdminUserRead(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_locked=user.is_locked,
        failed_login_attempts=user.failed_login_attempts,
        locked_until=user.locked_until,
        last_login_at=user.last_login_at,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        updated_at=user.updated_at,
        deleted_at=user.deleted_at,
        roles=[r.name for r in user.roles],
    )


class AdminService:

    def __init__(self, session: Session, current_user: User) -> None:
        self.db = session
        self.actor = current_user

    # ── Identity Administration ───────────────────────────────────────────────

    def list_users(
        self,
        *,
        q: str | None = None,
        is_active: bool | None = None,
        is_locked: bool | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> AdminUserListResponse:
        base = select(User).options(selectinload(User.roles))
        if q:
            term = f"%{q.lower()}%"
            base = base.where(
                or_(
                    func.lower(User.email).like(term),
                    func.lower(User.username).like(term),
                    func.lower(User.full_name).like(term),
                )
            )
        if is_active is not None:
            base = base.where(User.is_active == is_active)
        if is_locked is not None:
            base = base.where(User.is_locked == is_locked)

        total = self.db.execute(
            select(func.count()).select_from(base.subquery())
        ).scalar_one()

        offset = (page - 1) * page_size
        rows = list(
            self.db.execute(
                base.order_by(User.created_at.desc()).offset(offset).limit(page_size)
            ).scalars().all()
        )
        pages = max(1, math.ceil(total / page_size))
        return AdminUserListResponse(
            items=[_user_to_admin_read(u) for u in rows],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    def get_user(self, user_id: uuid.UUID) -> AdminUserRead | None:
        user = self.db.execute(
            select(User).where(User.id == user_id).options(selectinload(User.roles))
        ).scalar_one_or_none()
        if user is None:
            return None
        return _user_to_admin_read(user)

    def lock_user(
        self,
        user_id: uuid.UUID,
        *,
        reason: str | None,
        duration_minutes: int = 60,
    ) -> AdminUserRead | None:
        user = self.db.execute(
            select(User).where(User.id == user_id).options(selectinload(User.roles))
        ).scalar_one_or_none()
        if user is None:
            return None
        user.is_locked = True
        user.locked_until = _now() + timedelta(minutes=duration_minutes)
        self.db.flush()
        self._audit("account_locked", user_id=user.id, metadata={"reason": reason})
        return _user_to_admin_read(user)

    def unlock_user(self, user_id: uuid.UUID) -> AdminUserRead | None:
        user = self.db.execute(
            select(User).where(User.id == user_id).options(selectinload(User.roles))
        ).scalar_one_or_none()
        if user is None:
            return None
        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        self.db.flush()
        self._audit("account_unlocked", user_id=user.id)
        return _user_to_admin_read(user)

    def invite_user(
        self,
        *,
        email: str,
        full_name: str,
        username: str,
        temp_password: str,
        role_ids: list[uuid.UUID],
    ) -> AdminUserRead:
        roles = []
        for rid in role_ids:
            role = self.db.execute(select(Role).where(Role.id == rid)).scalar_one_or_none()
            if role:
                roles.append(role)

        user = User(
            email=email.lower(),
            username=username.lower(),
            full_name=full_name,
            password_hash=hash_password(temp_password),
            is_active=True,
        )
        user.roles = roles
        self.db.add(user)
        self.db.flush()
        self._audit("user_created", user_id=user.id, metadata={"invited_by": str(self.actor.id)})
        return _user_to_admin_read(user)

    def force_password_reset(self, user_id: uuid.UUID) -> bool:
        user = self.db.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        if user is None:
            return False
        self._audit("password_reset_requested", user_id=user.id, metadata={"forced_by_admin": True})
        return True

    # ── Sessions ──────────────────────────────────────────────────────────────

    def list_sessions(
        self,
        *,
        user_id: uuid.UUID | None = None,
        is_active: bool | None = True,
        page: int = 1,
        page_size: int = 50,
    ) -> SessionListResponse:
        base = (
            select(UserSession, User)
            .join(User, UserSession.user_id == User.id)
        )
        if user_id is not None:
            base = base.where(UserSession.user_id == user_id)
        if is_active is not None:
            base = base.where(UserSession.is_active == is_active)

        total = self.db.execute(
            select(func.count()).select_from(base.subquery())
        ).scalar_one()

        offset = (page - 1) * page_size
        rows = self.db.execute(
            base.order_by(UserSession.last_active_at.desc()).offset(offset).limit(page_size)
        ).all()

        items = [
            SessionRead(
                id=s.id,
                user_id=s.user_id,
                user_email=u.email,
                user_full_name=u.full_name,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                is_active=s.is_active,
                created_at=s.created_at,
                last_active_at=s.last_active_at,
                expires_at=s.expires_at,
            )
            for s, u in rows
        ]
        pages = max(1, math.ceil(total / page_size))
        return SessionListResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)

    def revoke_session(self, session_id: uuid.UUID) -> bool:
        session = self.db.execute(
            select(UserSession).where(UserSession.id == session_id)
        ).scalar_one_or_none()
        if session is None:
            return False
        session.is_active = False
        self.db.flush()
        self._audit("logout", user_id=session.user_id, metadata={"revoked_by_admin": True})
        return True

    def revoke_all_user_sessions(self, user_id: uuid.UUID) -> int:
        result = self.db.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.is_active.is_(True))
            .values(is_active=False)
        )
        count = result.rowcount
        if count:
            self._audit("logout", user_id=user_id, metadata={"revoked_all_by_admin": True, "count": count})
        return count

    # ── Audit Center ──────────────────────────────────────────────────────────

    def search_audit(
        self,
        *,
        q: str | None = None,
        event_type: str | None = None,
        user_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> AuditSearchResponse:
        AuditUser = User.__table__.alias("audit_user")
        ActorUser = User.__table__.alias("actor_user")

        base = (
            select(AuthAuditEvent)
            .options(selectinload(AuthAuditEvent.user))
        )
        if event_type:
            base = base.where(AuthAuditEvent.event_type == event_type)
        if user_id:
            base = base.where(AuthAuditEvent.user_id == user_id)
        if date_from:
            base = base.where(AuthAuditEvent.created_at >= date_from)
        if date_to:
            base = base.where(AuthAuditEvent.created_at <= date_to)
        if q:
            base = base.where(AuthAuditEvent.event_type.ilike(f"%{q}%"))

        total = self.db.execute(
            select(func.count()).select_from(base.subquery())
        ).scalar_one()

        offset = (page - 1) * page_size
        events = list(
            self.db.execute(
                base.order_by(AuthAuditEvent.created_at.desc()).offset(offset).limit(page_size)
            ).scalars().all()
        )

        actor_ids = {e.actor_id for e in events if e.actor_id}
        actor_map: dict[uuid.UUID, User] = {}
        if actor_ids:
            actors = self.db.execute(
                select(User).where(User.id.in_(actor_ids))
            ).scalars().all()
            actor_map = {a.id: a for a in actors}

        items = []
        for e in events:
            user_obj = e.user
            actor_obj = actor_map.get(e.actor_id) if e.actor_id else None
            items.append(AuditEventRead(
                id=e.id,
                event_type=e.event_type,
                user_id=e.user_id,
                user_email=user_obj.email if user_obj else None,
                user_full_name=user_obj.full_name if user_obj else None,
                actor_id=e.actor_id,
                actor_email=actor_obj.email if actor_obj else None,
                actor_full_name=actor_obj.full_name if actor_obj else None,
                ip_address=e.ip_address,
                user_agent=e.user_agent,
                metadata=e.metadata_,
                created_at=e.created_at,
            ))

        pages = max(1, math.ceil(total / page_size))
        return AuditSearchResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)

    def get_audit_stats(self) -> AuditStats:
        now = _now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = _days_ago(7)

        total = self.db.execute(select(func.count()).select_from(AuthAuditEvent)).scalar_one()
        today_count = self.db.execute(
            select(func.count()).select_from(AuthAuditEvent)
            .where(AuthAuditEvent.created_at >= today)
        ).scalar_one()
        week_count = self.db.execute(
            select(func.count()).select_from(AuthAuditEvent)
            .where(AuthAuditEvent.created_at >= week_ago)
        ).scalar_one()

        breakdown_rows = self.db.execute(
            select(AuthAuditEvent.event_type, func.count().label("cnt"))
            .group_by(AuthAuditEvent.event_type)
            .order_by(func.count().desc())
            .limit(20)
        ).all()
        breakdown = [AuditStatItem(event_type=r[0], count=r[1]) for r in breakdown_rows]

        return AuditStats(
            total_events=total,
            events_today=today_count,
            events_this_week=week_count,
            breakdown=breakdown,
            generated_at=now,
        )

    # ── Security Center ───────────────────────────────────────────────────────

    def get_security_overview(self) -> SecurityOverview:
        now = _now()
        yesterday = _days_ago(1)

        locked_users = list(self.db.execute(
            select(User)
            .where(User.is_locked.is_(True), User.deleted_at.is_(None))
            .options(selectinload(User.roles))
            .order_by(User.locked_until.asc())
            .limit(20)
        ).scalars().all())

        locked_count = self.db.execute(
            select(func.count()).select_from(User)
            .where(User.is_locked.is_(True), User.deleted_at.is_(None))
        ).scalar_one()

        inactive_count = self.db.execute(
            select(func.count()).select_from(User)
            .where(User.is_active.is_(False), User.deleted_at.is_(None))
        ).scalar_one()

        failed_logins_24h = self.db.execute(
            select(func.count()).select_from(AuthAuditEvent)
            .where(
                AuthAuditEvent.event_type == "login_failed",
                AuthAuditEvent.created_at >= yesterday,
            )
        ).scalar_one()

        active_sessions = self.db.execute(
            select(func.count()).select_from(UserSession)
            .where(UserSession.is_active.is_(True), UserSession.expires_at > now)
        ).scalar_one()

        expired_sessions_24h = self.db.execute(
            select(func.count()).select_from(UserSession)
            .where(
                UserSession.expires_at.between(yesterday, now),
                UserSession.is_active.is_(False),
            )
        ).scalar_one()

        # Top failed login perpetrators in 24h
        failed_rows = self.db.execute(
            select(
                AuthAuditEvent.user_id,
                func.count().label("cnt"),
                func.max(AuthAuditEvent.created_at).label("last"),
                func.array_agg(distinct(AuthAuditEvent.ip_address)).label("ips"),
            )
            .where(
                AuthAuditEvent.event_type == "login_failed",
                AuthAuditEvent.created_at >= yesterday,
                AuthAuditEvent.user_id.is_not(None),
            )
            .group_by(AuthAuditEvent.user_id)
            .order_by(func.count().desc())
            .limit(10)
        ).all()

        user_ids_needed = {r[0] for r in failed_rows if r[0]}
        user_email_map: dict[uuid.UUID, str] = {}
        if user_ids_needed:
            urows = self.db.execute(
                select(User.id, User.email).where(User.id.in_(user_ids_needed))
            ).all()
            user_email_map = {r[0]: r[1] for r in urows}

        top_failed = [
            FailedLoginSummary(
                user_id=r[0],
                user_email=user_email_map.get(r[0]) if r[0] else None,
                attempt_count=r[1],
                last_attempt=r[2],
                ip_addresses=[ip for ip in (r[3] or []) if ip],
            )
            for r in failed_rows
        ]

        # Recent suspicious IPs (many failed logins from same IP)
        ip_rows = self.db.execute(
            select(AuthAuditEvent.ip_address, func.count().label("cnt"))
            .where(
                AuthAuditEvent.event_type == "login_failed",
                AuthAuditEvent.created_at >= yesterday,
                AuthAuditEvent.ip_address.is_not(None),
            )
            .group_by(AuthAuditEvent.ip_address)
            .having(func.count() >= 3)
            .order_by(func.count().desc())
            .limit(10)
        ).all()
        suspicious_ips = [r[0] for r in ip_rows if r[0]]

        return SecurityOverview(
            locked_users_count=locked_count,
            inactive_users_count=inactive_count,
            failed_logins_24h=failed_logins_24h,
            active_sessions=active_sessions,
            expired_sessions_24h=expired_sessions_24h,
            top_failed_logins=top_failed,
            locked_users=[_user_to_admin_read(u) for u in locked_users],
            recent_suspicious_ips=suspicious_ips,
            generated_at=now,
        )

    # ── System Operations Center ──────────────────────────────────────────────

    def get_system_health(self) -> SystemHealthResponse:
        now = _now()
        services: list[ServiceHealthDetail] = []
        overall = "healthy"

        # PostgreSQL
        services.append(self._probe_postgres())

        # Redis
        services.append(self._probe_redis())

        # Neo4j
        services.append(self._probe_neo4j())

        # OpenSearch
        services.append(self._probe_opensearch())

        # Celery
        services.append(self._probe_celery())

        statuses = [s.status for s in services]
        if "down" in statuses:
            overall = "down"
        elif "degraded" in statuses:
            overall = "degraded"

        queues = self._get_celery_queues()
        workers = self._get_celery_workers()

        return SystemHealthResponse(
            services=services,
            queues=queues,
            workers=workers,
            overall_status=overall,
            generated_at=now,
        )

    def _probe_postgres(self) -> ServiceHealthDetail:
        t0 = time.monotonic()
        try:
            self.db.execute(text("SELECT 1"))
            latency = round((time.monotonic() - t0) * 1000, 1)
            return ServiceHealthDetail(name="PostgreSQL", status="healthy", latency_ms=latency, message=None, version=None, last_check=_now())
        except Exception as exc:
            return ServiceHealthDetail(name="PostgreSQL", status="down", latency_ms=None, message=str(exc)[:200], version=None, last_check=_now())

    def _probe_redis(self) -> ServiceHealthDetail:
        t0 = time.monotonic()
        try:
            from app.db.redis_client import get_redis
            r = get_redis()
            r.ping()
            info = r.info("server")
            version = info.get("redis_version")
            latency = round((time.monotonic() - t0) * 1000, 1)
            return ServiceHealthDetail(name="Redis", status="healthy", latency_ms=latency, message=None, version=version, last_check=_now())
        except Exception as exc:
            return ServiceHealthDetail(name="Redis", status="down", latency_ms=None, message=str(exc)[:200], version=None, last_check=_now())

    def _probe_neo4j(self) -> ServiceHealthDetail:
        t0 = time.monotonic()
        try:
            from app.db.neo4j_client import get_driver
            driver = get_driver()
            driver.verify_connectivity()
            latency = round((time.monotonic() - t0) * 1000, 1)
            return ServiceHealthDetail(name="Neo4j", status="healthy", latency_ms=latency, message=None, version=None, last_check=_now())
        except Exception as exc:
            return ServiceHealthDetail(name="Neo4j", status="down", latency_ms=None, message=str(exc)[:200], version=None, last_check=_now())

    def _probe_opensearch(self) -> ServiceHealthDetail:
        t0 = time.monotonic()
        try:
            from app.db.opensearch_client import get_client as get_opensearch_client
            client = get_opensearch_client()
            info = client.info()
            version = info.get("version", {}).get("number")
            latency = round((time.monotonic() - t0) * 1000, 1)
            return ServiceHealthDetail(name="OpenSearch", status="healthy", latency_ms=latency, message=None, version=version, last_check=_now())
        except Exception as exc:
            return ServiceHealthDetail(name="OpenSearch", status="down", latency_ms=None, message=str(exc)[:200], version=None, last_check=_now())

    def _probe_celery(self) -> ServiceHealthDetail:
        t0 = time.monotonic()
        try:
            from app.workers.celery_app import celery_app
            inspect = celery_app.control.inspect(timeout=2.0)
            ping = inspect.ping()
            latency = round((time.monotonic() - t0) * 1000, 1)
            if ping:
                return ServiceHealthDetail(name="Celery", status="healthy", latency_ms=latency, message=f"{len(ping)} worker(s)", version=None, last_check=_now())
            return ServiceHealthDetail(name="Celery", status="degraded", latency_ms=latency, message="No workers responded", version=None, last_check=_now())
        except Exception as exc:
            return ServiceHealthDetail(name="Celery", status="down", latency_ms=None, message=str(exc)[:200], version=None, last_check=_now())

    def _get_celery_queues(self) -> list[QueueDetail]:
        queues: list[QueueDetail] = []
        queue_names = ["default", "evidence", "ai", "ocr", "indexing"]
        try:
            from app.db.redis_client import get_redis
            r = get_redis()
            for name in queue_names:
                pending = r.llen(name) or 0
                queues.append(QueueDetail(name=name, pending=pending, active=0, failed=0, processed_total=0))
        except Exception:
            for name in queue_names:
                queues.append(QueueDetail(name=name, pending=0, active=0, failed=0, processed_total=0))
        return queues

    def _get_celery_workers(self) -> list[WorkerInfo]:
        workers: list[WorkerInfo] = []
        try:
            from app.workers.celery_app import celery_app
            inspect = celery_app.control.inspect(timeout=2.0)
            active_tasks = inspect.active() or {}
            stats = inspect.stats() or {}
            for name, worker_stats in stats.items():
                active = active_tasks.get(name, [])
                total = worker_stats.get("total", {})
                processed = sum(total.values()) if total else 0
                workers.append(WorkerInfo(
                    name=name,
                    status="online",
                    active_tasks=len(active),
                    processed=processed,
                    failed=0,
                ))
        except Exception:
            pass
        return workers

    # ── System Recommendations ────────────────────────────────────────────────

    def get_recommendations(self) -> RecommendationsResponse:
        now = _now()
        recs: list[SystemRecommendation] = []

        # Check locked users
        locked_count = self.db.execute(
            select(func.count()).select_from(User)
            .where(User.is_locked.is_(True), User.deleted_at.is_(None))
        ).scalar_one()
        if locked_count > 0:
            recs.append(SystemRecommendation(
                id="locked_users",
                severity="warning",
                title="Locked User Accounts",
                description=f"{locked_count} account(s) are currently locked.",
                action="Review and unlock legitimate users in Identity Administration.",
                metric_value=str(locked_count),
                generated_at=now,
            ))

        # Check failed logins in 24h
        failed_24h = self.db.execute(
            select(func.count()).select_from(AuthAuditEvent)
            .where(
                AuthAuditEvent.event_type == "login_failed",
                AuthAuditEvent.created_at >= _days_ago(1),
            )
        ).scalar_one()
        if failed_24h >= 20:
            severity = "critical" if failed_24h >= 50 else "warning"
            recs.append(SystemRecommendation(
                id="failed_logins",
                severity=severity,
                title="High Failed Login Rate",
                description=f"{failed_24h} failed login attempts in the last 24 hours.",
                action="Review the Security Center for suspicious IP addresses.",
                metric_value=str(failed_24h),
                generated_at=now,
            ))

        # Check expired sessions still marked active
        expired_active = self.db.execute(
            select(func.count()).select_from(UserSession)
            .where(UserSession.is_active.is_(True), UserSession.expires_at < now)
        ).scalar_one()
        if expired_active > 0:
            recs.append(SystemRecommendation(
                id="expired_sessions",
                severity="info",
                title="Expired Active Sessions",
                description=f"{expired_active} session(s) have expired but are still marked active.",
                action="Sessions will be cleaned up on next login attempt; no immediate action needed.",
                metric_value=str(expired_active),
                generated_at=now,
            ))

        # Check storage (from system_config)
        warning_pct_cfg = self._get_config_value("storage_warning_pct", "80")
        try:
            warning_pct = int(warning_pct_cfg or "80")
        except ValueError:
            warning_pct = 80

        storage_bytes = self.db.execute(
            select(func.sum(Evidence.file_size)).select_from(Evidence)
            .where(Evidence.deleted_at.is_(None))
        ).scalar_one() or 0
        max_mb = int(self._get_config_value("max_evidence_size_mb", "500") or "500") * 1024 * 1024 * 1000
        if max_mb > 0:
            used_pct = (storage_bytes / max_mb) * 100
            if used_pct >= warning_pct:
                recs.append(SystemRecommendation(
                    id="storage_warning",
                    severity="critical" if used_pct >= 95 else "warning",
                    title="Storage Usage High",
                    description=f"Evidence storage is at {used_pct:.1f}% capacity.",
                    action="Review Storage Center and apply retention policies.",
                    metric_value=f"{used_pct:.1f}%",
                    generated_at=now,
                ))

        # AI disabled but evidence in queue
        ai_queue = self.db.execute(
            select(func.count()).select_from(Evidence)
            .where(Evidence.status == "ai_queue", Evidence.deleted_at.is_(None))
        ).scalar_one()
        if ai_queue > 0:
            ai_enabled = self._get_config_value("ai_enabled", "false") == "true"
            if not ai_enabled:
                recs.append(SystemRecommendation(
                    id="ai_queue_disabled",
                    severity="warning",
                    title="AI Queue Items Pending",
                    description=f"{ai_queue} evidence item(s) are waiting for AI analysis but AI is disabled.",
                    action="Enable AI in the Configuration Center or clear the queue.",
                    metric_value=str(ai_queue),
                    generated_at=now,
                ))

        critical_count = sum(1 for r in recs if r.severity == "critical")
        warning_count = sum(1 for r in recs if r.severity == "warning")
        info_count = sum(1 for r in recs if r.severity == "info")
        return RecommendationsResponse(
            recommendations=sorted(recs, key=lambda r: {"critical": 0, "warning": 1, "info": 2}[r.severity]),
            critical_count=critical_count,
            warning_count=warning_count,
            info_count=info_count,
            generated_at=now,
        )

    # ── AI Administration ─────────────────────────────────────────────────────

    def get_ai_config(self) -> AiConfigRead:
        return AiConfigRead(
            provider=settings.ai_provider,
            model=settings.ai_model,
            embedding_model=settings.ai_embedding_model,
            max_tokens=settings.ai_max_tokens,
            temperature=settings.ai_temperature,
            api_base=settings.ai_api_base,
            api_key_configured=bool(settings.ai_api_key),
            ocr_enabled=settings.ocr_enabled,
        )

    def get_ai_usage_stats(self) -> AiUsageStats:
        now = _now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = _days_ago(7)
        month_ago = _days_ago(30)

        total = self.db.execute(
            select(func.count()).select_from(AiChatMessage)
            .where(AiChatMessage.role == "assistant")
        ).scalar_one()

        today_count = self.db.execute(
            select(func.count()).select_from(AiChatMessage)
            .where(AiChatMessage.role == "assistant", AiChatMessage.created_at >= today)
        ).scalar_one()

        week_count = self.db.execute(
            select(func.count()).select_from(AiChatMessage)
            .where(AiChatMessage.role == "assistant", AiChatMessage.created_at >= week_ago)
        ).scalar_one()

        month_count = self.db.execute(
            select(func.count()).select_from(AiChatMessage)
            .where(AiChatMessage.role == "assistant", AiChatMessage.created_at >= month_ago)
        ).scalar_one()

        model_rows = self.db.execute(
            select(AiChatMessage.model_used, func.count().label("cnt"), func.max(AiChatMessage.created_at).label("last"))
            .where(AiChatMessage.role == "assistant", AiChatMessage.model_used.is_not(None))
            .group_by(AiChatMessage.model_used)
            .order_by(func.count().desc())
            .limit(10)
        ).all()

        models = [AiModelStat(model_name=r[0], message_count=r[1], last_used=r[2]) for r in model_rows]

        case_count = self.db.execute(
            select(func.count(distinct(AiChatMessage.case_id))).select_from(AiChatMessage)
        ).scalar_one() or 1
        avg = round(total / case_count, 2)

        user_rows = self.db.execute(
            select(AiChatMessage.user_id, func.count().label("cnt"))
            .where(AiChatMessage.role == "user", AiChatMessage.user_id.is_not(None))
            .group_by(AiChatMessage.user_id)
            .order_by(func.count().desc())
            .limit(5)
        ).all()

        user_ids = [r[0] for r in user_rows]
        user_map: dict[uuid.UUID, str] = {}
        if user_ids:
            urows = self.db.execute(select(User.id, User.email).where(User.id.in_(user_ids))).all()
            user_map = {r[0]: r[1] for r in urows}

        top_users = [{"email": user_map.get(r[0], "Unknown"), "count": r[1]} for r in user_rows]

        return AiUsageStats(
            total_messages=total,
            messages_today=today_count,
            messages_this_week=week_count,
            messages_this_month=month_count,
            models_used=models,
            avg_messages_per_case=avg,
            top_users=top_users,
            generated_at=now,
        )

    # ── Storage Center ────────────────────────────────────────────────────────

    def get_storage_overview(self, *, limit_largest: int = 20) -> StorageOverview:
        now = _now()
        week_ago = _days_ago(7)
        month_ago = _days_ago(30)

        # Overall totals
        totals = self.db.execute(
            select(func.count().label("cnt"), func.coalesce(func.sum(Evidence.file_size), 0).label("bytes"))
            .select_from(Evidence)
            .where(Evidence.deleted_at.is_(None))
        ).one()
        total_count = totals[0]
        total_bytes = int(totals[1])

        # Growth
        week_bytes = self.db.execute(
            select(func.coalesce(func.sum(Evidence.file_size), 0))
            .select_from(Evidence)
            .where(Evidence.deleted_at.is_(None), Evidence.created_at >= week_ago)
        ).scalar_one() or 0

        month_bytes = self.db.execute(
            select(func.coalesce(func.sum(Evidence.file_size), 0))
            .select_from(Evidence)
            .where(Evidence.deleted_at.is_(None), Evidence.created_at >= month_ago)
        ).scalar_one() or 0

        # Breakdown by mime_type
        mime_rows = self.db.execute(
            select(Evidence.mime_type, func.count().label("cnt"), func.sum(Evidence.file_size).label("bytes"))
            .where(Evidence.deleted_at.is_(None))
            .group_by(Evidence.mime_type)
            .order_by(func.sum(Evidence.file_size).desc())
            .limit(20)
        ).all()

        def _mime_label(mime: str) -> str:
            mapping = {
                "application/pdf": "PDF",
                "image/jpeg": "JPEG Image",
                "image/png": "PNG Image",
                "video/mp4": "MP4 Video",
                "audio/mpeg": "MP3 Audio",
                "text/plain": "Text",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word Doc",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
            }
            return mapping.get(mime, mime.split("/")[-1].upper())

        by_type = [
            StorageBreakdown(
                mime_type=r[0],
                label=_mime_label(r[0]),
                file_count=int(r[1]),
                total_bytes=int(r[2] or 0),
            )
            for r in mime_rows
        ]

        # Largest files
        largest_rows = self.db.execute(
            select(Evidence, Case.reference_number)
            .join(Case, Evidence.case_id == Case.id)
            .where(Evidence.deleted_at.is_(None))
            .order_by(Evidence.file_size.desc())
            .limit(limit_largest)
        ).all()

        largest = [
            LargestFile(
                evidence_id=e.id,
                case_id=e.case_id,
                case_reference=ref,
                original_filename=e.original_filename,
                mime_type=e.mime_type,
                file_size=e.file_size,
                uploaded_at=e.created_at,
            )
            for e, ref in largest_rows
        ]

        warning_pct = int(self._get_config_value("storage_warning_pct", "80") or "80")
        max_mb = int(self._get_config_value("max_evidence_size_mb", "500") or "500") * 1024 * 1024 * 1000
        used_pct = round((total_bytes / max_mb) * 100, 2) if max_mb > 0 else 0.0

        return StorageOverview(
            total_used_bytes=total_bytes,
            total_file_count=total_count,
            evidence_bytes=total_bytes,
            evidence_count=total_count,
            by_type=by_type,
            growth_last_7_days=int(week_bytes),
            growth_last_30_days=int(month_bytes),
            warning_threshold_pct=warning_pct,
            used_pct=used_pct,
            largest_files=largest,
            generated_at=now,
        )

    # ── Configuration Center ──────────────────────────────────────────────────

    def list_config(self) -> list[ConfigEntry]:
        rows = list(self.db.execute(
            select(SystemConfig, User.email.label("email"))
            .outerjoin(User, SystemConfig.updated_by_id == User.id)
            .order_by(SystemConfig.key)
        ).all())
        return [
            ConfigEntry(
                key=r[0].key,
                value=None if r[0].is_secret else r[0].value,
                description=r[0].description,
                is_secret=r[0].is_secret,
                updated_at=r[0].updated_at,
                updated_by_email=r[1],
            )
            for r in rows
        ]

    def get_config(self, key: str) -> ConfigEntry | None:
        row = self.db.execute(
            select(SystemConfig, User.email.label("email"))
            .outerjoin(User, SystemConfig.updated_by_id == User.id)
            .where(SystemConfig.key == key)
        ).one_or_none()
        if row is None:
            return None
        cfg, email = row
        return ConfigEntry(
            key=cfg.key,
            value=None if cfg.is_secret else cfg.value,
            description=cfg.description,
            is_secret=cfg.is_secret,
            updated_at=cfg.updated_at,
            updated_by_email=email,
        )

    def set_config(self, key: str, value: str | None) -> ConfigEntry:
        cfg = self.db.execute(select(SystemConfig).where(SystemConfig.key == key)).scalar_one_or_none()
        is_new = cfg is None
        if is_new:
            cfg = SystemConfig(key=key, value=value, updated_by_id=self.actor.id)
            self.db.add(cfg)
        else:
            cfg.value = value
            cfg.updated_by_id = self.actor.id
        self.db.flush()
        # For new entries, refresh to get server defaults (updated_at); for existing, already set.
        if not is_new:
            self.db.refresh(cfg)
        return ConfigEntry(
            key=key,
            value=value,
            description=cfg.description if not is_new else None,
            is_secret=cfg.is_secret if not is_new else False,
            updated_at=cfg.updated_at if not is_new else _now(),
            updated_by_email=self.actor.email,
        )

    # ── Admin Overview Stats ──────────────────────────────────────────────────

    def get_overview_stats(self) -> AdminOverviewStats:
        now = _now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_users = self.db.execute(
            select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        ).scalar_one()
        active_users = self.db.execute(
            select(func.count()).select_from(User)
            .where(User.is_active.is_(True), User.deleted_at.is_(None))
        ).scalar_one()
        locked_users = self.db.execute(
            select(func.count()).select_from(User)
            .where(User.is_locked.is_(True), User.deleted_at.is_(None))
        ).scalar_one()
        inactive_users = total_users - active_users

        total_roles = self.db.execute(select(func.count()).select_from(Role)).scalar_one()
        total_permissions = self.db.execute(select(func.count()).select_from(Permission)).scalar_one()

        active_sessions = self.db.execute(
            select(func.count()).select_from(UserSession)
            .where(UserSession.is_active.is_(True), UserSession.expires_at > now)
        ).scalar_one()

        audit_today = self.db.execute(
            select(func.count()).select_from(AuthAuditEvent)
            .where(AuthAuditEvent.created_at >= today)
        ).scalar_one()

        failed_24h = self.db.execute(
            select(func.count()).select_from(AuthAuditEvent)
            .where(
                AuthAuditEvent.event_type == "login_failed",
                AuthAuditEvent.created_at >= _days_ago(1),
            )
        ).scalar_one()

        evidence_count = self.db.execute(
            select(func.count()).select_from(Evidence).where(Evidence.deleted_at.is_(None))
        ).scalar_one()

        case_count = self.db.execute(
            select(func.count()).select_from(Case).where(Case.deleted_at.is_(None))
        ).scalar_one()

        # System status: quick probe postgres only for speed
        try:
            self.db.execute(text("SELECT 1"))
            system_status = "healthy"
        except Exception:
            system_status = "down"

        return AdminOverviewStats(
            total_users=total_users,
            active_users=active_users,
            locked_users=locked_users,
            inactive_users=inactive_users,
            total_roles=total_roles,
            total_permissions=total_permissions,
            active_sessions=active_sessions,
            audit_events_today=audit_today,
            failed_logins_24h=failed_24h,
            evidence_items=evidence_count,
            total_cases=case_count,
            system_status=system_status,
            generated_at=now,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_config_value(self, key: str, default: str) -> str:
        cfg = self.db.execute(select(SystemConfig).where(SystemConfig.key == key)).scalar_one_or_none()
        return cfg.value if cfg and cfg.value is not None else default

    def _audit(self, event_type: str, *, user_id: uuid.UUID | None = None, metadata: dict | None = None) -> None:
        event = AuthAuditEvent(
            event_type=event_type,
            user_id=user_id,
            actor_id=self.actor.id,
            metadata_=metadata,
        )
        self.db.add(event)
        self.db.flush()
