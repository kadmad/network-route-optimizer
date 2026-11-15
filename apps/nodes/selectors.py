"""Read-side queries for nodes (the *selector* layer).

Selectors only read. They return querysets or plain values, never mutate state, and are the one
place where a node ``SELECT`` is written, so other apps (edges, routes) can reuse them without
importing the ``Node`` model or duplicating queries.
"""

from collections.abc import Iterable

from django.db.models import QuerySet

from .models import Node


def list_nodes() -> QuerySet[Node]:
    """Return all nodes in a deterministic order (stable pagination)."""
    return Node.objects.order_by("id")


def nodes_by_name(names: Iterable[str]) -> dict[str, Node]:
    """Resolve several names with **one** ``WHERE name IN (...)`` query (unique-index scan)."""
    return {node.name: node for node in Node.objects.filter(name__in=set(names))}


def existing_node_names(names: Iterable[str]) -> set[str]:
    """Return the subset of ``names`` that exist, fetching the name column only."""
    return set(Node.objects.filter(name__in=set(names)).values_list("name", flat=True))
