"""
HyperFileLens Backend - Recovery Tasks Views
"""

import os
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.http import FileResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
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

    def get_permissions(self):
        if getattr(self, 'action', None) in ('upload', 'public_info', 'public_download'):
            return [AllowAny()]
        return super().get_permissions()

    def get_authenticators(self):
        if getattr(self, 'action', None) in ('upload', 'public_info', 'public_download') or self._is_callback_request():
            return []
        return super().get_authenticators()

    def _is_callback_request(self):
        resolver_match = getattr(self.request, 'resolver_match', None)
        return bool(
            resolver_match
            and getattr(resolver_match, 'url_name', '') in (
                'recovery-export-upload',
                'recovery-export-public-info',
                'recovery-export-public-download',
            )
        )

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
        repository_id = self.request.query_params.get('repository')
        if repository_id:
            queryset = queryset.filter(repository_id=repository_id)
        task_id = self.request.query_params.get('task')
        if task_id:
            queryset = queryset.filter(snapshot__task_id=task_id)
        source_resource_id = self.request.query_params.get('source_resource')
        if source_resource_id:
            queryset = queryset.filter(snapshot__task__source_resource_id=source_resource_id)
        ordering = self.request.query_params.get('ordering') or '-created_at'
        allowed = {
            'name', '-name', 'status', '-status', 'created_at', '-created_at',
            'completed_at', '-completed_at', 'package_size', '-package_size',
            'download_count', '-download_count', 'expires_at', '-expires_at',
        }
        return queryset.order_by(ordering if ordering in allowed else '-created_at')

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
    def retry(self, request, pk=None):
        export = self.get_object()
        if export.status in [
            RecoveryExport.STATUS_PENDING,
            RecoveryExport.STATUS_DISPATCHED,
            RecoveryExport.STATUS_RUNNING,
            RecoveryExport.STATUS_PACKAGING,
        ]:
            return Response({'error': 'Export is already running'}, status=status.HTTP_400_BAD_REQUEST)
        if not export.selected_paths:
            return Response({'error': 'Export has no selected paths'}, status=status.HTTP_400_BAD_REQUEST)

        export.status = RecoveryExport.STATUS_PENDING
        export.progress = 0
        export.status_message = 'Retrying export'
        export.error_message = ''
        export.current_file = ''
        export.total_files = 0
        export.processed_files = 0
        export.total_size = 0
        export.processed_size = 0
        export.speed_mbps = 0
        export.eta = ''
        export.package_size = 0
        export.checksum = ''
        export.file_name = ''
        export.proxy_task = None
        export.executor_node = None
        export.started_at = None
        export.completed_at = None
        export.save(update_fields=[
            'status', 'progress', 'status_message', 'error_message',
            'current_file', 'total_files', 'processed_files', 'total_size',
            'processed_size', 'speed_mbps', 'eta', 'package_size',
            'checksum', 'file_name', 'proxy_task', 'executor_node',
            'started_at', 'completed_at', 'updated_at',
        ])

        try:
            dispatch_recovery_export(export)
        except RecoveryExportExecutionError as exc:
            export.status = RecoveryExport.STATUS_FAILED
            export.error_message = str(exc)
            export.status_message = str(exc)
            export.completed_at = timezone.now()
            export.save(update_fields=[
                'status', 'error_message', 'status_message',
                'completed_at', 'updated_at',
            ])
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RecoveryExportSerializer(export, context={'request': request}).data)

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

    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        ids = request.data.get('ids') or []
        if not isinstance(ids, list) or not ids:
            return Response({'error': 'ids is required'}, status=status.HTTP_400_BAD_REQUEST)
        active_statuses = [
            RecoveryExport.STATUS_PENDING,
            RecoveryExport.STATUS_DISPATCHED,
            RecoveryExport.STATUS_RUNNING,
            RecoveryExport.STATUS_PACKAGING,
        ]
        queryset = self.get_queryset().filter(id__in=ids)
        if queryset.filter(status__in=active_statuses).exists():
            return Response({'error': 'Running exports cannot be deleted'}, status=status.HTTP_400_BAD_REQUEST)
        deleted = 0
        for export in queryset:
            if export.file_path and os.path.exists(export.file_path):
                try:
                    os.remove(export.file_path)
                except OSError:
                    pass
            export.delete()
            deleted += 1
        return Response({'deleted': deleted})

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        export = self.get_object()
        export.share_enabled = bool(request.data.get('enabled', True))
        if export.share_enabled and not export.share_token:
            export.share_token = secrets.token_urlsafe(32)
        password = request.data.get('password')
        if export.share_enabled and not password and not export.share_password_hash:
            return Response({'error': 'Share password is required'}, status=status.HTTP_400_BAD_REQUEST)
        if password:
            export.share_password_hash = make_password(password)
        if request.data.get('clear_password') and not export.share_enabled:
            export.share_password_hash = ''
        expires_in_hours = request.data.get('expires_in_hours')
        if expires_in_hours:
            try:
                export.share_expires_at = timezone.now() + timedelta(hours=int(expires_in_hours))
            except (TypeError, ValueError):
                return Response({'error': 'expires_in_hours must be a number'}, status=status.HTTP_400_BAD_REQUEST)
        export.save(update_fields=[
            'share_enabled', 'share_token', 'share_password_hash',
            'share_expires_at', 'updated_at',
        ])
        return Response(RecoveryExportSerializer(export, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def upload(self, request, pk=None):
        try:
            export = RecoveryExport.objects.select_related(
                'proxy_task', 'proxy_task__proxy',
            ).get(pk=pk)
        except RecoveryExport.DoesNotExist:
            return Response({'error': 'Export not found'}, status=status.HTTP_404_NOT_FOUND)

        auth_header = request.headers.get('Authorization', '')
        api_token = request.data.get('api_token') or ''
        if not api_token and auth_header.startswith('Token '):
            api_token = auth_header[6:]

        expected_token = ''
        if export.proxy_task_id and export.proxy_task.proxy_id:
            expected_token = export.proxy_task.proxy.api_token

        if not expected_token or api_token != expected_token:
            return Response({'error': 'Invalid proxy token'}, status=status.HTTP_403_FORBIDDEN)

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
        export.download_count = (export.download_count or 0) + 1
        export.last_downloaded_at = timezone.now()
        export.save(update_fields=['download_count', 'last_downloaded_at', 'updated_at'])
        return FileResponse(
            open(export.file_path, 'rb'),
            as_attachment=True,
            filename=export.file_name or f'{export.id}.zip',
        )

    @action(detail=True, methods=['get'], url_path='public-info')
    def public_info(self, request, pk=None):
        token = request.query_params.get('token') or ''
        export = RecoveryExport.objects.select_related(
            'snapshot', 'repository',
        ).filter(
            pk=pk,
            share_enabled=True,
            share_token=token,
        ).first()
        if not export:
            return Response({'error': 'Share link is invalid'}, status=status.HTTP_404_NOT_FOUND)
        if export.share_expires_at and export.share_expires_at <= timezone.now():
            return Response({'error': 'Share link has expired'}, status=status.HTTP_410_GONE)

        snapshot_metadata = getattr(export.snapshot, 'metadata', None) or {}
        return Response({
            'id': export.id,
            'name': export.name,
            'description': export.description,
            'file_name': export.file_name,
            'package_format': export.package_format,
            'package_size': export.package_size,
            'selected_paths': export.selected_paths,
            'selected_path_count': len(export.selected_paths or []),
            'snapshot_name': getattr(export.snapshot, 'name', ''),
            'snapshot_source_path': (
                snapshot_metadata.get('source_path')
                or snapshot_metadata.get('kopia_source_path')
                or ''
            ),
            'snapshot_created_at': getattr(export.snapshot, 'created_at', None),
            'repository_name': getattr(export.repository, 'name', ''),
            'share_expires_at': export.share_expires_at,
            'expires_at': export.expires_at,
            'download_count': export.download_count,
            'has_share_password': bool(export.share_password_hash),
            'is_downloadable': export.is_downloadable,
        })

    @action(detail=True, methods=['post'], url_path='public-download')
    def public_download(self, request, pk=None):
        token = request.data.get('token') or ''
        password = request.data.get('password') or ''
        export = RecoveryExport.objects.filter(
            pk=pk,
            share_enabled=True,
            share_token=token,
        ).first()
        if not export:
            return Response({'error': 'Share link is invalid'}, status=status.HTTP_404_NOT_FOUND)
        if export.share_expires_at and export.share_expires_at <= timezone.now():
            return Response({'error': 'Share link has expired'}, status=status.HTTP_410_GONE)
        if export.share_password_hash and not check_password(password, export.share_password_hash):
            return Response({'error': 'Share password is invalid'}, status=status.HTTP_403_FORBIDDEN)
        if not export.is_downloadable or not os.path.exists(export.file_path):
            return Response({'error': 'Export package is not ready or has expired'}, status=status.HTTP_400_BAD_REQUEST)
        export.download_count = (export.download_count or 0) + 1
        export.last_downloaded_at = timezone.now()
        export.save(update_fields=['download_count', 'last_downloaded_at', 'updated_at'])
        return FileResponse(
            open(export.file_path, 'rb'),
            as_attachment=True,
            filename=export.file_name or f'{export.id}.zip',
        )
