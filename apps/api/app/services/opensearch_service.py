"""OpenSearch integration — full-text and semantic search over evidence.

Index name: ``dcip_evidence``

Gracefully no-ops when OpenSearch is not configured or unreachable.
"""

from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)

_INDEX = "dcip_evidence"

_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "evidence_id": {"type": "keyword"},
            "case_id": {"type": "keyword"},
            "filename": {"type": "text", "analyzer": "standard"},
            "mime_type": {"type": "keyword"},
            "status": {"type": "keyword"},
            "text_content": {"type": "text", "analyzer": "standard"},
            "entities": {"type": "text"},
            "keywords": {"type": "keyword"},
            "language": {"type": "keyword"},
            "created_at": {"type": "date"},
        }
    }
}


def _client():
    try:
        from app.core.config import settings
        if not settings.opensearch_enabled:
            return None
        from app.db.opensearch_client import get_client
        return get_client()
    except Exception:
        return None


def ensure_index() -> bool:
    """Create the evidence index if it doesn't exist. Returns True on success."""
    client = _client()
    if not client:
        return False
    try:
        if not client.indices.exists(index=_INDEX):
            client.indices.create(index=_INDEX, body=_INDEX_MAPPING)
            logger.info("Created OpenSearch index: %s", _INDEX)
        return True
    except Exception as exc:
        logger.warning("OpenSearch index creation failed: %s", exc)
        return False


def index_evidence(
    evidence_id: uuid.UUID | str,
    case_id: uuid.UUID | str,
    filename: str,
    mime_type: str,
    status: str,
    text_content: str | None,
    entities: list[str],
    keywords: list[str],
    language: str | None,
    created_at: str,
) -> bool:
    """Index or update an evidence document. Returns True on success."""
    client = _client()
    if not client:
        return False
    try:
        ensure_index()
        doc = {
            "evidence_id": str(evidence_id),
            "case_id": str(case_id),
            "filename": filename,
            "mime_type": mime_type,
            "status": status,
            "text_content": (text_content or "")[:50_000],
            "entities": entities[:500],
            "keywords": keywords[:100],
            "language": language,
            "created_at": created_at,
        }
        client.index(index=_INDEX, id=str(evidence_id), body=doc, refresh="wait_for")
        return True
    except Exception as exc:
        logger.warning("OpenSearch indexing failed for %s: %s", evidence_id, exc)
        return False


def search(
    query: str,
    case_id: str | None = None,
    size: int = 20,
) -> list[dict]:
    """Full-text search within evidence. Optionally scoped to a single case."""
    client = _client()
    if not client:
        return []
    try:
        must: list[dict] = [
            {"multi_match": {
                "query": query,
                "fields": ["filename^2", "text_content", "entities", "keywords"],
            }}
        ]
        if case_id:
            must.append({"term": {"case_id": case_id}})
        result = client.search(
            index=_INDEX,
            body={
                "query": {"bool": {"must": must}},
                "highlight": {"fields": {"text_content": {"fragment_size": 200, "number_of_fragments": 3}}},
                "size": size,
            },
        )
        hits = result.get("hits", {}).get("hits", [])
        return [
            {
                "evidence_id": h["_source"].get("evidence_id"),
                "filename": h["_source"].get("filename"),
                "score": h.get("_score", 0),
                "highlights": h.get("highlight", {}).get("text_content", []),
            }
            for h in hits
        ]
    except Exception as exc:
        logger.warning("OpenSearch search failed: %s", exc)
        return []


def delete_evidence(evidence_id: str | uuid.UUID) -> None:
    """Remove an evidence document from the index."""
    client = _client()
    if not client:
        return
    try:
        client.delete(index=_INDEX, id=str(evidence_id), ignore=[404])
    except Exception as exc:
        logger.debug("OpenSearch delete skipped: %s", exc)
