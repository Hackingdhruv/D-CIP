#!/usr/bin/env python
"""Seed a single, self-contained demo investigation case.

Usage (run manually — this never runs automatically):

    cd apps/api
    uv run python scripts/seed_demo_data.py

Safety:
    - Refuses to run when DCIP_ENV=production.
    - Idempotent: the demo case uses a fixed, deterministic id. Re-running
      this script detects the existing case and exits without creating a
      duplicate or modifying anything.
    - All data is fictional: emails use the .example TLD (RFC 2606), IPs use
      the documentation ranges from RFC 5737, phone numbers use the NANPA
      555-01xx fictional block. No real names, credentials, or evidence.
    - Evidence file content is generated in memory — no local filesystem
      paths are hardcoded, and files are written through the app's own
      storage abstraction (respects UPLOAD_DIR).
"""

from __future__ import annotations

import io
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402

# Fixed, deterministic id — reruns detect this case and no-op instead of
# creating a duplicate.
DEMO_CASE_ID = uuid.uuid5(uuid.NAMESPACE_URL, "https://dcip.local/demo-case/v1")

_NOW = datetime.now(timezone.utc)


def _days_ago(n: int, hour: int = 9, minute: int = 0) -> datetime:
    return (_NOW - timedelta(days=n)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )


def _chat_screenshot_png() -> bytes:
    """Render a small fictional chat screenshot in memory (for OCR demo)."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (900, 260), color="white")
    d = ImageDraw.Draw(img)
    lines = [
        "[DEMO DATA — FICTIONAL] Investment Advisor Chat Export",
        "Contact handle: advisor_marcus.wren (platform: FinGrow Capital)",
        "Requested wallet for deposit: 1DemoXFictionaLWaLLetNotReaLXX",
        "Follow-up contact: support@fingrow-capital.example",
        "Reported by victim on case intake form.",
    ]
    y = 20
    for line in lines:
        d.text((20, y), line, fill="black")
        y += 40
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _transaction_log_txt() -> bytes:
    """Fictional transaction/DLP-style log (for entity-extraction demo)."""
    text = (
        "[DEMO DATA — FICTIONAL EVIDENCE, NOT A REAL INCIDENT]\n"
        "FinGrow Capital — Outbound Transfer Log Export\n"
        "\n"
        "2026-06-01 09:14:02 TRANSFER initiated by victim account "
        "to wallet 1DemoXFictionaLWaLLetNotReaLXX amount=2500.00USD\n"
        "2026-06-01 09:14:05 Confirmation email sent to "
        "victim.contact@mail.example from support@fingrow-capital.example\n"
        "2026-06-03 14:22:11 TRANSFER initiated by victim account "
        "to wallet 1DemoXFictionaLWaLLetNotReaLXX amount=8750.00USD\n"
        "2026-06-03 14:22:40 Platform dashboard accessed from "
        "IP 203.0.113.42 (documentation range, fictional)\n"
        "2026-06-05 11:03:58 Withdrawal request DENIED — platform cited "
        "'account verification fee' requirement\n"
        "2026-06-05 11:10:02 Follow-up contact from "
        "advisor_marcus.wren via domain fingrow-capital.example, "
        "hosting IP 198.51.100.17 (documentation range, fictional)\n"
        "2026-06-06 08:45:00 Victim ceased contact and reported to D-CIP.\n"
    )
    return text.encode("utf-8")


def seed() -> None:
    if settings.is_production:
        print(
            "Refusing to seed demo data: DCIP_ENV=production. "
            "This script is for local/evaluation environments only.",
            file=sys.stderr,
        )
        sys.exit(1)

    from app.db.session import SessionLocal
    from app.models.case import Case, CasePriority, CaseStatus
    from app.models.case_note import CaseNote
    from app.models.case_task import CaseTask, TaskPriority, TaskStatus
    from app.models.timeline_event import (
        TimelineEvent,
        TimelineEventCategory,
        TimelineEventType,
        TimelineSourceType,
    )
    from app.models.user import User
    from app.services.evidence import EvidenceService

    db = SessionLocal()
    try:
        existing = db.get(Case, DEMO_CASE_ID)
        if existing is not None:
            print(
                f"Demo case already exists (id={DEMO_CASE_ID}, "
                f"title={existing.title!r}) — nothing to do."
            )
            return

        admin = db.query(User).filter(User.email == "admin@dcip.local").first()
        if admin is None:
            print(
                "No admin@dcip.local user found — run migrations first "
                "(alembic upgrade head creates it automatically).",
                file=sys.stderr,
            )
            sys.exit(1)

        # ── Case ──────────────────────────────────────────────────────────
        case = Case(
            id=DEMO_CASE_ID,
            reference_number="DEMO-2026-0001",
            title="[DEMO] Operation Golden Ledger — Cross-Border Investment Fraud",
            description=(
                "[DEMO DATA — entirely fictional, seeded for evaluation purposes only.] "
                "A victim reports being directed by an online contact to deposit funds "
                "into a cryptocurrency wallet through a fraudulent investment platform "
                "('FinGrow Capital') promising guaranteed returns. Withdrawal was later "
                "denied pending a fabricated 'verification fee'. This case demonstrates "
                "D-CIP's evidence integrity, automated entity/timeline extraction, and "
                "case management features using safe, synthetic data."
            ),
            status=CaseStatus.OPEN.value,
            priority=CasePriority.HIGH.value,
            category="Cybercrime",
            tags=["demo", "fraud", "cryptocurrency", "investment-scam"],
            owner_id=admin.id,
            created_by_id=admin.id,
        )
        db.add(case)
        db.flush()

        # ── Tasks ─────────────────────────────────────────────────────────
        tasks = [
            CaseTask(
                case_id=case.id,
                title="Verify wallet cluster ownership via blockchain analytics",
                description="Trace the destination wallet for linked addresses and exchange off-ramps.",
                status=TaskStatus.PENDING.value,
                priority=TaskPriority.HIGH.value,
                created_by_id=admin.id,
                due_date=_NOW + timedelta(days=5),
            ),
            CaseTask(
                case_id=case.id,
                title="Cross-reference scam domain against known infrastructure",
                description="Check fingrow-capital.example and its hosting IPs against watchlists.",
                status=TaskStatus.PENDING.value,
                priority=TaskPriority.MEDIUM.value,
                created_by_id=admin.id,
                due_date=_NOW + timedelta(days=7),
            ),
            CaseTask(
                case_id=case.id,
                title="Interview victim for additional transaction records",
                description="Collect bank statements and any further correspondence.",
                status=TaskStatus.IN_PROGRESS.value,
                priority=TaskPriority.HIGH.value,
                created_by_id=admin.id,
                due_date=_NOW + timedelta(days=2),
            ),
            CaseTask(
                case_id=case.id,
                title="Draft preliminary financial loss summary",
                status=TaskStatus.PENDING.value,
                priority=TaskPriority.MEDIUM.value,
                created_by_id=admin.id,
                due_date=_NOW + timedelta(days=10),
            ),
        ]
        db.add_all(tasks)

        # ── Notes ─────────────────────────────────────────────────────────
        notes = [
            CaseNote(
                case_id=case.id,
                title="Initial Triage Summary",
                content=(
                    "Victim reports contact via social media by an account presenting "
                    "as an investment advisor. Two transfers totaling $11,250 (fictional "
                    "figures) were made to a cryptocurrency wallet before withdrawal was "
                    "blocked. Platform is not a registered financial service."
                ),
                is_pinned=True,
                created_by_id=admin.id,
            ),
            CaseNote(
                case_id=case.id,
                title="Investigator Working Notes",
                content=(
                    "Domain registration for fingrow-capital.example appears recent. "
                    "Pattern consistent with a romance/investment ('pig-butchering') "
                    "scam structure — plan to check the wallet against public "
                    "blockchain explorers next."
                ),
                is_pinned=False,
                created_by_id=admin.id,
            ),
        ]
        db.add_all(notes)

        # ── Timeline events ───────────────────────────────────────────────
        events = [
            TimelineEvent(
                case_id=case.id,
                source_type=TimelineSourceType.MANUAL.value,
                event_type=TimelineEventType.MESSAGE.value,
                category=TimelineEventCategory.COMMUNICATION.value,
                title="Initial contact via social media",
                description="Victim contacted by 'advisor_marcus.wren' offering guaranteed investment returns.",
                event_timestamp=_days_ago(6),
                confidence=0.9,
                entities=[{"type": "username", "value": "advisor_marcus.wren"}],
                created_by_id=admin.id,
            ),
            TimelineEvent(
                case_id=case.id,
                source_type=TimelineSourceType.MANUAL.value,
                event_type=TimelineEventType.TRANSACTION.value,
                category=TimelineEventCategory.FINANCIAL.value,
                title="First transfer to fraudulent wallet",
                description="$2,500 (fictional) transferred to wallet 1DemoXFictionaLWaLLetNotReaLXX.",
                event_timestamp=_days_ago(5),
                confidence=0.95,
                entities=[{"type": "crypto_wallet", "value": "1DemoXFictionaLWaLLetNotReaLXX"}],
                created_by_id=admin.id,
            ),
            TimelineEvent(
                case_id=case.id,
                source_type=TimelineSourceType.MANUAL.value,
                event_type=TimelineEventType.TRANSACTION.value,
                category=TimelineEventCategory.FINANCIAL.value,
                title="Second, larger transfer following fabricated returns dashboard",
                description="$8,750 (fictional) transferred after platform showed fake profit growth.",
                event_timestamp=_days_ago(3),
                confidence=0.95,
                entities=[{"type": "crypto_wallet", "value": "1DemoXFictionaLWaLLetNotReaLXX"}],
                created_by_id=admin.id,
            ),
            TimelineEvent(
                case_id=case.id,
                source_type=TimelineSourceType.MANUAL.value,
                event_type=TimelineEventType.CUSTOM.value,
                category=TimelineEventCategory.FINANCIAL.value,
                title="Withdrawal denied, fabricated fee demanded",
                description="Platform blocked withdrawal, citing a fictitious 'verification fee'.",
                event_timestamp=_days_ago(1),
                confidence=0.9,
                created_by_id=admin.id,
            ),
            TimelineEvent(
                case_id=case.id,
                source_type=TimelineSourceType.CASE_ACTIVITY.value,
                event_type=TimelineEventType.CASE_ACTIVITY.value,
                category=TimelineEventCategory.INVESTIGATION.value,
                title="Case reported to D-CIP investigation team",
                event_timestamp=_days_ago(0),
                confidence=1.0,
                created_by_id=admin.id,
            ),
        ]
        db.add_all(events)
        db.commit()

        # ── Evidence (real upload path — hashed, custody-logged, dispatched
        #    to the worker for real pipeline processing) ────────────────────
        db.refresh(admin)
        from app.storage import get_storage

        storage = get_storage()
        evidence_svc = EvidenceService(db, storage=storage)

        for filename, content, mime, ext in (
            (
                "transaction_log_export.txt",
                _transaction_log_txt(),
                "text/plain",
                "txt",
            ),
            (
                "victim_chat_screenshot.png",
                _chat_screenshot_png(),
                "image/png",
                "png",
            ),
        ):
            evidence_id = uuid.uuid4()
            storage_path = f"evidence/{case.id}/{evidence_id}.{ext}"
            size, sha256 = storage.save(storage_path, io.BytesIO(content))
            evidence_svc.record_upload(
                case.id,
                original_filename=filename,
                storage_path=storage_path,
                file_size=size,
                mime_type=mime,
                file_extension=ext,
                sha256_hash=sha256,
                actor=admin,
            )

        print(f"Seeded demo case: {case.title!r}")
        print(f"  case_id: {case.id}")
        print(f"  reference_number: {case.reference_number}")
        print(f"  tasks: {len(tasks)}, notes: {len(notes)}, timeline events: {len(events)}")
        print("  evidence: 2 files uploaded and dispatched for processing")
        print(
            "  (evidence pipeline runs asynchronously — give the worker a "
            "few seconds, then refresh the case's Evidence tab)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
