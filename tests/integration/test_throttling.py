"""Rate limiting (the API is open, so abuse protection is the only access control)."""

import pytest
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

pytestmark = pytest.mark.django_db


def test_routes_endpoint_is_rate_limited_with_error_envelope(
    api_client: APIClient, monkeypatch: pytest.MonkeyPatch, diamond: object
) -> None:
    monkeypatch.setitem(SimpleRateThrottle.THROTTLE_RATES, "routes", "2/min")
    payload = {"source": "A", "destination": "D"}
    codes = [api_client.post("/api/v1/routes/shortest", payload).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    assert "error" in api_client.post("/api/v1/routes/shortest", payload).json()


def test_health_check_is_never_throttled(
    api_client: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(SimpleRateThrottle.THROTTLE_RATES, "anon", "1/min")
    assert [api_client.get("/health").status_code for _ in range(5)] == [200] * 5
