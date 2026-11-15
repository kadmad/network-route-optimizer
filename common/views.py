"""Operational endpoints: health check and JSON 404/500 handlers."""

from django.http import HttpRequest, JsonResponse
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """``GET /health`` - the process is up. Deliberately does not touch the database."""

    throttle_classes = ()  # health checks are polled frequently

    def get(self, request: Request) -> Response:
        """Return a static OK."""
        return Response({"status": "ok"})


def not_found(request: HttpRequest, exception: Exception) -> JsonResponse:
    """Django ``handler404``: JSON instead of the HTML debug page."""
    return JsonResponse({"error": "Not found."}, status=404)


def server_error(request: HttpRequest) -> JsonResponse:
    """Django ``handler500``: JSON body, never leaks internals to the client.

    The stack trace is already logged (ERROR, with request id) by Django's ``django.request``
    logger before this handler runs, so it is not logged a second time here.
    """
    return JsonResponse({"error": "Internal server error."}, status=500)
