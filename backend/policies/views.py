"""
HyperFileLens Backend - Policies Views
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from licenses.quota import QuotaCheckMixin
from audit_log.services import AuditService
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
        """Create a new backup policy."""
        self.check_quota_before_create()
        policy = serializer.save(user=self.request.user, tenant=self.request.user.tenant)
        AuditService.log_policy_create(self.request, policy, result='success')
    
    def perform_update(self, serializer):
        """Update a backup policy."""
        policy = serializer.save()
        changed_fields = list(serializer.validated_data.keys())
        AuditService.log_policy_update(self.request, policy, changed_fields=changed_fields, result='success')
    
    def perform_destroy(self, instance):
        """Delete a backup policy."""
        AuditService.log_policy_delete(self.request, instance, result='success')
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a policy."""
        policy = self.get_object()
        policy.is_active = True
        policy.save(update_fields=['is_active', 'updated_at'])
        AuditService.log_policy_update(request, policy, changed_fields=['is_active'], result='success')
        return Response({'message': 'Policy activated'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a policy."""
        policy = self.get_object()
        policy.is_active = False
        policy.save(update_fields=['is_active', 'updated_at'])
        AuditService.log_policy_update(request, policy, changed_fields=['is_active'], result='success')
        return Response({'message': 'Policy deactivated'})
