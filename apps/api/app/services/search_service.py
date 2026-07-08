"""Universal Intelligence Search Service.

Searches across: cases, evidence (OCR text + filename), AI summaries,
extracted entities, keywords, timeline events, case notes, case tasks, and users.

Permission model:
  - Only returns records from cases the requesting user can see
    (owner OR assigned, following the same RBAC as CaseRepository.search).
  - User results are only included when the user has users:read permission.
  - Every result carries a `url` that maps to the frontend route.
"""

from __future__ import annotations

import math
import re
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.case_assignment import CaseAssignment
from app.models.case_note import CaseNote
from app.models.case_task import CaseTask
from app.models.evidence import Evidence
from app.models.evidence_entity import EvidenceEntity
from app.models.evidence_summary import EvidenceSummary
from app.models.evidence_timeline_event import EvidenceTimelineEvent
from app.models.user import User
from app.schemas.search import SearchFilters, SearchResultItem

if TYPE_CHECKING:
    pass

_SNIPPET_LEN = 200
_MAX_PER_TYPE = 30  # max raw hits per content type before ranking

# ── Helpers ───────────────────────────────────────────────────────────────────

def _snip(text: str | None, query: str) -> str:
    """Return a ~200-char snippet centred on the first query match."""
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    lower_text = text.lower()
    lower_q = query.lower().split()[0] if query.strip() else ""
    pos = lower_text.find(lower_q) if lower_q else 0
    if pos < 0:
        pos = 0
    start = max(0, pos - 80)
    end = min(len(text), start + _SNIPPET_LEN)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end].strip() + suffix


def _score(title_hit: bool, snippet_len: int, confidence: float | None = None) -> float:
    base = 3.0 if title_hit else 1.0
    if confidence is not None:
        base *= 0.5 + confidence * 0.5
    return round(base, 3)


def _case_url(case_id: str) -> str:
    return f"/cases/{case_id}"


def _evidence_url(case_id: str, evidence_id: str) -> str:
    return f"/cases/{case_id}/evidence/{evidence_id}"


# ── Service ───────────────────────────────────────────────────────────────────

