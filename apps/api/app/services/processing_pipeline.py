"""Processing pipeline — orchestrates all evidence enrichment stages.

Called from the Celery worker task. Each stage is independent: a failure in one
stage is logged and the pipeline continues. Evidence status is updated at each
stage boundary so the UI can track progress in real time.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.evidence import Evidence, EvidenceStatus
from app.models.evidence_entity import EvidenceEntity
from app.models.evidence_keyword import EvidenceKeyword
from app.models.evidence_timeline_event import EvidenceTimelineEvent
from app.models.evidence_summary import EvidenceSummary

logger = logging.getLogger(__name__)

_IMAGE_MIMES = {"image/jpeg", "image/png", "image/gif", "image/tiff", "image/bmp", "image/webp"}
_IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "tiff", "bmp", "webp"}


class ProcessingPipeline:
    def __init__(self, session: Session) -> None:
        self.session = session

    def run(self, evidence_id: uuid.UUID) -> None:
        evidence = self.session.get(Evidence, evidence_id)
        if evidence is None:
            logger.error("ProcessingPipeline: evidence %s not found", evidence_id)
            return

        try:
            self._run_pipeline(evidence)
        except Exception as exc:
            logger.exception("Pipeline failed for evidence %s", evidence_id)
            evidence.status = EvidenceStatus.FAILED.value
            evidence.processing_error = str(exc)
            evidence.processing_completed_at = datetime.now(timezone.utc)
            self.session.commit()

    def _run_pipeline(self, evidence: Evidence) -> None:
        from app.storage import get_storage
        storage = get_storage()
        file_path_str = storage.absolute_path(evidence.storage_path)
        file_path = Path(file_path_str)

        self._set_status(evidence, EvidenceStatus.METADATA_EXTRACTION)

        # ── Stage 1: Metadata (EXIF for images) ───────────────────────────────
        meta = dict(evidence.extracted_metadata)
        ext = evidence.file_extension.lower()
        mime = evidence.mime_type

        if mime in _IMAGE_MIMES or ext in _IMAGE_EXTS:
            try:
                from app.services.text_extraction import extract_image_metadata
                img_meta = extract_image_metadata(file_path)
                meta.update(img_meta)
            except Exception as exc:
                logger.warning("Image metadata extraction failed: %s", exc)

        # ── Stage 2: OCR / Text extraction ────────────────────────────────────
        self._set_status(evidence, EvidenceStatus.OCR_QUEUE)
        extracted_text: str | None = None

        if file_path.exists():
            try:
                from app.services.text_extraction import extract_text
                extracted_text = extract_text(file_path, mime, ext)
            except Exception as exc:
                logger.warning("Text extraction failed: %s", exc)

            # OCR fallback for images and PDFs with no text layer
            needs_ocr = (
                mime in _IMAGE_MIMES
                or ext in _IMAGE_EXTS
                or (mime == "application/pdf" and not extracted_text)
            )
            from app.core.config import settings
            if needs_ocr and settings.ocr_enabled:
                try:
                    from app.services.ocr import ocr_image, ocr_pdf_pages
                    if mime in _IMAGE_MIMES or ext in _IMAGE_EXTS:
                        ocr_result = ocr_image(file_path)
                    else:
                        ocr_result = ocr_pdf_pages(file_path)
                    if ocr_result:
                        extracted_text = ocr_result
                        meta["ocr_applied"] = True
                except Exception as exc:
                    logger.warning("OCR failed: %s", exc)

        if extracted_text:
            evidence.ocr_text = extracted_text[:100_000]
            meta["word_count"] = len(extracted_text.split())
            meta["char_count"] = len(extracted_text)

        # PDF page count
        if mime == "application/pdf" and file_path.exists():
            try:
                import pypdf
                reader = pypdf.PdfReader(str(file_path))
                meta["page_count"] = len(reader.pages)
            except Exception:
                pass

        # ── Stage 3: AI_QUEUE — Language + Entity + Keyword extraction ────────
        self._set_status(evidence, EvidenceStatus.AI_QUEUE)
        entities_for_index: list[str] = []
        keywords_for_index: list[str] = []
        entity_counts: dict = {}

        if extracted_text:
            # Language detection
            try:
                from langdetect import detect
                lang = detect(extracted_text[:5000])
                meta["language"] = lang
            except Exception:
                pass

            # Entity extraction
            try:
                from app.services.entity_extraction import extract_entities
                entities = extract_entities(extracted_text)
                entity_counts = _count_by_type(entities)
                meta["entity_counts"] = entity_counts

                for entity in entities[:1000]:  # cap per evidence
                    self.session.add(EvidenceEntity(
                        evidence_id=evidence.id,
                        case_id=evidence.case_id,
                        entity_type=entity.entity_type,
                        value=entity.value[:500],
                        normalized_value=entity.normalized_value[:500],
                        confidence=entity.confidence,
                        context=entity.context[:500] if entity.context else None,
                        source=entity.source,
                    ))
                    entities_for_index.append(f"{entity.entity_type}:{entity.value}")
            except Exception as exc:
                logger.warning("Entity extraction failed: %s", exc)

            # Keyword extraction
            try:
                from app.services.keyword_extraction import extract_keywords
                keywords = extract_keywords(extracted_text, max_keywords=30)
                for kw in keywords:
                    self.session.add(EvidenceKeyword(
                        evidence_id=evidence.id,
                        case_id=evidence.case_id,
                        keyword=kw.keyword[:200],
                        score=kw.score,
                    ))
                    keywords_for_index.append(kw.keyword)
            except Exception as exc:
                logger.warning("Keyword extraction failed: %s", exc)

            self.session.flush()

            # Trigger async watchlist matching (non-blocking, best-effort)
            try:
                from app.worker.celery_app import celery_app
                celery_app.send_task(
                    "watchlist.match_evidence",
                    args=[str(evidence.id), str(evidence.case_id)],
                )
            except Exception as exc:
                logger.warning("Could not enqueue watchlist matching: %s", exc)

        # ── Stage 4: TIMELINE_QUEUE ────────────────────────────────────────────
        self._set_status(evidence, EvidenceStatus.TIMELINE_QUEUE)

        if extracted_text:
            try:
                from app.services.timeline_extraction import extract_timeline_events
                events = extract_timeline_events(
                    extracted_text,
                    filename=evidence.original_filename,
                    mime_type=mime,
                )
                for ev in events[:200]:
                    self.session.add(EvidenceTimelineEvent(
                        evidence_id=evidence.id,
                        case_id=evidence.case_id,
                        event_type=ev.event_type,
                        event_title=ev.event_title[:500],
                        description=ev.description,
                        event_timestamp=ev.event_timestamp,
                        confidence=ev.confidence,
                        source_text=ev.source_text[:500] if ev.source_text else None,
                    ))
                self.session.flush()
            except Exception as exc:
                logger.warning("Timeline extraction failed: %s", exc)

            # Mirror freshly extracted events into the canonical investigation
            # timeline (idempotent — Milestone 6). Never fails the pipeline.
            try:
                from app.services.timeline import TimelineService
                ingested = TimelineService(self.session).ingest_from_extraction(
                    evidence.case_id, evidence.id, commit=False
                )
                if ingested:
                    logger.info(
                        "Ingested %s timeline event(s) for evidence %s",
                        ingested, evidence.id,
                    )
            except Exception as exc:
                logger.warning("Timeline ingest failed: %s", exc)

        # ── Stage 5: GRAPH_QUEUE — entity/timeline prep for the graph engine ──
        self._set_status(evidence, EvidenceStatus.GRAPH_QUEUE)
        # Timeline events now carry an ``entities`` column and stable ids so the
        # Milestone 7 graph engine can build relationships directly from the
        # canonical timeline + EvidenceEntity records.

        # ── Stage 6: INDEXED — OpenSearch ─────────────────────────────────────
        self._set_status(evidence, EvidenceStatus.INDEXED)
        try:
            from app.services.opensearch_service import index_evidence as os_index
            os_index(
                evidence_id=evidence.id,
                case_id=evidence.case_id,
                filename=evidence.original_filename,
                mime_type=mime,
                status=EvidenceStatus.INDEXED.value,
                text_content=extracted_text,
                entities=entities_for_index,
                keywords=keywords_for_index,
                language=meta.get("language"),
                created_at=evidence.created_at.isoformat(),
            )
        except Exception as exc:
            logger.warning("OpenSearch indexing failed: %s", exc)

        # ── Stage 7: AI Summary ────────────────────────────────────────────────
        if extracted_text:
            try:
                from app.services.ai_provider import generate_evidence_summary
                ai_result = generate_evidence_summary(
                    filename=evidence.original_filename,
                    mime_type=mime,
                    extracted_text=extracted_text,
                    entity_summary=entity_counts,
                )
                if ai_result:
                    # Upsert summary
                    existing = (
                        self.session.query(EvidenceSummary)
                        .filter_by(evidence_id=evidence.id)
                        .first()
                    )
                    if existing:
                        existing.summary_text = ai_result.summary_text
                        existing.key_findings = ai_result.key_findings
                        existing.model_used = ai_result.model_used
                    else:
                        self.session.add(EvidenceSummary(
                            evidence_id=evidence.id,
                            summary_text=ai_result.summary_text,
                            key_findings=ai_result.key_findings,
                            model_used=ai_result.model_used,
                        ))
            except Exception as exc:
                logger.warning("AI summary generation failed: %s", exc)

        # ── Finalize ───────────────────────────────────────────────────────────
        evidence.extracted_metadata = meta
        evidence.status = EvidenceStatus.COMPLETED.value
        evidence.processing_completed_at = datetime.now(timezone.utc)
        self.session.commit()
        logger.info("Pipeline completed for evidence %s", evidence.id)

    def _set_status(self, evidence: Evidence, status: EvidenceStatus) -> None:
        evidence.status = status.value
        if not evidence.processing_started_at:
            evidence.processing_started_at = datetime.now(timezone.utc)
        self.session.flush()
        self.session.commit()


def _count_by_type(entities: list) -> dict:
    counts: dict[str, int] = {}
    for e in entities:
        counts[e.entity_type] = counts.get(e.entity_type, 0) + 1
    return counts
