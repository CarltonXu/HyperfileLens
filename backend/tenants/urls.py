"""
URL configuration for Tenants API
"""

from django.urls import path
from .views import TenantViewSet, TenantInvitationViewSet

urlpatterns = [
    # Tenant endpoints - more specific routes first
    path('', TenantViewSet.as_view({'get': 'list', 'post': 'create'}), name='tenant-list'),
    path('<uuid:pk>/stats/', TenantViewSet.as_view({'get': 'stats'}), name='tenant-stats'),
    path('<uuid:pk>/users/', TenantViewSet.as_view({'get': 'users', 'post': 'add_user'}), name='tenant-users'),
    path('<uuid:pk>/users/<int:user_id>/', TenantViewSet.as_view({'patch': 'update_user', 'delete': 'remove_user'}), name='tenant-user-detail'),
    path('<uuid:pk>/activate/', TenantViewSet.as_view({'post': 'activate'}), name='tenant-activate'),
    path('<uuid:pk>/deactivate/', TenantViewSet.as_view({'post': 'deactivate'}), name='tenant-deactivate'),
    path('<uuid:pk>/', TenantViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='tenant-detail'),
    # Invitation endpoints
    path('invitations/', TenantInvitationViewSet.as_view({'get': 'list', 'post': 'create'}), name='tenant-invitation-list'),
    path('invitations/<uuid:pk>/', TenantInvitationViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}), name='tenant-invitation-detail'),
]
