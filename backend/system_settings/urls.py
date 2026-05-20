"""
URL configuration for System Settings Application
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ai_query.views import AIProviderViewSet
from .views import SystemSettingViewSet, SMTPConfigViewSet, EmailTemplateViewSet

router = DefaultRouter()
router.register(r'settings', SystemSettingViewSet, basename='system-setting')
router.register(r'smtp', SMTPConfigViewSet, basename='smtp-config')
router.register(r'email-templates', EmailTemplateViewSet, basename='email-template')
router.register(r'ai-providers', AIProviderViewSet, basename='system-ai-provider')

urlpatterns = [
    path('', include(router.urls)),
]
