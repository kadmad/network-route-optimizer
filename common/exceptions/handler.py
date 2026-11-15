"""Single place that turns every exception into the API's error envelope.

Envelope::

    {"error": "<human readable summary>", "details": {...optional field errors...}}

This matches the contract in the exercise (``{"error": "..."}``) while still exposing
DRF's per-field validation messages under ``details``.
"""

import logging
from typing import Any

from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

from .base import DomainError

logger = logging.getLogger(__name__)


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """DRF ``EXCEPTION_HANDLER`` producing a uniform error body.

    Args:
        exc: The exception raised by the view.
        context: DRF context (view, request, args, kwargs).

    Returns:
        A ``Response``, or ``None`` for unexpected errors so Django's ``handler500``
        (JSON, see :func:`common.views.server_error`) logs and renders them.
    """
    if isinstance(exc, DomainError):
        logger.info("domain error: %s", exc.message, extra={"error_type": type(exc).__name__})
        return Response({"error": exc.message}, status=exc.status_code)

    response = drf_default_handler(exc, context)
    if response is None:
        return None  # unexpected -> handler500 logs the stack trace

    if isinstance(exc, drf_exceptions.ValidationError):
        response.data = {"error": "Validation failed.", "details": response.data}
    else:
        detail = response.data.get("detail", exc) if isinstance(response.data, dict) else exc
        response.data = {"error": str(detail)}
    return response
