"""
URL Configuration for Proxy Nodes Application

Defines URL patterns for proxy management, installation,
heartbeat, and task assignment endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProxyViewSet, ProxyHeartbeatView, ProxyRegisterView,
    ProxyTaskViewSet, NodeConnectionViewSet
)


# Create router for viewsets
router = DefaultRouter()
router.register(r'', ProxyViewSet, basename='proxy')
router.register(r'tasks', ProxyTaskViewSet, basename='proxy-task')
router.register(r'connections', NodeConnectionViewSet, basename='proxy-connection')

urlpatterns = [
    # Registration endpoint (no auth required for initial setup)
    path('register/', ProxyRegisterView.as_view(), name='proxy-register'),

    # Heartbeat endpoint (no auth required for proxies)
    path('heartbeat/', ProxyHeartbeatView.as_view(), name='proxy-heartbeat'),

    # Router URLs
    path('', include(router.urls)),
]
