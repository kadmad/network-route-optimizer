"""Write-side persistence for nodes (the *repository* layer).

The repository owns *how* a node is stored, in particular the translation of low-level database
errors into domain errors, so serializers and views stay free of ORM / driver details.

Concurrency strategy
--------------------
We do **not** rely on "check then insert" for correctness (that is a TOCTOU race). The write is
attempted and the database constraint arbitrates; the resulting ``IntegrityError`` is classified
(by SQLSTATE class and constraint name) and mapped to a precise domain error.

No explicit transaction is needed: each write here is a single statement, which PostgreSQL
executes atomically (autocommit), and Django already wraps a cascading ``delete()`` in its own
transaction.
"""

import logging

from django.db import IntegrityError

from common.db import is_foreign_key_violation, is_unique_violation
from common.exceptions import ConflictError

from .exceptions import DuplicateNodeError
from .models import NODE_NAME_UNIQUE, Node

logger = logging.getLogger(__name__)


class NodeRepository:
    """Persistence operations for :class:`~apps.nodes.models.Node` (stateless)."""

    def add(self, *, name: str) -> Node:
        """Insert a node.

        Raises:
            DuplicateNodeError: The name exists, including a concurrent insert that committed first.
        """
        try:
            node = Node.objects.create(name=name)
        except IntegrityError as exc:
            if is_unique_violation(exc, NODE_NAME_UNIQUE):
                raise DuplicateNodeError(f"Node '{name}' already exists.") from exc
            raise
        logger.info("node created", extra={"node_id": node.pk, "node_name": node.name})
        return node

    def remove(self, node: Node) -> None:
        """Delete a node; ``ON DELETE CASCADE`` removes its incident edges in the same transaction.

        Raises:
            ConflictError: A concurrent transaction attached a new edge to this node while it was
                being deleted (foreign-key violation). The client can safely retry.
        """
        node_id = node.pk
        try:
            node.delete()
        except IntegrityError as exc:
            if is_foreign_key_violation(exc):
                raise ConflictError from exc
            raise
        logger.info("node deleted", extra={"node_id": node_id})