class SearchService:

    def __init__(self, session: Session, current_user: User) -> None:
        self.session = session
        self.user = current_user

    # ── Accessible case IDs ────────────────────────────────────────────────────

    def _accessible_case_ids_subq(self):
        """Subquery of case IDs the current user may see (non-deleted)."""
        assigned_subq = (
            select(CaseAssignment.case_id)
            .where(CaseAssignment.user_id == self.user.id)
            .scalar_subquery()
        )
        return (
            select(Case.id)
            .where(
                Case.deleted_at.is_(None),
                or_(
                    Case.is_private.is_(False),
                    Case.owner_id == self.user.id,
                    Case.id.in_(assigned_subq),
                ),
            )
            .scalar_subquery()
        )

    def _has_permission(self, resource: str, action: str) -> bool:
        """Check if the current user has a given permission."""
        for role in self.user.roles:
            for perm in role.permissions:
                if perm.resource == resource and perm.action in (action, "*"):
                    return True
        return False

    # ── Per-type search methods ────────────────────────────────────────────────

    def _search_cases(
        self, q: str, f: SearchFilters
    ) -> list[SearchResultItem]:
        term = f"%{q.lower()}%"
        accessible = self._accessible_case_ids_subq()
        stmt = (
            select(Case)
            .where(
                Case.deleted_at.is_(None),
                Case.id.in_(accessible),
                or_(
                    func.lower(Case.title).like(term),
                    func.lower(Case.description).like(term),
                    func.lower(Case.reference_number).like(term),
                ),
            )
        )
        if f.case_status:
            stmt = stmt.where(Case.status == f.case_status)
        if f.priority:
            stmt = stmt.where(Case.priority == f.priority)
        if f.date_from:
            stmt = stmt.where(Case.created_at >= f.date_from)
        if f.date_to:
            stmt = stmt.where(Case.created_at <= f.date_to)
        stmt = stmt.limit(_MAX_PER_TYPE)
        rows = list(self.session.execute(stmt).scalars().all())
        results = []
        for row in rows:
            title_hit = q.lower() in (row.title or "").lower()
            snip = _snip(row.description, q) or row.reference_number
            results.append(
                SearchResultItem(
                    id=str(row.id),
                    type="case",
                    title=f"{row.reference_number} — {row.title}",
                    snippet=snip,
                    case_id=str(row.id),
                    case_title=row.title,
                    case_reference=row.reference_number,
                    score=_score(title_hit, len(snip)),
                    created_at=row.created_at,
                    url=_case_url(str(row.id)),
                )
            )
        return results

    def _search_evidence(
        self, q: str, f: SearchFilters
    ) -> list[SearchResultItem]:
        term = f"%{q.lower()}%"
        accessible = self._accessible_case_ids_subq()
        stmt = (
            select(Evidence, Case.title, Case.reference_number)
            .join(Case, Case.id == Evidence.case_id)
            .where(
                Evidence.deleted_at.is_(None),
                Evidence.case_id.in_(accessible),
                or_(
                    func.lower(Evidence.original_filename).like(term),
                    func.lower(Evidence.ocr_text).like(term),
                ),
            )
        )
        if f.case_id:
            stmt = stmt.where(Evidence.case_id == f.case_id)
        if f.date_from:
            stmt = stmt.where(Evidence.created_at >= f.date_from)
        if f.date_to:
            stmt = stmt.where(Evidence.created_at <= f.date_to)
        stmt = stmt.limit(_MAX_PER_TYPE)
        rows = list(self.session.execute(stmt).all())
        results = []
        for ev, case_title, case_ref in rows:
            title_hit = q.lower() in (ev.original_filename or "").lower()
            snip = _snip(ev.ocr_text, q) or ev.original_filename
            results.append(
                SearchResultItem(
                    id=str(ev.id),
                    type="evidence",
                    title=ev.original_filename,
                    snippet=snip,
                    case_id=str(ev.case_id),
                    case_title=case_title,
                    case_reference=case_ref,
                    evidence_id=str(ev.id),
                    score=_score(title_hit, len(snip)),
                    created_at=ev.created_at,
                    url=_case_url(str(ev.case_id)) + "?tab=evidence",
                )
            )
        return results

    def _search_summaries(
        self, q: str, f: SearchFilters
    ) -> list[SearchResultItem]:
        term = f"%{q.lower()}%"
        accessible = self._accessible_case_ids_subq()
        stmt = (
            select(EvidenceSummary, Evidence.original_filename, Evidence.case_id,
                   Case.title, Case.reference_number)
            .join(Evidence, Evidence.id == EvidenceSummary.evidence_id)
            .join(Case, Case.id == Evidence.case_id)
            .where(
                Evidence.case_id.in_(accessible),
                func.lower(EvidenceSummary.summary_text).like(term),
            )
        )
        if f.case_id:
            stmt = stmt.where(Evidence.case_id == f.case_id)
        stmt = stmt.limit(_MAX_PER_TYPE)
        rows = list(self.session.execute(stmt).all())
        results = []
        for summ, fname, case_id, case_title, case_ref in rows:
            snip = _snip(summ.summary_text, q)
            results.append(
                SearchResultItem(
                    id=str(summ.id),
                    type="evidence_summary",
                    title=f"AI Summary: {fname}",
                    snippet=snip,
                    case_id=str(case_id),
                    case_title=case_title,
                    case_reference=case_ref,
                    evidence_id=str(summ.evidence_id),
                    score=_score(False, len(snip)),
                    created_at=summ.created_at,
                    url=_case_url(str(case_id)) + "?tab=ai",
                )
            )
        return results

    def _search_entities(
        self, q: str, f: SearchFilters
    ) -> list[SearchResultItem]:
        term = f"%{q.lower()}%"
        accessible = self._accessible_case_ids_subq()
        stmt = (
            select(EvidenceEntity, Evidence.original_filename,
                   Case.title, Case.reference_number)
            .join(Evidence, Evidence.id == EvidenceEntity.evidence_id)
            .join(Case, Case.id == EvidenceEntity.case_id)
            .where(
                EvidenceEntity.case_id.in_(accessible),
                func.lower(EvidenceEntity.value).like(term),
            )
        )
        if f.case_id:
            stmt = stmt.where(EvidenceEntity.case_id == f.case_id)
        if f.entity_type:
            stmt = stmt.where(EvidenceEntity.entity_type == f.entity_type)
        if f.confidence_min is not None:
            stmt = stmt.where(EvidenceEntity.confidence >= f.confidence_min)
        stmt = stmt.order_by(EvidenceEntity.confidence.desc()).limit(_MAX_PER_TYPE)
        rows = list(self.session.execute(stmt).all())
        results = []
        for ent, fname, case_title, case_ref in rows:
            context = ent.context or ""
            snip = _snip(context, q) if context else ent.value
            results.append(
                SearchResultItem(
                    id=str(ent.id),
                    type="entity",
                    title=f"{ent.entity_type.replace('_', ' ').title()}: {ent.value}",
                    snippet=snip or f"Found in {fname}",
                    case_id=str(ent.case_id),
                    case_title=case_title,
                    case_reference=case_ref,
                    evidence_id=str(ent.evidence_id),
                    confidence=ent.confidence,
                    score=_score(True, len(snip), ent.confidence),
                    created_at=ent.created_at,
                    url=_case_url(str(ent.case_id)) + "?tab=ai&view=entities",
                )
            )
        return results

    def _search_timeline_events(
        self, q: str, f: SearchFilters
    ) -> list[SearchResultItem]:
        term = f"%{q.lower()}%"
        accessible = self._accessible_case_ids_subq()
        stmt = (
            select(EvidenceTimelineEvent, Case.title, Case.reference_number)
            .join(Case, Case.id == EvidenceTimelineEvent.case_id)
            .where(
                EvidenceTimelineEvent.case_id.in_(accessible),
                or_(
                    func.lower(EvidenceTimelineEvent.event_title).like(term),
                    func.lower(EvidenceTimelineEvent.description).like(term),
                    func.lower(EvidenceTimelineEvent.source_text).like(term),
                ),
            )
        )
        if f.case_id:
            stmt = stmt.where(EvidenceTimelineEvent.case_id == f.case_id)
        if f.confidence_min is not None:
            stmt = stmt.where(EvidenceTimelineEvent.confidence >= f.confidence_min)
        stmt = stmt.limit(_MAX_PER_TYPE)
        rows = list(self.session.execute(stmt).all())
        results = []
        for ev, case_title, case_ref in rows:
            snip = _snip(ev.description or ev.source_text, q) or ev.event_title
            ts_str = ""
            if ev.event_timestamp:
                ts_str = ev.event_timestamp.strftime(" · %Y-%m-%d %H:%M")
            results.append(
                SearchResultItem(
                    id=str(ev.id),
                    type="timeline_event",
                    title=f"{ev.event_type.replace('_', ' ').title()}: {ev.event_title}{ts_str}",
                    snippet=snip,
                    case_id=str(ev.case_id),
                    case_title=case_title,
                    case_reference=case_ref,
                    evidence_id=str(ev.evidence_id),
                    confidence=ev.confidence,
                    score=_score(True, len(snip), ev.confidence),
                    created_at=ev.created_at,
                    url=_case_url(str(ev.case_id)) + "?tab=timeline",
                )
            )
        return results

    def _search_notes(
        self, q: str, f: SearchFilters
    ) -> list[SearchResultItem]:
        term = f"%{q.lower()}%"
        accessible = self._accessible_case_ids_subq()
        stmt = (
            select(CaseNote, Case.title, Case.reference_number)
            .join(Case, Case.id == CaseNote.case_id)
            .where(
                CaseNote.case_id.in_(accessible),
                or_(
                    func.lower(CaseNote.title).like(term),
                    func.lower(CaseNote.content).like(term),
                ),
            )
        )
        if f.case_id:
            stmt = stmt.where(CaseNote.case_id == f.case_id)
        if f.date_from:
            stmt = stmt.where(CaseNote.created_at >= f.date_from)
        if f.date_to:
            stmt = stmt.where(CaseNote.created_at <= f.date_to)
        stmt = stmt.limit(_MAX_PER_TYPE)
        rows = list(self.session.execute(stmt).all())
        results = []
        for note, case_title, case_ref in rows:
            title_hit = q.lower() in (note.title or "").lower()
            snip = _snip(note.content, q) or note.title
            results.append(
                SearchResultItem(
                    id=str(note.id),
                    type="note",
                    title=note.title,
                    snippet=snip,
                    case_id=str(note.case_id),
                    case_title=case_title,
                    case_reference=case_ref,
                    score=_score(title_hit, len(snip)),
                    created_at=note.created_at,
                    url=_case_url(str(note.case_id)) + "?tab=notes",
                )
            )
        return results

    def _search_tasks(
        self, q: str, f: SearchFilters
    ) -> list[SearchResultItem]:
        term = f"%{q.lower()}%"
        accessible = self._accessible_case_ids_subq()
        stmt = (
            select(CaseTask, Case.title, Case.reference_number)
            .join(Case, Case.id == CaseTask.case_id)
            .where(
                CaseTask.case_id.in_(accessible),
                or_(
                    func.lower(CaseTask.title).like(term),
                    func.lower(CaseTask.description).like(term),
                ),
            )
        )
        if f.case_id:
            stmt = stmt.where(CaseTask.case_id == f.case_id)
        if f.priority:
            stmt = stmt.where(CaseTask.priority == f.priority)
        stmt = stmt.limit(_MAX_PER_TYPE)
        rows = list(self.session.execute(stmt).all())
        results = []
        for task, case_title, case_ref in rows:
            title_hit = q.lower() in (task.title or "").lower()
            snip = _snip(task.description, q) or task.title
            results.append(
                SearchResultItem(
                    id=str(task.id),
                    type="task",
                    title=f"[{task.status.upper()}] {task.title}",
                    snippet=snip,
                    case_id=str(task.case_id),
                    case_title=case_title,
                    case_reference=case_ref,
                    score=_score(title_hit, len(snip)),
                    created_at=task.created_at,
                    url=_case_url(str(task.case_id)) + "?tab=tasks",
                )
            )
        return results

    def _search_users(
        self, q: str
    ) -> list[SearchResultItem]:
        """Only included if caller has users:read permission."""
        if not self._has_permission("users", "read"):
            return []
        term = f"%{q.lower()}%"
        stmt = (
            select(User)
            .where(
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                or_(
                    func.lower(User.full_name).like(term),
                    func.lower(User.email).like(term),
                    func.lower(User.username).like(term),
                ),
            )
            .limit(10)
        )
        rows = list(self.session.execute(stmt).scalars().all())
        now = datetime.now(timezone.utc)
        results = []
        for u in rows:
            title_hit = q.lower() in u.full_name.lower()
            results.append(
                SearchResultItem(
                    id=str(u.id),
                    type="user",
                    title=f"{u.full_name} ({u.username})",
                    snippet=u.email,
                    score=_score(title_hit, len(u.email)),
                    created_at=u.created_at,
                    url=f"/admin/users/{u.id}",
                )
            )
        return results

    # ── Public API ─────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        t0 = time.monotonic()
        f = filters or SearchFilters()

        requested_types: set[str] | None = None
        if f.types:
            requested_types = set(f.types)

        def want(t: str) -> bool:
            return requested_types is None or t in requested_types

        all_items: list[SearchResultItem] = []

        if want("case"):
            all_items.extend(self._search_cases(query, f))
        if want("evidence"):
            all_items.extend(self._search_evidence(query, f))
        if want("evidence_summary"):
            all_items.extend(self._search_summaries(query, f))
        if want("entity"):
            all_items.extend(self._search_entities(query, f))
        if want("timeline_event"):
            all_items.extend(self._search_timeline_events(query, f))
        if want("note"):
            all_items.extend(self._search_notes(query, f))
        if want("task"):
            all_items.extend(self._search_tasks(query, f))
        if want("user"):
            all_items.extend(self._search_users(query))

        # Also run OpenSearch for evidence full-text, merge by evidence_id.
        # SECURITY: filter OS results against accessible case IDs to prevent
        # unauthorized data exposure from the full-text index.
        if want("evidence"):
            from app.services.opensearch_service import search as os_search
            case_id_str = str(f.case_id) if f.case_id else None
            os_results = os_search(query, case_id=case_id_str, size=20)
            if os_results:
                accessible_case_id_strs = {
                    str(r)
                    for r in self.session.execute(
                        select(Case.id).where(
                            Case.deleted_at.is_(None),
                            Case.id.in_(self._accessible_case_ids_subq()),
                        )
                    ).scalars().all()
                }
                existing_evidence_ids = {
                    item.evidence_id for item in all_items if item.type == "evidence"
                }
                now = datetime.now(timezone.utc)
                for r in os_results:
                    eid = r.get("evidence_id")
                    r_case_id = r.get("case_id", "")
                    if (
                        eid
                        and eid not in existing_evidence_ids
                        and r_case_id in accessible_case_id_strs
                    ):
                        highlights = r.get("highlights", [])
                        snip = highlights[0] if highlights else ""
                        all_items.append(
                            SearchResultItem(
                                id=eid,
                                type="evidence",
                                title=r.get("filename", ""),
                                snippet=snip,
                                evidence_id=eid,
                                case_id=r_case_id,
                                score=float(r.get("score", 1.0)),
                                created_at=now,
                                url=f"/cases/{r_case_id}?tab=evidence",
                            )
                        )

        # Sort by score descending
        all_items.sort(key=lambda x: x.score, reverse=True)

        # Count per type for facets
        sources: dict[str, int] = {}
        for item in all_items:
            sources[item.type] = sources.get(item.type, 0) + 1

        # Paginate
        total = len(all_items)
        offset = (page - 1) * page_size
        page_items = all_items[offset: offset + page_size]

        took_ms = int((time.monotonic() - t0) * 1000)
        return {
            "items": page_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(1, math.ceil(total / page_size)),
            "query": query,
            "took_ms": took_ms,
            "sources": sources,
        }

    def suggestions(self, query: str, limit: int = 8) -> list[dict]:
        """Quick autocomplete: entity values + case titles + keywords."""
        if len(query) < 2:
            return []
        term = f"%{query.lower()}%"
        accessible = self._accessible_case_ids_subq()
        results: list[dict] = []

        # Case titles
        for row in (
            self.session.execute(
                select(Case.title, Case.reference_number)
                .where(
                    Case.deleted_at.is_(None),
                    Case.id.in_(accessible),
                    func.lower(Case.title).like(term),
                )
                .limit(3)
            ).all()
        ):
            results.append({"text": row[0], "suggestion_type": "case"})

        # Entity values
        for row in (
            self.session.execute(
                select(EvidenceEntity.value, EvidenceEntity.entity_type)
                .where(
                    EvidenceEntity.case_id.in_(accessible),
                    func.lower(EvidenceEntity.value).like(term),
                )
                .distinct(EvidenceEntity.value)
                .limit(5)
            ).all()
        ):
            results.append({"text": row[0], "suggestion_type": row[1]})

        return results[:limit]
