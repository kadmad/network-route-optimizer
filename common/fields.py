"""Reusable serializer fields."""

from typing import Any

from rest_framework import serializers


class StrictCharField(serializers.CharField):
    """A ``CharField`` that accepts **only JSON strings**.

    DRF's stock ``CharField`` silently coerces numbers (``123`` -> ``"123"``), which would let
    ``{"name": 123}`` create a node called ``"123"``. For identifiers that is a latent bug
    (``1.0`` and ``"1.0"`` would alias), so the API rejects non-string input with a ``400``.
    """

    def to_internal_value(self, data: Any) -> str:
        """Reject anything that is not already a ``str`` before the usual trimming/validation."""
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)
