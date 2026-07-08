"""Entity extraction service — regex-based + optional NLP.

Structured entities (email, IP, phone, URL, hash, crypto) use compiled regex
patterns and work on any text. NLP-based entities (PERSON, ORG, LOC) are
extracted via spaCy if the ``en_core_web_sm`` model is installed; otherwise
skipped with a warning emitted once at startup.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_SPACY_AVAILABLE: bool | None = None
_nlp = None  # lazy spaCy model handle

# ── Compiled regex patterns ────────────────────────────────────────────────────

_RE_EMAIL = re.compile(
    r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"
)
_RE_PHONE = re.compile(
    r"""(?:
        \+?\d[\d\s\-().]{7,}\d   |  # international / formatted
        \b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b  # US style
    )""",
    re.VERBOSE,
)
_RE_IP = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)
_RE_URL = re.compile(
    r"https?://[^\s\"'<>]+",
    re.IGNORECASE,
)
_RE_DOMAIN = re.compile(
    r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)"
    r"+[a-zA-Z]{2,}\b"
)
_RE_MD5 = re.compile(r"\b[0-9a-fA-F]{32}\b")
_RE_SHA1 = re.compile(r"\b[0-9a-fA-F]{40}\b")
_RE_SHA256 = re.compile(r"\b[0-9a-fA-F]{64}\b")
_RE_BITCOIN = re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b")
_RE_ETHEREUM = re.compile(r"\b0x[0-9a-fA-F]{40}\b", re.IGNORECASE)
_RE_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}\b")
_RE_VEHICLE = re.compile(r"\b[A-Z]{2}\s?\d{1,2}\s?[A-Z]{1,3}\s?\d{1,4}\b")  # Indian format
# IPv6 (simplified)
_RE_IPV6 = re.compile(
    r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
    r"|\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b"
)


@dataclass
class ExtractedEntity:
    entity_type: str
    value: str
    normalized_value: str
    confidence: float
    context: str | None
    source: str


def extract_entities(text: str) -> list[ExtractedEntity]:
    """Extract all structured entities from *text*. Always safe to call."""
    results: list[ExtractedEntity] = []

    def _ctx(m: re.Match[str]) -> str:
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 40)
        return text[start:end].replace("\n", " ")

    def _add(etype: str, m: re.Match[str], conf: float = 0.95, norm: str | None = None) -> None:
        val = m.group(0).strip()
        results.append(ExtractedEntity(
            entity_type=etype,
            value=val,
            normalized_value=(norm or val).lower(),
            confidence=conf,
            context=_ctx(m),
            source="regex",
        ))

    for m in _RE_EMAIL.finditer(text):
        _add("email", m)

    # IPs before domain so IPs aren't double-counted as domains
    ip_spans: set[tuple[int, int]] = set()
    for m in _RE_IP.finditer(text):
        ip_spans.add((m.start(), m.end()))
        _add("ip_address", m)
    for m in _RE_IPV6.finditer(text):
        _add("ip_address", m, 0.9)

    for m in _RE_URL.finditer(text):
        _add("url", m)

    for m in _RE_PHONE.finditer(text):
        val = re.sub(r"\s+", "", m.group(0))
        if len(val) >= 7:
            results.append(ExtractedEntity(
                entity_type="phone",
                value=m.group(0).strip(),
                normalized_value=re.sub(r"[^\d+]", "", m.group(0)),
                confidence=0.8,
                context=_ctx(m),
                source="regex",
            ))

    for m in _RE_SHA256.finditer(text):
        _add("file_hash", m, 0.99)

    for m in _RE_SHA1.finditer(text):
        _add("file_hash", m, 0.95)

    for m in _RE_MD5.finditer(text):
        _add("file_hash", m, 0.85)

    for m in _RE_BITCOIN.finditer(text):
        _add("crypto_wallet", m)

    for m in _RE_ETHEREUM.finditer(text):
        _add("crypto_wallet", m)

    for m in _RE_IBAN.finditer(text):
        _add("bank_account", m, 0.9)

    for m in _RE_VEHICLE.finditer(text):
        _add("vehicle_number", m, 0.7)

    # Domain (only if not part of an email or URL already matched)
    email_spans = {(m.start(), m.end()) for m in _RE_EMAIL.finditer(text)}
    url_spans = {(m.start(), m.end()) for m in _RE_URL.finditer(text)}
    for m in _RE_DOMAIN.finditer(text):
        if not _overlaps(m.start(), m.end(), email_spans | url_spans | ip_spans):
            _add("domain", m, 0.75)

    # Optional NLP entities
    nlp_entities = _extract_nlp_entities(text)
    results.extend(nlp_entities)

    # Deduplicate by (type, normalized_value)
    seen: set[tuple[str, str]] = set()
    deduped: list[ExtractedEntity] = []
    for e in results:
        key = (e.entity_type, e.normalized_value[:100])
        if key not in seen:
            seen.add(key)
            deduped.append(e)

    return deduped


def _overlaps(start: int, end: int, spans: set[tuple[int, int]]) -> bool:
    for s, e in spans:
        if start < e and end > s:
            return True
    return False


def _load_spacy() -> bool:
    global _SPACY_AVAILABLE, _nlp
    if _SPACY_AVAILABLE is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
            _SPACY_AVAILABLE = True
        except Exception:
            _SPACY_AVAILABLE = False
            logger.info("spaCy en_core_web_sm not available — NLP entity extraction skipped.")
    return bool(_SPACY_AVAILABLE)


_SPACY_TYPE_MAP = {
    "PERSON": "person",
    "ORG": "organization",
    "GPE": "city",
    "LOC": "location",
    "FAC": "location",
    "NORP": "organization",
    "PRODUCT": "device",
    "LAW": "unknown",
    "DATE": "date",
    "TIME": "date",
}


def _extract_nlp_entities(text: str) -> list[ExtractedEntity]:
    if not _load_spacy() or _nlp is None:
        return []
    try:
        # Process in chunks to avoid memory issues
        chunk_size = 100_000
        results: list[ExtractedEntity] = []
        for i in range(0, min(len(text), 300_000), chunk_size):
            chunk = text[i : i + chunk_size]
            doc = _nlp(chunk)
            for ent in doc.ents:
                etype = _SPACY_TYPE_MAP.get(ent.label_)
                if not etype:
                    continue
                start = i + ent.start_char
                end = i + ent.end_char
                ctx_start = max(0, start - 40)
                ctx_end = min(len(text), end + 40)
                results.append(ExtractedEntity(
                    entity_type=etype,
                    value=ent.text.strip(),
                    normalized_value=ent.text.strip().lower(),
                    confidence=0.85,
                    context=text[ctx_start:ctx_end].replace("\n", " "),
                    source="nlp",
                ))
        return results
    except Exception as exc:
        logger.warning("spaCy NLP extraction error: %s", exc)
        return []
