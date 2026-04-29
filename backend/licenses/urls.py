"""
License URL Configuration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import LicenseViewSet, QuotaViewSet

router = DefaultRouter()
router.register(r'', LicenseViewSet, basename='license')
router.register(r'quota', QuotaViewSet, basename='quota')

urlpatterns = [
    path('', include(router.urls)),
]
