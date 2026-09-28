"""Shared pytest fixtures and environment guards."""

from __future__ import annotations

import sys

import pytest

# Fail loudly if run on the wrong interpreter.
if sys.version_info[:2] < (3, 10):
    raise RuntimeError(
        f"Wrong Python interpreter: {sys.version.split()[0]} "
        f"({sys.executable}). Expected Python >= 3.10."
    )


@pytest.fixture(scope="session", autouse=True)
def _assert_python_310() -> None:
    assert sys.version_info[:2] >= (
        3,
        10,
    ), f"Tests require Python >= 3.10, got {sys.version} from {sys.executable}"
