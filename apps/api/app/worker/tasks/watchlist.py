"""Watchlist matching Celery task.

Triggered by the processing pipeline after entity extraction completes.
Runs asynchronously so it does not block the main evidence pipeline.
"""

from __future__ import annotations

import logging
import uuid

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="watchlist.match_evidence",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def match_evidence(self, evidence_id: str, case_id: str) -> dict:
    """Run watchlist matching for a single evidence item."""
    from app.db.session import SessionLocal
    from app.services.watchlist_matching import WatchlistMatchingEngine
    from app.services.alert_service import AlertService
    from app.services.notification_service import NotificationService
    from app.models.user import User
    from sqlalchemy import select

    eid = uuid.UUID(evidence_id)
    cid = uuid.UUID(case_id)

    logger.info("Watchlist matching starting for evidence %s", evidence_id)

    try:
        with SessionLocal() as session:
            engine = WatchlistMatchingEngine(session)
            matches = engine.run(evidence_id=eid, case_id=cid)

            if not matches:
                logger.info(
                    "No watchlist matches for evidence %s", evidence_id
                )
                return {"evidence_id": evidence_id, "matches": 0}

            # Use a system/bot user concept: pick any admin user as actor,
            # or create alerts without an actor (created_by_id = NULL)
            # AlertService.create_from_matches works without a real actor
            # when we pass a minimal stub. We create alerts directly here.
            from app.models.watchlist_alert import WatchlistAlert, AlertStatus

            created_alerts: list[WatchlistAlert] = []
            from app.models.watchlist import WatchlistEntry
            for m in matches:
                alert = WatchlistAlert(
                    watchlist_id=m.watchlist_id,
                    watchlist_entry_id=m.watchlist_entry_id,
                    evidence_id=eid,
                    case_id=cid,
                    alert_type=m.alert_type,
                    severity=m.severity,
                    title=m.title[:500],
                    description=m.description,
                    matched_value=m.matched_value,
                    matched_entity_type=m.matched_entity_type,
                    confidence=m.confidence,
                    status=AlertStatus.NEW.value,
                    is_cross_case=m.is_cross_case,
                    cross_case_ids=m.cross_case_ids,
                    alert_metadata=m.metadata,
                )
                session.add(alert)
                created_alerts.append(alert)

                # Increment hit count on matched entry
                if m.watchlist_entry_id:
                    entry = session.get(WatchlistEntry, m.watchlist_entry_id)
                    if entry:
                        entry.hit_count += 1

            session.flush()

            # Fan out notifications to case members
            for alert in created_alerts:
                NotificationService.fan_out(session, alert)

            session.commit()

            logger.info(
                "Watchlist matching complete for evidence %s: %d alert(s) created",
                evidence_id, len(created_alerts),
            )
            return {"evidence_id": evidence_id, "matches": len(created_alerts)}

    except Exception as exc:
        logger.exception(
            "Watchlist matching error for evidence %s: %s", evidence_id, exc
        )
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(
                "Max retries exceeded for watchlist matching, evidence %s",
                evidence_id,
            )
            return {"evidence_id": evidence_id, "error": str(exc)}
