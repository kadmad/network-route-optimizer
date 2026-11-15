"""Persistence (writes) for the route use-case."""

from .dijkstra import PathResult
from .models import RouteQuery


class RouteHistoryRepository:
    """Append-only audit log of answered route queries (one ``INSERT`` per record)."""

    def record(self, *, source: str, destination: str, result: PathResult) -> None:
        """Persist one successful computation as a name snapshot."""
        RouteQuery.objects.create(
            source_name=source,
            destination_name=destination,
            total_latency=result.total_latency,
            path=list(result.path),
        )
