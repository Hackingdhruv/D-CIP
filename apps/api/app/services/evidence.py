"""Evidence service — business logic for the Digital Evidence Intelligence Engine."""

from __future__ import annotations

import math
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.evidence import Evidence, EvidencePriority, EvidenceStatus
from app.models.evidence_custody import CustodyAction
from app.models.user import User
from app.repositories.case import CaseRepository
from app.repositories.evidence import EvidenceCustodyRepository, EvidenceRepository
from app.schemas.evidence import EvidenceListResponse, EvidenceUpdate
from app.services.base import BaseService
from app.storage.local import LocalStorageBackend


def detect_mime_type(filename: str, hint: str | None = None) -> str:
    """Detect MIME type from filename extension, falling back to *hint*."""
    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed
    if hint and hint not in ("application/octet-stream", ""):
        return hint
    return "application/octet-stream"


def extract_metadata(
    *,
    original_filename: str,
    file_size: int,
    sha256_hash: str,
    mime_type: str,
    file_extension: str,
) -> dict:
    """Synchronous metadata extraction using stdlib only.

    The returned dict is stored in Evidence.extracted_metadata and serves as
    the extension point for the AI milestone (OCR, EXIF, NLP extraction will
    enrich this same field).
    """
    return {
        "filename": original_filename,
        "size_bytes": file_size,
        "sha256": sha256_hash,
        "mime_type": mime_type,
        "extension": file_extension,
        # AI milestone will add: page_count, dimensions, duration, gps, exif,
        # language, encoding, ocr_text, named_entities, …
    }


