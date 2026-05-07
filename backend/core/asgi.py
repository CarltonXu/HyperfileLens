"""
ASGI config for HyperFileLens project.

It exposes the ASGI callable as a module-level variable named ``application``.

This configuration supports:
- Django's ASGI application
- WebSocket connections for real-time node communication
- Channel layers for WebSocket routing

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import WebSocket URL patterns after Django is set up
from nodes.routing import websocket_urlpatterns as nodes_websocket_urlpatterns
from gateways.routing import websocket_urlpatterns as gateways_websocket_urlpatterns

# Combine all WebSocket URL patterns
all_websocket_urlpatterns = nodes_websocket_urlpatterns + gateways_websocket_urlpatterns

# Application definition
application = ProtocolTypeRouter({
    # Django's HTTP ASGI application
    'http': django_asgi_app,

    # WebSocket connections
    'websocket': AuthMiddlewareStack(
        URLRouter(
            all_websocket_urlpatterns
        )
    ),
})
