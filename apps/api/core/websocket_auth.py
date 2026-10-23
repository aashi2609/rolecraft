"""WebSocket authentication helper."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from core.database import AsyncSessionLocal
from core.security import decode_access_token
from core.ws_manager import ws_manager
from models import User

logger = logging.getLogger(__name__)


async def _verify_user_active_and_version(user_id: UUID, token_version: int | None) -> bool:
    """Check the database to verify the user exists, is active, and token_version matches."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User.is_active, User.token_version).where(User.id == user_id)
        )
        row = result.first()
        if not row:
            return False
        is_active, db_version = row
        if not is_active:
            return False
        if token_version is not None and db_version != token_version:
            return False
        return True


async def authenticate_websocket_connection(
    websocket: WebSocket,
    timeout: float = 10.0,
) -> UUID | None:
    """Authenticate a WebSocket connection using JWT token."""
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
    except (ValueError, KeyError):
        await websocket.close(code=4003, reason="Invalid token")
        return None

    token_version = payload.get("token_version")

    # ── Check that the user still exists, is active, and token_version matches ──
    if not await _verify_user_active_and_version(user_id, token_version):
        await websocket.close(code=4004, reason="Account deactivated or token revoked")
        return None

    return user_id


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

