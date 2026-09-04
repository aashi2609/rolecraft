"""WebSocket authentication helper."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from core.security import decode_access_token
from core.ws_manager import ws_manager

logger = logging.getLogger(__name__)


async def authenticate_websocket_connection(
    websocket: WebSocket,
    timeout: float = 10.0,
) -> UUID | None:
    """Authenticate a WebSocket connection using JWT token.

    The client must send a JSON message with {"token": "<jwt>"} immediately
    after connecting. Returns the user_id if authentication succeeds, None otherwise.

    Args:
        websocket: The WebSocket connection to authenticate
        timeout: Maximum time to wait for auth token (default 10 seconds)

    Returns:
        The authenticated user's UUID, or None if authentication fails
    """
    await websocket.accept()

    # Wait for the client to send their auth token
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_json(), timeout=timeout)
    except Exception:
        await websocket.close(code=4001, reason="Auth timeout")
        return None

    token = auth_msg.get("token")
    if not token:
        await websocket.close(code=4002, reason="Missing token")
        return None

    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
        return user_id
    except (ValueError, KeyError):
        await websocket.close(code=4003, reason="Invalid token")
        return None


async def handle_websocket_lifecycle(
    websocket: WebSocket,
    user_id: UUID,
) -> None:
    """Handle the lifecycle of an authenticated WebSocket connection.

    Registers the connection, keeps it alive by responding to pings,
    and cleans up on disconnect.

    Args:
        websocket: The authenticated WebSocket connection
        user_id: The authenticated user's UUID
    """
    await ws_manager.connect(user_id, websocket)
    try:
        # Keep the connection alive — listen for pings or client messages
        while True:
            data = await websocket.receive_json()
            # Handle client-side ping to keep the connection alive
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WS error for user=%s: %s", user_id, exc)
    finally:
        await ws_manager.disconnect(user_id, websocket)
