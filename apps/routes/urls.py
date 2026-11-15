"""Route routes (contract paths have no trailing slash)."""

from django.urls import path

from .views import RouteHistoryView, ShortestRouteView

urlpatterns = [
    path("routes/shortest", ShortestRouteView.as_view(), name="route-shortest"),
    path("routes/history", RouteHistoryView.as_view(), name="route-history"),
]
