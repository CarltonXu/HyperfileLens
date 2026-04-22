"""
HyperFileLens Backend - Audit Log Views
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import AuditLog
from .serializers import AuditLogSerializer, AuditLogFilterSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs.
    
    Read-only access to audit logs.
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['action', 'resource_type', 'user']
    ordering_fields = ['timestamp', 'action']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """Filter queryset for admin users only."""
        user = self.request.user
        if not (user.is_superuser or user.role == 'admin'):
            return AuditLog.objects.none()
        return AuditLog.objects.all()
    
    def filter_queryset(self, queryset):
        """Apply custom filters."""
        queryset = super().filter_queryset(queryset)
        
        # Apply date range filter
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset
