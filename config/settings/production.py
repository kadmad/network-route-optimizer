"""Production settings: secure by default, fail fast on unsafe configuration."""

from django.core.exceptions import ImproperlyConfigured

from .base import *
from .base import ALLOWED_HOSTS, env

# --------------------------------------------------------------------------- #
# Fail fast: refuse to boot with a configuration that is unsafe in production.
# --------------------------------------------------------------------------- #
if not ALLOWED_HOSTS:
    msg = "DJANGO_ALLOWED_HOSTS must be set in production."
    raise ImproperlyConfigured(msg)

# --------------------------------------------------------------------------- #
# Transport security (TLS is terminated by the load balancer / reverse proxy)
# --------------------------------------------------------------------------- #
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Toggle only for plain-HTTP smoke tests (e.g. `make up` on a laptop).
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_REDIRECT_EXEMPT = [r"^health$"]  # health checks reach the container over plain HTTP
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31_536_000)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
