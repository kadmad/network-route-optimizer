"""HTTP contract tests for ``/edges``."""

from decimal import Decimal
from typing import Any

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.edges.models import Edge
from apps.edges.serializers import SELF_LOOP_MESSAGE
from apps.nodes.models import Node
from tests.factories import create_edge, create_node

pytestmark = pytest.mark.django_db

EDGES = "/api/v1/edges"


class TestEdges:
    @pytest.fixture(autouse=True)
    def _nodes(self) -> None:
        create_node(name="ServerA")
        create_node(name="ServerB")

    def test_create_returns_contract_shape(self, api_client: APIClient) -> None:
        response = api_client.post(
            EDGES, {"source": "ServerA", "destination": "ServerB", "latency": 12.5}
        )
        assert response.status_code == 201
        assert response.json() == {
            "id": Edge.objects.get().pk,
            "source": "ServerA",
            "destination": "ServerB",
            "latency": 12.5,
        }

    @pytest.mark.parametrize(
        ("payload", "field"),
        [
            ({"destination": "ServerB", "latency": 1}, "source"),
            ({"source": "ServerA", "latency": 1}, "destination"),
            ({"source": "ServerA", "destination": "ServerB"}, "latency"),
            ({"source": "ServerA", "destination": "ServerB", "latency": 0}, "latency"),
            ({"source": "ServerA", "destination": "ServerB", "latency": -3}, "latency"),
            ({"source": "ServerA", "destination": "ServerB", "latency": "fast"}, "latency"),
            ({"source": "ServerA", "destination": "ServerB", "latency": "NaN"}, "latency"),
            ({"source": "ServerA", "destination": "ServerB", "latency": 1.0001}, "latency"),
        ],
    )
    def test_invalid_payloads_are_400(
        self, api_client: APIClient, payload: dict[str, Any], field: str
    ) -> None:
        response = api_client.post(EDGES, payload)
        assert response.status_code == 400
        assert field in response.json()["details"]
        assert Edge.objects.count() == 0

    def test_self_loop_is_400_with_contract_style_error(self, api_client: APIClient) -> None:
        """Exact payload from the review: an edge from a node to itself is rejected."""
        response = api_client.post(
            EDGES, {"source": "ServerA", "destination": "ServerA", "latency": 10.5}
        )
        assert response.status_code == 400
        assert response.json() == {"error": SELF_LOOP_MESSAGE}  # plain {"error": ...}, no details
        assert Edge.objects.count() == 0

    def test_self_loop_check_is_case_sensitive(self, api_client: APIClient) -> None:
        """'servera' is a different node name than 'ServerA', so this is *not* a self-loop."""
        create_node(name="servera")
        response = api_client.post(
            EDGES, {"source": "ServerA", "destination": "servera", "latency": 10.5}
        )
        assert response.status_code == 201

    @pytest.mark.parametrize("field", ["source", "destination"])
    def test_non_string_endpoints_are_rejected_not_coerced(
        self, api_client: APIClient, field: str
    ) -> None:
        payload: dict[str, Any] = {"source": "ServerA", "destination": "ServerB", "latency": 1}
        payload[field] = 123
        response = api_client.post(EDGES, payload)
        assert response.status_code == 400
        assert field in response.json()["details"]

    def test_unknown_node_is_400(self, api_client: APIClient) -> None:
        response = api_client.post(
            EDGES, {"source": "ServerA", "destination": "Ghost", "latency": 1}
        )
        assert response.status_code == 400
        assert "Ghost" in response.json()["error"]

    def test_duplicate_edge_is_400(self, api_client: APIClient) -> None:
        payload = {"source": "ServerA", "destination": "ServerB", "latency": 1}
        assert api_client.post(EDGES, payload).status_code == 201
        assert api_client.post(EDGES, {**payload, "latency": 9}).status_code == 400

    def test_list_is_a_bare_array_of_names(self, api_client: APIClient) -> None:
        create_edge(source="ServerA", destination="ServerB", latency=Decimal("2.5"))
        body = api_client.get(EDGES).json()
        assert isinstance(body, list)
        assert body[0] == {
            "id": Edge.objects.get().pk,
            "source": "ServerA",
            "destination": "ServerB",
            "latency": 2.5,
        }

    def test_delete_edge(self, api_client: APIClient) -> None:
        edge = create_edge(source="ServerA", destination="ServerB", latency=Decimal(1))
        assert api_client.delete(reverse("edge-detail", args=[edge.pk])).status_code == 204
        assert Edge.objects.count() == 0
        assert Node.objects.count() == 2  # nodes untouched
