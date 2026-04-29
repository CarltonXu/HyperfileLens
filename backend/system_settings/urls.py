"""
URL configuration for System Settings Application
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SystemSettingViewSet, SMTPConfigViewSet, EmailTemplateViewSet

router = DefaultRouter()
router.register(r'settings', SystemSettingViewSet, basename='system-setting')
router.register(r'smtp', SMTPConfigViewSet, basename='smtp-config')
router.register(r'email-templates', EmailTemplateViewSet, basename='email-template')

urlpatterns = [
    path('', include(router.urls)),
]
