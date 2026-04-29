"""
HyperFileLens Backend - Policies Views
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from licenses.quota import QuotaCheckMixin
from .models import BackupPolicy
from .serializers import BackupPolicySerializer, BackupPolicyCreateSerializer


class BackupPolicyViewSet(QuotaCheckMixin, viewsets.ModelViewSet):
    """ViewSet for managing backup policies."""
    queryset = BackupPolicy.objects.all()
    permission_classes = [IsAuthenticated]
    quota_resource_type = 'policies'  # 配额类型
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BackupPolicyCreateSerializer
        return BackupPolicySerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return BackupPolicy.objects.all()
        return BackupPolicy.objects.filter(user=user)
    
    def perform_create(self, serializer):
        self.check_quota_before_create()
        serializer.save(user=self.request.user, tenant=self.request.user.tenant)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user, tenant=self.request.user.tenant)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a policy."""
        policy = self.get_object()
        policy.is_active = True
        policy.save(update_fields=['is_active', 'updated_at'])
        return Response({'message': 'Policy activated'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a policy."""
        policy = self.get_object()
        policy.is_active = False
        policy.save(update_fields=['is_active', 'updated_at'])
        return Response({'message': 'Policy deactivated'})
