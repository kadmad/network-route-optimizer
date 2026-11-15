"""HTTP middleware: request-id propagation and one structured access-log line per request."""

import logging
import re
import time
import uuid
from collections.abc import Callable
from urllib.parse import quote

from django.http import HttpRequest, HttpResponse

from .logging import request_id_var

logger = logging.getLogger("common.access")

REQUEST_ID_HEADER = "X-Request-ID"
# Polled every few seconds by load balancers / Docker: logging it would only add noise.
_UNLOGGED_PATHS = frozenset({"/health"})
# Only accept sane inbound ids: prevents log injection / unbounded log field size.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestContextMiddleware:
    """Assign a request id, time the request and emit an access log line.

    * Reuses a client/proxy supplied ``X-Request-ID`` when it is well-formed, else generates one.
    * Echoes the id on the response so callers can quote it in bug reports.
    * Logs method, path, status and latency. Query strings and bodies are *not* logged
      (they may carry sensitive data). The path is percent-encoded so a newline in a URL
      cannot forge a log line. ``/health`` is not logged.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Store the next handler in the middleware chain."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process one request."""
        inbound = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = inbound if _VALID_REQUEST_ID.match(inbound) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500  # Django converts view exceptions to 500 responses below us
        try:
            response = self.get_response(request)
            status_code = response.status_code
        finally:
            if request.path not in _UNLOGGED_PATHS:
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                path = quote(request.path)
                logger.info(
                    "%s %s -> %s (%.2f ms)",
                    request.method,
                    path,
                    status_code,
                    duration_ms,
                    extra={
                        "method": request.method,
                        "path": path,
                        "status": status_code,
                        "duration_ms": duration_ms,
                    },
                )
            request_id_var.reset(token)
        response[REQUEST_ID_HEADER] = request_id
        return response
