"""Request-correlated logging primitives.

A ``ContextVar`` carries the request id across the call stack without passing it around
explicitly. :class:`RequestContextFilter` copies it
onto every ``LogRecord`` so any logger - ours, Django's, third-party - can emit it.
"""

import logging
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestContextFilter(logging.Filter):
    """Inject ``request_id`` into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach the current request id; never drops records."""
        record.request_id = request_id_var.get()
        return True
