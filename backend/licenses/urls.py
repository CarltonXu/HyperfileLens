"""
URL configuration for Licenses API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LicenseViewSet, LicenseAuditLogViewSet, check_feature

router = DefaultRouter()
router.register(r'licenses', LicenseViewSet, basename='license')
router.register(r'license-audit-logs', LicenseAuditLogViewSet, basename='license-audit-log')

urlpatterns = [
    path('', include(router.urls)),
    path('features/<str:feature_name>/', check_feature, name='check-feature'),
]
