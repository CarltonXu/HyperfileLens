"""
URL configuration for Tenants API
"""

from django.urls import path
from .views import TenantViewSet, TenantInvitationViewSet

urlpatterns = [
    # Tenant endpoints
    path('', TenantViewSet.as_view({'get': 'list', 'post': 'create'}), name='tenant-list'),
    path('<uuid:pk>/', TenantViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='tenant-detail'),
    path('<uuid:pk>/stats/', TenantViewSet.as_view({'get': 'stats'}), name='tenant-stats'),
    path('<uuid:pk>/users/', TenantViewSet.as_view({'get': 'users'}), name='tenant-users'),
    path('<uuid:pk>/add-user/', TenantViewSet.as_view({'post': 'add_user'}), name='tenant-add-user'),
    path('<uuid:pk>/remove-user/', TenantViewSet.as_view({'post': 'remove_user'}), name='tenant-remove-user'),
    path('<uuid:pk>/activate/', TenantViewSet.as_view({'post': 'activate'}), name='tenant-activate'),
    path('<uuid:pk>/deactivate/', TenantViewSet.as_view({'post': 'deactivate'}), name='tenant-deactivate'),
    # Invitation endpoints
    path('invitations/', TenantInvitationViewSet.as_view({'get': 'list', 'post': 'create'}), name='tenant-invitation-list'),
    path('invitations/<uuid:pk>/', TenantInvitationViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}), name='tenant-invitation-detail'),
]
