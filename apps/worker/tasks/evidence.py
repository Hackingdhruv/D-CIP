"""Evidence processing tasks.

Milestone 4: stubs that establish the processing pipeline extension point.
Milestone 5 (AI): replace the stub bodies with real OCR / NLP / EXIF logic.
"""

from __future__ import annotations

from apps.worker.celery_app import celery_app


@celery_app.task(
    name="evidence.process",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_evidence(self, evidence_id: str) -> dict:
    """Full processing pipeline for a single evidence item.

    Milestone 5 will implement:
      1. EXIF / GPS extraction (images)
      2. PDF page count + text layer extraction
      3. OCR via Tesseract (scanned documents / images)
      4. NLP named-entity recognition (people, orgs, locations)
      5. Audio/video duration + codec metadata
      6. Language detection
      7. OpenSearch indexing of extracted text
    """
    return {
        "status": "queued",
        "evidence_id": evidence_id,
        "milestone": 4,
        "note": "Full processing implemented in Milestone 5 (AI Engine).",
    }
