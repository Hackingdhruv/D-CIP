"""Timeline extraction — detect real-world events and timestamps from evidence text.

Each extracted event includes the timestamp (when the event occurred, not when the
record was created), event type, and a confidence score.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Date/time patterns ─────────────────────────────────────────────────────────

_RE_DATE_ISO = re.compile(
    r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?)\b"
)
_RE_DATE_US = re.compile(
    r"\b(\d{1,2}/\d{1,2}/\d{2,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)?)\b",
    re.IGNORECASE,
)
_RE_DATE_LONG = re.compile(
    r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"[\s,]+\d{1,2}[\s,]+\d{4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)?)\b",
    re.IGNORECASE,
)
_RE_EMAIL_DATE = re.compile(r"^Date:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_RE_SENT_AT = re.compile(r"(?:sent|received|on)\s+(.{10,40}?\d{4})", re.IGNORECASE)

# ── Event type keyword patterns ────────────────────────────────────────────────

_EVENT_PATTERNS = [
    ("email_sent",     re.compile(r"\b(?:sent|emailed|forwarded|replied)\b", re.I)),
    ("email_received", re.compile(r"\b(?:received|incoming|inbox)\b", re.I)),
    ("login",          re.compile(r"\b(?:logged in|sign in|signed in|login|authentication)\b", re.I)),
    ("logout",         re.compile(r"\b(?:logged out|sign out|signed out|logout)\b", re.I)),
    ("purchase",       re.compile(r"\b(?:purchased|bought|payment|paid|invoice|order(?:ed)?)\b", re.I)),
    ("transaction",    re.compile(r"\b(?:transfer(?:red)?|transaction|wire|deposit|withdrawal)\b", re.I)),
    ("travel",         re.compile(r"\b(?:flight|boarded|departed|arrived|travelled|checked in)\b", re.I)),
    ("meeting",        re.compile(r"\b(?:meeting|met with|conference|call with|appointment)\b", re.I)),
    ("download",       re.compile(r"\b(?:downloaded|export(?:ed)?|extracted)\b", re.I)),
    ("upload",         re.compile(r"\b(?:uploaded|import(?:ed)?|submitted)\b", re.I)),
    ("phone_call",     re.compile(r"\b(?:called|phone call|spoke with|conversation with)\b", re.I)),
    ("message",        re.compile(r"\b(?:message(?:d)?|text(?:ed)?|chat(?:ted)?|dm(?:ed)?)\b", re.I)),
    ("file_created",   re.compile(r"\b(?:created|new file|generated|written)\b", re.I)),
    ("file_modified",  re.compile(r"\b(?:modified|updated|edited|changed)\b", re.I)),
]


@dataclass
class ExtractedTimelineEvent:
    event_type: str
    event_title: str
    description: str | None
    event_timestamp: datetime | None
    confidence: float
    source_text: str | None


def extract_timeline_events(
    text: str,
    filename: str = "",
    mime_type: str = "",
) -> list[ExtractedTimelineEvent]:
    """Extract timeline events from evidence text. Returns events sorted by timestamp."""
    events: list[ExtractedTimelineEvent] = []

    # EML-specific: extract the email date header as a high-confidence event
    if mime_type in ("message/rfc822",) or filename.endswith((".eml", ".msg")):
        m = _RE_EMAIL_DATE.search(text)
        if m:
            ts = _parse_datetime(m.group(1).strip())
            events.append(ExtractedTimelineEvent(
                event_type="email_sent",
                event_title="Email",
                description=None,
                event_timestamp=ts,
                confidence=0.95,
                source_text=m.group(0)[:200],
            ))

    # General event extraction: find date patterns, then look for event keywords nearby
    all_dates = list(_RE_DATE_ISO.finditer(text)) + list(_RE_DATE_LONG.finditer(text))

    for date_match in all_dates[:100]:  # cap search
        date_str = date_match.group(1)
        ts = _parse_datetime(date_str)

        # Look in the surrounding 200-char window for event type keywords
        ctx_start = max(0, date_match.start() - 150)
        ctx_end = min(len(text), date_match.end() + 150)
        ctx = text[ctx_start:ctx_end]

        matched_type = "unknown"
        for etype, pattern in _EVENT_PATTERNS:
            if pattern.search(ctx):
                matched_type = etype
                break

        # Skip pure unknowns unless the date is highly structured (ISO)
        if matched_type == "unknown" and _RE_DATE_ISO.match(date_str) is None:
            continue

        events.append(ExtractedTimelineEvent(
            event_type=matched_type,
            event_title=_event_title(matched_type, date_str),
            description=None,
            event_timestamp=ts,
            confidence=0.75 if matched_type != "unknown" else 0.5,
            source_text=ctx[:300].replace("\n", " "),
        ))

    # Deduplicate by (type, timestamp)
    seen: set[tuple[str, str]] = set()
    deduped: list[ExtractedTimelineEvent] = []
    for ev in events:
        key = (ev.event_type, str(ev.event_timestamp))
        if key not in seen:
            seen.add(key)
            deduped.append(ev)

    deduped.sort(key=lambda e: (e.event_timestamp or datetime.min.replace(tzinfo=timezone.utc)))
    return deduped[:200]  # cap output


def _parse_datetime(text: str) -> datetime | None:
    """Attempt to parse a datetime string. Returns None on failure."""
    from email.utils import parsedate_to_datetime
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%B %d, %Y %I:%M %p",
        "%B %d, %Y",
        "%b %d, %Y",
    ]
    text = text.strip()
    # Try email header format first
    try:
        return parsedate_to_datetime(text)
    except Exception:
        pass
    for fmt in formats:
        try:
            dt = datetime.strptime(text[:len(fmt) + 4], fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    # ISO with timezone offset
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


def _event_title(etype: str, date_str: str) -> str:
    labels = {
        "email_sent": "Email Sent",
        "email_received": "Email Received",
        "login": "Login",
        "logout": "Logout",
        "purchase": "Purchase",
        "transaction": "Transaction",
        "travel": "Travel",
        "meeting": "Meeting",
        "download": "Download",
        "upload": "Upload",
        "phone_call": "Phone Call",
        "message": "Message",
        "file_created": "File Created",
        "file_modified": "File Modified",
        "unknown": "Event",
    }
    return f"{labels.get(etype, 'Event')} — {date_str[:20]}"
