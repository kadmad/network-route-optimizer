"""Settings used by the automated test-suite (pytest-django).

Needs a reachable PostgreSQL and the usual environment (``DJANGO_SECRET_KEY``, ``DATABASE_URL``),
from ``.env`` (``make env``) or the real environment.
"""

from .base import *
from .base import REST_FRAMEWORK

# DRF's test client defaults to multipart; the API only accepts JSON.
# Throttling is effectively disabled; throttle tests patch the rates explicitly.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_THROTTLE_RATES": {"anon": "100000/min", "routes": "100000/min"},
}
