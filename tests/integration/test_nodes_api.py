"""HTTP contract tests for ``/nodes``."""

from decimal import Decimal
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.edges.models import Edge
from apps.nodes.models import Node
from tests.factories import create_node

pytestmark = pytest.mark.django_db

NODES = "/api/v1/nodes"


class TestNodes:
    def test_create_returns_contract_shape(self, api_client: APIClient) -> None:
        response = api_client.post(NODES, {"name": "ServerA"})
        assert response.status_code == 201
        assert response.json() == {"id": Node.objects.get().pk, "name": "ServerA"}

    def test_name_is_trimmed(self, api_client: APIClient) -> None:
        assert api_client.post(NODES, {"name": "  ServerA  "}).json()["name"] == "ServerA"

    def test_duplicate_is_400_with_error_envelope(self, api_client: APIClient) -> None:
        api_client.post(NODES, {"name": "ServerA"})
        response = api_client.post(NODES, {"name": "ServerA"})
        assert response.status_code == 400
        assert "already exists" in response.json()["error"]

    @pytest.mark.parametrize(
        "payload",
        [{}, {"name": ""}, {"name": "   "}, {"name": None}, {"name": "x" * 101}, {"name": "a\nb"}],
    )
    def test_invalid_names_are_400(self, api_client: APIClient, payload: dict[str, Any]) -> None:
        response = api_client.post(NODES, payload)
        assert response.status_code == 400
        assert "name" in response.json()["details"]

    @pytest.mark.parametrize("bad", [123, 1.5, True, ["x"], {"a": 1}])
    def test_non_string_names_are_rejected_not_coerced(
        self, api_client: APIClient, bad: Any
    ) -> None:
        """``{"name": 123}`` must not silently create a node called "123"."""
        response = api_client.post(NODES, {"name": bad})
        assert response.status_code == 400
        assert "name" in response.json()["details"]
        assert Node.objects.count() == 0

    def test_malformed_json_is_400_and_wrong_media_type_is_415(self, api_client: APIClient) -> None:
        assert api_client.post(NODES, "{bad", content_type="application/json").status_code == 400
        assert api_client.post(NODES, "x", content_type="text/plain").status_code == 415

    def test_list_returns_a_bare_array_ordered_by_id(self, api_client: APIClient) -> None:
        for name in ("A", "B", "C"):
            create_node(name=name)
        body = api_client.get(NODES).json()
        assert isinstance(body, list)  # "List all nodes": a plain array, no envelope
        assert [n["name"] for n in body] == ["A", "B", "C"]
        assert set(body[0]) == {"id", "name"}

    def test_list_supports_limit_and_offset(self, api_client: APIClient) -> None:
        for name in ("A", "B", "C", "D"):
            create_node(name=name)
        page = api_client.get(NODES, {"limit": 2, "offset": 1}).json()
        assert [n["name"] for n in page] == ["B", "C"]
        assert api_client.get(NODES, {"offset": 99}).json() == []

    @pytest.mark.parametrize(
        "params", [{"limit": 0}, {"limit": "x"}, {"offset": -1}, {"offset": "x"}]
    )
    def test_list_rejects_invalid_paging_params(
        self, api_client: APIClient, params: dict[str, Any]
    ) -> None:
        assert api_client.get(NODES, params).status_code == 400

    def test_delete_removes_node_and_its_edges(
        self, api_client: APIClient, diamond: dict[str, Decimal]
    ) -> None:
        node_b = Node.objects.get(name="B")
        assert api_client.delete(f"{NODES}/{node_b.pk}").status_code == 204
        assert not Node.objects.filter(name="B").exists()
        remaining = {
            (e.source.name, e.destination.name)
            for e in Edge.objects.select_related("source", "destination")
        }
        assert remaining == {("A", "C"), ("C", "D")}  # A->B and B->D cascaded away

    def test_delete_unknown_is_404(self, api_client: APIClient) -> None:
        response = api_client.delete(f"{NODES}/999999")
        assert response.status_code == 404
        assert "error" in response.json()
