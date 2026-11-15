"""Nodes HTTP layer: thin generic views (reads via selectors, writes via the serializer)."""

from django.db.models import QuerySet
from rest_framework import generics

from . import selectors
from .models import Node
from .repositories import NodeRepository
from .serializers import NodeSerializer


class NodeListCreateView(generics.ListCreateAPIView[Node]):
    """``GET /nodes`` lists nodes, ``POST /nodes`` creates one (one URL, two methods)."""

    serializer_class = NodeSerializer

    def get_queryset(self) -> QuerySet[Node]:
        """Ordered node queryset from the selector layer (deterministic pagination)."""
        return selectors.list_nodes()


class NodeDestroyView(generics.DestroyAPIView[Node]):
    """``DELETE /nodes/{id}``; its edges are removed by the database cascade."""

    serializer_class = NodeSerializer

    def get_queryset(self) -> QuerySet[Node]:
        """Nodes the id is looked up in."""
        return selectors.list_nodes()

    def perform_destroy(self, instance: Node) -> None:
        """Delete through the repository (a racing edge insert becomes a 409)."""
        NodeRepository().remove(instance)
