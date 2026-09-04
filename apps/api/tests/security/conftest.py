"""Shared TestClient fixture — dispose async engine after each test to avoid loop leaks."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from core.database import engine
from main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(engine.dispose())
    finally:
        loop.close()
