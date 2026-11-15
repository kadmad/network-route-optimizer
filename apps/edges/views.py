"""Edges HTTP layer: thin generic views (reads via selectors, writes via the serializer)."""

from django.db.models import QuerySet
from rest_framework import generics

from . import selectors
from .models import Edge
from .repositories import EdgeRepository
from .serializers import EdgeSerializer


class EdgeListCreateView(generics.ListCreateAPIView[Edge]):
    """``GET /edges`` lists edges, ``POST /edges`` creates one (one URL, two methods)."""

    serializer_class = EdgeSerializer

    def get_queryset(self) -> QuerySet[Edge]:
        """Joined, ordered edge queryset from the selector layer (no N+1)."""
        return selectors.list_edges()


class EdgeDestroyView(generics.DestroyAPIView[Edge]):
    """``DELETE /edges/{id}``."""

    serializer_class = EdgeSerializer

    def get_queryset(self) -> QuerySet[Edge]:
        """Edges the id is looked up in."""
        return selectors.list_edges()

    def perform_destroy(self, instance: Edge) -> None:
        """Delete through the repository."""
        EdgeRepository().remove(instance)
