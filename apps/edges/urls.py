"""Edge routes (contract paths have no trailing slash)."""

from django.urls import path

from .views import EdgeDestroyView, EdgeListCreateView

urlpatterns = [
    path("edges", EdgeListCreateView.as_view(), name="edge-list"),
    path("edges/<int:pk>", EdgeDestroyView.as_view(), name="edge-detail"),
]