class EvidenceService(BaseService):
    def __init__(
        self, session: Session, storage: LocalStorageBackend | None = None
    ) -> None:
        super().__init__(session)
        self._evidence = EvidenceRepository(session)
        self._custody = EvidenceCustodyRepository(session)
        self._cases = CaseRepository(session)
        if storage is None:
            from app.storage import get_storage
            storage = get_storage()
        self._storage = storage

    # ── Upload ─────────────────────────────────────────────────────────────────

    def record_upload(
        self,
        case_id: uuid.UUID,
        *,
        original_filename: str,
        storage_path: str,
        file_size: int,
        mime_type: str,
        file_extension: str,
        sha256_hash: str,
        actor: User,
    ) -> tuple[Evidence, bool]:
        """Persist a pre-streamed file as evidence.

        Returns ``(evidence, is_new)``.  ``is_new=False`` means the exact same
        file (by SHA-256) was already uploaded to this case; the existing
        record is returned and the caller should remove the temp file.
        """
        case = self._cases.get_active(case_id)
        if not case:
            raise NotFoundError(f"Case {case_id} not found.")

        # Duplicate detection — same hash already exists in this case
        existing = self._evidence.get_by_hash_in_case(sha256_hash, case_id)
        if existing:
            return existing, False

        extracted = extract_metadata(
            original_filename=original_filename,
            file_size=file_size,
            sha256_hash=sha256_hash,
            mime_type=mime_type,
            file_extension=file_extension,
        )

        evidence = Evidence(
            case_id=case_id,
            original_filename=original_filename,
            storage_path=storage_path,
            file_size=file_size,
            mime_type=mime_type,
            file_extension=file_extension,
            sha256_hash=sha256_hash,
            extracted_metadata=extracted,
            status=EvidenceStatus.UPLOADED.value,
            tags=[],
            priority=EvidencePriority.MEDIUM.value,
            uploaded_by_id=actor.id,
        )
        self.session.add(evidence)
        self.session.flush()

        self._custody.log(
            evidence.id,
            actor_id=actor.id,
            action=CustodyAction.UPLOADED.value,
            description=f"Uploaded: {original_filename}",
            event_data={
                "file_size": file_size,
                "sha256": sha256_hash,
                "mime_type": mime_type,
            },
        )

        # Set initial pipeline state, then commit — task dispatched after commit
        # so the evidence row exists in DB before the worker reads it.
        self._set_pipeline_initial_state(evidence)

        self.session.commit()
        self.session.refresh(evidence)

        # Dispatch async processing AFTER commit to avoid race condition
        self._dispatch_processing(str(evidence.id))

        return evidence, True

    def _set_pipeline_initial_state(self, evidence: Evidence) -> None:
        """Mark evidence as queued for processing (sync, before commit)."""
        evidence.status = EvidenceStatus.OCR_QUEUE.value
        evidence.processing_started_at = datetime.now(timezone.utc)
        self.session.flush()

    def _dispatch_processing(self, evidence_id: str) -> None:
        """Dispatch the Celery task. Logs a warning on failure but never raises."""
        try:
            from app.worker.tasks.evidence import process_evidence
            process_evidence.delay(evidence_id)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Could not dispatch evidence processing task (Redis unavailable?): %s — "
                "Re-run manually when the worker is available.", exc
            )

    # ── Read ───────────────────────────────────────────────────────────────────

    def get(
        self, evidence_id: uuid.UUID, case_id: uuid.UUID
    ) -> Evidence:
        evidence = self._evidence.get_for_case(evidence_id, case_id)
        if not evidence:
            raise NotFoundError("Evidence not found.")
        return evidence

    def list_evidence(
        self,
        case_id: uuid.UUID,
        *,
        q: str | None = None,
        mime_category: str | None = None,
        status: str | None = None,
        file_extension: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> EvidenceListResponse:
        case = self._cases.get_active(case_id)
        if not case:
            raise NotFoundError(f"Case {case_id} not found.")

        items, total = self._evidence.list_for_case(
            case_id,
            q=q,
            mime_category=mime_category,
            status=status,
            file_extension=file_extension,
            page=page,
            page_size=page_size,
        )
        from app.schemas.evidence import EvidenceReadSlim
        return EvidenceListResponse(
            items=[EvidenceReadSlim.model_validate(e) for e in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=max(1, math.ceil(total / page_size)),
        )

    # ── Update ─────────────────────────────────────────────────────────────────

    def update(
        self,
        evidence_id: uuid.UUID,
        case_id: uuid.UUID,
        data: EvidenceUpdate,
        actor: User,
    ) -> Evidence:
        evidence = self._evidence.get_for_case(evidence_id, case_id)
        if not evidence:
            raise NotFoundError("Evidence not found.")

        changes: dict = {}
        if data.tags is not None:
            changes["tags"] = data.tags
            evidence.tags = data.tags
        if data.priority is not None:
            changes["priority"] = data.priority
            evidence.priority = data.priority
        if data.source is not None:
            changes["source"] = data.source
            evidence.source = data.source
        if data.classification is not None:
            changes["classification"] = data.classification
            evidence.classification = data.classification
        if data.notes is not None:
            changes["notes"] = "updated"
            evidence.notes = data.notes
        if data.is_starred is not None:
            evidence.is_starred = data.is_starred

        if changes:
            self._custody.log(
                evidence.id,
                actor_id=actor.id,
                action=CustodyAction.UPDATED.value,
                description="Evidence metadata updated",
                event_data={"changes": changes},
            )

        self.session.commit()
        self.session.refresh(evidence)
        return evidence

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete(
        self,
        evidence_id: uuid.UUID,
        case_id: uuid.UUID,
        actor: User,
    ) -> None:
        evidence = self._evidence.get_for_case(evidence_id, case_id)
        if not evidence:
            raise NotFoundError("Evidence not found.")

        self._custody.log(
            evidence.id,
            actor_id=actor.id,
            action=CustodyAction.DELETED.value,
            description=f"Evidence removed: {evidence.original_filename}",
        )
        self._evidence.soft_delete(evidence)
        self.session.commit()

    # ── Verify hash ────────────────────────────────────────────────────────────

    def verify_hash(
        self,
        evidence_id: uuid.UUID,
        case_id: uuid.UUID,
        actor: User,
    ) -> dict:
        evidence = self._evidence.get_for_case(evidence_id, case_id)
        if not evidence:
            raise NotFoundError("Evidence not found.")

        computed = self._storage.compute_sha256(evidence.storage_path)
        matches = computed == evidence.sha256_hash

        self._custody.log(
            evidence.id,
            actor_id=actor.id,
            action=CustodyAction.VERIFIED.value,
            description=f"Integrity verification {'passed' if matches else 'FAILED'}",
            event_data={
                "original_hash": evidence.sha256_hash,
                "computed_hash": computed,
                "matches": matches,
            },
        )
        self.session.commit()

        return {
            "matches": matches,
            "original_hash": evidence.sha256_hash,
            "computed_hash": computed,
        }

    # ── Chain of custody ───────────────────────────────────────────────────────

    def get_custody(
        self,
        evidence_id: uuid.UUID,
        case_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list, int]:
        evidence = self._evidence.get_for_case(evidence_id, case_id)
        if not evidence:
            raise NotFoundError("Evidence not found.")
        return self._custody.list_for_evidence(
            evidence_id, page=page, page_size=page_size
        )

    # ── Download logging ───────────────────────────────────────────────────────

    def log_download(self, evidence_id: uuid.UUID, actor_id: uuid.UUID) -> None:
        self._custody.log(
            evidence_id,
            actor_id=actor_id,
            action=CustodyAction.DOWNLOADED.value,
            description="Evidence file downloaded",
        )
        self.session.commit()
