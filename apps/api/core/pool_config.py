"""Database connection pool configuration."""

import os
import sys
from dataclasses import dataclass


@dataclass
class PoolSettings:
    """Connection pool settings based on environment."""

    pool_size: int
    max_overflow: int
    pool_timeout: float
    pool_recycle: float
    pool_pre_ping: bool
    statement_cache_size: int

    @staticmethod
    def for_environment() -> "PoolSettings":
        """Auto-detect pool settings based on environment and database URL."""
        db_url = os.getenv("DATABASE_URL", "")
        is_test = "pytest" in sys.modules or os.getenv("TEST_DATABASE_URL")
        is_neon_pooler = "-pooler." in db_url

        if is_test:
            return PoolSettings(
                pool_size=0,
                max_overflow=0,
                pool_timeout=30.0,
                pool_recycle=3600.0,
                pool_pre_ping=False,
                statement_cache_size=0,
            )

        if is_neon_pooler:
            return PoolSettings(
                pool_size=5,
                max_overflow=10,
                pool_timeout=30.0,
                pool_recycle=3600.0,
                pool_pre_ping=True,
                statement_cache_size=0,  # PgBouncer doesn't support prepared statements
            )

        # Direct PostgreSQL
        return PoolSettings(
            pool_size=10,
            max_overflow=5,
            pool_timeout=30.0,
            pool_recycle=3600.0,
            pool_pre_ping=True,
            statement_cache_size=10,
        )
