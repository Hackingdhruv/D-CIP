"""OpenSearch client factory.

A single client is shared across the process for full-text and (later) semantic
search. Index definitions are created in a later milestone; this module only
configures the connection.
"""

from __future__ import annotations

from opensearchpy import OpenSearch

from app.core.config import settings

_client: OpenSearch | None = None


def get_client() -> OpenSearch:
    """Return the shared OpenSearch client, creating it on first use."""
    global _client
    if _client is None:
        _client = OpenSearch(
            hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
            http_auth=(settings.opensearch_user, settings.opensearch_password),
            use_ssl=settings.opensearch_use_ssl,
            verify_certs=settings.opensearch_verify_certs,
            ssl_show_warn=False,
        )
    return _client


def check_connection() -> None:
    """Ping the OpenSearch cluster to verify connectivity."""
    if not get_client().ping():
        raise ConnectionError("OpenSearch ping returned a falsy response.")
