"""Tiny helpers that put test data in the database through the ORM."""

from decimal import Decimal

from apps.edges.models import Edge
from apps.nodes.models import Node


def create_node(*, name: str) -> Node:
    """Insert a node."""
    return Node.objects.create(name=name)


def create_edge(*, source: str, destination: str, latency: Decimal) -> Edge:
    """Insert an edge between two existing nodes, given by name."""
    return Edge.objects.create(
        source=Node.objects.get(name=source),
        destination=Node.objects.get(name=destination),
        latency=latency,
    )
