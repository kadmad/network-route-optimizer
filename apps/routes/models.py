"""Route query history.

Design decision: **denormalised snapshot, no foreign keys.**
History is an append-only audit log of *what was answered at that time*. Storing node names
(and the resolved path) instead of FKs means:

* history survives node deletion (an FK would force CASCADE-delete or SET NULL, both lossy);
* reading history needs **no joins** -> no N+1 and the listing is a single index range scan;
* writes are one INSERT with nothing to lock.

Indexes mirror the query patterns of ``GET /routes/history`` (filter by source and/or
destination, optional time range, oldest first).
"""

from django.db import models

from apps.nodes.models import NODE_NAME_MAX_LENGTH
from common.models import CreatedAtModel


class RouteQuery(CreatedAtModel):
    """One successful shortest-path computation."""

    source_name = models.CharField(max_length=NODE_NAME_MAX_LENGTH)
    destination_name = models.CharField(max_length=NODE_NAME_MAX_LENGTH)
    total_latency = models.DecimalField(max_digits=14, decimal_places=3)
    path = models.JSONField(help_text="Ordered list of node names (snapshot).")

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            # Unfiltered listing: index scan in order, stops after LIMIT rows.
            models.Index(fields=["created_at", "id"], name="rq_created_idx"),
            # Prefix lookups: source only, or source+time range (also serves ORDER BY).
            models.Index(fields=["source_name", "created_at"], name="rq_source_created_idx"),
            models.Index(
                fields=["destination_name", "created_at"], name="rq_destination_created_idx"
            ),
        ]

    def __str__(self) -> str:
        """Return ``source -> destination (latency)``."""
        return f"{self.source_name} -> {self.destination_name} ({self.total_latency})"
