"""
HyperFileLens Backend - AI Query URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIQueryViewSet


router = DefaultRouter()
router.register(r'queries', AIQueryViewSet, basename='ai-query')

urlpatterns = [
    path('', include(router.urls)),
]
