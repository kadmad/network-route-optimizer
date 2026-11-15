"""Query budgets: every endpoint has a fixed SQL cost that must not grow with the data.

These are regression guards for N+1 problems and accidental ``COUNT(*)`` / join creep. They assert
the *number* of SQL statements, which is deterministic, instead of wall-clock time, which would
make the suite flaky on shared CI runners.
"""

from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest
from rest_framework.test import APIClient

from tests.factories import create_edge, create_node

pytestmark = pytest.mark.django_db

NODES = "/api/v1/nodes"
EDGES = "/api/v1/edges"
SHORTEST = "/api/v1/routes/shortest"
HISTORY = "/api/v1/routes/history"


def test_create_node_is_a_single_insert(
    api_client: APIClient, count_queries: Callable[[], Any]
) -> None:
    with count_queries() as ctx:
        assert api_client.post(NODES, {"name": "A"}).status_code == 201
    assert len(ctx.statements) == 1


def test_create_edge_is_one_lookup_and_one_insert(
    api_client: APIClient, count_queries: Callable[[], Any]
) -> None:
    create_node(name="A")
    create_node(name="B")
    with count_queries() as ctx:
        response = api_client.post(EDGES, {"source": "A", "destination": "B", "latency": 1})
    assert response.status_code == 201
    assert len(ctx.statements) == 2  # IN (...) lookup of both endpoints + INSERT


def test_list_nodes_is_one_query_without_count(
    api_client: APIClient, count_queries: Callable[[], Any]
) -> None:
    for i in range(5):
        create_node(name=f"N{i}")
    with count_queries() as ctx:
        assert api_client.get(NODES).status_code == 200
    assert len(ctx.statements) == 1


def test_list_edges_cost_is_independent_of_the_number_of_edges(
    api_client: APIClient, count_queries: Callable[[], Any]
) -> None:
    """Rendering ``source`` / ``destination`` names must not query per row (no N+1)."""

    def queries_for_list() -> int:
        with count_queries() as ctx:
            assert api_client.get(EDGES).status_code == 200
        return len(ctx.statements)

    create_node(name="Hub")
    create_node(name="N0")
    create_edge(source="Hub", destination="N0", latency=Decimal(1))
    small = queries_for_list()
    for i in range(1, 11):
        create_node(name=f"N{i}")
        create_edge(source="Hub", destination=f"N{i}", latency=Decimal(1))
    assert queries_for_list() == small == 1  # one joined SELECT, no COUNT(*)


def test_shortest_route_cost_is_independent_of_graph_size(
    api_client: APIClient, diamond: dict[str, Decimal], count_queries: Callable[[], Any]
) -> None:
    def run() -> int:
        with count_queries() as ctx:
            response = api_client.post(SHORTEST, {"source": "A", "destination": "D"})
            assert response.status_code == 200
        return len(ctx.statements)

    baseline = run()
    for i in range(25):  # grow the graph substantially
        create_node(name=f"X{i}")
        create_edge(source="A", destination=f"X{i}", latency=Decimal(1))
    # node validation + graph load + history insert
    assert baseline == run() == 3


def test_history_listing_is_a_single_query_without_joins(
    api_client: APIClient, diamond: dict[str, Decimal], count_queries: Callable[[], Any]
) -> None:
    api_client.post(SHORTEST, {"source": "A", "destination": "D"})
    with count_queries() as ctx:
        assert api_client.get(HISTORY).status_code == 200
    assert len(ctx.statements) == 1
    assert "JOIN" not in ctx.statements[0].upper()
