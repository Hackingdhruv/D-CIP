"""Unit tests for the dependency-free PDF writer."""

from __future__ import annotations

from app.services.pdf_export import render_text_pdf


class TestPdfExport:
    def test_produces_valid_pdf_header_and_trailer(self) -> None:
        pdf = render_text_pdf("Test Timeline", ["line one", "line two"])
        assert pdf.startswith(b"%PDF-1.4")
        assert b"%%EOF" in pdf
        assert b"/Type /Catalog" in pdf
        assert b"/Type /Pages" in pdf

    def test_paginates_long_input(self) -> None:
        lines = [f"event number {i}" for i in range(500)]
        pdf = render_text_pdf("Big Timeline", lines)
        # More than one page object must be present for 500 lines.
        assert pdf.count(b"/Type /Page ") >= 2

    def test_escapes_parentheses(self) -> None:
        pdf = render_text_pdf("T", ["a (tricky) line with ) and ("])
        assert b"\\(" in pdf and b"\\)" in pdf

    def test_handles_empty_input(self) -> None:
        pdf = render_text_pdf("Empty", [])
        assert pdf.startswith(b"%PDF")
        assert b"%%EOF" in pdf
