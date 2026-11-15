"""DRF serializers for the nodes API (pure HTTP <-> Python mapping, no business rules)."""

from rest_framework import serializers

from common.fields import StrictCharField

from .models import NODE_NAME_MAX_LENGTH, Node
from .repositories import NodeRepository


class NodeSerializer(serializers.ModelSerializer[Node]):
    """``{"id": 1, "name": "ServerA"}``.

    Uniqueness is deliberately *not* validated here: the DB constraint is the single source
    of truth and the repository maps its violation to a 400 (no check-then-insert race).
    """

    # Declared explicitly so DRF does NOT auto-generate a UniqueValidator from the DB
    # constraint (that would add a redundant pre-check SELECT and a second error path).
    name = StrictCharField(max_length=NODE_NAME_MAX_LENGTH)

    class Meta:
        model = Node
        fields = ("id", "name")
        read_only_fields = ("id",)

    def validate_name(self, value: str) -> str:
        """Reject control / non-printable characters (log-injection and look-alike names)."""
        if not value.isprintable():
            raise serializers.ValidationError("Name must not contain control characters.")
        return value

    def create(self, validated_data: dict[str, str]) -> Node:
        """Insert through the repository, which turns a duplicate name into a 400."""
        return NodeRepository().add(name=validated_data["name"])
