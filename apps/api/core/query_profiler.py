"""SQLAlchemy query profiling for performance measurement.

Tracks query count and database time per request.
- Enabled in test and debug mode only
- Off in production

Usage:
1. Enable in conftest.py or main.py via install_profiler()
2. Pytest fixture: get profiler state from request.state.db_profiler
3. Response headers: X-DB-Queries, X-DB-Time-Ms
"""

import time
import logging
from contextvars import ContextVar
from typing import Optional

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

logger = logging.getLogger(__name__)

# Context variable to store profiler state per request/task
_profiler_context: ContextVar[Optional["RequestProfiler"]] = ContextVar(
    "db_profiler", default=None
)


class RequestProfiler:
    """Tracks database queries and timing for a single request."""

    def __init__(self):
        self.query_count = 0
        self.db_time_ms = 0.0
        self.queries = []  # List of (statement, duration_ms, params)
        self.enabled = True

    def add_query(self, statement: str, duration_ms: float, params: dict = None):
        """Record a query."""
        if not self.enabled:
            return
        self.query_count += 1
        self.db_time_ms += duration_ms
        self.queries.append(
            {
                "statement": statement[:200],  # Truncate long statements
                "duration_ms": duration_ms,
                "params": params or {},
            }
        )

    def reset(self):
        """Reset counters."""
        self.query_count = 0
        self.db_time_ms = 0.0
        self.queries = []

    def to_headers(self) -> dict:
        """Convert to response headers."""
        return {
            "X-DB-Queries": str(self.query_count),
            "X-DB-Time-Ms": f"{self.db_time_ms:.2f}",
        }

    def __repr__(self) -> str:
        return (
            f"RequestProfiler(queries={self.query_count}, "
            f"db_time_ms={self.db_time_ms:.2f})"
        )


def get_current_profiler() -> Optional[RequestProfiler]:
    """Get the current request's profiler."""
    return _profiler_context.get()


def set_current_profiler(profiler: Optional[RequestProfiler]):
    """Set the profiler for the current context."""
    _profiler_context.set(profiler)


def install_profiler(engine: Engine, enabled: bool = True) -> None:
    """Install profiling listeners on a SQLAlchemy engine.

    Args:
        engine: SQLAlchemy AsyncEngine instance
        enabled: Whether to enable profiling (default: True)
    """
    if not enabled:
        logger.info("Query profiler disabled")
        return

    logger.info("Installing query profiler")

    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Called before each SQL statement is executed."""
        conn.info.setdefault("query_start_time", []).append(time.time())
        # Log statement at debug level
        logger.debug(f"SQL: {statement[:100]}")

    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Called after each SQL statement is executed."""
        try:
            # Get start time
            start_times = conn.info.get("query_start_time", [])
            if not start_times:
                return

            start_time = start_times.pop()
            duration_ms = (time.time() - start_time) * 1000

            # Record to current profiler
            profiler = get_current_profiler()
            if profiler:
                # Sanitize statement for logging (remove params)
                safe_statement = statement.replace("%s", "?")[:200]
                profiler.add_query(safe_statement, duration_ms, parameters)

            # Log slow queries (> 100ms)
            if duration_ms > 100:
                logger.warning(
                    f"Slow query ({duration_ms:.1f}ms): {statement[:80]}..."
                )

        except Exception as e:
            logger.debug(f"Error in query profiler: {e}")


class ProfilerMiddleware:
    """ASGI middleware to attach profiler to each request."""

    def __init__(self, app, enabled: bool = True):
        self.app = app
        self.enabled = enabled

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not self.enabled:
            await self.app(scope, receive, send)
            return

        # Create and set profiler for this request
        profiler = RequestProfiler()
        token = _profiler_context.set(profiler)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                # Add profiler headers
                headers.extend(
                    [
                        (k.encode(), v.encode())
                        for k, v in profiler.to_headers().items()
                    ]
                )
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            # Clean up context
            _profiler_context.reset(token)
