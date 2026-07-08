"""Unit tests for timeline extraction service."""

from __future__ import annotations

import pytest

from app.services.timeline_extraction import extract_timeline_events, _parse_datetime


class TestDatetimeParsing:
    def test_parses_iso_date(self) -> None:
        dt = _parse_datetime("2026-06-26")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 6
        assert dt.day == 26

    def test_parses_iso_datetime(self) -> None:
        dt = _parse_datetime("2026-06-26T14:30:00")
        assert dt is not None
        assert dt.hour == 14

    def test_parses_email_date(self) -> None:
        dt = _parse_datetime("Mon, 26 Jun 2026 12:00:00 +0000")
        assert dt is not None
        assert dt.year == 2026

    def test_returns_none_for_garbage(self) -> None:
        dt = _parse_datetime("not a date")
        assert dt is None


class TestTimelineExtraction:
    def test_extracts_event_from_iso_date(self) -> None:
        text = "The payment was made on 2026-01-15. Transaction confirmed."
        events = extract_timeline_events(text)
        assert any(e.event_timestamp is not None for e in events)

    def test_detects_email_event_type(self) -> None:
        text = "Message sent on 2026-03-10. Email forwarded successfully."
        events = extract_timeline_events(text)
        types = {e.event_type for e in events}
        assert len(types) > 0

    def test_eml_header_extracted(self) -> None:
        text = (
            "From: alice@example.com\r\n"
            "Date: Mon, 26 Jun 2026 12:00:00 +0000\r\n"
            "\r\nBody text"
        )
        events = extract_timeline_events(text, mime_type="message/rfc822")
        assert any(e.event_type == "email_sent" for e in events)

    def test_empty_text_returns_empty(self) -> None:
        events = extract_timeline_events("")
        assert events == []

    def test_events_sorted_by_timestamp(self) -> None:
        text = "Event at 2026-03-01. Earlier event at 2026-01-01. Late event at 2026-05-01."
        events = extract_timeline_events(text)
        timestamps = [e.event_timestamp for e in events if e.event_timestamp]
        assert timestamps == sorted(timestamps)
