"""Write-side persistence for edges (the *repository* layer).

Translates database errors into domain errors, using the same "let the constraint arbitrate"
strategy (and the same no-explicit-transaction reasoning) as :mod:`apps.nodes.repositories`.
"""

import logging
from decimal import Decimal

from django.db import IntegrityError

from apps.nodes.exceptions import NodeNotFoundError
from apps.nodes.models import Node
from common.db import is_foreign_key_violation, is_unique_violation

from .exceptions import DuplicateEdgeError
from .models import EDGE_PAIR_UNIQUE, Edge

logger = logging.getLogger(__name__)


class EdgeRepository:
    """Persistence operations for :class:`~apps.edges.models.Edge` (stateless)."""

    def add(self, *, source: Node, destination: Node, latency: Decimal) -> Edge:
        """Insert an edge between two already-resolved nodes.

        The returned ``Edge`` has ``source`` and ``destination`` attached, so serialising it
        triggers no further queries.

        Raises:
            DuplicateEdgeError: The ordered pair already has an edge.
            NodeNotFoundError: An endpoint was deleted between lookup and insert. PostgreSQL
                checks the (deferred) foreign key when the statement's own transaction commits,
                which still happens inside this call, so it is caught here.
        """
        try:
            edge = Edge.objects.create(source=source, destination=destination, latency=latency)
        except IntegrityError as exc:
            if is_unique_violation(exc, EDGE_PAIR_UNIQUE):
                raise DuplicateEdgeError(
                    f"Edge '{source.name}' -> '{destination.name}' already exists."
                ) from exc
            if is_foreign_key_violation(exc):
                raise NodeNotFoundError("A referenced node was deleted concurrently.") from exc
            raise
        logger.info("edge created", extra={"edge_id": edge.pk, "latency": str(latency)})
        return edge

    def remove(self, edge: Edge) -> None:
        """Delete a single edge."""
        edge_id = edge.pk
        edge.delete()
        logger.info("edge deleted", extra={"edge_id": edge_id})
