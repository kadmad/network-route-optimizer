"""Read-side queries for edges (the *selector* layer)."""

from collections.abc import Iterator
from decimal import Decimal

from django.db.models import QuerySet

from .models import Edge


def list_edges() -> QuerySet[Edge]:
    """Return edges with both endpoints joined, in a deterministic order.

    ``select_related`` => ONE joined query for the whole page; rendering ``source`` /
    ``destination`` names then costs no further queries (this is what prevents the classic
    N+1 on ``edge.source`` / ``edge.destination``).
    """
    return Edge.objects.select_related("source", "destination").order_by("id")


def iter_edge_rows() -> Iterator[tuple[str, str, Decimal]]:
    """Yield ``(source_name, destination_name, latency)`` for every edge in ONE query.

    ``values_list`` skips model instantiation (cheaper than building ``Edge`` / ``Node``
    objects) and the join resolves names in the database, so there is no per-edge lookup.
    """
    yield from Edge.objects.values_list("source__name", "destination__name", "latency")
