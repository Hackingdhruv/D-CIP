"""WatchlistMatchingEngine — compares extracted entities against active watchlists.

Matching strategy:
  1. Exact match   — normalized_value equality
  2. Regex match   — entry.value treated as a compiled regex pattern
  3. Repeated appearance — same entity appears in 3+ evidence items in one case
  4. Cross-case match — entity seen in entities from a different case

Results are MatchResult dataclass objects which the caller converts to
WatchlistAlert rows via AlertService.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.evidence_entity import EvidenceEntity
from app.models.watchlist import WatchlistEntry
from app.models.watchlist_alert import AlertSeverity, AlertType

logger = logging.getLogger(__name__)

# Watchlist types that map to one or more EvidenceEntity entity_type values
_WATCHLIST_TO_ENTITY_TYPES: dict[str, list[str]] = {
    "email": ["email"],
    "phone": ["phone"],
    "domain": ["domain"],
    "url": ["url"],
    "ip_address": ["ip_address"],
    "sha256": ["file_hash"],
    "md5": ["file_hash"],
    "crypto_wallet": ["crypto_wallet"],
    "bank_account": ["bank_account"],
    "vehicle_registration": ["vehicle_number"],
    "passport": [],  # matched via regex only
    "device_id": ["device"],
    "imei": [],  # matched via regex only
    "mac_address": [],  # matched via regex only
    "regex": None,  # matches all entity types
    "keyword": None,  # matches all entity types
}

_HIGH_RISK_WATCHLIST_TYPES = {"crypto_wallet", "bank_account", "sha256", "md5"}
_REPEATED_APPEARANCE_THRESHOLD = 3


@dataclass
class MatchResult:
    alert_type: str
    severity: str
    title: str
    description: str
    matched_value: str
    matched_entity_type: str
    confidence: float
    watchlist_id: uuid.UUID | None = None
    watchlist_entry_id: uuid.UUID | None = None
    is_cross_case: bool = False
    cross_case_ids: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def _severity_for_watchlist_type(watchlist_type: str) -> str:
    if watchlist_type in _HIGH_RISK_WATCHLIST_TYPES:
        return AlertSeverity.CRITICAL.value
    if watchlist_type in ("email", "phone", "ip_address"):
        return AlertSeverity.HIGH.value
    return AlertSeverity.MEDIUM.value


class WatchlistMatchingEngine:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(
        self,
        evidence_id: uuid.UUID,
        case_id: uuid.UUID,
    ) -> list[MatchResult]:
        """Run all match passes for a single evidence item. Returns MatchResults."""
        # Load entities extracted from this evidence
        entities: list[EvidenceEntity] = list(
            self.db.execute(
                select(EvidenceEntity).where(
                    EvidenceEntity.evidence_id == evidence_id
                )
            ).scalars()
        )
        if not entities:
            return []

        results: list[MatchResult] = []
        results.extend(self._watchlist_match(entities, case_id))
        results.extend(self._repeated_appearance_check(entities, case_id, evidence_id))
        results.extend(self._cross_case_match(entities, case_id))
        return results

    # ── Pass 1: Watchlist exact + regex matching ──────────────────────────────

    def _watchlist_match(
        self,
        entities: list[EvidenceEntity],
        case_id: uuid.UUID,
    ) -> list[MatchResult]:
        from sqlalchemy import or_
        from app.models.watchlist import Watchlist

        # Load all active entries from watchlists that apply to this case
        entries: list[WatchlistEntry] = list(
            self.db.execute(
                select(WatchlistEntry)
                .join(Watchlist, WatchlistEntry.watchlist_id == Watchlist.id)
                .where(
                    WatchlistEntry.is_active.is_(True),
                    Watchlist.is_active.is_(True),
                    or_(
                        Watchlist.case_id.is_(None),
                        Watchlist.case_id == case_id,
                    ),
                )
            ).scalars()
        )

        results: list[MatchResult] = []
        for entry in entries:
            # Determine which entity types this watchlist entry targets
            wl = entry.watchlist
            target_types = _WATCHLIST_TO_ENTITY_TYPES.get(wl.watchlist_type)

            for entity in entities:
                # Skip if entity type doesn't match (None means any type)
                if (
                    target_types is not None
                    and entity.entity_type not in target_types
                ):
                    continue

                if entry.is_regex:
                    matched = self._regex_match(entry, entity)
                else:
                    matched = self._exact_match(entry, entity)

                if matched:
                    sev = _severity_for_watchlist_type(wl.watchlist_type)
                    if wl.watchlist_type in _HIGH_RISK_WATCHLIST_TYPES:
                        alert_type = AlertType.HIGH_RISK_MATCH.value
                        sev = AlertSeverity.CRITICAL.value
                    elif entry.is_regex:
                        alert_type = AlertType.REGEX_MATCH.value
                    else:
                        alert_type = AlertType.EXACT_MATCH.value

                    results.append(
                        MatchResult(
                            alert_type=alert_type,
                            severity=sev,
                            title=(
                                f"Watchlist hit: {entity.value!r} "
                                f"matches \"{wl.name}\""
                            ),
                            description=(
                                f"Entity [{entity.entity_type}] "
                                f"\"{entity.value}\" matched watchlist "
                                f"\"{wl.name}\" "
                                f"({'regex' if entry.is_regex else 'exact'} match)."
                            ),
                            matched_value=entity.value,
                            matched_entity_type=entity.entity_type,
                            confidence=entity.confidence,
                            watchlist_id=wl.id,
                            watchlist_entry_id=entry.id,
                            metadata={
                                "watchlist_type": wl.watchlist_type,
                                "entry_value": entry.value,
                                "entity_source": entity.source,
                            },
                        )
                    )
        return results

    def _exact_match(self, entry: WatchlistEntry, entity: EvidenceEntity) -> bool:
        return entry.normalized_value == entity.normalized_value

    def _regex_match(
        self, entry: WatchlistEntry, entity: EvidenceEntity
    ) -> bool:
        try:
            return bool(re.search(entry.value, entity.value, re.IGNORECASE))
        except re.error as exc:
            logger.warning(
                "Invalid regex in watchlist entry %s: %s", entry.id, exc
            )
            return False

    # ── Pass 2: Repeated appearance within the same case ─────────────────────

    def _repeated_appearance_check(
        self,
        entities: list[EvidenceEntity],
        case_id: uuid.UUID,
        evidence_id: uuid.UUID,
    ) -> list[MatchResult]:
        results: list[MatchResult] = []
        seen: set[str] = set()

        for entity in entities:
            key = f"{entity.entity_type}:{entity.normalized_value}"
            if key in seen:
                continue
            seen.add(key)

            # Count how many distinct evidence items in this case have this entity
            count = self.db.execute(
                select(func.count(func.distinct(EvidenceEntity.evidence_id))).where(
                    EvidenceEntity.case_id == case_id,
                    EvidenceEntity.entity_type == entity.entity_type,
                    EvidenceEntity.normalized_value == entity.normalized_value,
                    EvidenceEntity.evidence_id != evidence_id,
                )
            ).scalar_one()

            if count >= _REPEATED_APPEARANCE_THRESHOLD - 1:
                results.append(
                    MatchResult(
                        alert_type=AlertType.REPEATED_APPEARANCE.value,
                        severity=AlertSeverity.MEDIUM.value,
                        title=(
                            f"Repeated entity: {entity.value!r} "
                            f"appears in {count + 1} evidence items"
                        ),
                        description=(
                            f"Entity [{entity.entity_type}] \"{entity.value}\" "
                            f"has appeared in {count + 1} evidence items "
                            f"within this case, indicating possible significance."
                        ),
                        matched_value=entity.value,
                        matched_entity_type=entity.entity_type,
                        confidence=0.9,
                        metadata={"appearance_count": count + 1},
                    )
                )
        return results

    # ── Pass 3: Cross-case entity matching (RBAC-blind, RBAC applied at read) ─

    def _cross_case_match(
        self,
        entities: list[EvidenceEntity],
        case_id: uuid.UUID,
    ) -> list[MatchResult]:
        results: list[MatchResult] = []
        seen: set[str] = set()

        for entity in entities:
            key = f"{entity.entity_type}:{entity.normalized_value}"
            if key in seen:
                continue
            seen.add(key)

            # Find the same entity value in OTHER cases (no RBAC filter here —
            # the cross_case_ids field is RBAC-filtered at API read time)
            rows = self.db.execute(
                select(EvidenceEntity.case_id)
                .where(
                    EvidenceEntity.entity_type == entity.entity_type,
                    EvidenceEntity.normalized_value == entity.normalized_value,
                    EvidenceEntity.case_id != case_id,
                )
                .distinct()
            ).scalars().all()

            if rows:
                cross_ids = [str(c) for c in rows]
                results.append(
                    MatchResult(
                        alert_type=AlertType.CROSS_CASE_MATCH.value,
                        severity=AlertSeverity.HIGH.value,
                        title=(
                            f"Cross-case match: {entity.value!r} "
                            f"found in {len(cross_ids)} other investigation(s)"
                        ),
                        description=(
                            f"Entity [{entity.entity_type}] \"{entity.value}\" "
                            f"was also found in {len(cross_ids)} other case(s). "
                            f"This may indicate a connection between investigations."
                        ),
                        matched_value=entity.value,
                        matched_entity_type=entity.entity_type,
                        confidence=1.0,
                        is_cross_case=True,
                        cross_case_ids=cross_ids,
                        metadata={"cross_case_count": len(cross_ids)},
                    )
                )
        return results
