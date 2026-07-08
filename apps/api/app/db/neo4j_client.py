"""Neo4j driver factory.

The official driver manages its own connection pool, so a single ``Driver`` is
shared across the process. The relationship-graph schema is defined in a later
milestone; this module only establishes connectivity.
"""

from __future__ import annotations

from neo4j import Driver, GraphDatabase

from app.core.config import settings

_driver: Driver | None = None


def get_driver() -> Driver:
    """Return the shared Neo4j driver, creating it on first use."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


def check_connection() -> None:
    """Verify connectivity to the Neo4j server."""
    get_driver().verify_connectivity()


def close_driver() -> None:
    """Close the driver on shutdown."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
