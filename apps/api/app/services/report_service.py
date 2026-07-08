"""Investigation Report Service.

Orchestrates data collection from every module and synthesises it into a
structured report.  Export (PDF / DOCX / HTML / JSON) is handled separately
by app.services.report_export.

AI content (case summary, evidence summaries) is read from the DB — it is
NEVER fabricated here.  Every AI-generated section carries an explicit
is_ai_generated=True flag so the export layer can mark it clearly.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.case import Case
from app.models.case_assignment import CaseAssignment
from app.models.case_note import CaseNote
from app.models.case_summary import CaseSummary
from app.models.case_task import CaseTask
from app.models.evidence import Evidence
from app.models.evidence_custody import EvidenceCustodyEvent
from app.models.evidence_entity import EvidenceEntity
from app.models.evidence_summary import EvidenceSummary
from app.models.evidence_timeline_event import EvidenceTimelineEvent
from app.models.report import InvestigationReport, ReportExport
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.schemas.report import (
    CreateReportRequest,
    GenerateReportRequest,
    ReportFilters,
    SectionConfig,
)

if TYPE_CHECKING:
    pass

# ── Template definitions ──────────────────────────────────────────────────────

def _make_section(t: str, title: str, order: int) -> dict:
    return {"type": t, "title": title, "order_index": order, "enabled": True}


_TEMPLATES: dict[str, list[dict]] = {
    "professional": [
        _make_section("cover", "Cover Page", 0),
        _make_section("table_of_contents", "Table of Contents", 1),
        _make_section("executive_summary", "Executive Summary", 2),
        _make_section("case_overview", "Case Overview", 3),
        _make_section("evidence_inventory", "Evidence Inventory", 4),
        _make_section("timeline", "Investigation Timeline", 5),
        _make_section("entities", "Entity Intelligence", 6),
        _make_section("ai_findings", "AI Analysis Findings", 7),
        _make_section("notes_tasks", "Notes & Tasks", 8),
        _make_section("chain_of_custody", "Chain of Custody", 9),
        _make_section("appendix", "Appendix", 10),
    ],
    "police": [
        _make_section("cover", "Cover Page", 0),
        _make_section("case_overview", "Case Details", 1),
        _make_section("evidence_inventory", "Evidence Inventory", 2),
        _make_section("chain_of_custody", "Chain of Custody", 3),
        _make_section("timeline", "Chronological Timeline", 4),
        _make_section("entities", "Persons of Interest", 5),
        _make_section("notes_tasks", "Investigation Notes", 6),
    ],
    "cyber": [
        _make_section("cover", "Cover Page", 0),
        _make_section("executive_summary", "Executive Summary", 1),
        _make_section("case_overview", "Incident Overview", 2),
        _make_section("timeline", "Attack Timeline", 3),
        _make_section("entities", "Indicators of Compromise", 4),
        _make_section("evidence_inventory", "Digital Evidence", 5),
        _make_section("ai_findings", "Threat Intelligence Analysis", 6),
        _make_section("chain_of_custody", "Chain of Custody", 7),
    ],
    "incident_response": [
        _make_section("cover", "Cover Page", 0),
        _make_section("executive_summary", "Incident Summary", 1),
        _make_section("timeline", "Incident Timeline", 2),
        _make_section("entities", "Affected Assets & Entities", 3),
        _make_section("evidence_inventory", "Evidence Collected", 4),
        _make_section("ai_findings", "AI Analysis", 5),
        _make_section("notes_tasks", "Response Actions", 6),
    ],
    "executive_summary": [
        _make_section("cover", "Cover Page", 0),
        _make_section("executive_summary", "Executive Summary", 1),
        _make_section("case_overview", "Case Overview", 2),
    ],
    "custom": [
        _make_section("cover", "Cover Page", 0),
        _make_section("case_overview", "Case Overview", 1),
    ],
}

_REPORT_TYPE_TO_DEFAULT_TEMPLATE = {
    "executive": "executive_summary",
    "detailed": "professional",
    "evidence_inventory": "professional",
    "timeline": "professional",
    "entity_intelligence": "professional",
    "chain_of_custody": "police",
    "ai_findings": "professional",
    "case_progress": "professional",
    "activity": "professional",
}


def get_template_sections(template: str) -> list[dict]:
    return list(_TEMPLATES.get(template, _TEMPLATES["professional"]))


# ── Service ───────────────────────────────────────────────────────────────────

class ReportService:

    def __init__(self, session: Session, current_user: User) -> None:
        self.session = session
        self.user = current_user

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def create(self, case_id: uuid.UUID, req: CreateReportRequest) -> InvestigationReport:
        case = self._require_case(case_id)
        sections = req.sections_config or [
            SectionConfig(**s) for s in get_template_sections(req.template)
        ]
        report = InvestigationReport(
            case_id=case.id,
            report_type=req.report_type,
            template=req.template,
            title=req.title,
            status="draft",
            sections_config=[s.model_dump() for s in sections],
            report_filters=req.report_filters.model_dump(mode="json"),
            sections_content={},
            generated_by_id=self.user.id,
        )
        self.session.add(report)
        self.session.commit()
        self.session.refresh(report)
        return report

    def get(self, case_id: uuid.UUID, report_id: uuid.UUID) -> InvestigationReport:
        r = (
            self.session.query(InvestigationReport)
            .filter(
                InvestigationReport.id == report_id,
                InvestigationReport.case_id == case_id,
                InvestigationReport.deleted_at.is_(None),
            )
            .first()
        )
        if not r:
            raise NotFoundError(f"Report {report_id} not found.")
        return r

    def list_for_case(self, case_id: uuid.UUID) -> list[InvestigationReport]:
        self._require_case(case_id)
        return (
            self.session.query(InvestigationReport)
            .filter(
                InvestigationReport.case_id == case_id,
                InvestigationReport.deleted_at.is_(None),
            )
            .order_by(InvestigationReport.created_at.desc())
            .all()
        )

    def delete(self, case_id: uuid.UUID, report_id: uuid.UUID) -> None:
        r = self.get(case_id, report_id)
        r.deleted_at = datetime.now(timezone.utc)
        self.session.commit()

    def publish(self, case_id: uuid.UUID, report_id: uuid.UUID) -> InvestigationReport:
        r = self.get(case_id, report_id)
        if r.status not in ("ready",):
            raise PermissionDeniedError("Only ready reports can be published.")
        r.status = "published"
        r.published_at = datetime.now(timezone.utc)
        r.approved_by_id = self.user.id
        self.session.commit()
        self.session.refresh(r)
        return r

    def create_new_version(
        self, case_id: uuid.UUID, report_id: uuid.UUID, req: GenerateReportRequest | None = None
    ) -> InvestigationReport:
        """Clone this report as a new version with bumped version number."""
        parent = self.get(case_id, report_id)
        sections = (
            [s.model_dump() for s in req.sections_config]
            if req and req.sections_config
            else parent.sections_config
        )
        filters = (
            req.report_filters.model_dump(mode="json")
            if req and req.report_filters
            else parent.report_filters
        )
        new_report = InvestigationReport(
            case_id=parent.case_id,
            report_type=parent.report_type,
            template=parent.template,
            title=parent.title,
            status="draft",
            version=parent.version + 1,
            parent_report_id=parent.id,
            sections_config=sections,
            report_filters=filters,
            sections_content={},
            generated_by_id=self.user.id,
        )
        self.session.add(new_report)
        self.session.commit()
        self.session.refresh(new_report)
        return new_report

    # ── Generation ─────────────────────────────────────────────────────────────

    def generate(
        self, case_id: uuid.UUID, report_id: uuid.UUID, req: GenerateReportRequest | None = None
    ) -> InvestigationReport:
        """Collect data for all enabled sections and populate sections_content."""
        report = self.get(case_id, report_id)
        case = self._require_case(case_id)

        if req:
            if req.sections_config:
                report.sections_config = [s.model_dump() for s in req.sections_config]
            if req.report_filters:
                report.report_filters = req.report_filters.model_dump(mode="json")

        filters = ReportFilters(**report.report_filters)

        report.status = "generating"
        report.generation_error = None
        self.session.commit()

        try:
            content: dict = {}
            for sec in sorted(report.sections_config, key=lambda s: s.get("order_index", 99)):
                if not sec.get("enabled", True):
                    continue
                sec_type = sec["type"]
                content[sec_type] = self._generate_section(sec_type, case, filters)

            # Compute hash for immutability guarantee
            raw = json.dumps(content, sort_keys=True, default=str).encode()
            content_hash = hashlib.sha256(raw).hexdigest()

            report.sections_content = content
            report.content_hash = content_hash
            report.status = "ready"
            report.generated_at = datetime.now(timezone.utc)
        except Exception as exc:
            report.status = "draft"
            report.generation_error = str(exc)

        self.session.commit()
        self.session.refresh(report)
        return report

    # ── Section collectors ─────────────────────────────────────────────────────

    def _generate_section(self, sec_type: str, case: Case, f: ReportFilters) -> dict:
        dispatch = {
            "cover": self._collect_cover,
            "table_of_contents": self._collect_toc,
            "executive_summary": self._collect_executive_summary,
            "case_overview": self._collect_case_overview,
            "evidence_inventory": self._collect_evidence_inventory,
            "timeline": self._collect_timeline,
            "entities": self._collect_entities,
            "ai_findings": self._collect_ai_findings,
            "notes_tasks": self._collect_notes_tasks,
            "chain_of_custody": self._collect_chain_of_custody,
            "appendix": self._collect_appendix,
        }
        fn = dispatch.get(sec_type)
        if fn is None:
            return {"type": sec_type, "title": sec_type, "items": []}
        return fn(case, f)

    def _collect_cover(self, case: Case, f: ReportFilters) -> dict:
        return {
            "type": "cover",
            "title": "Cover Page",
            "case_reference": case.reference_number,
            "case_title": case.title,
            "case_status": case.status,
            "case_priority": case.priority,
            "case_category": case.category,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": self.user.full_name,
            "classification": f.classification_label,
            "watermark_text": f.watermark_text,
            "is_ai_generated": False,
        }

    def _collect_toc(self, case: Case, f: ReportFilters) -> dict:
        return {"type": "table_of_contents", "title": "Table of Contents", "is_ai_generated": False}

    def _collect_executive_summary(self, case: Case, f: ReportFilters) -> dict:
        summary = (
            self.session.query(CaseSummary)
            .filter_by(case_id=case.id)
            .first()
        )
        return {
            "type": "executive_summary",
            "title": "Executive Summary",
            "summary_text": summary.summary_text if summary else None,
            "key_findings": summary.key_findings if summary else [],
            "potential_leads": summary.potential_leads if summary else [],
            "missing_information": summary.missing_information if summary else [],
            "open_questions": summary.open_questions if summary else [],
            "model_used": summary.model_used if summary else None,
            "is_ai_generated": True,
            "ai_disclaimer": (
                "Content in this section is AI-generated from analysed evidence. "
                "All findings must be independently verified by the lead investigator."
            ),
        }

    def _collect_case_overview(self, case: Case, f: ReportFilters) -> dict:
        assignments = (
            self.session.query(CaseAssignment)
            .filter_by(case_id=case.id)
            .all()
        )
        user_ids = [a.user_id for a in assignments]
        team_users = (
            self.session.query(User)
            .filter(User.id.in_(user_ids))
            .all()
            if user_ids else []
        )
        user_map = {u.id: u.full_name for u in team_users}
        team = [
            {"name": user_map.get(a.user_id, "Unknown"), "role": a.role}
            for a in assignments
        ]
        # Counts
        evidence_count = (
            self.session.query(func.count(Evidence.id))
            .filter(Evidence.case_id == case.id, Evidence.deleted_at.is_(None))
            .scalar()
        )
        task_count = (
            self.session.query(func.count(CaseTask.id))
            .filter(CaseTask.case_id == case.id)
            .scalar()
        )
        note_count = (
            self.session.query(func.count(CaseNote.id))
            .filter(CaseNote.case_id == case.id)
            .scalar()
        )
        return {
            "type": "case_overview",
            "title": "Case Overview",
            "reference_number": case.reference_number,
            "description": case.description,
            "status": case.status,
            "priority": case.priority,
            "category": case.category,
            "tags": case.tags or [],
            "owner": self.user.full_name,
            "team": team,
            "evidence_count": evidence_count,
            "task_count": task_count,
            "note_count": note_count,
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "closed_at": case.closed_at.isoformat() if case.closed_at else None,
            "is_ai_generated": False,
        }

    def _collect_evidence_inventory(self, case: Case, f: ReportFilters) -> dict:
        stmt = (
            select(Evidence)
            .where(Evidence.case_id == case.id, Evidence.deleted_at.is_(None))
        )
        if f.evidence_ids:
            ev_uuids = [uuid.UUID(e) for e in f.evidence_ids]
            stmt = stmt.where(Evidence.id.in_(ev_uuids))
        if f.date_from:
            stmt = stmt.where(Evidence.created_at >= f.date_from)
        if f.date_to:
            stmt = stmt.where(Evidence.created_at <= f.date_to)
        evs = list(self.session.execute(stmt).scalars().all())

        # For each evidence, get summary and entity/keyword counts
        ev_ids = [e.id for e in evs]
        summary_map: dict = {}
        if ev_ids:
            for s in self.session.query(EvidenceSummary).filter(
                EvidenceSummary.evidence_id.in_(ev_ids)
            ).all():
                summary_map[s.evidence_id] = s

        entity_counts: dict = {}
        if ev_ids:
            for row in (
                self.session.query(
                    EvidenceEntity.evidence_id,
                    func.count(EvidenceEntity.id),
                )
                .filter(EvidenceEntity.evidence_id.in_(ev_ids))
                .group_by(EvidenceEntity.evidence_id)
                .all()
            ):
                entity_counts[row[0]] = row[1]

        uploaders: dict = {}
        uploader_ids = list({e.uploaded_by_id for e in evs if e.uploaded_by_id})
        if uploader_ids:
            for u in self.session.query(User).filter(User.id.in_(uploader_ids)).all():
                uploaders[u.id] = u.full_name

        items = []
        for ev in evs:
            items.append({
                "id": str(ev.id),
                "filename": ev.original_filename,
                "mime_type": ev.mime_type,
                "file_size": ev.file_size,
                "sha256_hash": ev.sha256_hash,
                "status": ev.status,
                "uploaded_by": uploaders.get(ev.uploaded_by_id, "Unknown") if ev.uploaded_by_id else "Unknown",
                "uploaded_at": ev.created_at.isoformat() if ev.created_at else None,
                "classification": ev.classification,
                "tags": ev.tags or [],
                "has_ai_summary": ev.id in summary_map,
                "entity_count": entity_counts.get(ev.id, 0),
                "notes": ev.notes,
            })

        return {
            "type": "evidence_inventory",
            "title": "Evidence Inventory",
            "total_count": len(items),
            "items": items,
            "is_ai_generated": False,
        }

    def _collect_timeline(self, case: Case, f: ReportFilters) -> dict:
        stmt = (
            select(TimelineEvent)
            .where(
                TimelineEvent.case_id == case.id,
                TimelineEvent.deleted_at.is_(None),
            )
            .order_by(TimelineEvent.event_timestamp.asc().nulls_last())
        )
        if f.date_from:
            stmt = stmt.where(TimelineEvent.event_timestamp >= f.date_from)
        if f.date_to:
            stmt = stmt.where(TimelineEvent.event_timestamp <= f.date_to)
        events = list(self.session.execute(stmt).scalars().all())

        items = []
        for ev in events:
            items.append({
                "id": str(ev.id),
                "event_type": ev.event_type,
                "category": ev.category,
                "title": ev.title,
                "description": ev.description,
                "event_timestamp": ev.event_timestamp.isoformat() if ev.event_timestamp else None,
                "confidence": ev.confidence,
                "verification_status": ev.verification_status,
                "is_pinned": ev.is_pinned,
                "source_type": ev.source_type,
                "tags": ev.tags or [],
                "evidence_id": str(ev.evidence_id) if ev.evidence_id else None,
            })

        ts_list = [ev.event_timestamp for ev in events if ev.event_timestamp]
        return {
            "type": "timeline",
            "title": "Investigation Timeline",
            "total_count": len(items),
            "date_from": min(ts_list).isoformat() if ts_list else None,
            "date_to": max(ts_list).isoformat() if ts_list else None,
            "items": items,
            "is_ai_generated": False,
        }

    def _collect_entities(self, case: Case, f: ReportFilters) -> dict:
        stmt = (
            select(EvidenceEntity)
            .where(EvidenceEntity.case_id == case.id)
            .order_by(EvidenceEntity.confidence.desc())
        )
        if f.entity_types:
            stmt = stmt.where(EvidenceEntity.entity_type.in_(f.entity_types))
        entities = list(self.session.execute(stmt).scalars().all())

        by_type: dict[str, list] = {}
        max_per_type = f.max_entities_per_type
        type_counts: dict[str, int] = {}
        for ent in entities:
            et = ent.entity_type
            type_counts[et] = type_counts.get(et, 0) + 1
            lst = by_type.setdefault(et, [])
            if len(lst) < max_per_type:
                lst.append({
                    "id": str(ent.id),
                    "value": ent.value,
                    "normalized_value": ent.normalized_value,
                    "confidence": ent.confidence,
                    "context": ent.context,
                    "source": ent.source,
                    "evidence_id": str(ent.evidence_id),
                })

        return {
            "type": "entities",
            "title": "Entity Intelligence",
            "total_count": len(entities),
            "type_counts": type_counts,
            "by_type": by_type,
            "is_ai_generated": False,
        }

    def _collect_ai_findings(self, case: Case, f: ReportFilters) -> dict:
        if not f.include_ai:
            return {
                "type": "ai_findings",
                "title": "AI Analysis Findings",
                "excluded": True,
                "is_ai_generated": True,
            }

        case_summary = (
            self.session.query(CaseSummary).filter_by(case_id=case.id).first()
        )

        # Evidence-level summaries
        ev_summaries = []
        rows = (
            self.session.query(EvidenceSummary, Evidence.original_filename)
            .join(Evidence, Evidence.id == EvidenceSummary.evidence_id)
            .filter(Evidence.case_id == case.id)
            .all()
        )
        for es, fname in rows:
            ev_summaries.append({
                "evidence_id": str(es.evidence_id),
                "filename": fname,
                "summary_text": es.summary_text,
                "key_findings": es.key_findings or [],
                "model_used": es.model_used,
                "is_ai_generated": True,
            })

        return {
            "type": "ai_findings",
            "title": "AI Analysis Findings",
            "disclaimer": (
                "The following content was generated by an AI model based on the "
                "evidence in this case. AI analysis is provided as an investigative "
                "aid ONLY. All conclusions must be independently verified. "
                "AI NEVER makes investigative decisions."
            ),
            "case_summary": {
                "summary_text": case_summary.summary_text if case_summary else None,
                "key_findings": case_summary.key_findings if case_summary else [],
                "potential_leads": case_summary.potential_leads if case_summary else [],
                "missing_information": case_summary.missing_information if case_summary else [],
                "open_questions": case_summary.open_questions if case_summary else [],
                "model_used": case_summary.model_used if case_summary else None,
                "is_ai_generated": True,
            },
            "evidence_summaries": ev_summaries,
            "is_ai_generated": True,
        }

    def _collect_notes_tasks(self, case: Case, f: ReportFilters) -> dict:
        notes = (
            self.session.query(CaseNote)
            .filter(CaseNote.case_id == case.id)
            .order_by(CaseNote.is_pinned.desc(), CaseNote.created_at.asc())
            .all()
        )
        tasks = (
            self.session.query(CaseTask)
            .filter(CaseTask.case_id == case.id)
            .order_by(CaseTask.created_at.asc())
            .all()
        )

        author_ids = {n.created_by_id for n in notes} | {t.created_by_id for t in tasks}
        if author_ids:
            authors = {
                u.id: u.full_name
                for u in self.session.query(User).filter(User.id.in_(author_ids)).all()
            }
        else:
            authors = {}

        note_items = [
            {
                "id": str(n.id),
                "title": n.title,
                "content": n.content,
                "is_pinned": n.is_pinned,
                "created_by": authors.get(n.created_by_id, "Unknown"),
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ]
        task_items = [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "created_by": authors.get(t.created_by_id, "Unknown"),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in tasks
        ]

        return {
            "type": "notes_tasks",
            "title": "Notes & Tasks",
            "note_count": len(note_items),
            "task_count": len(task_items),
            "notes": note_items,
            "tasks": task_items,
            "is_ai_generated": False,
        }

    def _collect_chain_of_custody(self, case: Case, f: ReportFilters) -> dict:
        if not f.include_chain_of_custody:
            return {
                "type": "chain_of_custody",
                "title": "Chain of Custody",
                "excluded": True,
                "is_ai_generated": False,
            }
        evs = (
            self.session.query(Evidence)
            .filter(Evidence.case_id == case.id, Evidence.deleted_at.is_(None))
            .all()
        )
        ev_ids = [e.id for e in evs]
        custody_map: dict = {e.id: [] for e in evs}
        if ev_ids:
            events = (
                self.session.query(EvidenceCustodyEvent)
                .filter(EvidenceCustodyEvent.evidence_id.in_(ev_ids))
                .order_by(EvidenceCustodyEvent.created_at.asc())
                .all()
            )
            actor_ids = {ev.actor_id for ev in events if ev.actor_id}
            actor_map: dict = {}
            if actor_ids:
                actor_map = {
                    u.id: u.full_name
                    for u in self.session.query(User).filter(User.id.in_(actor_ids)).all()
                }
            for ev in events:
                custody_map[ev.evidence_id].append({
                    "action": ev.action,
                    "actor": actor_map.get(ev.actor_id, "System") if ev.actor_id else "System",
                    "description": ev.description,
                    "reason": ev.reason,
                    "timestamp": ev.created_at.isoformat() if ev.created_at else None,
                })

        items = [
            {
                "evidence_id": str(e.id),
                "filename": e.original_filename,
                "sha256_hash": e.sha256_hash,
                "events": custody_map[e.id],
            }
            for e in evs
        ]
        return {
            "type": "chain_of_custody",
            "title": "Chain of Custody",
            "total_evidence": len(items),
            "items": items,
            "is_ai_generated": False,
        }

    def _collect_appendix(self, case: Case, f: ReportFilters) -> dict:
        return {
            "type": "appendix",
            "title": "Appendix",
            "note": "Additional materials and references.",
            "is_ai_generated": False,
        }

    # ── Export tracking ────────────────────────────────────────────────────────

    def record_export(
        self,
        report_id: uuid.UUID,
        fmt: str,
        size: int,
        file_hash: str,
    ) -> ReportExport:
        ex = ReportExport(
            report_id=report_id,
            format=fmt,
            file_size=size,
            file_hash=file_hash,
            generated_by_id=self.user.id,
        )
        self.session.add(ex)
        self.session.commit()
        return ex

    # ── Templates endpoint helper ──────────────────────────────────────────────

    @staticmethod
    def get_available_templates() -> list[dict]:
        return [
            {
                "key": "professional",
                "label": "Professional",
                "description": "Full professional report with all sections.",
                "sections": get_template_sections("professional"),
            },
            {
                "key": "police",
                "label": "Police Investigation",
                "description": "Format suitable for law-enforcement investigation dossiers.",
                "sections": get_template_sections("police"),
            },
            {
                "key": "cyber",
                "label": "Cyber Investigation",
                "description": "Optimised for cybercrime and digital forensics cases.",
                "sections": get_template_sections("cyber"),
            },
            {
                "key": "incident_response",
                "label": "Incident Response",
                "description": "Structured for security incident response reports.",
                "sections": get_template_sections("incident_response"),
            },
            {
                "key": "executive_summary",
                "label": "Executive Summary",
                "description": "Concise single-page summary for management.",
                "sections": get_template_sections("executive_summary"),
            },
            {
                "key": "custom",
                "label": "Custom Template",
                "description": "Start with minimal sections and add your own.",
                "sections": get_template_sections("custom"),
            },
        ]

    @staticmethod
    def get_report_types() -> list[dict]:
        return [
            {"key": "executive", "label": "Executive Investigation Report", "description": "High-level summary for leadership.", "default_template": "executive_summary"},
            {"key": "detailed", "label": "Detailed Investigation Report", "description": "Comprehensive full-detail report.", "default_template": "professional"},
            {"key": "evidence_inventory", "label": "Evidence Inventory Report", "description": "Complete catalogue of all collected evidence.", "default_template": "professional"},
            {"key": "timeline", "label": "Timeline Report", "description": "Chronological investigation timeline.", "default_template": "professional"},
            {"key": "entity_intelligence", "label": "Entity Intelligence Report", "description": "Extracted persons, IPs, emails and entities.", "default_template": "professional"},
            {"key": "chain_of_custody", "label": "Chain of Custody Report", "description": "Evidence chain of custody audit trail.", "default_template": "police"},
            {"key": "ai_findings", "label": "AI Findings Report", "description": "AI-generated analysis and insights.", "default_template": "professional"},
            {"key": "case_progress", "label": "Case Progress Report", "description": "Current status of tasks and investigation.", "default_template": "professional"},
            {"key": "activity", "label": "Investigation Activity Report", "description": "Audit of all investigation actions.", "default_template": "professional"},
        ]

    # ── Private helpers ────────────────────────────────────────────────────────

    def _require_case(self, case_id: uuid.UUID) -> Case:
        case = (
            self.session.query(Case)
            .filter(Case.id == case_id, Case.deleted_at.is_(None))
            .first()
        )
        if not case:
            raise NotFoundError(f"Case {case_id} not found.")
        return case
