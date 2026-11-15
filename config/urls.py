"""Root URL configuration.

Layout::

    /health                        -> health check (unauthenticated, unversioned)
    /api/v1/...                    -> versioned public API (nodes + edges + routes)
"""

from django.urls import URLPattern, URLResolver, include, path

from common.views import HealthView

handler404 = "common.views.not_found"
handler500 = "common.views.server_error"

urlpatterns: list[URLPattern | URLResolver] = [
    path("health", HealthView.as_view()),
    path("api/v1/", include("apps.nodes.urls")),
    path("api/v1/", include("apps.edges.urls")),
    path("api/v1/", include("apps.routes.urls")),
]
