"""
Gateway URL Configuration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GatewayViewSet

router = DefaultRouter()
router.register(r'', GatewayViewSet, basename='gateway')

urlpatterns = [
    path('', include(router.urls)),
]
