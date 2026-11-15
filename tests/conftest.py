"""Shared fixtures for the integration and performance suites (HTTP-level tests)."""

from collections.abc import Callable
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from tests.factories import create_edge, create_node


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Throttle counters live in the cache; never let one test affect another."""
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    """DRF test client (JSON by default, see TEST_REQUEST_DEFAULT_FORMAT)."""
    return APIClient()


@pytest.fixture
def diamond() -> dict[str, Decimal]:
    """Topology used by most tests::

        A --12.5--> B --10.9--> D       cheapest A->D = 23.4 via B
        A --5.0---> C --30.0--> D       (alternative costs 35.0)

    Returns the edge latencies keyed ``"A-B"`` etc. for assertions.
    """
    latencies = {
        ("A", "B"): Decimal("12.5"),
        ("B", "D"): Decimal("10.9"),
        ("A", "C"): Decimal("5"),
        ("C", "D"): Decimal("30"),
    }
    for name in "ABCD":
        create_node(name=name)
    for (src, dst), latency in latencies.items():
        create_edge(source=src, destination=dst, latency=latency)
    return {f"{s}-{d}": v for (s, d), v in latencies.items()}


@pytest.fixture
def count_queries() -> Callable[[], CaptureQueriesContext]:
    """Factory returning a context manager that records the SQL statements it executed."""

    class _Capture(CaptureQueriesContext):
        @property
        def statements(self) -> list[str]:
            return [q["sql"] for q in self.captured_queries]

    return lambda: _Capture(connection)
