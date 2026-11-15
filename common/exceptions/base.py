"""Framework-agnostic domain exceptions.

Repositories, serializers and services raise these; none builds an HTTP response.
``status_code`` is only a *transport hint* consumed by
:func:`common.exceptions.handler.api_exception_handler`.
"""


class DomainError(Exception):
    """Base class for every expected, business-rule failure."""

    status_code: int = 400
    default_message: str = "The request could not be processed."

    def __init__(self, message: str | None = None) -> None:
        """Create the error.

        Args:
            message: Human readable, client-safe message. Falls back to ``default_message``.
        """
        self.message = message or self.default_message
        super().__init__(self.message)


class ConflictError(DomainError):
    """The operation lost a race with a concurrent writer; the client may retry."""

    status_code = 409
    default_message = "The resource was modified concurrently. Please retry."
