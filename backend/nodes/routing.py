"""
WebSocket Routing for Proxy Nodes

This module defines WebSocket URL patterns for real-time
proxy communication and task distribution.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Proxy WebSocket connection (new)
    re_path(
        r'ws/proxy/(?P<proxy_id>[0-9a-f-]+)/$',
        consumers.ProxyConsumer.as_asgi()
    ),

    # Node WebSocket connection (legacy alias)
    re_path(
        r'ws/nodes/(?P<node_id>[0-9a-f-]+)/$',
        consumers.NodeConsumer.as_asgi()
    ),

    # Task execution WebSocket
    re_path(
        r'ws/tasks/(?P<task_id>[0-9a-f-]+)/$',
        consumers.TaskConsumer.as_asgi()
    ),

    # System status stream
    re_path(
        r'ws/status/$',
        consumers.StatusConsumer.as_asgi()
    ),
]
