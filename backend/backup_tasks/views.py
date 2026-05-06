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
from django.db.models import Sum, Count

from core.permissions import IsAdminOrOperator
from licenses.quota import QuotaCheckMixin
from audit_log.services import AuditService
from .models import BackupTask, BackupSnapshot
from .serializers import (
    BackupTaskSerializer,
    BackupTaskListSerializer,
    BackupTaskCreateSerializer,
    BackupTaskUpdateSerializer,
    BackupTaskExecuteSerializer,
    BackupTaskCancelSerializer,
    BackupTaskStatisticsSerializer,
    BackupSnapshotSerializer,
    BackupSnapshotListSerializer
)


class BackupTaskViewSet(QuotaCheckMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing backup tasks.
    
    Provides CRUD operations and custom actions for backup task management.
    A backup task connects a SourceResource to a Repository.
    """
    quota_resource_type = 'backup_tasks'
    queryset = BackupTask.objects.select_related(
        'source_resource', 'target_repository',
        'source_resource__bound_node', 'target_repository__bound_node',
        'user', 'schedule'
    ).prefetch_related('snapshots')
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return BackupTaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return BackupTaskUpdateSerializer
        elif self.action == 'list':
            return BackupTaskListSerializer
        elif self.action == 'statistics':
            return BackupTaskStatisticsSerializer
        return BackupTaskSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions and query params."""
        user = self.request.user
        
        # Base queryset with related data
        queryset = BackupTask.objects.select_related(
            'source_resource', 'target_repository',
            'source_resource__bound_node', 'target_repository__bound_node',
            'user', 'schedule'
        ).prefetch_related('snapshots')
        
        # Permission-based filtering
        if user.is_superuser or user.role.code == 'admin':
            pass  # Admin sees all
        elif user.role.code == 'operator':
            queryset = queryset.filter(user=user)
        else:
            queryset = queryset.filter(user=user)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by task type
        task_type = self.request.query_params.get('task_type')
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        
        # Filter by source resource
        source_resource = self.request.query_params.get('source_resource')
        if source_resource:
            queryset = queryset.filter(source_resource_id=source_resource)
        
        # Filter by target repository
        target_repository = self.request.query_params.get('target_repository')
        if target_repository:
            queryset = queryset.filter(target_repository_id=target_repository)
        
        # Filter by execution node (via source resource)
        execution_node = self.request.query_params.get('execution_node')
        if execution_node:
            queryset = queryset.filter(source_resource__bound_node_id=execution_node)
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        # Ordering
        ordering = self.request.query_params.get('ordering', '-created_at')
        if ordering:
            queryset = queryset.order_by(ordering)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create a new backup task with the current user."""
        self.check_quota_before_create()
        task = serializer.save(user=self.request.user, tenant=self.request.user.tenant)
        AuditService.log_backup_task_create(self.request, task, result='success')
    
    def perform_update(self, serializer):
        """Update a backup task."""
        task = serializer.save()
        changed_fields = list(serializer.validated_data.keys())
        AuditService.log_backup_task_update(self.request, task, changed_fields=changed_fields, result='success')
    
    def perform_destroy(self, instance):
        """Delete a backup task."""
        AuditService.log_backup_task_delete(self.request, instance, result='success')
        instance.delete()
    
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
        if task.status == BackupTask.STATUS_RUNNING and not serializer.validated_data.get('force'):
            return Response(
                {'error': 'Task is already running. Use force=true to override.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if source resource has a bound node
        if not task.source_resource.bound_node:
            return Response(
                {'error': 'Source resource has no bound node for execution'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if target repository has a bound node
        if not task.target_repository.bound_node:
            return Response(
                {'error': 'Target repository has no bound node for execution'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset task status if forcing
        if serializer.validated_data.get('force'):
            task.mark_pending()
        
        # Trigger async backup task
        try:
            from .tasks import execute_backup_task
            execute_backup_task.delay(str(task.id))
        except Exception as e:
            return Response(
                {'error': f'Failed to start backup task: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': 'Backup task started',
            'task_id': str(task.id),
            'execution_node': task.execution_node.name if task.execution_node else None
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running backup task."""
        task = self.get_object()
        serializer = BackupTaskCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if task.status != BackupTask.STATUS_RUNNING:
            return Response(
                {'error': 'Task is not running'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.status = BackupTask.STATUS_CANCELLED
        task.status_message = serializer.validated_data.get('reason', '')
        task.save(update_fields=['status', 'status_message', 'updated_at'])
        
        return Response({
            'message': 'Task cancelled',
            'task_id': str(task.id)
        })
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a running backup task."""
        task = self.get_object()
        
        if task.status != BackupTask.STATUS_RUNNING:
            return Response(
                {'error': 'Task is not running'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.status = BackupTask.STATUS_PAUSED
        task.save(update_fields=['status', 'updated_at'])
        
        return Response({
            'message': 'Task paused',
            'task_id': str(task.id)
        })
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume a paused backup task."""
        task = self.get_object()
        
        if task.status != BackupTask.STATUS_PAUSED:
            return Response(
                {'error': 'Task is not paused'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.status = BackupTask.STATUS_RUNNING
        task.save(update_fields=['status', 'updated_at'])
        
        return Response({
            'message': 'Task resumed',
            'task_id': str(task.id)
        })
    
    @action(detail=True, methods=['post'])
    def reset(self, request, pk=None):
        """Reset a failed or cancelled task to pending."""
        task = self.get_object()
        
        if task.status not in [BackupTask.STATUS_FAILED, BackupTask.STATUS_CANCELLED]:
            return Response(
                {'error': 'Only failed or cancelled tasks can be reset'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.mark_pending()
        
        return Response({
            'message': 'Task reset to pending',
            'task_id': str(task.id)
        })
    
    @action(detail=True, methods=['get'])
    def snapshots(self, request, pk=None):
        """List all snapshots for a backup task."""
        task = self.get_object()
        snapshots = BackupSnapshot.objects.filter(task=task).order_by('-created_at')
        
        # Pagination
        page = self.paginate_queryset(snapshots)
        if page is not None:
            serializer = BackupSnapshotListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = BackupSnapshotListSerializer(snapshots, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def detail(self, request, pk=None):
        """Get detailed task information including latest snapshot."""
        task = self.get_object()
        serializer = BackupTaskSerializer(task)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """
        Restore from a snapshot.
        
        Request body:
        {
            "snapshot_id": "uuid",
            "target_path": "/path/to/restore",
            "file_patterns": ["*.txt"],  // optional
            "target_node_id": "uuid"     // optional, defaults to source node
        }
        """
        task = self.get_object()
        snapshot_id = request.data.get('snapshot_id')
        target_path = request.data.get('target_path')
        file_patterns = request.data.get('file_patterns', [])
        target_node_id = request.data.get('target_node_id')
        
        if not snapshot_id or not target_path:
            return Response(
                {'error': 'snapshot_id and target_path are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        snapshot = get_object_or_404(BackupSnapshot, id=snapshot_id, task=task)
        
        # Trigger restore task
        try:
            from .tasks import execute_restore_task
            execute_restore_task.delay(
                str(snapshot.id),
                target_path,
                file_patterns,
                target_node_id
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to start restore task: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': 'Restore task started',
            'snapshot_id': str(snapshot.id)
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get backup task statistics."""
        queryset = BackupTask.objects.all()
        
        # Filter by user role
        user = request.user
        if not (user.is_superuser or user.role.code == 'admin'):
            queryset = queryset.filter(user=user)
        
        # Calculate statistics
        stats = queryset.aggregate(
            total_tasks=Count('id'),
            total_size=Sum('total_size'),
            total_backed_up_size=Sum('backed_up_size'),
            total_files=Sum('total_files'),
            total_backed_up_files=Sum('backed_up_files'),
        )
        
        # Count by status
        status_counts = {
            'pending_tasks': queryset.filter(status=BackupTask.STATUS_PENDING).count(),
            'running_tasks': queryset.filter(status=BackupTask.STATUS_RUNNING).count(),
            'completed_tasks': queryset.filter(status=BackupTask.STATUS_COMPLETED).count(),
            'failed_tasks': queryset.filter(status=BackupTask.STATUS_FAILED).count(),
            'cancelled_tasks': queryset.filter(status=BackupTask.STATUS_CANCELLED).count(),
            'paused_tasks': queryset.filter(status=BackupTask.STATUS_PAUSED).count(),
        }
        
        # Calculate average duration for completed tasks
        completed_tasks = queryset.filter(
            status=BackupTask.STATUS_COMPLETED,
            started_at__isnull=False,
            completed_at__isnull=False
        )
        
        avg_duration = None
        if completed_tasks.exists():
            durations = []
            for task in completed_tasks:
                if task.started_at and task.completed_at:
                    durations.append((task.completed_at - task.started_at).total_seconds())
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        return Response({
            **stats,
            **status_counts,
            'avg_duration': avg_duration,
        })


class BackupSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing backup snapshots."""
    
    queryset = BackupSnapshot.objects.select_related('task', 'repository')
    serializer_class = BackupSnapshotSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter snapshots based on user permissions."""
        user = self.request.user
        queryset = BackupSnapshot.objects.select_related('task', 'repository')
        
        # Permission-based filtering
        if user.is_superuser or user.role.code == 'admin':
            pass  # Admin sees all
        elif user.role.code == 'operator':
            queryset = queryset.filter(task__user=user)
        else:
            queryset = queryset.filter(task__user=user)
        
        # Filter by task
        task_id = self.request.query_params.get('task')
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        
        # Filter by repository
        repository_id = self.request.query_params.get('repository')
        if repository_id:
            queryset = queryset.filter(repository_id=repository_id)
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return BackupSnapshotListSerializer
        return BackupSnapshotSerializer
