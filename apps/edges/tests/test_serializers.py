"""Edge creation tests (through the serializer): business rules and database-level edge cases."""

from decimal import Decimal
from typing import Any

import pytest
from pytest_django.fixtures import DjangoAssertNumQueries

from apps.edges.exceptions import DuplicateEdgeError, InvalidEdgeError
from apps.edges.models import Edge
from apps.edges.repositories import EdgeRepository
from apps.edges.serializers import EdgeSerializer
from apps.nodes.exceptions import NodeNotFoundError
from apps.nodes.models import Node
from apps.nodes.repositories import NodeRepository
from tests.factories import create_node

pytestmark = pytest.mark.django_db


def create_edge(source: str, destination: str, latency: Decimal) -> Edge:
    """Create an edge exactly like ``POST /edges`` does: validate, then save."""
    serializer = EdgeSerializer(
        data={"source": source, "destination": destination, "latency": latency}
    )
    serializer.is_valid(raise_exception=True)
    edge: Edge = serializer.save()
    return edge


def test_create_edge_rejects_self_loop() -> None:
    create_node(name="A")
    with pytest.raises(InvalidEdgeError):
        create_edge("A", "A", Decimal(1))


def test_create_edge_reports_every_missing_node_using_one_query(
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    create_node(name="A")
    with django_assert_num_queries(1), pytest.raises(NodeNotFoundError, match="'X'"):
        create_edge("A", "X", Decimal(1))  # one IN (...) query


def test_edges_are_directed_so_reverse_pair_is_allowed_but_not_repeatable() -> None:
    create_node(name="A")
    create_node(name="B")
    create_edge("A", "B", Decimal(1))
    create_edge("B", "A", Decimal(2))  # reverse is a new edge
    with pytest.raises(DuplicateEdgeError):
        create_edge("A", "B", Decimal(3))


def test_create_edge_returns_instance_ready_to_serialise_without_extra_queries(
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    create_node(name="A")
    create_node(name="B")
    edge = create_edge("A", "B", Decimal(1))
    with django_assert_num_queries(0):
        assert (edge.source.name, edge.destination.name) == ("A", "B")


def test_deleting_a_node_cascades_to_its_incident_edges_only() -> None:
    for name in "ABC":
        create_node(name=name)
    create_edge("A", "B", Decimal(1))
    create_edge("B", "C", Decimal(1))
    create_edge("A", "C", Decimal(1))

    NodeRepository().remove(Node.objects.get(name="B"))

    remaining = {
        (e.source.name, e.destination.name)
        for e in Edge.objects.select_related("source", "destination")
    }
    assert remaining == {("A", "C")}


def test_removing_an_edge_leaves_its_nodes() -> None:
    create_node(name="A")
    create_node(name="B")
    edge = create_edge("A", "B", Decimal(1))
    EdgeRepository().remove(edge)
    assert Edge.objects.count() == 0
    assert Node.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_endpoint_deleted_between_lookup_and_commit_is_reported_as_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FK constraints are DEFERRABLE: the violation surfaces at COMMIT, not at INSERT.

    Simulate a concurrent delete of the destination right after our lookup. The repository must
    translate the commit-time ForeignKeyViolation into a clean domain error (not a 500).
    """
    create_node(name="A")
    create_node(name="B")
    real_create = Edge.objects.create

    def delete_destination_then_insert(**kwargs: Any) -> Edge:
        Node.objects.filter(pk=kwargs["destination"].pk).delete()
        return real_create(**kwargs)

    monkeypatch.setattr(Edge.objects, "create", delete_destination_then_insert)

    with pytest.raises(NodeNotFoundError, match="concurrently"):
        create_edge("A", "B", Decimal(1))
    assert Edge.objects.count() == 0  # nothing half-written
