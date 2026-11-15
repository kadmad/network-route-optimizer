"""Error model shared by every app.

* :mod:`common.exceptions.base` - framework-agnostic domain exceptions (repositories, services).
* :mod:`common.exceptions.handler` - the single DRF handler that renders them as JSON.
"""

from .base import ConflictError, DomainError

__all__ = ["ConflictError", "DomainError"]
