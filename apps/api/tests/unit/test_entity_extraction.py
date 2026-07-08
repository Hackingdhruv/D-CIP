"""Unit tests for entity extraction service."""

from __future__ import annotations

import pytest

from app.services.entity_extraction import extract_entities


class TestEmailExtraction:
    def test_extracts_email(self) -> None:
        entities = extract_entities("Contact john.doe@example.com for details.")
        types = {e.entity_type for e in entities}
        assert "email" in types

    def test_email_value_correct(self) -> None:
        entities = extract_entities("Send to alice@corp.org")
        emails = [e.value for e in entities if e.entity_type == "email"]
        assert "alice@corp.org" in emails

    def test_no_false_email(self) -> None:
        entities = extract_entities("Plain text with no email here.")
        assert not any(e.entity_type == "email" for e in entities)


class TestIPExtraction:
    def test_extracts_ipv4(self) -> None:
        entities = extract_entities("Server at 192.168.1.100 responded.")
        ips = [e.value for e in entities if e.entity_type == "ip_address"]
        assert "192.168.1.100" in ips

    def test_ignores_out_of_range(self) -> None:
        entities = extract_entities("Bad IP: 300.300.300.300 is invalid.")
        ips = [e.value for e in entities if e.entity_type == "ip_address"]
        assert "300.300.300.300" not in ips


class TestURLExtraction:
    def test_extracts_url(self) -> None:
        entities = extract_entities("Visit https://example.com/path?q=1 now.")
        urls = [e.value for e in entities if e.entity_type == "url"]
        assert any("example.com" in u for u in urls)


class TestHashExtraction:
    def test_extracts_sha256(self) -> None:
        sha = "a" * 64
        entities = extract_entities(f"File hash: {sha}")
        hashes = [e.value for e in entities if e.entity_type == "file_hash"]
        assert sha in hashes

    def test_extracts_md5(self) -> None:
        md5 = "d" * 32
        entities = extract_entities(f"MD5: {md5}")
        hashes = [e.value for e in entities if e.entity_type == "file_hash"]
        assert md5 in hashes


class TestCryptoExtraction:
    def test_extracts_ethereum(self) -> None:
        eth = "0x" + "a" * 40
        entities = extract_entities(f"Wallet: {eth}")
        wallets = [e.value for e in entities if e.entity_type == "crypto_wallet"]
        assert any(eth.lower() in w.lower() for w in wallets)


class TestDeduplication:
    def test_deduplicates_same_email(self) -> None:
        text = "Email test@test.com and test@test.com again."
        entities = extract_entities(text)
        emails = [e for e in entities if e.entity_type == "email"]
        assert len(emails) == 1

    def test_multiple_types(self) -> None:
        text = "Email: a@b.com, IP: 10.0.0.1, URL: https://x.com"
        entities = extract_entities(text)
        types = {e.entity_type for e in entities}
        assert "email" in types
        assert "ip_address" in types
        assert "url" in types
