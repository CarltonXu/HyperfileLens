"""
HyperFileLens Backend - Policies Views
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import BackupPolicy
from .serializers import BackupPolicySerializer, BackupPolicyCreateSerializer


class BackupPolicyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing backup policies."""
    queryset = BackupPolicy.objects.all()
    permission_classes = [IsAuthenticated]
    
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
        serializer.save(user=self.request.user)
    
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
