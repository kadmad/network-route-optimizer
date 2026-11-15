"""Shortest path in a weighted directed graph: Dijkstra with a binary heap.

Pure Python (no I/O, no Django), so it is unit-tested without a database.
"""

import heapq
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

# Adjacency list: node name -> [(neighbour name, latency), ...]
Graph = Mapping[str, Sequence[tuple[str, Decimal]]]

_ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class PathResult:
    """Outcome of a successful path search."""

    path: tuple[str, ...]
    total_latency: Decimal


def shortest_path(graph: Graph, source: str, destination: str) -> PathResult | None:
    """Return the lowest-latency path from ``source`` to ``destination``, or ``None``.

    ``O((V + E) log V)``. Correct only for **non-negative** weights, which the
    ``edge_latency_positive`` database constraint guarantees. Ties are broken deterministically
    (the heap orders ``(cost, name)``), so the same graph always yields the same path.
    """
    best_cost: dict[str, Decimal] = {source: _ZERO}
    predecessor: dict[str, str] = {}
    finalised: set[str] = set()
    heap: list[tuple[Decimal, str]] = [(_ZERO, source)]

    while heap:
        cost, node = heapq.heappop(heap)
        if node in finalised:
            continue  # stale heap entry: a cheaper one was already processed
        if node == destination:
            # First time the target is popped its cost is optimal -> early exit.
            return PathResult(
                path=_rebuild_path(predecessor, source, destination), total_latency=cost
            )
        finalised.add(node)
        for neighbour, weight in graph.get(node, ()):
            if neighbour in finalised:
                continue
            candidate = cost + weight
            known = best_cost.get(neighbour)
            if known is None or candidate < known:
                best_cost[neighbour] = candidate
                predecessor[neighbour] = node
                heapq.heappush(heap, (candidate, neighbour))
    return None


def _rebuild_path(predecessor: dict[str, str], source: str, destination: str) -> tuple[str, ...]:
    """Walk predecessor links back from ``destination`` to ``source``."""
    path = [destination]
    while path[-1] != source:
        path.append(predecessor[path[-1]])
    path.reverse()
    return tuple(path)
