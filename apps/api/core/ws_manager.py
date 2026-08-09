"""In-memory WebSocket connection manager for real-time application status updates.

Manages active WebSocket connections keyed by user_id. When an application
status changes, the manager broadcasts the event to the relevant candidate.
Thread-safe for single-process deployments (uvicorn with --workers 1 or --reload).
"""

import asyncio
import logging
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Track active WebSocket connections per user and broadcast events."""

    def __init__(self) -> None:
        # Maps user_id -> set of active WebSocket connections (supports multiple tabs)
        self._connections: dict[UUID, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        """Register a WebSocket connection for a user."""
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = set()
            self._connections[user_id].add(websocket)
        logger.info("WS connected: user=%s  (total=%d)", user_id, len(self._connections[user_id]))

    async def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        """Remove a WebSocket connection for a user."""
        async with self._lock:
            conns = self._connections.get(user_id)
            if conns:
                conns.discard(websocket)
                if not conns:
                    del self._connections[user_id]
        logger.info("WS disconnected: user=%s", user_id)

    async def send_to_user(self, user_id: UUID, event: dict) -> None:
        """Send a JSON event to all active connections for a given user."""
        async with self._lock:
            conns = self._connections.get(user_id)
            if not conns:
                return
            # Copy to avoid mutation during iteration
            targets = list(conns)

        stale: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(event)
            except Exception:
                stale.append(ws)

        # Clean up broken connections
        if stale:
            async with self._lock:
                conns = self._connections.get(user_id)
                if conns:
                    for ws in stale:
                        conns.discard(ws)
                    if not conns:
                        del self._connections[user_id]

    @property
    def active_count(self) -> int:
        """Total number of active WebSocket connections across all users."""
        return sum(len(v) for v in self._connections.values())


# Singleton instance used across the application
ws_manager = ConnectionManager()
