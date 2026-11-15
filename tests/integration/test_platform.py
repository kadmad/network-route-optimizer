"""Cross-cutting platform behaviour: DB pool, request ids, health, JSON error handlers."""

import logging
from unittest import mock

import pytest
from django.db import connection
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_database_uses_the_native_psycopg_connection_pool() -> None:
    with connection.cursor():
        pass
    assert connection.pool is not None  # type: ignore[attr-defined]
    assert connection.settings_dict["CONN_MAX_AGE"] == 0


class TestRequestId:
    def test_generated_when_absent(self, api_client: APIClient) -> None:
        assert len(api_client.get("/health").headers["X-Request-ID"]) == 32

    def test_well_formed_inbound_id_is_propagated(self, api_client: APIClient) -> None:
        response = api_client.get("/health", headers={"X-Request-ID": "trace-abc_123"})
        assert response.headers["X-Request-ID"] == "trace-abc_123"

    @pytest.mark.parametrize("hostile", ["a b", "x" * 65, "id;DROP", "<script>"])
    def test_malformed_inbound_id_is_replaced_not_logged(
        self, api_client: APIClient, hostile: str
    ) -> None:
        response = api_client.get("/health", headers={"X-Request-ID": hostile})
        assert response.headers["X-Request-ID"] != hostile

    def test_access_log_line_is_emitted_with_status_and_latency(
        self, api_client: APIClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="common.access"):
            api_client.get("/api/v1/nodes")
        record = next(r for r in caplog.records if r.name == "common.access")
        assert (record.method, record.path, record.status) == ("GET", "/api/v1/nodes", 200)  # type: ignore[attr-defined]
        assert record.duration_ms >= 0  # type: ignore[attr-defined]

    def test_health_checks_are_not_logged(
        self, api_client: APIClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="common.access"):
            api_client.get("/health")
        assert not [r for r in caplog.records if r.name == "common.access"]

    def test_newline_in_the_path_cannot_forge_a_log_line(
        self, api_client: APIClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="common.access"):
            api_client.get("/api/v1/nodes/%0AFAKE%20LINE")
        record = next(r for r in caplog.records if r.name == "common.access")
        assert "\n" not in record.getMessage()
        assert "%0A" in record.path  # type: ignore[attr-defined]


def test_host_header_outside_allowed_hosts_is_rejected(api_client: APIClient) -> None:
    assert api_client.get("/health", HTTP_HOST="evil.example").status_code == 400


def test_unknown_route_returns_json_404(api_client: APIClient, settings: object) -> None:
    settings.DEBUG = False  # type: ignore[attr-defined]  # DEBUG=True renders Django's HTML page
    response = api_client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"error": "Not found."}


def test_unexpected_exception_returns_json_500_without_leaking_details(
    api_client: APIClient, settings: object
) -> None:
    settings.DEBUG = False  # type: ignore[attr-defined]
    api_client.raise_request_exception = False
    with mock.patch("apps.nodes.views.NodeListCreateView.list", side_effect=RuntimeError("secret")):
        response = api_client.get("/api/v1/nodes")
    assert response.status_code == 500
    assert response.json() == {"error": "Internal server error."}
