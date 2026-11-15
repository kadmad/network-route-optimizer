"""Settings shared by every environment (secrets and hosts come from environment variables)."""

from pathlib import Path
from typing import Any

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env()
_env_file = BASE_DIR / ".env"
if _env_file.is_file():
    environ.Env.read_env(str(_env_file))  # real environment variables win over .env

SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS: list[str] = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "rest_framework",
    "django_filters",
    "common",
    "apps.nodes",
    "apps.edges",
    "apps.routes",
]

# No auth, sessions or CSRF: the API is open and sets no cookies.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "common.middleware.RequestContextMiddleware",
    "django.middleware.common.CommonMiddleware",  # enforces ALLOWED_HOSTS
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
SILENCED_SYSTEM_CHECKS = ["security.W003"]  # CSRF middleware is absent on purpose

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES: dict[str, dict[str, Any]] = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["OPTIONS"] = {
    "pool": True,  # Django's native psycopg3 connection pool
    "options": "-c statement_timeout=5000",  # a runaway query cannot hold a connection forever
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TIME_ZONE = "UTC"

REST_FRAMEWORK: dict[str, Any] = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": "common.pagination.ArrayPagination",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "120/min", "routes": "30/min"},
    "NUM_PROXIES": env.int("NUM_PROXIES", default=0),  # set to 1 behind a load balancer
    "EXCEPTION_HANDLER": "common.exceptions.handler.api_exception_handler",
    "COERCE_DECIMAL_TO_STRING": False,  # latency is a JSON number, as in the contract
}

LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_context": {"()": "common.logging.RequestContextFilter"}},
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
            "rename_fields": {"asctime": "timestamp", "levelname": "level", "name": "logger"},
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_context"],
        },
    },
    "root": {"handlers": ["stdout"], "level": "INFO"},
    # Django logs each 4xx again after our access log line, without the request id.
    "loggers": {"django.request": {"level": "ERROR"}},
}
