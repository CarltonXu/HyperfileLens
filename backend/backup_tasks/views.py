"""
HyperFileLens Backend - Backup Tasks Views

This module provides REST API views for backup task management.
"""

import copy
import re
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
from nodes.models import ProxyNode, ProxyTask
from nodes.proxy_service import ProxyService
from repository.models import Repository
from .models import BackupTask, BackupSnapshot, BackupTaskRun
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
    BackupTaskRunSerializer,
)
from .services.execution import dispatch_backup_task, BackupTaskExecutionError


def _parse_kopia_snapshot_ids(output):
    """Return (root_object_id, snapshot_manifest_id) from Kopia snapshot output."""
    if not output:
        return '', ''
    match = re.search(
        r'Created snapshot with root\s+(\S+)\s+and ID\s+(\S+)',
        str(output),
    )
    if not match:
        return '', ''
    return match.group(1).strip(), match.group(2).strip().rstrip('.')


def _is_probably_kopia_object_id(value):
    """Reject platform UUIDs and other values Kopia cannot use as a content object ID."""
    if not value:
        return False
    value = str(value).strip()
    return bool(re.match(r'^[A-Za-z][A-Za-z0-9]{10,}$', value))


def _dedupe_list(values):
    result = []
    seen = set()
    for value in values or []:
        if value is None:
            continue
        item = str(value).strip()
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _merge_policy_section(base, overrides, override_key):
    base_section = copy.deepcopy(base or {})
    override_section = copy.deepcopy(overrides.get(override_key) or {})
    if override_section.get('override') is True:
        override_section.pop('override', None)
        base_section.update({k: v for k, v in override_section.items() if v is not None})
    return base_section


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
        'preferred_execution_node', 'user', 'schedule'
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
            'preferred_execution_node', 'user', 'schedule', 'tenant'
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
        task.next_run_time = task.calculate_next_run_time()
        task.save(update_fields=['next_run_time', 'updated_at'])
        AuditService.log_backup_task_create(self.request, task, result='success')
    
    def perform_update(self, serializer):
        """Update a backup task."""
        task = serializer.save()
        if any(field in serializer.validated_data for field in ['schedule', 'is_enabled', 'policy_overrides']):
            task.next_run_time = task.calculate_next_run_time()
            task.save(update_fields=['next_run_time', 'updated_at'])
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
        
        try:
            run, proxy_task = dispatch_backup_task(
                task,
                trigger_type=BackupTaskRun.TRIGGER_MANUAL,
                force=serializer.validated_data.get('force'),
                task_type=serializer.validated_data.get('task_type') or task.task_type,
                repository_password=serializer.validated_data.get('repository_password'),
            )
        except BackupTaskExecutionError as exc:
            error_text = str(exc)
            payload = {'error': error_text}
            if 'password' in error_text.lower():
                payload['error_code'] = 'REPOSITORY_PASSWORD_REQUIRED'
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'message': 'Backup task started',
            'task_id': str(task.id),
            'proxy_task_id': str(proxy_task.id),
            'run_id': str(run.id),
            'execution_node': proxy_task.proxy.name if proxy_task.proxy_id else None
        })

    def _select_execution_node(self, task):
        """Select the proxy that should execute this backup task."""
        source = task.source_resource
        repo = task.target_repository
        mode = task.execution_mode or BackupTask.EXECUTION_MODE_PINNED

        def online_error(proxy):
            if not proxy:
                return 'No execution proxy is configured for this task'
            is_online, error_msg = ProxyService.check_proxy_connectivity(str(proxy.id))
            if not is_online:
                return f"Execution proxy is not reachable: {error_msg}"
            return ''

        def is_network_source():
            return source and source.resource_type in (
                source.TYPE_NAS,
                source.TYPE_NFS,
                source.TYPE_CIFS,
                source.TYPE_S3,
            )

        def is_network_repository():
            return repo and repo.repo_type in (
                Repository.TYPE_NAS,
                Repository.TYPE_NFS,
                Repository.TYPE_S3,
                Repository.TYPE_AZURE,
                Repository.TYPE_GCS,
            )

        if not source:
            return None, 'Backup task has no source resource'
        if not repo:
            return None, 'Backup task has no target repository'

        if source.resource_type == source.TYPE_LOCAL:
            proxy = source.bound_node
            error = online_error(proxy)
            return (None, error) if error else (proxy, '')

        if repo.repo_type == Repository.TYPE_LOCAL:
            proxy = repo.bound_node
            error = online_error(proxy)
            return (None, error) if error else (proxy, '')

        if mode == BackupTask.EXECUTION_MODE_PINNED:
            proxy = source.bound_node or repo.bound_node
            error = online_error(proxy)
            return (None, error) if error else (proxy, '')

        if not (is_network_source() and is_network_repository()):
            return None, 'Auto proxy selection requires network-accessible source and repository resources'

        if mode == BackupTask.EXECUTION_MODE_PREFERRED and task.preferred_execution_node_id:
            preferred = task.preferred_execution_node
            if preferred.role == ProxyNode.Role.SYNC and preferred.active_tasks < preferred.max_concurrent_tasks:
                if not online_error(preferred):
                    return preferred, ''

        candidates = ProxyNode.objects.filter(
            role=ProxyNode.Role.SYNC,
            status=ProxyNode.NodeStatus.ONLINE,
        )
        if task.tenant_id:
            candidates = candidates.filter(tenant_id=task.tenant_id)
        candidates = candidates.order_by('active_tasks', '-health_score', 'name')
        for proxy in candidates:
            if proxy.active_tasks < proxy.max_concurrent_tasks:
                return proxy, ''

        return None, 'No available Sync Proxy found for automatic execution. Please start a Sync Proxy or reduce running tasks.'

    def _build_source_resource_config(self, source):
        """Build source resource payload for proxy-side dynamic access."""
        if not source:
            return {}
        config = source.config or {}
        credentials = source.credentials or {}
        payload = {
            'id': str(source.id),
            'name': source.name,
            'type': source.resource_type,
            'resource_type': source.resource_type,
            'mount_point': source.mount_point or source.get_effective_mount_point(),
            'config': config,
            'credentials': credentials,
        }
        if source.resource_type in (source.TYPE_NAS, source.TYPE_NFS, source.TYPE_CIFS):
            payload.update({
                'server': config.get('server', ''),
                'export_path': config.get('export_path') or config.get('share') or '',
                'share': config.get('share') or config.get('export_path') or '',
                'mount_type': config.get('mount_type') or config.get('protocol') or ('cifs' if source.resource_type == source.TYPE_CIFS else 'nfs'),
                'mount_options': config.get('mount_options', ''),
                'username': credentials.get('username') or config.get('username', ''),
                'password': credentials.get('password') or config.get('password', ''),
            })
        elif source.resource_type == source.TYPE_S3:
            payload.update({
                'endpoint': config.get('endpoint', ''),
                'bucket': config.get('bucket', ''),
                'region': config.get('region', 'us-east-1'),
                'prefix': config.get('prefix', ''),
                'access_key': credentials.get('access_key') or config.get('access_key', ''),
                'secret_key': credentials.get('secret_key') or config.get('secret_key', ''),
                'use_tls': config.get('use_tls', True),
                'url_style': config.get('url_style', 'virtual'),
            })
        elif source.resource_type == source.TYPE_LOCAL:
            payload['path'] = config.get('root_path') or config.get('path') or ''
        return payload

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

    def _build_effective_policy(self, task, source_path):
        """Resolve the Kopia policy that must be applied before snapshot creation."""
        policy = task.schedule
        overrides = task.policy_overrides or {}

        if policy:
            effective = {
                'source': 'policy',
                'policy_id': str(policy.id),
                'policy_name': policy.name,
                'policy_scope': policy.policy_scope,
                'policy_target': copy.deepcopy(policy.policy_target or {}),
                'snapshot_schedule': copy.deepcopy(policy.snapshot_schedule or {}),
                'retention_policy': copy.deepcopy(policy.retention_policy or {}),
                'file_policy': {
                    'ignore_patterns': [],
                    'dot_ignore_files': ['.kopiaignore'],
                    'one_file_system': False,
                    'ignore_file_errors': False,
                    'ignore_dir_errors': False,
                },
                'compression_policy': {
                    'compression': task.compression_type if task.compression_enabled else 'none',
                    'metadata_compression': task.compression_enabled,
                    'max_parallel_file_reads': task.max_concurrent_files,
                    'ignore_identical_snapshots': True,
                },
                'advanced_policy': copy.deepcopy(policy.advanced_policy or {}),
            }
        else:
            effective = {
                'source': 'task',
                'policy_id': None,
                'policy_name': '',
                'policy_scope': 'path',
                'policy_target': {},
                'snapshot_schedule': {'mode': 'manual', 'interval': '', 'time_of_day': '', 'cron': '', 'run_missed': True},
                'retention_policy': {
                    'keep_latest': task.max_snapshots,
                    'keep_hourly': 0,
                    'keep_daily': task.retention_days,
                    'keep_weekly': 0,
                    'keep_monthly': 0,
                    'keep_annual': 0,
                },
                'file_policy': {
                    'ignore_patterns': [],
                    'dot_ignore_files': ['.kopiaignore'],
                    'one_file_system': False,
                    'ignore_file_errors': False,
                    'ignore_dir_errors': False,
                },
                'compression_policy': {
                    'compression': task.compression_type if task.compression_enabled else 'none',
                    'metadata_compression': task.compression_enabled,
                    'max_parallel_file_reads': task.max_concurrent_files,
                    'ignore_identical_snapshots': True,
                },
                'advanced_policy': {},
            }

        effective['policy_target'] = copy.deepcopy(effective.get('policy_target') or {})
        if not effective['policy_target'].get('kopia_target'):
            effective['policy_target']['kopia_target'] = source_path

        effective['snapshot_schedule'] = _merge_policy_section(effective.get('snapshot_schedule'), overrides, 'snapshot_schedule')
        effective['retention_policy'] = _merge_policy_section(effective.get('retention_policy'), overrides, 'retention_policy')
        effective['compression_policy'] = _merge_policy_section(effective.get('compression_policy'), overrides, 'compression_policy')

        file_policy = copy.deepcopy(effective.get('file_policy') or {})
        file_override = copy.deepcopy(overrides.get('file_policy') or {})
        if file_override.get('override') is True:
            file_override.pop('override', None)
            file_policy.update({k: v for k, v in file_override.items() if v is not None})

        merged_ignores = []
        merged_ignores.extend(file_policy.get('ignore_patterns') or [])
        merged_ignores.extend(task.exclude_patterns or [])
        merged_ignores.extend(file_override.get('additional_ignore_patterns') or [])
        file_policy['ignore_patterns'] = _dedupe_list(merged_ignores)
        file_policy['include_patterns'] = _dedupe_list(task.include_patterns or [])
        effective['file_policy'] = file_policy

        effective['task_overrides'] = overrides
        return effective

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
        task.last_run_status = BackupTaskRun.STATUS_CANCELLED
        task.save(update_fields=['status', 'status_message', 'last_run_status', 'completed_at', 'updated_at'])

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
            BackupTaskRun.objects.filter(proxy_task=proxy_task).update(
                status=BackupTaskRun.STATUS_CANCELLED,
                message=serializer.validated_data.get('reason', 'Task cancelled by user'),
                completed_at=timezone.now(),
            )
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
        task.next_run_time = task.calculate_next_run_time()
        task.save(update_fields=['is_enabled', 'next_run_time', 'updated_at'])
        return Response({'message': 'Task enabled', 'task_id': str(task.id)})

    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable a backup task and cancel it if it is currently running."""
        task = self.get_object()
        task.is_enabled = False
        task.next_run_time = None
        update_fields = ['is_enabled', 'next_run_time', 'updated_at']
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
        recent_proxy_tasks = list(ProxyTask.objects.filter(
            task_type=ProxyTask.TaskType.BACKUP,
            parameters__backup_task_id=str(task.id),
            status=ProxyTask.TaskStatus.COMPLETED,
        ).order_by('-completed_at', '-created_at')[:20])
        for proxy_task in reversed(recent_proxy_tasks):
            result = proxy_task.result or {}
            output = str(result.get('output') or '')
            parsed_root_object_id, parsed_snapshot_id = _parse_kopia_snapshot_ids(output)
            root_object_id = (
                result.get('root_object_id') or result.get('object_id')
                or result.get('root_id') or result.get('root')
                or result.get('manifest_path') or parsed_root_object_id
            )
            snapshot_id = (
                result.get('snapshot_id') or result.get('manifest_id')
                or result.get('snapshot') or result.get('id')
                or parsed_snapshot_id
            )
            if not snapshot_id or not _is_probably_kopia_object_id(root_object_id):
                continue
            no_changes = bool(result.get('no_changes'))
            if no_changes:
                snapshot = BackupSnapshot.objects.filter(
                    task=task,
                    metadata__proxy_task_id=str(proxy_task.id),
                ).first()
                if not snapshot:
                    snapshot = BackupSnapshot.objects.create(
                        task=task,
                        repository=task.target_repository,
                        name=f'no-change-{timezone.now().strftime("%Y%m%d_%H%M%S")}',
                        version=str(snapshot_id),
                        storage_path=str(snapshot_id),
                        manifest_path=str(root_object_id),
                        total_size=result.get('total_size') or result.get('backed_up_size') or 0,
                        file_count=result.get('total_files') or result.get('backed_up_files') or 0,
                        metadata={},
                    )
            else:
                snapshot = next(
                    (
                        item for item in BackupSnapshot.objects.filter(
                            task=task,
                            storage_path=str(snapshot_id),
                        )
                        if not (item.metadata or {}).get('no_changes')
                    ),
                    None,
                )
                if not snapshot:
                    snapshot = BackupSnapshot.objects.create(
                        task=task,
                        repository=task.target_repository,
                        name=f'snapshot-{timezone.now().strftime("%Y%m%d_%H%M%S")}',
                        version=str(snapshot_id),
                        storage_path=str(snapshot_id),
                        manifest_path=str(root_object_id),
                        total_size=result.get('total_size') or result.get('backed_up_size') or 0,
                        file_count=result.get('total_files') or result.get('backed_up_files') or 0,
                        metadata={},
                    )
            metadata = snapshot.metadata or {}
            metadata.update({
                'proxy_task_id': str(proxy_task.id),
                'source_path': (proxy_task.parameters or {}).get('source_path', ''),
                'root_object_id': str(root_object_id),
                'snapshot_id': str(snapshot_id),
                'referenced_snapshot_id': str(snapshot_id) if no_changes else '',
                'kopia_output': output,
                'no_changes': no_changes,
                'last_no_changes': no_changes,
                'last_seen_at': (
                    proxy_task.completed_at or proxy_task.updated_at or timezone.now()
                ).isoformat(),
            })
            snapshot.repository = task.target_repository
            snapshot.version = str(snapshot_id)
            snapshot.storage_path = str(snapshot_id)
            snapshot.manifest_path = str(root_object_id)
            snapshot.total_size = snapshot.total_size or result.get('total_size') or result.get('backed_up_size') or 0
            snapshot.file_count = snapshot.file_count or result.get('total_files') or result.get('backed_up_files') or 0
            snapshot.metadata = metadata
            snapshot.save(update_fields=[
                'repository', 'version', 'storage_path', 'manifest_path',
                'total_size', 'file_count', 'metadata',
            ])

        for snapshot in BackupSnapshot.objects.filter(task=task, manifest_path=''):
            parsed_object_id, parsed_snapshot_id = _parse_kopia_snapshot_ids(
                (snapshot.metadata or {}).get('kopia_output', '')
            )
            if parsed_object_id:
                snapshot.manifest_path = parsed_object_id
                if parsed_snapshot_id and snapshot.storage_path != parsed_snapshot_id:
                    snapshot.storage_path = parsed_snapshot_id
                    snapshot.version = parsed_snapshot_id
                metadata = snapshot.metadata or {}
                metadata.update({
                    'root_object_id': parsed_object_id,
                    'snapshot_id': parsed_snapshot_id or snapshot.storage_path,
                })
                snapshot.metadata = metadata
                snapshot.save(update_fields=[
                    'storage_path', 'version', 'manifest_path', 'metadata',
                ])

        valid_snapshot_ids = [
            snapshot.id
            for snapshot in BackupSnapshot.objects.filter(task=task).only('id', 'manifest_path')
            if _is_probably_kopia_object_id(snapshot.manifest_path)
        ]
        snapshots = list(BackupSnapshot.objects.filter(
            id__in=valid_snapshot_ids,
        ))
        snapshots.sort(
            key=lambda item: (item.metadata or {}).get('last_seen_at') or item.created_at.isoformat(),
            reverse=True,
        )
        
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
        runs = BackupTaskRun.objects.filter(task=task).select_related(
            'selected_proxy', 'repository', 'source_resource', 'proxy_task'
        ).order_by('-created_at')

        page = self.paginate_queryset(runs)
        if page is not None:
            serializer = BackupTaskRunSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = BackupTaskRunSerializer(runs, many=True)
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

        object_id = (
            snapshot.manifest_path
            or (snapshot.metadata or {}).get('root_object_id')
            or ''
        )
        if not _is_probably_kopia_object_id(object_id):
            parsed_object_id, parsed_snapshot_id = _parse_kopia_snapshot_ids(
                (snapshot.metadata or {}).get('kopia_output', '')
            )
            if parsed_object_id:
                object_id = parsed_object_id
                if parsed_snapshot_id and snapshot.storage_path != parsed_snapshot_id:
                    snapshot.storage_path = parsed_snapshot_id
                    snapshot.version = parsed_snapshot_id
                snapshot.manifest_path = parsed_object_id
                metadata = snapshot.metadata or {}
                metadata.update({
                    'root_object_id': parsed_object_id,
                    'snapshot_id': parsed_snapshot_id or snapshot.storage_path,
                })
                snapshot.metadata = metadata
                snapshot.save(update_fields=[
                    'storage_path', 'version', 'manifest_path', 'metadata',
                ])

        if not _is_probably_kopia_object_id(object_id):
            return Response(
                {
                    'error': (
                        'Snapshot root object ID is missing or invalid. '
                        'Please run a new backup or resync snapshots before browsing files.'
                    )
                },
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
                'object_id': object_id,
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
            'object_id': object_id,
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
