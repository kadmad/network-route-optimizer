"""Domain errors for the nodes bounded context."""

from common.exceptions import DomainError


class DuplicateNodeError(DomainError):
    """A node with the same name already exists."""

    default_message = "A node with this name already exists."


class NodeNotFoundError(DomainError):
    """One or more referenced nodes do not exist (also raised by the edges / routes apps)."""

    default_message = "Node not found."
