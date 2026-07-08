"""AI Intelligence Service — case-level AI orchestration.

Provides:
  - Case summary generation (aggregates evidence summaries)
  - Case-scoped AI chat (RAG over evidence text)
  - Entity/keyword/timeline aggregation queries
"""

from __future__ import annotations

import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.exceptions import NotFoundError
from app.models.ai_chat_message import AiChatMessage
from app.models.case_summary import CaseSummary
from app.models.evidence import Evidence, EvidenceStatus
from app.models.evidence_entity import EvidenceEntity
from app.models.evidence_keyword import EvidenceKeyword
from app.models.evidence_summary import EvidenceSummary
from app.models.evidence_timeline_event import EvidenceTimelineEvent
from app.repositories.case import CaseRepository
from app.services.base import BaseService


class AIIntelligenceService(BaseService):

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self._cases = CaseRepository(session)

    # ── Case summary ───────────────────────────────────────────────────────────

    def get_case_summary(self, case_id: uuid.UUID) -> CaseSummary | None:
        return (
            self.session.query(CaseSummary)
            .filter_by(case_id=case_id)
            .first()
        )

    def regenerate_case_summary(self, case_id: uuid.UUID) -> CaseSummary | None:
        """Generate or refresh the AI case summary from processed evidence."""
        case = self._cases.get_active(case_id)
        if not case:
            raise NotFoundError(f"Case {case_id} not found.")

        # Collect evidence summaries for context
        ev_summaries = (
            self.session.query(EvidenceSummary)
            .join(Evidence, EvidenceSummary.evidence_id == Evidence.id)
            .filter(Evidence.case_id == case_id, Evidence.deleted_at.is_(None))
            .all()
        )

        # Count entities across the case
        entity_row = (
            self.session.query(
                EvidenceEntity.entity_type,
                func.count(EvidenceEntity.id).label("cnt")
            )
            .filter(EvidenceEntity.case_id == case_id)
            .group_by(EvidenceEntity.entity_type)
            .all()
        )
        entity_counts = {row.entity_type: row.cnt for row in entity_row}

        from app.services.ai_provider import generate_case_summary
        result = generate_case_summary(
            case_title=case.title,
            evidence_summaries=[
                {
                    "filename": s.evidence.original_filename if s.evidence else "unknown",
                    "summary": s.summary_text,
                }
                for s in ev_summaries
            ],
            entity_counts=entity_counts,
        )
        if not result:
            return None

        existing = self.get_case_summary(case_id)
        if existing:
            existing.summary_text = result.summary_text
            existing.key_findings = result.key_findings
            existing.potential_leads = result.potential_leads
            existing.missing_information = result.missing_information
            existing.open_questions = result.open_questions
            existing.model_used = result.model_used
            self.session.commit()
            return existing
        else:
            summary = CaseSummary(
                case_id=case_id,
                summary_text=result.summary_text,
                key_findings=result.key_findings,
                potential_leads=result.potential_leads,
                missing_information=result.missing_information,
                open_questions=result.open_questions,
                model_used=result.model_used,
            )
            self.session.add(summary)
            self.session.commit()
            self.session.refresh(summary)
            return summary

    # ── Chat ───────────────────────────────────────────────────────────────────

    def chat(
        self,
        case_id: uuid.UUID,
        user_message: str,
        user_id: uuid.UUID,
        history_limit: int = 10,
    ) -> AiChatMessage:
        """Process a user chat message and return the AI reply."""
        case = self._cases.get_active(case_id)
        if not case:
            raise NotFoundError(f"Case {case_id} not found.")

        # Persist user message
        user_msg = AiChatMessage(
            case_id=case_id,
            user_id=user_id,
            role="user",
            content=user_message,
        )
        self.session.add(user_msg)
        self.session.flush()

        # Build conversation history
        history = (
            self.session.query(AiChatMessage)
            .filter_by(case_id=case_id)
            .order_by(AiChatMessage.created_at.desc())
            .limit(history_limit)
            .all()
        )
        history_msgs = [
            {"role": m.role, "content": m.content}
            for m in reversed(history)
        ]

        # Build evidence context (processed evidence with text)
        evidence_items = (
            self.session.query(Evidence)
            .filter(
                Evidence.case_id == case_id,
                Evidence.deleted_at.is_(None),
                Evidence.status == EvidenceStatus.COMPLETED.value,
            )
            .order_by(Evidence.created_at.desc())
            .limit(20)
            .all()
        )
        context = [
            {
                "id": str(ev.id),
                "filename": ev.original_filename,
                "text": (ev.ocr_text or "")[:2000],
                "summary": _get_evidence_summary_text(self.session, ev.id),
            }
            for ev in evidence_items
        ]

        from app.services.ai_provider import chat as ai_chat
        ai_result = ai_chat(
            case_title=case.title,
            messages=history_msgs,
            evidence_context=context,
        )

        if ai_result:
            reply_content = ai_result.content
            refs = ai_result.evidence_references
            model = ai_result.model_used
        else:
            reply_content = (
                "AI is not configured. Set AI_PROVIDER=openai and AI_API_KEY to enable the AI assistant."
            )
            refs = []
            model = None

        ai_msg = AiChatMessage(
            case_id=case_id,
            user_id=None,
            role="assistant",
            content=reply_content,
            evidence_references=refs,
            model_used=model,
        )
        self.session.add(ai_msg)
        self.session.commit()
        self.session.refresh(ai_msg)
        return ai_msg

    def get_chat_history(
        self, case_id: uuid.UUID, *, page: int = 1, page_size: int = 50
    ) -> tuple[list[AiChatMessage], int]:
        q = (
            self.session.query(AiChatMessage)
            .filter_by(case_id=case_id)
            .order_by(AiChatMessage.created_at)
        )
        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    # ── Entity/keyword/timeline aggregations ───────────────────────────────────

    def list_entities(
        self,
        case_id: uuid.UUID,
        *,
        entity_type: str | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[EvidenceEntity], int]:
        query = self.session.query(EvidenceEntity).filter(
            EvidenceEntity.case_id == case_id
        )
        if entity_type:
            query = query.filter(EvidenceEntity.entity_type == entity_type)
        if q:
            query = query.filter(EvidenceEntity.normalized_value.contains(q.lower()))
        total = query.count()
        items = (
            query.order_by(EvidenceEntity.confidence.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def list_keywords(
        self, case_id: uuid.UUID, *, page: int = 1, page_size: int = 50
    ) -> tuple[list[EvidenceKeyword], int]:
        query = (
            self.session.query(EvidenceKeyword)
            .filter(EvidenceKeyword.case_id == case_id)
            .order_by(EvidenceKeyword.score.desc())
        )
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def list_timeline(
        self,
        case_id: uuid.UUID,
        *,
        event_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[EvidenceTimelineEvent], int]:
        query = self.session.query(EvidenceTimelineEvent).filter(
            EvidenceTimelineEvent.case_id == case_id
        )
        if event_type:
            query = query.filter(EvidenceTimelineEvent.event_type == event_type)
        total = query.count()
        items = (
            query.order_by(EvidenceTimelineEvent.event_timestamp.asc().nulls_last())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_evidence_summary(self, evidence_id: uuid.UUID) -> EvidenceSummary | None:
        return (
            self.session.query(EvidenceSummary)
            .filter_by(evidence_id=evidence_id)
            .first()
        )

    def get_evidence_entities(self, evidence_id: uuid.UUID) -> list[EvidenceEntity]:
        return (
            self.session.query(EvidenceEntity)
            .filter_by(evidence_id=evidence_id)
            .order_by(EvidenceEntity.confidence.desc())
            .all()
        )

    def get_evidence_keywords(self, evidence_id: uuid.UUID) -> list[EvidenceKeyword]:
        return (
            self.session.query(EvidenceKeyword)
            .filter_by(evidence_id=evidence_id)
            .order_by(EvidenceKeyword.score.desc())
            .all()
        )

    def get_evidence_timeline(self, evidence_id: uuid.UUID) -> list[EvidenceTimelineEvent]:
        return (
            self.session.query(EvidenceTimelineEvent)
            .filter_by(evidence_id=evidence_id)
            .order_by(EvidenceTimelineEvent.event_timestamp.asc().nulls_last())
            .all()
        )

    def search_evidence(
        self, case_id: uuid.UUID, query: str
    ) -> list[dict]:
        """Full-text search using OpenSearch; falls back to DB keyword search."""
        from app.services.opensearch_service import search as os_search
        results = os_search(query, case_id=str(case_id))
        if results:
            return results

        # DB fallback: search in ocr_text and original_filename
        rows = (
            self.session.query(Evidence)
            .filter(
                Evidence.case_id == case_id,
                Evidence.deleted_at.is_(None),
                Evidence.ocr_text.ilike(f"%{query}%")
                | Evidence.original_filename.ilike(f"%{query}%"),
            )
            .limit(20)
            .all()
        )
        return [
            {"evidence_id": str(r.id), "filename": r.original_filename, "score": 1.0}
            for r in rows
        ]


    def get_relationship_graph(
        self, case_id: uuid.UUID, *, max_nodes: int = 80
    ) -> dict:
        """Build entity co-occurrence graph for the case.

        Nodes are deduplicated entities; edges connect entities that appear
        in the same evidence item, weighted by co-occurrence count.
        """
        # Fetch top-confidence entities (fetch more to survive dedup)
        entities = (
            self.session.query(EvidenceEntity)
            .filter(EvidenceEntity.case_id == case_id)
            .order_by(EvidenceEntity.confidence.desc())
            .limit(max_nodes * 5)
            .all()
        )

        # Deduplicate: key = (type, normalized[:50])
        seen: dict[tuple[str, str], dict] = {}
        for e in entities:
            norm = (e.normalized_value or e.value or "")[:50]
            key = (e.entity_type, norm)
            if key not in seen:
                seen[key] = {
                    "id": f"{e.entity_type}:{norm}",
                    "label": (e.value or "")[:80],
                    "node_type": e.entity_type,
                    "confidence": e.confidence,
                    "evidence_ids": set(),
                }
            seen[key]["evidence_ids"].add(str(e.evidence_id))
            if len(seen) >= max_nodes:
                break

        nodes = []
        node_by_key: dict[tuple[str, str], str] = {}
        for key, nd in seen.items():
            nd_id = nd["id"]
            node_by_key[key] = nd_id
            nodes.append({
                "id": nd_id,
                "label": nd["label"],
                "node_type": nd["node_type"],
                "confidence": nd["confidence"],
                "evidence_count": len(nd["evidence_ids"]),
            })

        if len(nodes) < 2:
            return {"nodes": nodes, "edges": []}

        # Build evidence_id → list of node_ids
        evidence_to_nodes: dict[str, list[str]] = {}
        for e in entities:
            norm = (e.normalized_value or e.value or "")[:50]
            key = (e.entity_type, norm)
            if key not in node_by_key:
                continue
            nid = node_by_key[key]
            eid = str(e.evidence_id)
            if eid not in evidence_to_nodes:
                evidence_to_nodes[eid] = []
            if nid not in evidence_to_nodes[eid]:
                evidence_to_nodes[eid].append(nid)

        # Count co-occurrences
        edge_counts: dict[tuple[str, str], int] = {}
        for ev_nodes in evidence_to_nodes.values():
            for i in range(len(ev_nodes)):
                for j in range(i + 1, len(ev_nodes)):
                    a, b = ev_nodes[i], ev_nodes[j]
                    if a > b:
                        a, b = b, a
                    k = (a, b)
                    edge_counts[k] = edge_counts.get(k, 0) + 1

        edges = [
            {"source": src, "target": tgt, "weight": cnt}
            for (src, tgt), cnt in sorted(edge_counts.items(), key=lambda x: -x[1])
        ][:200]

        return {"nodes": nodes, "edges": edges}

    def get_processing_status(self, case_id: uuid.UUID) -> list[dict]:
        """Return processing status for all evidence in a case."""
        from app.models.evidence_entity import EvidenceEntity
        from app.models.evidence_keyword import EvidenceKeyword
        from app.models.evidence_summary import EvidenceSummary
        from app.models.evidence_timeline_event import EvidenceTimelineEvent

        evidence_list = (
            self.session.query(Evidence)
            .filter(Evidence.case_id == case_id, Evidence.deleted_at.is_(None))
            .order_by(Evidence.created_at.desc())
            .all()
        )

        results: list[dict] = []
        for ev in evidence_list:
            entity_count = (
                self.session.query(func.count(EvidenceEntity.id))
                .filter_by(evidence_id=ev.id)
                .scalar()
            )
            keyword_count = (
                self.session.query(func.count(EvidenceKeyword.id))
                .filter_by(evidence_id=ev.id)
                .scalar()
            )
            timeline_count = (
                self.session.query(func.count(EvidenceTimelineEvent.id))
                .filter_by(evidence_id=ev.id)
                .scalar()
            )
            has_summary = (
                self.session.query(EvidenceSummary)
                .filter_by(evidence_id=ev.id)
                .first()
            ) is not None
            meta: dict = ev.extracted_metadata or {}
            results.append({
                "evidence_id": ev.id,
                "filename": ev.original_filename,
                "status": ev.status,
                "processing_started_at": ev.processing_started_at,
                "processing_completed_at": ev.processing_completed_at,
                "processing_error": ev.processing_error,
                "word_count": meta.get("word_count"),
                "language": meta.get("language"),
                "entity_count": entity_count,
                "keyword_count": keyword_count,
                "timeline_event_count": timeline_count,
                "has_summary": has_summary,
            })
        return results


def _get_evidence_summary_text(session: Session, evidence_id: uuid.UUID) -> str:
    s = session.query(EvidenceSummary).filter_by(evidence_id=evidence_id).first()
    return s.summary_text if s else ""
