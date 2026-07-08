"""Custom ASGI middleware.

* ``RequestContextMiddleware`` assigns a request id and propagates an inbound
  correlation id (or generates one), binds both to the request context for
  logging, and echoes them back as response headers.
* ``SecurityHeadersMiddleware`` applies a conservative set of security headers
  to every response.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.context import correlation_id_var, request_id_var
from app.core.logging import get_logger

logger = get_logger("app.request")

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"

Handler = Callable[[Request], Awaitable[Response]]


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind request/correlation ids and emit a structured access log line."""

    async def dispatch(self, request: Request, call_next: Handler) -> Response:
        request_id = uuid.uuid4().hex
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or request_id

        request_token = request_id_var.set(request_id)
        correlation_token = correlation_id_var.set(correlation_id)
        start = time.perf_counter()

        try:
            response = await call_next(request)
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "%s %s",
                request.method,
                request.url.path,
                extra={"duration_ms": duration_ms, "path": request.url.path},
            )
            request_id_var.reset(request_token)
            correlation_id_var.reset(correlation_token)

        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply baseline security headers to every response."""

    _HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-XSS-Protection": "0",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        # Restrict resources to same-origin; allow inline styles for FastAPI docs.
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        ),
    }

    async def dispatch(self, request: Request, call_next: Handler) -> Response:
        response = await call_next(request)
        for header, value in self._HEADERS.items():
            response.headers.setdefault(header, value)
        # Hint clients to use bearer auth on 401 responses.
        if response.status_code == 401:
            response.headers.setdefault("WWW-Authenticate", "Bearer")
        return response
