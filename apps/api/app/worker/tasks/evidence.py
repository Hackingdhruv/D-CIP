"""Evidence processing Celery task — AI Intelligence Engine pipeline.

Executes the full processing pipeline:
  METADATA_EXTRACTION → OCR_QUEUE → AI_QUEUE → TIMELINE_QUEUE
  → GRAPH_QUEUE → INDEXED → COMPLETED

Runs outside any FastAPI request with a dedicated sync DB session.
"""

from __future__ import annotations

import logging
import uuid

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="evidence.process",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_evidence(self, evidence_id: str) -> dict:
    """Run the full AI processing pipeline for one evidence item."""
    from app.db.session import SessionLocal
    from app.services.processing_pipeline import ProcessingPipeline

    eid = uuid.UUID(evidence_id)
    logger.info("Starting evidence pipeline for %s", evidence_id)

    with SessionLocal() as session:
        pipeline = ProcessingPipeline(session)
        try:
            pipeline.run(eid)
        except Exception as exc:
            logger.exception("Pipeline error for evidence %s: %s", evidence_id, exc)
            try:
                raise self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                logger.error("Max retries exceeded for evidence %s", evidence_id)
                return {"evidence_id": evidence_id, "status": "failed", "error": str(exc)}

    logger.info("Evidence pipeline finished for %s", evidence_id)
    return {"evidence_id": evidence_id, "status": "completed"}
