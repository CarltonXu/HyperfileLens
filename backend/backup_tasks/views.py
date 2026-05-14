"""
HyperFileLens Backend - Backup Tasks Views

This module provides REST API views for backup task management.
"""

import time
import uuid

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
from nodes.models import ProxyTask
from nodes.proxy_service import ProxyService
from repository.models import Repository
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
    BackupSnapshotListSerializer,
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
            'user', 'schedule', 'tenant'
        ).prefetch_related('snapshots')
        
        # Permission-based filtering by tenant
        if user.is_superuser:
            pass  # Superuser sees all
        elif user.tenant:
            queryset = queryset.filter(tenant=user.tenant)
        else:
            # Users without tenant can only see their own tasks
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
        if not task.is_enabled:
            return Response(
                {'error': 'Task is disabled. Enable it before execution.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if source resource has a bound node
        if not task.source_resource.bound_node:
            return Response(
                {'error': 'Source resource has no bound node for execution'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        execution_node = task.execution_node
        is_online, error_msg = ProxyService.check_proxy_connectivity(str(execution_node.id))
        if not is_online:
            return Response(
                {'error': f'Execution proxy is not reachable: {error_msg}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset task status if forcing
        if serializer.validated_data.get('force'):
            task.mark_pending()
        
        repository_config = self._build_repository_config(task.target_repository)
        source_path = self._resolve_source_path(task)
        if not source_path:
            return Response(
                {'error': 'Backup task has no source path to execute'},
                status=status.HTTP_400_BAD_REQUEST
            )

        repository_password = (
            serializer.validated_data.get('repository_password')
            or task.target_repository.get_kopia_password()
        )
        if not repository_password:
            return Response(
                {
                    'error': (
                        'Repository password is not saved. '
                        'Please save the Kopia repository password before executing backup tasks.'
                    ),
                    'error_code': 'REPOSITORY_PASSWORD_REQUIRED',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        proxy_task = ProxyTask.objects.create(
            proxy=execution_node,
            task_type=ProxyTask.TaskType.BACKUP,
            parameters={
                'backup_task_id': str(task.id),
                'backup_task_name': task.name,
                'source_resource_id': str(task.source_resource_id),
                'repository_id': str(task.target_repository_id),
                'source_path': source_path,
                'backup_paths': task.backup_paths,
                'exclude_patterns': task.exclude_patterns,
                'include_patterns': task.include_patterns,
                'task_type': serializer.validated_data.get('task_type') or task.task_type,
                'priority': task.priority,
            },
            repository_id=task.target_repository_id,
            source_resource_id=task.source_resource_id,
            status=ProxyTask.TaskStatus.PENDING,
            timeout_seconds=task.checkpoint_interval_minutes * 60 if task.checkpoint_interval_minutes else 3600,
        )
        proxy_task.dispatch()

        payload = {
            'task_id': str(proxy_task.id),
            'backup_task_id': str(task.id),
            'source_resource_id': str(task.source_resource_id),
            'repository_id': str(task.target_repository_id),
            'source_path': source_path,
            'backup_paths': task.backup_paths,
            'exclude_patterns': task.exclude_patterns,
            'include_patterns': task.include_patterns,
            'repository': repository_config,
            'password': repository_password,
            'task_type': serializer.validated_data.get('task_type') or task.task_type,
            'priority': task.priority,
            'compression_enabled': task.compression_enabled,
            'compression_type': task.compression_type,
            'compression_level': task.compression_level,
            'verify_checksum': task.verify_checksum,
            'max_concurrent_files': task.max_concurrent_files,
            'bandwidth_limit_kbps': task.bandwidth_limit_kbps,
            'timestamp': timezone.now().isoformat(),
        }

        if not ProxyService.send_to_proxy(
            str(execution_node.id),
            {
                'type': 'backup',
                'id': str(proxy_task.id),
                'timestamp': timezone.now().isoformat(),
                'payload': payload,
            },
        ):
            proxy_task.fail('Failed to send backup command to proxy')
            return Response(
                {'error': 'Failed to send backup command to proxy'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        task.status = BackupTask.STATUS_RUNNING
        task.progress = 0
        task.status_message = 'Backup command dispatched to proxy'
        task.error_message = ''
        task.started_at = timezone.now()
        task.last_run_time = timezone.now()
        task.save(update_fields=[
            'status', 'progress', 'status_message', 'error_message',
            'started_at', 'last_run_time', 'updated_at'
        ])
        
        return Response({
            'message': 'Backup task started',
            'task_id': str(task.id),
            'proxy_task_id': str(proxy_task.id),
            'execution_node': task.execution_node.name if task.execution_node else None
        })

    def _resolve_source_path(self, task):
        """Return the first executable source path for the current proxy implementation."""
        if task.backup_paths:
            return task.backup_paths[0]
        source = task.source_resource
        if not source:
            return ''
        config = source.config or {}
        if source.resource_type == 'local':
            return config.get('root_path') or config.get('path') or '/'
        if source.resource_type == 's3':
            return config.get('prefix') or '/'
        return source.mount_point or source.get_effective_mount_point()

    def _build_repository_config(self, repo):
        """Build the repository payload expected by the Go proxy Kopia client."""
        config = repo.config or {}
        credentials = repo.get_decrypted_credentials() if hasattr(repo, 'get_decrypted_credentials') else (repo.credentials or {})
        repository_config = {
            'id': str(repo.id),
            'type': repo.repo_type,
        }

        if repo.repo_type == Repository.TYPE_LOCAL:
            repository_config['path'] = config.get('path') or repo.path or ''
        elif repo.repo_type in (Repository.TYPE_NAS, Repository.TYPE_NFS):
            server = config.get('server') or config.get('nas_server') or ''
            export_path = config.get('export_path') or config.get('path') or config.get('nas_path') or repo.path or ''
            mount_type = config.get('mount_type') or config.get('nas_type') or 'nfs'
            mount_path = config.get('mount_path') or ''
            repository_config.update({
                'path': mount_path or export_path,
                'server': server,
                'export_path': export_path,
                'nas_server': server,
                'nas_path': export_path,
                'mount_type': mount_type,
                'mount_path': mount_path,
                'mount_options': config.get('mount_options', ''),
                'username': credentials.get('username', ''),
                'password': credentials.get('password', ''),
            })
        elif repo.repo_type == Repository.TYPE_S3:
            bucket = config.get('bucket') or repo.path or ''
            prefix = (config.get('prefix') or '').strip('/')
            repository_url = config.get('url') or config.get('repository_url') or (
                f"s3://{bucket}/{prefix}" if prefix else f"s3://{bucket}"
            )
            repository_config.update({
                'path': repository_url,
                'url': repository_url,
                'endpoint': config.get('endpoint', ''),
                'bucket': bucket,
                'region': config.get('region', 'us-east-1'),
                'access_key': credentials.get('access_key', config.get('access_key', '')),
                'secret_key': credentials.get('secret_key', config.get('secret_key', '')),
                'prefix': prefix,
                'use_tls': config.get('use_tls', True),
                'url_style': config.get('url_style', 'virtual'),
            })
        else:
            repository_config['path'] = config.get('path') or repo.path or ''

        return repository_config
    
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
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'status_message', 'completed_at', 'updated_at'])

        proxy_tasks = ProxyTask.objects.filter(
            parameters__backup_task_id=str(task.id),
            status__in=[
                ProxyTask.TaskStatus.PENDING,
                ProxyTask.TaskStatus.DISPATCHED,
                ProxyTask.TaskStatus.ACCEPTED,
                ProxyTask.TaskStatus.RUNNING,
            ],
        ).select_related('proxy')
        for proxy_task in proxy_tasks:
            proxy_task.cancel()
            ProxyService.send_to_proxy(
                str(proxy_task.proxy_id),
                {
                    'type': 'cancel',
                    'id': str(proxy_task.id),
                    'timestamp': timezone.now().isoformat(),
                    'payload': {
                        'task_id': str(proxy_task.id),
                        'reason': serializer.validated_data.get('reason', 'Task cancelled by user'),
                    },
                },
            )
        
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

    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable a backup task."""
        task = self.get_object()
        task.is_enabled = True
        task.save(update_fields=['is_enabled', 'updated_at'])
        return Response({'message': 'Task enabled', 'task_id': str(task.id)})

    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable a backup task and cancel it if it is currently running."""
        task = self.get_object()
        task.is_enabled = False
        update_fields = ['is_enabled', 'updated_at']
        if task.status == BackupTask.STATUS_RUNNING:
            task.status = BackupTask.STATUS_CANCELLED
            task.status_message = 'Task disabled by user'
            task.completed_at = timezone.now()
            update_fields.extend(['status', 'status_message', 'completed_at'])
        task.save(update_fields=update_fields)
        return Response({'message': 'Task disabled', 'task_id': str(task.id)})
    
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
    def runs(self, request, pk=None):
        """List execution runs for a backup task."""
        task = self.get_object()
        proxy_tasks = ProxyTask.objects.filter(
            parameters__backup_task_id=str(task.id),
            task_type=ProxyTask.TaskType.BACKUP,
        ).select_related('proxy').order_by('-created_at')

        def duration_seconds(proxy_task):
            if not proxy_task.started_at:
                return None
            end = proxy_task.completed_at or timezone.now()
            return (end - proxy_task.started_at).total_seconds()

        def normalize(proxy_task):
            result = proxy_task.result or {}
            return {
                'id': str(proxy_task.id),
                'source': 'backup',
                'name': f'Backup Run - {task.name}',
                'task_type': proxy_task.task_type,
                'status': proxy_task.status,
                'progress': proxy_task.progress,
                'message': proxy_task.progress_message or proxy_task.error_message or '',
                'proxy_id': str(proxy_task.proxy_id),
                'proxy_name': proxy_task.proxy.name if proxy_task.proxy_id else '',
                'repository_id': str(proxy_task.repository_id) if proxy_task.repository_id else None,
                'source_resource_id': str(proxy_task.source_resource_id) if proxy_task.source_resource_id else None,
                'created_at': proxy_task.created_at,
                'dispatched_at': proxy_task.dispatched_at,
                'started_at': proxy_task.started_at,
                'completed_at': proxy_task.completed_at,
                'duration_seconds': duration_seconds(proxy_task),
                'progress_message': proxy_task.progress_message,
                'current_file': proxy_task.current_file,
                'total_files': proxy_task.total_files or result.get('total_files') or result.get('file_count') or 0,
                'processed_files': proxy_task.processed_files or result.get('processed_files') or 0,
                'total_bytes': proxy_task.total_bytes or result.get('total_bytes') or result.get('total_size') or 0,
                'processed_bytes': proxy_task.processed_bytes or result.get('processed_bytes') or result.get('processed_size') or 0,
                'speed_mbps': proxy_task.speed_mbps,
                'eta': proxy_task.eta,
                'parameters': proxy_task.parameters,
                'result': result,
                'error_message': proxy_task.error_message,
            }

        page = self.paginate_queryset(proxy_tasks)
        if page is not None:
            return self.get_paginated_response([normalize(item) for item in page])

        return Response([normalize(item) for item in proxy_tasks])
    
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
        if not (user.is_superuser or (user.role and user.role.code == 'admin')):
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
        queryset = BackupSnapshot.objects.select_related('task', 'repository', 'task__tenant')
        
        # Permission-based filtering by tenant
        if user.is_superuser:
            pass  # Superuser sees all
        elif user.tenant:
            queryset = queryset.filter(task__tenant=user.tenant)
        else:
            # Users without tenant can only see their own snapshots
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

    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        """List files for a snapshot by asking the execution proxy on demand."""
        snapshot = self.get_object()
        path = (request.query_params.get('path') or '').strip('/')
        task = snapshot.task
        proxy = task.execution_node
        if not proxy:
            return Response(
                {'error': 'Backup task has no execution proxy'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        repository_password = task.target_repository.get_kopia_password()
        if not repository_password:
            return Response(
                {'error': 'Repository password is not saved'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_online, error_msg = ProxyService.check_proxy_connectivity(str(proxy.id))
        if not is_online:
            return Response(
                {'error': f'Execution proxy is not reachable: {error_msg}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        proxy_task = ProxyTask.objects.create(
            proxy=proxy,
            task_type='list_snapshot_files',
            parameters={
                'snapshot_id': snapshot.storage_path,
                'object_id': snapshot.manifest_path or snapshot.storage_path,
                'snapshot_record_id': str(snapshot.id),
                'backup_task_id': str(task.id),
                'repository_id': str(task.target_repository_id),
                'path': path,
            },
            repository_id=task.target_repository_id,
            source_resource_id=task.source_resource_id,
            status=ProxyTask.TaskStatus.PENDING,
            timeout_seconds=60,
        )
        proxy_task.dispatch()

        payload = {
            'task_id': str(proxy_task.id),
            'snapshot_id': snapshot.storage_path,
            'object_id': snapshot.manifest_path or snapshot.storage_path,
            'snapshot_record_id': str(snapshot.id),
            'path': path,
            'repository': BackupTaskViewSet()._build_repository_config(task.target_repository),
            'password': repository_password,
            'timestamp': timezone.now().isoformat(),
        }
        sent = ProxyService.send_to_proxy(
            str(proxy.id),
            {
                'type': 'list_snapshot_files',
                'id': str(uuid.uuid4()),
                'timestamp': timezone.now().isoformat(),
                'payload': payload,
            },
        )
        if not sent:
            proxy_task.fail('Failed to send snapshot file browser command to proxy')
            return Response(
                {'error': 'Failed to send snapshot file browser command to proxy'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            proxy_task.refresh_from_db()
            if proxy_task.status == ProxyTask.TaskStatus.COMPLETED:
                result = proxy_task.result or {}
                files = result.get('files') or []
                return Response({
                    'results': files,
                    'count': len(files),
                    'task_id': str(proxy_task.id),
                })
            if proxy_task.status in (
                ProxyTask.TaskStatus.FAILED,
                ProxyTask.TaskStatus.CANCELLED,
                ProxyTask.TaskStatus.TIMEOUT,
            ):
                return Response(
                    {'error': proxy_task.error_message or 'Failed to list snapshot files'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            time.sleep(0.25)

        return Response(
            {
                'error': 'Snapshot file browser request is still running',
                'task_id': str(proxy_task.id),
                'results': [],
                'pending': True,
            },
            status=status.HTTP_202_ACCEPTED,
        )
