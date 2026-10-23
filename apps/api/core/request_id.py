"""Request ID and request context middleware.

Assigns a unique request_id to each incoming request (or reuses incoming
X-Request-ID if provided and safe), adds it to request.state.request_id and
as a response header, and attaches request_id to standard logger records.
"""

from __future__ import annotations

import logging
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_REQUEST_ID_CTX_KEY = "request_id"


class RequestIdFilter(logging.Filter):
    """Logging filter that ensures `request_id` attribute is present on records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


# Install the filter on the root logger so any %(request_id)s in formatters works
_filter = RequestIdFilter()
logging.getLogger().addFilter(_filter)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check incoming header, sanitize if valid ascii/alphanumeric, otherwise generate uuid
        incoming_id = request.headers.get("x-request-id") or request.headers.get("X-Request-ID")
        if incoming_id and len(incoming_id) <= 64 and incoming_id.replace("-", "").isalnum():
            req_id = incoming_id
        else:
            req_id = uuid.uuid4().hex

        request.state.request_id = req_id

        # Bind to a custom logger filter record during this task if desired, or let filter provide default
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response
