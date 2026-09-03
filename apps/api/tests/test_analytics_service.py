"""Unit tests for analytics_service cache."""
from __future__ import annotations

from uuid import uuid4

from services import analytics_service


def test_analytics_cache_round_trip() -> None:
    analytics_service._cache.clear()
    user_id = uuid4()
    payload = {"period_days": 7, "total_applications": 3}

    assert analytics_service._get_cached(user_id, "candidate", 7) is None
    analytics_service._set_cached(user_id, "candidate", 7, payload)
    assert analytics_service._get_cached(user_id, "candidate", 7) == payload
    assert analytics_service._get_cached(user_id, "candidate", 30) is None
