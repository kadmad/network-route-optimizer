"""Domain errors for the edges bounded context."""

from common.exceptions import DomainError


class DuplicateEdgeError(DomainError):
    """An edge between the same ordered pair of nodes already exists."""

    default_message = "An edge between these nodes already exists."


class InvalidEdgeError(DomainError):
    """The edge violates a structural rule (e.g. self-loop)."""

    default_message = "Invalid edge."
