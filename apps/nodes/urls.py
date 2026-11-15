"""Node routes (contract paths have no trailing slash)."""

from django.urls import path

from .views import NodeDestroyView, NodeListCreateView

urlpatterns = [
    path("nodes", NodeListCreateView.as_view(), name="node-list"),
    path("nodes/<int:pk>", NodeDestroyView.as_view(), name="node-detail"),
]
