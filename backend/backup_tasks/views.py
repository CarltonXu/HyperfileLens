"""
HyperFileLens Backend - Backup Tasks Views

This module provides REST API views for backup task management.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404

from core.permissions import IsAdminOrOperator
from .models import BackupTask, BackupSnapshot
from .serializers import (
    BackupTaskSerializer,
    BackupTaskCreateSerializer,
    BackupTaskUpdateSerializer,
    BackupTaskExecuteSerializer,
    BackupSnapshotSerializer,
    BackupSnapshotListSerializer
)
from .tasks import execute_backup_task


class BackupTaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing backup tasks.
    
    Provides CRUD operations and custom actions for backup task management.
    """
    queryset = BackupTask.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return BackupTaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return BackupTaskUpdateSerializer
        return BackupTaskSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return BackupTask.objects.all()
        elif user.role == 'operator':
            return BackupTask.objects.filter(user=user)
        return BackupTask.objects.filter(user=user)
    
    def perform_create(self, serializer):
        """Create a new backup task with the current user."""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        Execute a backup task immediately.
        
        This triggers the backup process asynchronously via Celery.
        """
        task = self.get_object()
        serializer = BackupTaskExecuteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if task is already running
        if task.status == 'running' and not serializer.validated_data.get('force'):
            return Response(
                {'error': 'Task is already running'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trigger async backup task
        execute_backup_task.delay(str(task.id))
        
        return Response({
            'message': 'Backup task started',
            'task_id': str(task.id)
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running backup task."""
        task = self.get_object()
        
        if task.status != 'running':
            return Response(
                {'error': 'Task is not running'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.status = 'cancelled'
        task.save(update_fields=['status', 'updated_at'])
        
        return Response({'message': 'Task cancelled'})
    
    @action(detail=True, methods=['get'])
    def snapshots(self, request, pk=None):
        """List all snapshots for a backup task."""
        task = self.get_object()
        snapshots = BackupSnapshot.objects.filter(task=task)
        serializer = BackupSnapshotListSerializer(snapshots, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """
        Restore from a snapshot.
        
        Request body:
        {
            "snapshot_id": "uuid",
            "target_path": "/path/to/restore",
            "file_patterns": ["*.txt"]  // optional, restore specific files
        }
        """
        task = self.get_object()
        snapshot_id = request.data.get('snapshot_id')
        target_path = request.data.get('target_path')
        file_patterns = request.data.get('file_patterns')
        
        if not snapshot_id or not target_path:
            return Response(
                {'error': 'snapshot_id and target_path are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        snapshot = get_object_or_404(BackupSnapshot, id=snapshot_id, task=task)
        
        # Trigger restore task
        from .tasks import execute_restore_task
        execute_restore_task.delay(
            str(snapshot.id),
            target_path,
            file_patterns
        )
        
        return Response({
            'message': 'Restore task started',
            'snapshot_id': str(snapshot.id)
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get backup task statistics."""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'pending': queryset.filter(status='pending').count(),
            'running': queryset.filter(status='running').count(),
            'completed': queryset.filter(status='completed').count(),
            'failed': queryset.filter(status='failed').count(),
            'total_size': sum(t.total_size for t in queryset),
            'total_backed_up_size': sum(t.backed_up_size for t in queryset),
        }
        
        return Response(stats)
