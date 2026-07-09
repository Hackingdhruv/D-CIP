"""Unit tests for the general-purpose AI response cleanup helper."""

from __future__ import annotations
from unittest.mock import MagicMock, patch

from app.services.ai_provider import (
    _clean_ai_response,
    _guard_unsupported_last_day_claims,
    chat,
)


class TestCleanAiResponse:
    def test_normalizes_paren_citation_to_bracket_form(self) -> None:
        text = "The transfer occurred (Evidence: dlp_alerts.log) on May 3rd."
        assert _clean_ai_response(text) == (
            "The transfer occurred [Evidence: dlp_alerts.log] on May 3rd."
        )

    def test_normalizes_paren_file_citation_to_bracket_form(self) -> None:
        text = "The document was uploaded (File: report.docx) that day."
        assert _clean_ai_response(text) == (
            "The document was uploaded [Evidence: report.docx] that day."
        )

    def test_normalizes_bulleted_file_citation_to_bracket_form(self) -> None:
        text = "Relevant Evidence:\n* File: dlp_alerts.log\n* Source: usb_registry.txt"
        assert _clean_ai_response(text) == (
            "Relevant Evidence:\n* [Evidence: dlp_alerts.log]\n* [Evidence: usb_registry.txt]"
        )

    def test_strips_contradictory_trailing_fallback_after_substantive_answer(self) -> None:
        substantive = (
            "Based on the DLP alerts and USB registry extract, the user account "
            "HELIOS\\e.solano transferred files to a SanDisk Ultra USB 3.0 device "
            "on four separate occasions between May 1 and May 5, 2026. "
            "[Evidence: symantec_dlp_alerts_solano_may2026.log]"
        )
        text = substantive + "\n\nI don't have enough evidence to answer this."
        assert _clean_ai_response(text) == substantive

    def test_keeps_standalone_fallback_when_it_is_the_entire_answer(self) -> None:
        text = "I don't have enough evidence to answer this."
        assert _clean_ai_response(text) == text

    def test_strips_trailing_bare_id_lines(self) -> None:
        text = (
            "The exfiltration totaled approximately 47.5 GB across four transfers.\n\n"
            "68310095\n"
            "e447d54f"
        )
        cleaned = _clean_ai_response(text)
        assert "68310095" not in cleaned
        assert "e447d54f" not in cleaned
        assert cleaned == "The exfiltration totaled approximately 47.5 GB across four transfers."

    def test_does_not_strip_numbers_that_are_part_of_a_sentence(self) -> None:
        text = "The transfer was 23449600000 bytes (~23.45 GB) in size, per the DLP log."
        assert _clean_ai_response(text) == text

    def test_empty_after_cleanup_falls_back_to_original(self) -> None:
        text = "abcdef1234"
        assert _clean_ai_response(text) == text

    def test_collapses_nested_bracket_citation(self) -> None:
        text = "Files were uploaded [Evidence: [usb_registry_forensic_extract.txt]]."
        assert _clean_ai_response(text) == (
            "Files were uploaded [Evidence: usb_registry_forensic_extract.txt]."
        )

    def test_annotates_raw_byte_counts_with_human_readable_size(self) -> None:
        text = "The transfer totaled 23449600000 bytes on May 28."
        assert _clean_ai_response(text) == (
            "The transfer totaled 23,449,600,000 bytes (~23.45 GB) on May 28."
        )

    def test_does_not_reannotate_already_annotated_byte_counts(self) -> None:
        text = "The transfer was 23,449,600,000 bytes (~23.45 GB) in size."
        assert _clean_ai_response(text) == text

    def test_leaves_small_byte_counts_unannotated(self) -> None:
        text = "The header was 512 bytes long."
        assert _clean_ai_response(text) == text


class TestGuardUnsupportedLastDayClaims:
    """The idiom "last/final working day" is common in departure-related case
    narratives, but background context often uses it without ever stating
    which calendar date it refers to. A model that then pins a specific date
    or event to it is inferring a fact nobody established."""

    def test_hedges_pronoun_form_when_phrase_has_no_adjacent_date(self) -> None:
        # The resignation date appears earlier in the same paragraph, but is
        # not literally adjacent to "last working day" — mirrors real case
        # narratives where a background date and the idiom are mentioned
        # separately, not stated as the same fact.
        grounding = (
            "A departing employee, who resigned effective 2099-01-01, is "
            "suspected of copying data to personal devices in the weeks "
            "before departure. Alerts were triggered on her last working day."
        )
        content = "Alerts fired on her last working day, indicating exfiltration."
        result = _guard_unsupported_last_day_claims(content, grounding)
        assert "last working day" not in result.lower()
        assert "in the days leading up to her departure" in result

    def test_hedges_possessive_name_form(self) -> None:
        grounding = "Subject resigned. Alerts triggered on his last working day."
        content = "Multiple alerts were triggered on Mr. Doe's last working day."
        result = _guard_unsupported_last_day_claims(content, grounding)
        assert "last working day" not in result.lower()
        assert "in the days leading up to Mr. Doe's departure" in result

    def test_leaves_claim_alone_when_source_pins_it_to_a_specific_date(self) -> None:
        grounding = "Badge log confirms 2099-03-04 was her last working day."
        content = "Badge access ended on her last working day."
        assert _guard_unsupported_last_day_claims(content, grounding) == content

    def test_leaves_content_unchanged_when_phrase_not_present_in_content(self) -> None:
        grounding = "No such phrase here."
        content = "Activity occurred over several days in May."
        assert _guard_unsupported_last_day_claims(content, grounding) == content


class TestChatEvidenceReferences:
    """`evidence_references` must surface human-readable filenames, never raw
    internal evidence IDs — the frontend renders these directly to the user."""

    def _mock_client(self, reply_text: str) -> MagicMock:
        client = MagicMock()
        response = MagicMock()
        response.choices[0].message.content = reply_text
        client.chat.completions.create.return_value = response
        return client

    def test_references_cited_files_by_filename_not_id(self) -> None:
        evidence_context = [
            {"id": "68310095-34f5-4cea-b317-c323c6758787", "filename": "usb_registry_forensic_extract.txt", "text": "", "summary": ""},
            {"id": "e447d54f-514d-4af7-b91c-cf30027dcb6e", "filename": "symantec_dlp_alerts_solano_may2026.log", "text": "", "summary": ""},
        ]
        reply = "Files were transferred. [Evidence: usb_registry_forensic_extract.txt]"
        with patch("app.services.ai_provider._get_client", return_value=(self._mock_client(reply), "llama3.2")):
            result = chat(case_title="Test Case", messages=[{"role": "user", "content": "q"}], evidence_context=evidence_context)

        assert result is not None
        assert result.evidence_references == ["usb_registry_forensic_extract.txt"]
        assert "68310095" not in "".join(result.evidence_references)
        assert "e447d54f" not in "".join(result.evidence_references)

    def test_falls_back_to_all_filenames_when_nothing_cited(self) -> None:
        evidence_context = [
            {"id": "68310095-34f5-4cea-b317-c323c6758787", "filename": "usb_registry_forensic_extract.txt", "text": "", "summary": ""},
        ]
        reply = "I don't have enough evidence to answer this."
        with patch("app.services.ai_provider._get_client", return_value=(self._mock_client(reply), "llama3.2")):
            result = chat(case_title="Test Case", messages=[{"role": "user", "content": "q"}], evidence_context=evidence_context)

        assert result is not None
        assert result.evidence_references == ["usb_registry_forensic_extract.txt"]
