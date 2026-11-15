"""Serializers for the routes API."""

from rest_framework import serializers

from apps.nodes.models import NODE_NAME_MAX_LENGTH
from common.fields import StrictCharField

from .models import RouteQuery


class ShortestRouteRequestSerializer(serializers.Serializer[dict[str, str]]):
    """Request body for ``POST /routes/shortest``."""

    source = StrictCharField(max_length=NODE_NAME_MAX_LENGTH)  # type: ignore[assignment]
    destination = StrictCharField(max_length=NODE_NAME_MAX_LENGTH)


class ShortestRouteResponseSerializer(serializers.Serializer[dict[str, object]]):
    """Response body for ``POST /routes/shortest``."""

    total_latency = serializers.DecimalField(
        max_digits=14, decimal_places=3, coerce_to_string=False
    )
    path = serializers.ListField(child=serializers.CharField())


class RouteQuerySerializer(serializers.ModelSerializer[RouteQuery]):
    """One entry of ``GET /routes/history`` (field names follow the published contract)."""

    source = serializers.CharField(source="source_name", read_only=True)  # type: ignore[assignment]
    destination = serializers.CharField(source="destination_name", read_only=True)
    total_latency = serializers.DecimalField(
        max_digits=14, decimal_places=3, coerce_to_string=False, read_only=True
    )

    class Meta:
        model = RouteQuery
        fields = ("id", "source", "destination", "total_latency", "path", "created_at")
        read_only_fields = fields
