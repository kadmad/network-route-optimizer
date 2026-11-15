"""DRF serializers for the edges API (pure HTTP <-> Python mapping, no business rules)."""

from typing import Any

from rest_framework import serializers

from apps.nodes.exceptions import NodeNotFoundError
from apps.nodes.models import NODE_NAME_MAX_LENGTH, Node
from apps.nodes.selectors import nodes_by_name
from common.fields import StrictCharField

from .exceptions import InvalidEdgeError
from .models import MIN_LATENCY, Edge
from .repositories import EdgeRepository

SELF_LOOP_MESSAGE = (
    "Source and destination must be different nodes; an edge cannot connect a node to itself."
)


class NodeNameField(StrictCharField):
    """Accepts a node *name* on input; renders ``instance.name`` on output.

    Lets ``EdgeSerializer`` expose ``source``/``destination`` as plain names while the model
    holds ``Node`` foreign keys (``select_related`` keeps rendering at zero extra queries).
    """

    def to_representation(self, value: Node) -> str:  # type: ignore[override]
        """Render the related node as its name."""
        return value.name


class EdgeSerializer(serializers.ModelSerializer[Edge]):
    """``{"id": 1, "source": "A", "destination": "B", "latency": 12.5}``."""

    source = NodeNameField(  # type: ignore[assignment]  # drf-stubs: Field.source is str|None
        max_length=NODE_NAME_MAX_LENGTH
    )
    destination = NodeNameField(max_length=NODE_NAME_MAX_LENGTH)
    latency = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=MIN_LATENCY,
        coerce_to_string=False,
        help_text="Latency in milliseconds (> 0, up to 3 decimal places).",
    )

    class Meta:
        model = Edge
        fields = ("id", "source", "destination", "latency")
        read_only_fields = ("id",)
        # Uniqueness AND the self-loop rule are enforced in validate() / by the DB (single source
        # of truth), so they return the contract-style {"error": "..."} body.
        validators: list[Any] = []

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Reject self-loops, then swap the two node names for ``Node`` objects (one query)."""
        source, destination = attrs["source"], attrs["destination"]
        if source == destination:
            raise InvalidEdgeError(SELF_LOOP_MESSAGE)
        nodes = nodes_by_name((source, destination))
        missing = [name for name in (source, destination) if name not in nodes]
        if missing:
            raise NodeNotFoundError(f"Node(s) not found: {', '.join(repr(m) for m in missing)}.")
        return {**attrs, "source": nodes[source], "destination": nodes[destination]}

    def create(self, validated_data: dict[str, Any]) -> Edge:
        """Insert through the repository, which turns a duplicate pair into a 400."""
        return EdgeRepository().add(**validated_data)
