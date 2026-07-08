"""Request-scoped context.

Holds the request id and correlation id for the lifetime of a single request
using :mod:`contextvars`, so any log record emitted while handling the request
can be tagged without threading the ids through every function signature.
"""

from __future__ import annotations

from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_request_id() -> str | None:
    return request_id_var.get()


def get_correlation_id() -> str | None:
    return correlation_id_var.get()
