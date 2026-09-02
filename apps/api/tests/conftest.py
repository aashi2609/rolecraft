"""Shared pytest fixtures and environment guards."""

from __future__ import annotations

import sys

import pytest

# Fail loudly if run on the wrong interpreter (must be Python 3.13.x).
if sys.version_info[:2] != (3, 13):
    raise RuntimeError(
        f"Wrong Python interpreter: {sys.version.split()[0]} "
        f"({sys.executable}). Activate apps/api/.venv313 and re-run "
        f"(expected Python 3.13.x)."
    )


@pytest.fixture(scope="session", autouse=True)
def _assert_python_313() -> None:
    assert sys.version_info[:2] == (3, 13), (
        f"Tests require Python 3.13.x, got {sys.version} from {sys.executable}"
    )
