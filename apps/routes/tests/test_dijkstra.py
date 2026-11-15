"""Pure unit tests for the path-finding algorithm (no database, no Django)."""

from decimal import Decimal

from apps.routes.dijkstra import Graph, shortest_path

D = Decimal


def test_prefers_cheaper_multi_hop_path_over_expensive_direct_edge() -> None:
    graph: Graph = {
        "A": [("D", D("100")), ("B", D("1"))],
        "B": [("C", D("1"))],
        "C": [("D", D("1"))],
    }
    result = shortest_path(graph, "A", "D")
    assert result is not None
    assert result.path == ("A", "B", "C", "D")
    assert result.total_latency == D("3")


def test_graph_is_directed() -> None:
    graph: Graph = {"A": [("B", D("1"))]}
    assert shortest_path(graph, "A", "B") is not None
    assert shortest_path(graph, "B", "A") is None


def test_unreachable_destination_returns_none() -> None:
    graph: Graph = {"A": [("B", D("1"))], "C": [("D", D("1"))]}
    assert shortest_path(graph, "A", "D") is None


def test_source_equals_destination_is_a_zero_cost_trivial_path() -> None:
    result = shortest_path({}, "A", "A")
    assert result is not None
    assert (result.path, result.total_latency) == (("A",), D(0))


def test_decimal_arithmetic_is_exact() -> None:
    """With floats 0.1 + 0.2 == 0.30000000000000004; Decimal keeps the API output exact."""
    graph: Graph = {"A": [("B", D("0.1"))], "B": [("C", D("0.2"))]}
    result = shortest_path(graph, "A", "C")
    assert result is not None
    assert result.total_latency == D("0.3")


def test_equal_cost_paths_resolve_deterministically() -> None:
    graph: Graph = {"A": [("C", D("1")), ("B", D("1"))], "B": [("D", D("1"))], "C": [("D", D("1"))]}
    paths = {shortest_path(graph, "A", "D").path for _ in range(20)}  # type: ignore[union-attr]
    assert len(paths) == 1


def test_cycles_do_not_loop_forever() -> None:
    graph: Graph = {"A": [("B", D("1"))], "B": [("A", D("1")), ("C", D("1"))]}
    result = shortest_path(graph, "A", "C")
    assert result is not None
    assert result.path == ("A", "B", "C")
