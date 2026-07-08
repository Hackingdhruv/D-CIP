"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """A TestClient bound to a freshly constructed app instance."""
    with TestClient(create_app()) as test_client:
        yield test_client
