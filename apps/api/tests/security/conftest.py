"""Shared TestClient fixture — dispose async engine after each test to avoid loop leaks."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
