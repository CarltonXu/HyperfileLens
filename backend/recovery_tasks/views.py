"""
HyperFileLens Backend - Recovery Tasks Views
"""

import os
from datetime import timedelta

from django.conf import settings
from django.http import FileResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import RecoveryExport, RecoveryRun, RecoveryTask
from .serializers import (
    RecoveryExportCreateSerializer,
    RecoveryExportSerializer,
    RecoveryRunSerializer,
    RecoveryTaskCreateSerializer,
    RecoveryTaskSerializer,
)
from .services.export import dispatch_recovery_export, RecoveryExportExecutionError
from .services.execution import dispatch_recovery_task, RecoveryTaskExecutionError
from licenses.quota import QuotaCheckMixin
from nodes.models import ProxyTask
from nodes.proxy_service import ProxyService


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
        queryset = RecoveryTask.objects.select_related(
            'user', 'tenant', 'snapshot', 'snapshot__repository',
            'snapshot__task', 'target_node', 'proxy_task'
        )
        
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
        
        try:
            run, proxy_task = dispatch_recovery_task(task)
        except RecoveryTaskExecutionError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'message': 'Recovery task dispatched',
            'task_id': str(task.id),
            'run_id': str(run.id),
            'proxy_task_id': str(proxy_task.id),
        })

    @action(detail=True, methods=['get'])
    def runs(self, request, pk=None):
        """List execution attempts for a recovery task."""
        task = self.get_object()
        queryset = task.runs.select_related(
            'task', 'snapshot', 'target_node', 'proxy_task'
        ).order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = RecoveryRunSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = RecoveryRunSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='precheck')
    def precheck(self, request, pk=None):
        """Validate whether a recovery task is ready to be dispatched."""
        task = self.get_object()
        checks = []

        def add_check(key, ok, message):
            checks.append({'key': key, 'ok': bool(ok), 'message': message})

        snapshot_ok = task.snapshot.snapshot_status == 'available'
        add_check(
            'snapshot',
            snapshot_ok,
            'Snapshot is available' if snapshot_ok else 'Snapshot is not available in Kopia',
        )

        is_online, proxy_msg = ProxyService.check_proxy_connectivity(str(task.target_node_id))
        add_check(
            'target_proxy',
            is_online,
            'Target proxy is online' if is_online else f'Target proxy is not reachable: {proxy_msg}',
        )

        has_password = bool(task.snapshot.repository.get_kopia_password())
        add_check(
            'repository_password',
            has_password,
            'Repository password is saved' if has_password else 'Repository password is not saved',
        )

        target_path = task.target_path or (task.snapshot.metadata or {}).get('source_path') or ''
        add_check(
            'target_path',
            bool(target_path),
            'Target path is configured' if target_path else 'Target path is required',
        )

        scope_ok = task.restore_scope != RecoveryTask.SCOPE_SELECTED_PATHS or bool(task.selected_paths)
        add_check(
            'restore_scope',
            scope_ok,
            'Restore scope is valid' if scope_ok else 'Selected paths are required for granular recovery',
        )

        success = all(item['ok'] for item in checks)
        return Response({
            'success': success,
            'checks': checks,
            'message': 'Recovery precheck passed' if success else 'Recovery precheck failed',
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
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'completed_at', 'updated_at'])
        RecoveryRun.objects.filter(
            task=task,
            status__in=[
                RecoveryRun.STATUS_PENDING,
                RecoveryRun.STATUS_DISPATCHED,
                RecoveryRun.STATUS_RUNNING,
            ],
        ).update(
            status=RecoveryRun.STATUS_CANCELLED,
            completed_at=timezone.now(),
            message='Task cancelled by user',
        )

        proxy_tasks = ProxyTask.objects.filter(
            parameters__recovery_task_id=str(task.id),
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
                        'reason': 'Task cancelled by user',
                    },
                },
            )
        
        return Response({'message': 'Task cancelled'})

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a recovery task by cancelling the active proxy command."""
        task = self.get_object()
        if task.status != RecoveryTask.STATUS_RUNNING:
            return Response(
                {'error': 'Only running recovery tasks can be paused'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task.status = RecoveryTask.STATUS_PAUSED
        task.status_message = 'Recovery paused by user'
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'status_message', 'completed_at', 'updated_at'])
        RecoveryRun.objects.filter(
            task=task,
            status__in=[RecoveryRun.STATUS_PENDING, RecoveryRun.STATUS_DISPATCHED, RecoveryRun.STATUS_RUNNING],
        ).update(
            status=RecoveryRun.STATUS_PAUSED,
            completed_at=timezone.now(),
            message='Recovery paused by user',
        )

        proxy_tasks = ProxyTask.objects.filter(
            parameters__recovery_task_id=str(task.id),
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
                        'reason': 'Recovery paused by user',
                    },
                },
            )
        return Response({'message': 'Recovery task paused'})
    
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
            'cancelled': queryset.filter(status='cancelled').count(),
            'total_files': sum(queryset.values_list('restored_files', flat=True)),
            'total_size': sum(queryset.values_list('restored_size', flat=True)),
        }
        
        return Response(stats)


class RecoveryExportViewSet(viewsets.ModelViewSet):
    """ViewSet for downloadable recovery exports."""

    queryset = RecoveryExport.objects.all()
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == 'create':
            return RecoveryExportCreateSerializer
        return RecoveryExportSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = RecoveryExport.objects.select_related(
            'snapshot', 'snapshot__task', 'repository', 'executor_node',
            'proxy_task', 'user', 'tenant',
        )
        if user.is_superuser:
            pass
        elif user.tenant:
            queryset = queryset.filter(tenant=user.tenant)
        else:
            queryset = queryset.filter(user=user)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        snapshot_id = self.request.query_params.get('snapshot')
        if snapshot_id:
            queryset = queryset.filter(snapshot_id=snapshot_id)
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        expires_in_hours = serializer.validated_data.pop('expires_in_hours', 24)
        snapshot = serializer.validated_data['snapshot']
        export = serializer.save(
            user=self.request.user,
            tenant=self.request.user.tenant,
            repository=snapshot.repository,
            expires_at=timezone.now() + timedelta(hours=expires_in_hours),
        )
        try:
            dispatch_recovery_export(export)
        except RecoveryExportExecutionError as exc:
            export.status = RecoveryExport.STATUS_FAILED
            export.error_message = str(exc)
            export.completed_at = timezone.now()
            export.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        export = self.get_object()
        try:
            dispatch_recovery_export(export)
        except RecoveryExportExecutionError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Export dispatched'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        export = self.get_object()
        if export.status not in [
            RecoveryExport.STATUS_PENDING,
            RecoveryExport.STATUS_DISPATCHED,
            RecoveryExport.STATUS_RUNNING,
            RecoveryExport.STATUS_PACKAGING,
        ]:
            return Response({'error': 'Export is not running'}, status=status.HTTP_400_BAD_REQUEST)
        export.status = RecoveryExport.STATUS_CANCELLED
        export.status_message = 'Export cancelled by user'
        export.completed_at = timezone.now()
        export.save(update_fields=['status', 'status_message', 'completed_at', 'updated_at'])
        if export.proxy_task_id:
            export.proxy_task.cancel()
            ProxyService.send_to_proxy(
                str(export.proxy_task.proxy_id),
                {
                    'type': 'cancel',
                    'id': str(export.proxy_task_id),
                    'timestamp': timezone.now().isoformat(),
                    'payload': {
                        'task_id': str(export.proxy_task_id),
                        'reason': 'Export cancelled by user',
                    },
                },
            )
        return Response({'message': 'Export cancelled'})

    @action(detail=True, methods=['post'])
    def upload(self, request, pk=None):
        export = self.get_object()
        package = request.FILES.get('file')
        if not package:
            return Response({'error': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)

        export_dir = os.path.join(settings.MEDIA_ROOT, 'recovery_exports', str(export.id))
        os.makedirs(export_dir, exist_ok=True)
        filename = package.name or f'{export.id}.zip'
        file_path = os.path.join(export_dir, filename)
        with open(file_path, 'wb') as destination:
            for chunk in package.chunks():
                destination.write(chunk)

        export.file_path = file_path
        export.file_name = filename
        export.package_size = os.path.getsize(file_path)
        export.checksum = request.data.get('checksum', export.checksum or '')
        export.status = RecoveryExport.STATUS_READY
        export.progress = 100
        export.status_message = 'Export package is ready'
        export.completed_at = timezone.now()
        export.save(update_fields=[
            'file_path', 'file_name', 'package_size', 'checksum', 'status',
            'progress', 'status_message', 'completed_at', 'updated_at',
        ])
        return Response(RecoveryExportSerializer(export, context={'request': request}).data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        export = self.get_object()
        if not export.is_downloadable:
            return Response({'error': 'Export package is not ready or has expired'}, status=status.HTTP_400_BAD_REQUEST)
        if not os.path.exists(export.file_path):
            return Response({'error': 'Export package file is missing'}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(
            open(export.file_path, 'rb'),
            as_attachment=True,
            filename=export.file_name or f'{export.id}.zip',
        )
