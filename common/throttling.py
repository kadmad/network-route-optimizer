"""Rate limiting.

The API is open (no authentication), so every client is anonymous and DRF's built-in
``AnonRateThrottle`` (keyed on the client IP, rate ``anon`` in settings) is the global limit.
Only the CPU-heavy shortest-path endpoint gets an additional, stricter limit.

NOTE: counters live in Django's cache. The default per-process ``LocMemCache`` is fine for one
worker; use a shared cache (Redis/Memcached) in multi-worker production deployments.
"""

from rest_framework.throttling import AnonRateThrottle


class RouteComputationThrottle(AnonRateThrottle):
    """Stricter per-IP limit for ``POST /routes/shortest`` (rate ``routes`` in settings)."""

    scope = "routes"
