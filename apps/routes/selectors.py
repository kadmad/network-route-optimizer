"""Read-side queries for routes (the *selector* layer)."""

from collections import defaultdict
from decimal import Decimal

from django.db.models import QuerySet

from apps.edges.selectors import iter_edge_rows

from .dijkstra import Graph
from .models import RouteQuery


def list_route_history() -> QuerySet[RouteQuery]:
    """Return the history, oldest first (default ordering ``created_at, id``).

    A single table with no foreign keys, so listing never needs a join.
    """
    return RouteQuery.objects.all()


def load_graph() -> Graph:
    """Load every edge in a single joined query and fold it into an adjacency list."""
    adjacency: dict[str, list[tuple[str, Decimal]]] = defaultdict(list)
    for source, destination, latency in iter_edge_rows():
        adjacency[source].append((destination, latency))
    return adjacency
