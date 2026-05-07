"""
WebSocket Routing for Gateway Nodes

This module defines WebSocket URL patterns for real-time
gateway communication and task distribution.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Gateway WebSocket connection
    re_path(
        r'ws/gateway/(?P<gateway_id>[0-9a-f-]+)/$',
        consumers.GatewayConsumer.as_asgi()
    ),

    # Task monitoring WebSocket
    re_path(
        r'ws/gateway-task/(?P<task_id>[0-9a-f-]+)/$',
        consumers.TaskConsumer.as_asgi()
    ),

    # System status stream
    re_path(
        r'ws/gateway-status/$',
        consumers.StatusConsumer.as_asgi()
    ),
]
