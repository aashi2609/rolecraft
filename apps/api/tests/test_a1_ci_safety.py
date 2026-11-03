"""A1: Test that CI catches test failures (temporary verification test)"""
import pytest


def test_ci_fails_on_deliberate_failure():
    """This test MUST fail to verify CI properly reports failure."""
    assert False, "Intentional failure to verify CI error handling works"
