"""
HyperFileLens Backend - Recovery Tasks Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import RecoveryTask
from .serializers import RecoveryTaskSerializer, RecoveryTaskCreateSerializer
from .tasks import execute_recovery_task
from licenses.quota import QuotaCheckMixin


class RecoveryTaskViewSet(QuotaCheckMixin, viewsets.ModelViewSet):
    """ViewSet for managing recovery tasks."""
    queryset = RecoveryTask.objects.all()
    permission_classes = [IsAuthenticated]
    quota_resource_type = 'recovery_tasks'
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RecoveryTaskCreateSerializer
        return RecoveryTaskSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = RecoveryTask.objects.select_related('user', 'tenant')
        
        # Superuser can see all recovery tasks
        if user.is_superuser:
            return queryset
        # Filter by tenant for tenant users
        if user.tenant:
            return queryset.filter(tenant=user.tenant)
        # Users without tenant can only see their own recovery tasks
        return queryset.filter(user=user)
    
    def perform_create(self, serializer):
        self.check_quota_before_create()
        serializer.save(user=self.request.user, tenant=self.request.user.tenant)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute a recovery task immediately."""
        task = self.get_object()
        
        if task.status == 'running':
            return Response(
                {'error': 'Task is already running'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trigger async recovery task
        execute_recovery_task.delay(str(task.id))
        
        return Response({
            'message': 'Recovery task started',
            'task_id': str(task.id)
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running recovery task."""
        task = self.get_object()
        
        if task.status != 'running':
            return Response(
                {'error': 'Task is not running'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.status = 'cancelled'
        task.save(update_fields=['status', 'updated_at'])
        
        return Response({'message': 'Task cancelled'})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get recovery task statistics."""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'pending': queryset.filter(status='pending').count(),
            'running': queryset.filter(status='running').count(),
            'completed': queryset.filter(status='completed').count(),
            'failed': queryset.filter(status='failed').count(),
        }
        
        return Response(stats)
