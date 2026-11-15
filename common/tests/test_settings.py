"""Production settings must fail fast on unsafe configuration and enable hardening."""

import importlib
import sys
from collections.abc import Callable
from types import ModuleType

import pytest
from django.core.exceptions import ImproperlyConfigured

PROD = "config.settings.production"


@pytest.fixture
def import_production(monkeypatch: pytest.MonkeyPatch) -> Callable[[], ModuleType]:
    """Import production settings fresh, restoring ``sys.modules`` afterwards."""
    for name in (PROD, "config.settings.base"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    return lambda: importlib.import_module(PROD)


def test_refuses_to_boot_without_allowed_hosts(
    monkeypatch: pytest.MonkeyPatch, import_production: Callable[[], ModuleType]
) -> None:
    monkeypatch.delenv("DJANGO_ALLOWED_HOSTS", raising=False)
    with pytest.raises(ImproperlyConfigured, match="DJANGO_ALLOWED_HOSTS"):
        import_production()


def test_secure_configuration_enables_hardening(
    monkeypatch: pytest.MonkeyPatch, import_production: Callable[[], ModuleType]
) -> None:
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "api.example.com")
    module = import_production()
    assert module.SECURE_SSL_REDIRECT is True
    assert module.SECURE_HSTS_SECONDS >= 31_536_000
