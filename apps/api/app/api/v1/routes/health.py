"""Health and readiness endpoints.

* ``/health`` is a cheap liveness probe — it returns ``ok`` if the process is
  up, with no external calls.
* ``/health/ready`` is a readiness probe that checks every backing service and
  reports per-component status, returning 503 if any component is unreachable.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.db import neo4j_client, opensearch_client, redis_client, session
from app.schemas.health import ComponentCheck, HealthStatus

router = APIRouter(tags=["health"])

_CHECKS = {
    "postgres": session.check_connection,
    "redis": redis_client.check_connection,
    "neo4j": neo4j_client.check_connection,
    "opensearch": opensearch_client.check_connection,
}


@router.get("/health", response_model=HealthStatus, summary="Liveness probe")
def health() -> HealthStatus:
    return HealthStatus(status="ok", checks={})


@router.get("/health/ready", response_model=HealthStatus, summary="Readiness probe")
def readiness(response: Response) -> HealthStatus:
    checks: dict[str, ComponentCheck] = {}
    healthy = True

    for name, probe in _CHECKS.items():
        try:
            probe()
            checks[name] = ComponentCheck(status="ok")
        except Exception as exc:  # noqa: BLE001 - report, don't crash the probe
            healthy = False
            checks[name] = ComponentCheck(status="error", detail=str(exc))

    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthStatus(status="ok" if healthy else "degraded", checks=checks)
