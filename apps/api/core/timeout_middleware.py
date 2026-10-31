"""Request timeout middleware for Step 7D."""

import asyncio
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from core.config import get_settings


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Enforce request timeout (excludes streaming endpoints)."""

    STREAMING_PATHS = {"/ws/", "/stream/", "/download/", "/docs", "/redoc", "/openapi"}

    async def dispatch(self, request: Request, call_next):
        """Apply timeout to non-streaming requests."""
        # Skip timeout for streaming/docs endpoints
        path = request.url.path
        if any(path.startswith(p) for p in self.STREAMING_PATHS):
            return await call_next(request)

        settings = get_settings()
        timeout = settings.request_timeout_seconds
        start = time.time()

        try:
            response = await asyncio.wait_for(call_next(request), timeout=timeout)
            return response
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            return JSONResponse(
                status_code=504,
                content={
                    "error": "Gateway Timeout",
                    "message": f"Request exceeded {timeout}s limit (elapsed {elapsed:.1f}s)",
                },
            )
