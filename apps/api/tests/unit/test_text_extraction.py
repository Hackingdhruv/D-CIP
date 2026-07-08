"""Unit tests for text extraction service."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pytest

from app.services.text_extraction import extract_text, _extract_plaintext


class TestPlainTextExtraction:
    def test_reads_utf8(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("Hello world, this is a test file.", encoding="utf-8")
        result = extract_text(f, "text/plain", "txt")
        assert result is not None
        assert "Hello world" in result

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        result = extract_text(tmp_path / "missing.txt", "text/plain", "txt")
        assert result is None


class TestEmailExtraction:
    def test_extracts_eml_headers(self, tmp_path: Path) -> None:
        eml = tmp_path / "test.eml"
        eml.write_bytes(
            b"From: alice@example.com\r\n"
            b"To: bob@example.com\r\n"
            b"Subject: Test Email\r\n"
            b"Date: Mon, 26 Jun 2026 12:00:00 +0000\r\n"
            b"\r\n"
            b"This is the email body."
        )
        result = extract_text(eml, "message/rfc822", "eml")
        assert result is not None
        assert "alice@example.com" in result
        assert "Test Email" in result
        assert "email body" in result


class TestExtractPlaintext:
    def test_handles_latin1(self, tmp_path: Path) -> None:
        f = tmp_path / "latin.txt"
        f.write_bytes("Caf\xe9 au lait".encode("latin-1"))
        result = _extract_plaintext(f)
        assert result is not None
        assert len(result) > 0


class TestImageMetadata:
    def test_no_exception_on_text_file(self, tmp_path: Path) -> None:
        from app.services.text_extraction import extract_image_metadata
        f = tmp_path / "fake.png"
        f.write_bytes(b"notanimage")
        result = extract_image_metadata(f)
        assert isinstance(result, dict)
