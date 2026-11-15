"""Pagination.

All list endpoints in this API return a **bare JSON array** (as the contract shows), so the
paginator communicates nothing in the body; the client simply asks for ``?limit=&offset=``.
No ``COUNT(*)`` is issued, which keeps list endpoints a single indexed query.
"""

from collections.abc import Sequence
from typing import Any

from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import BasePagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class ArrayPagination(BasePagination):
    """``?limit=N&offset=M`` returning a *bare JSON array*.

    * ``limit``: clamped to ``max_limit`` (DoS protection); a non-integer or non-positive
      value is a ``400``.
    * ``offset``: rows to skip; a non-integer or negative value is a ``400``.

    The view's queryset **must** be ordered so that pages are deterministic.
    """

    default_limit = 100
    max_limit = 1000
    limit_query_param = "limit"
    offset_query_param = "offset"

    def paginate_queryset(
        self,
        queryset: QuerySet[Any] | Sequence[Any],
        request: Request,
        view: APIView | None = None,
    ) -> list[Any]:
        """Return one page using a single ``LIMIT/OFFSET`` query."""
        limit = self._get_limit(request)
        offset = self._get_offset(request)
        return list(queryset[offset : offset + limit])

    def get_paginated_response(self, data: Any) -> Response:
        """Return the page as a plain array."""
        return Response(data)

    def _get_limit(self, request: Request) -> int:
        limit = self._parse_int(request, self.limit_query_param)
        if limit is None:
            return self.default_limit
        if limit < 1:
            raise ValidationError({self.limit_query_param: ["Must be a positive integer."]})
        return min(limit, self.max_limit)

    def _get_offset(self, request: Request) -> int:
        offset = self._parse_int(request, self.offset_query_param)
        if offset is None:
            return 0
        if offset < 0:
            raise ValidationError({self.offset_query_param: ["Must be a non-negative integer."]})
        return offset

    @staticmethod
    def _parse_int(request: Request, name: str) -> int | None:
        """Parse an optional integer query parameter; garbage becomes a field error."""
        raw = request.query_params.get(name)
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError:
            raise ValidationError({name: ["Must be an integer."]}) from None
