"""Tests for the version endpoint."""

from __future__ import annotations


def test_version_metadata(client) -> None:
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert body["name"]
    assert body["version"]
    assert body["environment"] in {"development", "testing", "production"}
