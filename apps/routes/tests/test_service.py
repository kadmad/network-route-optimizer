"""``find_shortest_route`` orchestration tests against the real database."""

from decimal import Decimal

import pytest

from apps.nodes.exceptions import NodeNotFoundError
from apps.routes.exceptions import NoPathFoundError
from apps.routes.models import RouteQuery
from apps.routes.services import find_shortest_route
from tests.factories import create_edge, create_node

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def graph() -> None:
    """A -> B (2) -> C (3); no way back."""
    for name in ("A", "B", "C"):
        create_node(name=name)
    create_edge(source="A", destination="B", latency=Decimal("2"))
    create_edge(source="B", destination="C", latency=Decimal("3"))


def test_unknown_node_is_rejected_and_not_recorded() -> None:
    with pytest.raises(NodeNotFoundError, match="'Z'"):
        find_shortest_route(source="A", destination="Z")
    assert RouteQuery.objects.count() == 0


def test_unreachable_is_not_recorded_in_history() -> None:
    with pytest.raises(NoPathFoundError, match="No path exists between C and A"):
        find_shortest_route(source="C", destination="A")
    assert RouteQuery.objects.count() == 0


def test_success_is_recorded_as_a_snapshot() -> None:
    result = find_shortest_route(source="A", destination="C")
    assert result.total_latency == Decimal("5")
    row = RouteQuery.objects.get()
    assert (row.source_name, row.destination_name, row.path) == ("A", "C", ["A", "B", "C"])
    assert row.total_latency == Decimal("5")
