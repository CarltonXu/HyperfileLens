"""
HyperFileLens Backend - AI Insights URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AIProviderViewSet,
    AIQueryViewSet,
    gateway_mount_status,
    gateway_index_status,
    gateway_ai_query,
    gateway_rebuild_index,
    gateway_list_files,
    insights_overview,
    sensitive_data_scan,
    content_profile,
    data_heatmap,
    redundancy_analysis,
    smart_search,
    scope_options,
)


router = DefaultRouter()
router.register(r'queries', AIQueryViewSet, basename='ai-query')
router.register(r'providers', AIProviderViewSet, basename='ai-provider')

urlpatterns = [
    path('', include(router.urls)),
    
    # Gateway proxy endpoints
    path('gateway/mount-status/', gateway_mount_status, name='gateway-mount-status'),
    path('gateway/index-status/', gateway_index_status, name='gateway-index-status'),
    path('gateway/ai-query/', gateway_ai_query, name='gateway-ai-query'),
    path('gateway/rebuild-index/', gateway_rebuild_index, name='gateway-rebuild-index'),
    path('gateway/files/', gateway_list_files, name='gateway-files'),
    
    # AI Insights feature endpoints
    path('overview/', insights_overview, name='insights-overview'),
    path('scopes/options/', scope_options, name='ai-insights-scope-options'),
    path('sensitive-data/', sensitive_data_scan, name='sensitive-data-scan'),
    path('content-profile/', content_profile, name='content-profile'),
    path('data-heatmap/', data_heatmap, name='data-heatmap'),
    path('redundancy/', redundancy_analysis, name='redundancy-analysis'),
    path('smart-search/', smart_search, name='smart-search'),
]
