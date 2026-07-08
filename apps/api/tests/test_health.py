"""Tests for the health and readiness endpoints."""

from __future__ import annotations

import app.api.v1.routes.health as health_module


def test_liveness_is_ok(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {}


def test_readiness_reports_components(client, monkeypatch) -> None:
    # Make every component probe succeed so the test is hermetic.
    monkeypatch.setattr(health_module, "_CHECKS", {"postgres": lambda: None})
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["checks"]["postgres"]["status"] == "ok"


def test_readiness_degrades_when_a_component_fails(client, monkeypatch) -> None:
    def _boom() -> None:
        raise ConnectionError("down")

    monkeypatch.setattr(health_module, "_CHECKS", {"redis": _boom})
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["redis"]["status"] == "error"


def test_response_carries_request_id_header(client) -> None:
    response = client.get("/api/v1/health")
    assert response.headers.get("X-Request-ID")
