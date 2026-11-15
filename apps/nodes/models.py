"""Persistence model for network nodes.

Schema design notes
-------------------
* **Integrity lives in the database.** Uniqueness and value rules are DB constraints, so they
  hold under concurrency and for any writer (shell, migration, future service) - application
  validation is only a friendlier first line of defence.
* **Case-sensitive, unique names.** ``UNIQUE(name)`` also provides the index used for every
  "resolve node by name" lookup (edge creation, route validation).
"""

from django.db import models
from django.db.models import Q

from common.models import CreatedAtModel

NODE_NAME_MAX_LENGTH = 100
NODE_NAME_UNIQUE = "uniq_node_name"


class Node(CreatedAtModel):
    """A network endpoint (server, router, ...) identified by a unique name."""

    name = models.CharField(max_length=NODE_NAME_MAX_LENGTH)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name"], name=NODE_NAME_UNIQUE),
            models.CheckConstraint(condition=~Q(name=""), name="node_name_not_blank"),
        ]

    def __str__(self) -> str:
        """Return the node name."""
        return self.name
