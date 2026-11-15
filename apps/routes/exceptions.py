"""Domain errors for the routes bounded context."""

from common.exceptions import DomainError


class NoPathFoundError(DomainError):
    """The destination is not reachable from the source."""

    status_code = 404
    default_message = "No path exists between the given nodes."
