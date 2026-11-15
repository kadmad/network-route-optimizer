"""Query-string filters for ``GET /routes/history`` (django-filter)."""

from typing import Any

import django_filters
from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError

from .models import RouteQuery


class RouteQueryFilter(django_filters.FilterSet):
    """``?source=&destination=&date_from=&date_to=`` - all optional, combinable.

    ``date_from``/``date_to`` are inclusive ISO-8601 timestamps (e.g. ``2026-02-20T00:00:00Z``).
    """

    source = django_filters.CharFilter(field_name="source_name", lookup_expr="exact")
    destination = django_filters.CharFilter(field_name="destination_name", lookup_expr="exact")
    date_from = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    date_to = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = RouteQuery
        fields: list[str] = []

    def filter_queryset(self, queryset: QuerySet[RouteQuery]) -> QuerySet[RouteQuery]:
        """Apply filters after validating the date range is not inverted."""
        data: dict[str, Any] = self.form.cleaned_data
        date_from, date_to = data.get("date_from"), data.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise ValidationError({"date_to": ["Must be greater than or equal to date_from."]})
        return super().filter_queryset(queryset)
