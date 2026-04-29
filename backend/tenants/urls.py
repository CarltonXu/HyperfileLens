"""
URL configuration for Tenants API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantViewSet, TenantInvitationViewSet

router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'invitations', TenantInvitationViewSet, basename='tenant-invitation')

urlpatterns = [
    path('', include(router.urls)),
]
