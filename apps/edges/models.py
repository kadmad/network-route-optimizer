"""Persistence model for directed, weighted edges.

Schema design notes
-------------------
* **Integrity lives in the database** (see :mod:`apps.nodes.models`): uniqueness, positive
  latency and the no-self-loop rule are constraints, so they hold under concurrency.
* **Directed graph.** ``Edge(source -> destination)``; the reverse direction is a separate row.
* **Latency is a ``Decimal``.** Binary floats make path sums non-deterministic
  (0.1 + 0.2 != 0.3); ``NUMERIC(10,3)`` keeps arithmetic exact. Unit: milliseconds.
* **Index strategy.** ``UNIQUE(source, destination)`` doubles as the index for "outgoing edges of
  X" (leftmost-prefix), so the separate FK index on ``source`` is disabled (``db_index=False``)
  to avoid a redundant index slowing every write. ``destination`` keeps its FK index, which
  serves reverse lookups and the cascade when a node is deleted.
"""

from decimal import Decimal

from django.db import models
from django.db.models import F, Q

from apps.nodes.models import Node
from common.models import CreatedAtModel

MIN_LATENCY = Decimal("0.001")
EDGE_PAIR_UNIQUE = "uniq_edge_source_destination"


class Edge(CreatedAtModel):
    """A directed link ``source -> destination`` with a latency weight (milliseconds)."""

    source = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name="outgoing_edges",
        db_index=False,  # covered by the leading column of the unique constraint below
    )
    destination = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="incoming_edges")
    latency = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "destination"], name=EDGE_PAIR_UNIQUE),
            models.CheckConstraint(
                condition=Q(latency__gte=MIN_LATENCY), name="edge_latency_positive"
            ),
            models.CheckConstraint(condition=~Q(source=F("destination")), name="edge_no_self_loop"),
        ]

    def __str__(self) -> str:
        """Return a compact human-readable description."""
        return f"{self.source_id} -> {self.destination_id} ({self.latency} ms)"
