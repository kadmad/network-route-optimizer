"""Route computation use-case (the *service layer*).

Reads go through selectors, the graph math is ``dijkstra.shortest_path`` and the history write is
``RouteHistoryRepository``; this function only orchestrates them.
"""

import logging

from apps.nodes.exceptions import NodeNotFoundError
from apps.nodes.selectors import existing_node_names

from .dijkstra import PathResult, shortest_path
from .exceptions import NoPathFoundError
from .repositories import RouteHistoryRepository
from .selectors import load_graph

logger = logging.getLogger(__name__)


def find_shortest_route(*, source: str, destination: str) -> PathResult:
    """Return the shortest route and persist it to the history.

    Total cost: 2 SELECTs (node validation + graph load) + 1 INSERT, independent of graph size.

    Raises:
        NodeNotFoundError: ``source`` or ``destination`` does not exist.
        NoPathFoundError: The nodes exist but are not connected.
    """
    wanted = {source, destination}
    missing = wanted - existing_node_names(wanted)
    if missing:
        names = ", ".join(repr(name) for name in sorted(missing))
        raise NodeNotFoundError(f"Node(s) not found: {names}.")

    result = shortest_path(load_graph(), source, destination)
    if result is None:
        raise NoPathFoundError(f"No path exists between {source} and {destination}")

    RouteHistoryRepository().record(source=source, destination=destination, result=result)
    logger.info(
        "shortest route computed",
        extra={"route_source": source, "route_destination": destination},
    )
    return result
