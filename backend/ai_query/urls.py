"""
HyperFileLens Backend - AI Query URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AIQueryViewSet,
    gateway_mount_status,
    gateway_index_status,
    gateway_ai_query,
    gateway_rebuild_index,
    gateway_list_files
)


router = DefaultRouter()
router.register(r'queries', AIQueryViewSet, basename='ai-query')

urlpatterns = [
    path('', include(router.urls)),
    # Gateway proxy endpoints
    path('gateway/mount-status/', gateway_mount_status, name='gateway-mount-status'),
    path('gateway/index-status/', gateway_index_status, name='gateway-index-status'),
    path('gateway/ai-query/', gateway_ai_query, name='gateway-ai-query'),
    path('gateway/rebuild-index/', gateway_rebuild_index, name='gateway-rebuild-index'),
    path('gateway/files/', gateway_list_files, name='gateway-files'),
]
