"""Routes HTTP layer."""

from django.db.models import QuerySet
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from common.throttling import RouteComputationThrottle

from . import selectors
from .filters import RouteQueryFilter
from .models import RouteQuery
from .serializers import (
    RouteQuerySerializer,
    ShortestRouteRequestSerializer,
    ShortestRouteResponseSerializer,
)
from .services import find_shortest_route


class ShortestRouteView(APIView):
    """``POST /routes/shortest`` - compute (and record) the lowest-latency path."""

    throttle_classes = [AnonRateThrottle, RouteComputationThrottle]

    def post(self, request: Request) -> Response:
        """Validate input, delegate to the service function, serialise the result."""
        serializer = ShortestRouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = find_shortest_route(**serializer.validated_data)
        body = ShortestRouteResponseSerializer(
            {"total_latency": result.total_latency, "path": list(result.path)}
        )
        return Response(body.data, status=status.HTTP_200_OK)


class RouteHistoryView(generics.ListAPIView[RouteQuery]):
    """``GET /routes/history`` - oldest first (as in the contract example); filters + ``limit``.

    Single query, no joins (history stores a name snapshot), served by the history indexes.
    """

    serializer_class = RouteQuerySerializer
    filterset_class = RouteQueryFilter

    def get_queryset(self) -> QuerySet[RouteQuery]:
        """Oldest-first history queryset from the selector layer."""
        return selectors.list_route_history()
