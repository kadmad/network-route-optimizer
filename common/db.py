"""Helpers for classifying low-level database integrity errors.

Django wraps driver exceptions in :class:`django.db.IntegrityError` and chains the original
psycopg error on ``__cause__``. Inspecting the *driver* error (SQLSTATE class + constraint
name) is far more reliable than matching on error-message text.
"""

from django.db import IntegrityError
from psycopg import errors as pg_errors


def is_unique_violation(exc: IntegrityError, constraint: str) -> bool:
    """Return True if ``exc`` violated the unique constraint called ``constraint``."""
    cause = exc.__cause__
    return isinstance(cause, pg_errors.UniqueViolation) and cause.diag.constraint_name == constraint


def is_foreign_key_violation(exc: IntegrityError) -> bool:
    """Return True if ``exc`` was caused by a missing referenced row."""
    return isinstance(exc.__cause__, pg_errors.ForeignKeyViolation)
