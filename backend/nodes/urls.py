"""
URL Configuration for Nodes Application

Defines URL patterns for node management, heartbeat,
and task assignment endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NodeViewSet, NodeHeartbeatView,
    NodeConnectionViewSet, NodeTaskAssignmentViewSet
)


# Create router for viewsets
router = DefaultRouter()
router.register(r'', NodeViewSet, basename='node')
router.register(r'connections', NodeConnectionViewSet, basename='node-connection')
router.register(r'assignments', NodeTaskAssignmentViewSet, basename='task-assignment')

urlpatterns = [
    # Heartbeat endpoint (no auth required for nodes)
    path('heartbeat/', NodeHeartbeatView.as_view(), name='node-heartbeat'),

    # Router URLs
    path('', include(router.urls)),
]
