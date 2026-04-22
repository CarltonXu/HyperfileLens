"""
WebSocket Routing for Nodes Application

This module defines WebSocket URL patterns for real-time
node communication and task distribution.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Node WebSocket connection
    re_path(
        r'ws/nodes/(?P<node_id>[0-9a-f-]+)/$',
        consumers.NodeConsumer.as_asgi()
    ),

    # Task execution WebSocket
    re_path(
        r'ws/tasks/(?P<task_id>[0-9a-f-]+)/$',
        consumers.TaskConsumer.as_asgi()
    ),

    # Node status stream
    re_path(
        r'ws/status/$',
        consumers.StatusConsumer.as_asgi()
    ),
]
