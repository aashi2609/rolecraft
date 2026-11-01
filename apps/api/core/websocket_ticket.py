"""
WebSocket authentication ticket system for Step 7F.

Tickets are short-lived, one-time use tokens issued by authenticated REST calls.
Never expose tokens in query strings (ends up in logs/proxies).
"""

import secrets
import time
from typing import Optional

from core.websocket_config import WS_AUTH_TIMEOUT_SECONDS


class TicketStore:
    """Simple in-memory ticket store (single worker only)."""

    def __init__(self):
        self._tickets: dict[
            str, dict
        ] = {}  # ticket -> {user_id, issued_at, expires_at}

    def issue(self, user_id: str) -> str:
        """Issue a one-time WebSocket ticket (valid for 5 seconds)."""
        ticket = secrets.token_urlsafe(32)
        now = time.time()
        self._tickets[ticket] = {
            "user_id": user_id,
            "issued_at": now,
            "expires_at": now + WS_AUTH_TIMEOUT_SECONDS,
        }
        return ticket

    def validate(self, ticket: str) -> Optional[str]:
        """
        Validate and consume ticket. Returns user_id if valid, None otherwise.
        Ticket is deleted after validation (one-time use).
        """
        if ticket not in self._tickets:
            return None

        data = self._tickets.pop(ticket)
        now = time.time()

        # Check expiry
        if now > data["expires_at"]:
            return None

        return data["user_id"]

    def cleanup_expired(self):
        """Remove expired tickets (call periodically or on demand)."""
        now = time.time()
        expired = [t for t, d in self._tickets.items() if now > d["expires_at"]]
        for ticket in expired:
            del self._tickets[ticket]


# Global ticket store (single worker only)
_ticket_store = TicketStore()


def issue_websocket_ticket(user_id: str) -> str:
    """
    Issue a WebSocket authentication ticket via REST endpoint.

    Example:
        POST /auth/ws-ticket
        Authorization: Bearer <jwt_token>

        Response:
        {
            "ticket": "token123...",
            "expires_in_seconds": 5
        }
    """
    return _ticket_store.issue(user_id)


def validate_websocket_ticket(ticket: str) -> Optional[str]:
    """
    Validate WebSocket ticket on connection.
    Returns user_id if valid, None if invalid or expired.
    """
    user_id = _ticket_store.validate(ticket)
    if user_id is None:
        _ticket_store.cleanup_expired()
    return user_id
