"""HTTP contract tests for /routes/shortest and /routes/history."""

from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.nodes.models import Node
from apps.routes.models import RouteQuery

pytestmark = pytest.mark.django_db

SHORTEST = "/api/v1/routes/shortest"
HISTORY = "/api/v1/routes/history"


class TestShortestRoute:
    def test_returns_contract_example(
        self, api_client: APIClient, diamond: dict[str, Decimal]
    ) -> None:
        response = api_client.post(SHORTEST, {"source": "A", "destination": "D"})
        assert response.status_code == 200
        assert response.json() == {"total_latency": 23.4, "path": ["A", "B", "D"]}

    def test_no_path_is_404_with_contract_message(
        self, api_client: APIClient, diamond: dict[str, Decimal]
    ) -> None:
        response = api_client.post(SHORTEST, {"source": "D", "destination": "A"})
        assert response.status_code == 404
        assert response.json() == {"error": "No path exists between D and A"}

    @pytest.mark.parametrize(
        "payload",
        [
            {"source": "A", "destination": "Ghost"},
            {"source": "Ghost", "destination": "A"},
            {"source": "A"},
            {"destination": "A"},
            {"source": 1, "destination": "A"},
            {"source": "A", "destination": 2.5},
            {},
        ],
    )
    def test_invalid_or_unknown_nodes_are_400(
        self, api_client: APIClient, diamond: dict[str, Decimal], payload: dict[str, Any]
    ) -> None:
        assert api_client.post(SHORTEST, payload).status_code == 400
        assert RouteQuery.objects.count() == 0


class TestHistory:
    @pytest.fixture
    def rows(self, api_client: APIClient, diamond: dict[str, Decimal]) -> None:
        api_client.post(SHORTEST, {"source": "A", "destination": "D"})
        api_client.post(SHORTEST, {"source": "A", "destination": "C"})
        api_client.post(SHORTEST, {"source": "B", "destination": "D"})
        now = timezone.now()
        for age, row in enumerate(RouteQuery.objects.order_by("id")):  # id1 oldest
            RouteQuery.objects.filter(pk=row.pk).update(created_at=now - timedelta(days=3 - age))

    def test_returns_bare_array_oldest_first_with_contract_fields(
        self, api_client: APIClient, rows: None
    ) -> None:
        body = api_client.get(HISTORY).json()
        assert isinstance(body, list)
        assert [(r["source"], r["destination"]) for r in body] == [
            ("A", "D"),
            ("A", "C"),
            ("B", "D"),
        ]
        assert set(body[0]) == {
            "id",
            "source",
            "destination",
            "total_latency",
            "path",
            "created_at",
        }
        assert body[0]["path"] == ["A", "B", "D"]

    def test_filters_combine(self, api_client: APIClient, rows: None) -> None:
        assert len(api_client.get(HISTORY, {"source": "A"}).json()) == 2
        assert len(api_client.get(HISTORY, {"destination": "D"}).json()) == 2
        assert len(api_client.get(HISTORY, {"source": "A", "destination": "D"}).json()) == 1
        assert api_client.get(HISTORY, {"source": "nobody"}).json() == []

    def test_date_range_is_inclusive_and_validated(self, api_client: APIClient, rows: None) -> None:
        middle = RouteQuery.objects.order_by("created_at")[1].created_at
        got = api_client.get(
            HISTORY, {"date_from": middle.isoformat(), "date_to": middle.isoformat()}
        )
        assert [r["destination"] for r in got.json()] == ["C"]
        bad = api_client.get(
            HISTORY, {"date_from": "2030-01-02T00:00:00Z", "date_to": "2030-01-01T00:00:00Z"}
        )
        assert bad.status_code == 400
        assert api_client.get(HISTORY, {"date_from": "not-a-date"}).status_code == 400

    def test_limit_is_applied_clamped_and_validated(
        self, api_client: APIClient, rows: None
    ) -> None:
        assert len(api_client.get(HISTORY, {"limit": 2}).json()) == 2
        assert len(api_client.get(HISTORY, {"limit": 10_000}).json()) == 3  # clamped, not an error
        for bad in ("0", "-1", "abc"):
            assert api_client.get(HISTORY, {"limit": bad}).status_code == 400

    def test_history_survives_node_deletion(self, api_client: APIClient, rows: None) -> None:
        Node.objects.get(name="B").delete()
        body = api_client.get(HISTORY, {"source": "B"}).json()
        assert len(body) == 1
        assert body[0]["destination"] == "D"
