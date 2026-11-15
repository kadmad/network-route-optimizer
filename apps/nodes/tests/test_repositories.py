"""Node repository tests: database-level edge cases (races, constraint translation)."""

import threading
from typing import Any

import pytest
from django.db import IntegrityError, connection
from psycopg import errors as pg_errors

from apps.nodes.exceptions import DuplicateNodeError
from apps.nodes.models import Node
from apps.nodes.repositories import NodeRepository
from common.exceptions import ConflictError

pytestmark = pytest.mark.django_db


@pytest.mark.django_db(transaction=True)  # a failed INSERT aborts pytest's wrapping transaction
def test_create_node_duplicate_is_translated_from_db_constraint() -> None:
    NodeRepository().add(name="A")
    with pytest.raises(DuplicateNodeError):
        NodeRepository().add(name="A")
    assert Node.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_node_creation_yields_exactly_one_winner() -> None:
    """Two simultaneous inserts of the same name: one 'wins', the other gets a domain error.

    Proves correctness comes from the DB constraint, not from a racy check-then-insert.
    """
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def worker() -> None:
        try:
            barrier.wait(timeout=5)
            NodeRepository().add(name="Racer")
            outcomes.append("created")
        except DuplicateNodeError:
            outcomes.append("duplicate")
        finally:
            connection.close()  # hand the pooled connection back

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert sorted(outcomes) == ["created", "duplicate"]
    assert Node.objects.filter(name="Racer").count() == 1


def test_node_delete_hitting_fk_violation_is_a_retryable_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A concurrent edge insert makes DELETE fail its FK check -> 409 (retry), never a 500."""
    NodeRepository().add(name="A")
    node = Node.objects.get(name="A")

    def failing_delete(*args: Any, **kwargs: Any) -> None:
        raise IntegrityError("fk violated") from pg_errors.ForeignKeyViolation("fk violated")

    monkeypatch.setattr(Node, "delete", failing_delete)
    with pytest.raises(ConflictError):
        NodeRepository().remove(node)
