"""Evidence and custody-event repositories."""

from __future__ import annotations

import math
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.models.evidence_custody import EvidenceCustodyEvent
from app.repositories.base import BaseRepository


class EvidenceRepository(BaseRepository[Evidence]):
    model = Evidence

    # ── Lookups ────────────────────────────────────────────────────────────────

    def get_active(self, evidence_id: uuid.UUID) -> Evidence | None:
        return self.session.execute(
            select(Evidence).where(
                Evidence.id == evidence_id,
                Evidence.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def get_for_case(
        self, evidence_id: uuid.UUID, case_id: uuid.UUID
    ) -> Evidence | None:
        return self.session.execute(
            select(Evidence).where(
                Evidence.id == evidence_id,
                Evidence.case_id == case_id,
                Evidence.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    def get_by_hash_in_case(
        self, sha256_hash: str, case_id: uuid.UUID
    ) -> Evidence | None:
        return self.session.execute(
            select(Evidence).where(
                Evidence.sha256_hash == sha256_hash,
                Evidence.case_id == case_id,
                Evidence.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

    # ── Search / list ──────────────────────────────────────────────────────────

    def list_for_case(
        self,
        case_id: uuid.UUID,
        *,
        q: str | None = None,
        mime_category: str | None = None,
        status: str | None = None,
        file_extension: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Evidence], int]:
        base = select(Evidence).where(
            Evidence.case_id == case_id,
            Evidence.deleted_at.is_(None),
        )

        if q:
            base = base.where(Evidence.original_filename.ilike(f"%{q}%"))

        if mime_category:
            base = base.where(Evidence.mime_type.ilike(f"{mime_category}/%"))

        if status:
            base = base.where(Evidence.status == status)

        if file_extension:
            base = base.where(Evidence.file_extension == file_extension.lower())

        total: int = self.session.execute(
            select(func.count()).select_from(base.subquery())
        ).scalar_one()

        items = list(
            self.session.execute(
                base.order_by(Evidence.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).scalars()
        )
        return items, total

    # ── Mutations ──────────────────────────────────────────────────────────────

    def soft_delete(self, evidence: Evidence) -> None:
        from datetime import datetime, timezone
        evidence.deleted_at = datetime.now(timezone.utc)
        self.session.flush()


class EvidenceCustodyRepository(BaseRepository[EvidenceCustodyEvent]):
    model = EvidenceCustodyEvent

    def log(
        self,
        evidence_id: uuid.UUID,
        *,
        actor_id: uuid.UUID | None,
        action: str,
        description: str,
        reason: str | None = None,
        event_data: dict | None = None,
    ) -> EvidenceCustodyEvent:
        event = EvidenceCustodyEvent(
            evidence_id=evidence_id,
            actor_id=actor_id,
            action=action,
            description=description,
            reason=reason,
            event_data=event_data or {},
        )
        self.session.add(event)
        self.session.flush()
        return event

    def list_for_evidence(
        self,
        evidence_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[EvidenceCustodyEvent], int]:
        base = select(EvidenceCustodyEvent).where(
            EvidenceCustodyEvent.evidence_id == evidence_id
        )
        total: int = self.session.execute(
            select(func.count()).select_from(base.subquery())
        ).scalar_one()
        items = list(
            self.session.execute(
                base.order_by(EvidenceCustodyEvent.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).scalars()
        )
        return items, total
