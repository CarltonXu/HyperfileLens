"""
Views for Proxy Nodes Application

This module provides API views for proxy management,
including CRUD operations, installation, heartbeat handling, and statistics.
"""

import secrets
import time

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from .models import ProxyNode, ProxyHeartbeat, ProxyTask, NodeConnection
from .serializers import (
    ProxyNodeSerializer, ProxyNodeCreateSerializer, ProxyNodeUpdateSerializer,
    ProxyNodeDetailSerializer, ProxyHeartbeatSerializer, ProxyTaskSerializer,
    ProxyTaskCreateSerializer, NodeConnectionSerializer,
    ProxyStatsSerializer, ProxyHeartbeatCreateSerializer,
    ProxyRegisterSerializer, InstallCommandSerializer, InstallCommandResponseSerializer
)
from .query_optimizations import (
    get_proxy_statistics, get_proxy_summary, get_task_list,
    get_alert_list, invalidate_cache
)
from audit_log.services import AuditService
from .proxy_service import ProxyService


def evaluate_proxy_metric_alerts(proxy):
    from alerts.services.metric_evaluator import evaluate_metric_policies_for_resource

    evaluate_metric_policies_for_resource(proxy)


class ProxyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for proxy management.

    Provides CRUD operations for agent and sync proxies.
    """

    permission_classes = [IsAuthenticated]
    filterset_fields = ['role', 'status', 'operating_system']
    search_fields = ['name', 'hostname']
    ordering_fields = ['name', 'created_at', 'last_heartbeat', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return proxies filtered by user's access permissions with optimized query."""
        user = self.request.user
        base_queryset = ProxyNode.objects.select_related('owner', 'tenant')
        if user.is_superuser:
            return base_queryset
        # Filter by tenant if user belongs to one
        if user.tenant:
            return base_queryset.filter(tenant=user.tenant)
        # Fallback to owner-based filtering
        return base_queryset.filter(owner=user)

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return ProxyNodeCreateSerializer
        if self.action in ['update', 'partial_update']:
            return ProxyNodeUpdateSerializer
        if self.action == 'retrieve':
            return ProxyNodeDetailSerializer
        return ProxyNodeSerializer

    @extend_schema(
        summary='List all proxies',
        description='Retrieve a list of all registered proxies.',
        parameters=[
            OpenApiParameter(name='role', description='Filter by role (agent/sync)'),
            OpenApiParameter(name='status', description='Filter by status'),
            OpenApiParameter(name='search', description='Search by name or hostname'),
        ]
    )
    def list(self, request, *args, **kwargs):
        """List all proxies with status sync."""
        # Sync status based on heartbeat before returning
        queryset = self.filter_queryset(self.get_queryset())
        for proxy in queryset:
            proxy.update_status_based_on_heartbeat()
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Get a specific proxy',
        description='Retrieve detailed information about a specific proxy.'
    )
    def retrieve(self, request, *args, **kwargs):
        """Get a specific proxy with status sync."""
        proxy = self.get_object()
        proxy.update_status_based_on_heartbeat()
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary='Create a new proxy',
        description='Register a new agent or sync proxy.',
        responses={201: ProxyNodeSerializer}
    )
    def create(self, request, *args, **kwargs):
        """Create a new proxy."""
        from licenses.quota import enforce_license_quota

        try:
            enforce_license_quota(getattr(request.user, 'tenant', None), 'proxies')
        except Exception as exc:
            AuditService.log_proxy_create(request, None, result='failure', error_message=str(exc))
            raise
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proxy = serializer.save()

        # Set owner and tenant to current user
        proxy.owner = request.user
        if request.user.tenant:
            proxy.tenant = request.user.tenant
        proxy.save(update_fields=['owner', 'tenant'])

        # Generate installation command
        self._generate_install_command(proxy, request)
        
        # Record audit log
        AuditService.log_proxy_create(request, proxy, result='success')

        response_serializer = ProxyNodeSerializer(proxy)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def _generate_install_command(self, proxy, request):
        """Generate installation command for the proxy."""
        # Get server URL from settings or request
        server_url = getattr(settings, 'PROXY_SERVER_URL', None)
        if not server_url:
            server_url = request.build_absolute_uri('/').rstrip('/')

        # Get target OS from request or use saved value
        os_type = request.data.get('target_os', proxy.target_os or 'linux')
        
        # Update proxy's target_os if provided
        if os_type != proxy.target_os:
            proxy.target_os = os_type

        install_command = self._build_install_command(
            server_url=server_url,
            role=proxy.role,
            proxy_id=proxy.id,
            install_token=proxy.install_token,
            os_type=os_type,
            name=proxy.name
        )

        proxy.install_command = install_command
        proxy.installed_by = request.user
        proxy.save(update_fields=['install_command', 'installed_by', 'target_os'])

    def _build_install_command(self, server_url, role, proxy_id, install_token, os_type, name):
        """Build the installation command string."""
        if os_type == 'windows':
            return f'''# PowerShell (Run as Administrator)
Invoke-WebRequest -Uri "{server_url}/static/downloads/install.ps1" -OutFile "install.ps1"
./install.ps1 -ProxyId "{proxy_id}" -Role {role} -Server "{server_url}" -Token "{install_token}" -Name "{name}"'''
        else:
            return f'''# Linux/macOS
curl -sSL {server_url}/static/downloads/install.sh | bash -s -- \\
  --proxy-id {proxy_id} \\
  --role {role} \\
  --server {server_url} \\
  --token {install_token} \\
  --name "{name}"'''

    def perform_destroy(self, instance):
        """Delete a proxy with audit logging."""
        AuditService.log_proxy_delete(self.request, instance, result='success')
        # Invalidate cache for this proxy
        invalidate_cache(str(instance.id))
        instance.delete()

    def perform_update(self, serializer):
        """Update a proxy with audit logging."""
        # Get the old instance data before update
        old_instance = self.get_object()
        old_data = {
            'name': old_instance.name,
            'hostname': old_instance.hostname,
            'role': old_instance.role,
            'status': old_instance.status,
            'labels': old_instance.labels,
        }

        # Save the updated instance
        instance = serializer.save()

        # Invalidate cache for this proxy
        invalidate_cache(str(instance.id))

        # Track changed fields
        changed_fields = []
        new_data = {
            'name': instance.name,
            'hostname': instance.hostname,
            'role': instance.role,
            'status': instance.status,
            'labels': instance.labels,
        }

        for field in old_data.keys():
            if old_data[field] != new_data[field]:
                changed_fields.append(field)

        # Record audit log
        AuditService.log_proxy_update(
            self.request, instance,
            changed_fields=changed_fields,
            before_data=old_data,
            after_data=new_data,
            result='success'
        )

    def perform_create(self, serializer):
        """Create a proxy with cache invalidation."""
        # Invalidate all caches when a new proxy is created
        invalidate_cache()
        serializer.save()

    @extend_schema(
        summary='Get installation command',
        description='Generate installation command for a specific OS.',
        request=InstallCommandSerializer,
        responses={200: InstallCommandResponseSerializer}
    )
    @action(detail=False, methods=['post'])
    def generate_install(self, request):
        """
        Generate installation command for a new proxy.

        This creates a pending proxy and returns the installation command.
        """
        from licenses.quota import enforce_license_quota

        enforce_license_quota(getattr(request.user, 'tenant', None), 'proxies')
        
        serializer = InstallCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # Check if name already exists
        if ProxyNode.objects.filter(name=data['name']).exists():
            return Response(
                {'error': f'Proxy with name "{data["name"]}" already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the proxy
        proxy = ProxyNode.objects.create(
            name=data['name'],
            role=data['role'],
            target_os=data.get('os', 'linux'),
            owner=request.user,
            tenant=getattr(request.user, 'tenant', None),
            status=ProxyNode.NodeStatus.PENDING,
            api_token=secrets.token_urlsafe(32),
            install_token=secrets.token_urlsafe(32)
        )

        # Get server URL
        server_url = data.get('server_url') or getattr(
            settings, 'PROXY_SERVER_URL',
            request.build_absolute_uri('/').rstrip('/')
        )

        # Build commands
        install_command = self._build_install_command(
            server_url=server_url,
            role=proxy.role,
            proxy_id=proxy.id,
            install_token=proxy.install_token,
            os_type=data['os'],
            name=proxy.name
        )

        windows_command = self._build_install_command(
            server_url=server_url,
            role=proxy.role,
            proxy_id=proxy.id,
            install_token=proxy.install_token,
            os_type='windows',
            name=proxy.name
        )

        # Generate config YAML
        config_yaml = self._generate_config_yaml(
            server_url=server_url,
            role=proxy.role,
            install_token=proxy.install_token,
            name=proxy.name,
            labels=data.get('labels', [])
        )

        proxy.install_command = install_command
        proxy.installed_by = request.user
        proxy.save()

        # Record audit log
        AuditService.log_proxy_create(request, proxy, result='success')

        response_data = {
            'proxy_id': proxy.id,
            'name': proxy.name,
            'role': proxy.role,
            'install_token': proxy.install_token,
            'api_token': proxy.api_token,
            'install_command': install_command,
            'windows_command': windows_command,
            'config_yaml': config_yaml,
            'expires_at': timezone.now() + timezone.timedelta(hours=24)
        }

        return Response(response_data)

    @extend_schema(
        summary='Regenerate install token',
        description='Regenerate the install token for a pending proxy. The old token will be invalidated immediately.',
        responses={200: OpenApiResponse(
            description='New install information',
            response={
                'type': 'object',
                'properties': {
                    'proxy_id': {'type': 'string'},
                    'install_token': {'type': 'string'},
                    'install_command': {'type': 'string'},
                    'windows_command': {'type': 'string'},
                }
            }
        )}
    )
    @action(detail=True, methods=['post'])
    def regenerate_token(self, request, pk=None):
        """Regenerate install token for a pending proxy."""
        proxy = self.get_object()

        # Only allow for pending proxies
        if proxy.status != ProxyNode.NodeStatus.PENDING:
            AuditService.log_proxy_token_regenerate(request, proxy, result='failure', 
                error_message='Can only regenerate token for pending proxies')
            return Response(
                {'error': 'Can only regenerate token for pending proxies'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate new tokens
        proxy.install_token = secrets.token_urlsafe(32)
        proxy.api_token = secrets.token_urlsafe(32)
        proxy.install_token_used = False
        proxy.save()

        # Get server URL
        server_url = getattr(
            settings, 'PROXY_SERVER_URL',
            request.build_absolute_uri('/').rstrip('/')
        )

        # Build new commands
        install_command = self._build_install_command(
            server_url=server_url,
            role=proxy.role,
            proxy_id=proxy.id,
            install_token=proxy.install_token,
            os_type=proxy.target_os or 'linux',
            name=proxy.name
        )

        windows_command = self._build_install_command(
            server_url=server_url,
            role=proxy.role,
            proxy_id=proxy.id,
            install_token=proxy.install_token,
            os_type='windows',
            name=proxy.name
        )

        proxy.install_command = install_command
        proxy.save()
        
        # Record audit log
        AuditService.log_proxy_token_regenerate(request, proxy, result='success')

        return Response({
            'proxy_id': proxy.id,
            'install_token': proxy.install_token,
            'api_token': proxy.api_token,
            'install_command': install_command,
            'windows_command': windows_command,
        })

    def _generate_config_yaml(self, server_url, role, install_token, name, labels):
        """Generate configuration YAML for manual installation."""
        labels_str = '\n'.join([f'    - "{label}"' for label in labels]) if labels else '  []'

        return f'''# HyperFileLens Proxy Configuration
# Save as /etc/hyperfilelens/config.yaml

version: "1.0.0"
role: "{role}"

server:
  url: "{server_url}"
  api_token: ""  # Will be set after registration
  install_token: "{install_token}"
  ws_protocol: "wss"
  reconnect_delay: 5s
  heartbeat_interval: 10s

agent:
  name: "{name}"
  hostname: ""  # Auto-detected

kopia:
  path: "/usr/local/bin/kopia"
  cache_path: "/var/lib/hyperfilelens/cache"

mount:  # Sync Proxy only
  enabled: false
  nfs: {{}}
  smb: {{}}

labels:
{labels_str}

logging:
  level: "info"
  file: "/var/log/hyperfilelens/proxy.log"
'''

    @extend_schema(
        summary='Get proxy statistics',
        description='Get statistics summary for all proxies.',
        responses={200: ProxyStatsSerializer}
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get proxy statistics using optimized queries."""
        hours = int(request.query_params.get('hours', 24))

        # Use optimized query from query_optimizations module
        queryset = self.get_queryset()

        # Get statistics with optimized single query using annotations
        from django.db.models import Count, Q

        stats = queryset.annotate(
            online_count=Count('id', filter=Q(status=ProxyNode.NodeStatus.ONLINE)),
            offline_count=Count('id', filter=Q(status=ProxyNode.NodeStatus.OFFLINE)),
            agent_count=Count('id', filter=Q(role=ProxyNode.Role.AGENT)),
            sync_count=Count('id', filter=Q(role=ProxyNode.Role.SYNC)),
        ).aggregate(
            total=Count('id'),
            online=Count('id', filter=Q(status=ProxyNode.NodeStatus.ONLINE)),
            offline=Count('id', filter=Q(status=ProxyNode.NodeStatus.OFFLINE)),
            agent_count=Count('id', filter=Q(role=ProxyNode.Role.AGENT)),
            sync_count=Count('id', filter=Q(role=ProxyNode.Role.SYNC)),
        )

        total = stats['total']
        online = stats['online']
        offline = stats['offline']

        # Group by status (optimized query)
        by_status = dict(
            queryset.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )

        # Group by OS (optimized query)
        by_os = dict(
            queryset.exclude(operating_system='')
            .values('operating_system')
            .annotate(count=Count('id'))
            .values_list('operating_system', 'count')
        )

        # Average uptime for active proxies (optimized)
        avg_uptime = 0
        active_proxies = queryset.filter(status=ProxyNode.NodeStatus.ONLINE)
        if active_proxies.exists():
            total_uptime = sum(
                (timezone.now() - p.registered_at).total_seconds()
                for p in active_proxies
                if p.registered_at
            )
            avg_uptime = total_uptime / active_proxies.count() if active_proxies.count() > 0 else 0

        # Total active tasks (optimized query)
        total_tasks = ProxyTask.objects.filter(
            proxy__in=queryset,
            status__in=['pending', 'dispatched', 'accepted', 'running']
        ).count()

        data = {
            'total_proxies': total,
            'online_proxies': online,
            'offline_proxies': offline,
            'agent_proxies': stats['agent_count'],
            'sync_proxies': stats['sync_count'],
            'proxies_by_status': by_status,
            'proxies_by_os': by_os,
            'average_uptime': avg_uptime,
            'total_active_tasks': total_tasks,
            'time_range_hours': hours,
        }

        return Response(data)

    @extend_schema(
        summary='Get agent proxies',
        description='List all agent proxies.',
    )
    @action(detail=False, methods=['get'])
    def agents(self, request):
        """List agent proxies."""
        queryset = self.get_queryset().filter(role=ProxyNode.Role.AGENT)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ProxyNodeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ProxyNodeSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Get sync proxies',
        description='List all sync proxies.',
    )
    @action(detail=False, methods=['get'])
    def syncs(self, request):
        """List sync proxies."""
        queryset = self.get_queryset().filter(role=ProxyNode.Role.SYNC)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ProxyNodeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ProxyNodeSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Get proxy heartbeats',
        description='Get heartbeat history for a specific proxy.',
        parameters=[
            OpenApiParameter(name='hours', description='Time range in hours', type=int, required=False, default=24),
            OpenApiParameter(name='page', description='Page number for pagination', type=int, required=False, default=1),
            OpenApiParameter(name='page_size', description='Items per page', type=int, required=False, default=50),
        ],
        responses={200: ProxyHeartbeatSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def heartbeats(self, request, pk=None):
        """Get heartbeat history for a proxy with pagination."""
        proxy = self.get_object()
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timezone.timedelta(hours=hours)
        
        # Get heartbeats in time range, ordered by most recent first
        queryset = proxy.heartbeats.filter(timestamp__gte=since).order_by('-timestamp')
        
        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ProxyHeartbeatSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ProxyHeartbeatSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Get proxy directories',
        description='Get directory listing for a Sync Proxy. Used for browsing local filesystem.',
        parameters=[
            OpenApiParameter(
                name='path',
                description='Directory path to list',
                type=str,
                required=False,
                default='/'
            )
        ],
        responses={200: OpenApiResponse(description='Directory listing')}
    )
    @action(detail=True, methods=['get'])
    def directories(self, request, pk=None):
        """Get directory listing for a Sync Proxy."""
        proxy = self.get_object()
        
        # Check if proxy is online
        if proxy.status != ProxyNode.NodeStatus.ONLINE:
            return Response(
                {'error': 'Proxy is not online.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        path = request.query_params.get('path') or '/'
        task = ProxyTask.objects.create(
            proxy=proxy,
            task_type=ProxyTask.TaskType.VERIFY,
            parameters={
                'operation': 'list_directory',
                'path': path,
            },
            status=ProxyTask.TaskStatus.PENDING,
            timeout_seconds=30,
        )

        task.dispatch()
        ProxyService.send_list_directory_command(
            proxy_id=str(proxy.id),
            path=path,
            task_id=str(task.id),
        )

        task = self._wait_for_proxy_task(task, timeout=8)
        if task.status == ProxyTask.TaskStatus.COMPLETED:
            result = task.result or {}
            entries = result.get('directories') or []
            return Response({
                'path': result.get('path') or path,
                'directories': [
                    item.get('name') for item in entries
                    if isinstance(item, dict) and item.get('name')
                ],
                'entries': entries,
                'task_id': str(task.id),
            })

        if task.status == ProxyTask.TaskStatus.FAILED:
            return Response(
                {
                    'error': task.error_message or 'Failed to list directory.',
                    'task_id': str(task.id),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                'error': 'Directory listing timed out.',
                'task_id': str(task.id),
            },
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )

    @extend_schema(
        summary='Verify proxy local path',
        description='Verify a local filesystem path on a Sync Proxy.',
        responses={200: OpenApiResponse(description='Path verification result')}
    )
    @action(detail=True, methods=['post'], url_path='verify-path')
    def verify_path(self, request, pk=None):
        """Verify local path existence, access and writability on a Sync Proxy."""
        proxy = self.get_object()

        if proxy.role != ProxyNode.Role.SYNC:
            return Response(
                {'error': 'Only Sync Proxy can verify local repository paths.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if proxy.status != ProxyNode.NodeStatus.ONLINE:
            return Response(
                {'error': 'Proxy is not online.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        path = (request.data.get('path') or '').strip()
        if not path:
            return Response(
                {'error': 'Path is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        task = ProxyTask.objects.create(
            proxy=proxy,
            task_type=ProxyTask.TaskType.TEST_STORAGE,
            parameters={
                'operation': 'verify_path',
                'storage_type': 'local',
                'storage_config': {'path': path},
            },
            status=ProxyTask.TaskStatus.PENDING,
            timeout_seconds=30,
        )

        task.dispatch()
        ProxyService.send_test_storage_command(
            proxy_id=str(proxy.id),
            repository_id='',
            storage_type='local',
            storage_config={'path': path},
            test_write=True,
            task_id=str(task.id),
        )

        task = self._wait_for_proxy_task(task, timeout=10)
        if task.status == ProxyTask.TaskStatus.COMPLETED:
            result = task.result or {}
            write_test = result.get('write_test') or {}
            space_info = result.get('space_info') or {}
            connectivity = result.get('connectivity') or {}
            return Response({
                'success': result.get('success', True),
                'path': path,
                'message': result.get('message') or 'Path verification successful.',
                'exists': connectivity.get('reachable', True),
                'writable': write_test.get('writable'),
                'write_test': write_test,
                'space_info': space_info,
                'details': result,
                'task_id': str(task.id),
            })

        if task.status == ProxyTask.TaskStatus.FAILED:
            return Response(
                {
                    'success': False,
                    'path': path,
                    'error': task.error_message or 'Path verification failed.',
                    'task_id': str(task.id),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                'success': False,
                'path': path,
                'error': 'Path verification timed out.',
                'task_id': str(task.id),
            },
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )

    def _wait_for_proxy_task(self, task: ProxyTask, timeout: int = 10) -> ProxyTask:
        """Wait briefly for an interactive proxy task result."""
        deadline = time.monotonic() + timeout
        terminal_statuses = {
            ProxyTask.TaskStatus.COMPLETED,
            ProxyTask.TaskStatus.FAILED,
            ProxyTask.TaskStatus.CANCELLED,
            ProxyTask.TaskStatus.TIMEOUT,
        }
        while time.monotonic() < deadline:
            task.refresh_from_db()
            if task.status in terminal_statuses:
                return task
            time.sleep(0.2)
        task.refresh_from_db()
        return task

    @extend_schema(
        summary='Get proxy tasks',
        description='Get task history for a specific proxy.',
        responses={200: ProxyTaskSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        """Get task history for a proxy with optimized query."""
        proxy = self.get_object()
        limit = int(request.query_params.get('limit', 50))

        # Use optimized query with annotations for task statistics
        proxy_with_stats = ProxyNode.objects.filter(id=proxy.id).annotate(
            total_tasks=Count('tasks'),
            completed_tasks=Count('tasks', filter=Q(tasks__status='completed')),
            failed_tasks=Count('tasks', filter=Q(tasks__status='failed')),
            running_tasks=Count('tasks', filter=Q(tasks__status__in=['pending', 'dispatched', 'accepted', 'running'])),
        ).first()

        # Get tasks with optimized query using select_related
        tasks = proxy.tasks.select_related('proxy').order_by('-created_at')[:limit]

        serializer = ProxyTaskSerializer(tasks, many=True)
        return Response({
            'tasks': serializer.data,
            'stats': {
                'total': proxy_with_stats.total_tasks,
                'completed': proxy_with_stats.completed_tasks,
                'failed': proxy_with_stats.failed_tasks,
                'running': proxy_with_stats.running_tasks,
            }
        })

    @extend_schema(
        summary='Get proxy overview',
        description='Get overview data for a specific proxy including system info, resources, and stats.',
    )
    @action(detail=True, methods=['get'])
    def overview(self, request, pk=None):
        """Get overview data for a proxy with optimized query."""
        proxy = self.get_object()
        since = timezone.now() - timezone.timedelta(hours=24)
        heartbeats = proxy.heartbeats.filter(timestamp__gte=since).order_by('timestamp')

        # Calculate uptime
        uptime_seconds = None
        if proxy.registered_at:
            uptime_seconds = int((timezone.now() - proxy.registered_at).total_seconds())

        # Task statistics - optimized with single query using annotations
        proxy_with_task_stats = ProxyNode.objects.filter(id=proxy.id).annotate(
            total_tasks=Count('tasks'),
            completed_tasks=Count('tasks', filter=Q(tasks__status='completed')),
            failed_tasks=Count('tasks', filter=Q(tasks__status='failed')),
            running_tasks=Count('tasks', filter=Q(tasks__status__in=['pending', 'dispatched', 'accepted', 'running'])),
        ).first()

        total_tasks = proxy_with_task_stats.total_tasks
        completed_tasks = proxy_with_task_stats.completed_tasks
        failed_tasks = proxy_with_task_stats.failed_tasks
        running_tasks = proxy_with_task_stats.running_tasks

        # Heartbeat stats - calculate based on actual registration time
        total_heartbeats = heartbeats.count()

        # Calculate expected heartbeats based on actual uptime (max 24 hours)
        heartbeat_interval = proxy.heartbeat_interval or 10  # Default 10 seconds
        if proxy.registered_at:
            uptime_hours = min(24, (timezone.now() - proxy.registered_at).total_seconds() / 3600)
        else:
            uptime_hours = 24
        expected_heartbeats = int((uptime_hours * 3600) / heartbeat_interval)

        # Average values
        avg_cpu = 0
        avg_memory = 0
        avg_disk = 0
        if total_heartbeats > 0:
            avg_cpu = sum(h.cpu_usage or 0 for h in heartbeats) / total_heartbeats
            avg_memory = sum(h.memory_usage or 0 for h in heartbeats) / total_heartbeats
            avg_disk = sum(h.disk_usage or 0 for h in heartbeats) / total_heartbeats

        data = {
            # Basic info
            'id': str(proxy.id),
            'name': proxy.name,
            'role': proxy.role,
            'status': proxy.status,
            'is_online': proxy.is_online(),
            'owner_name': proxy.owner.username if proxy.owner else None,
            'created_at': proxy.created_at.isoformat() if proxy.created_at else None,

            # System info
            'hostname': proxy.hostname,
            'internal_ip': proxy.internal_ip,
            'operating_system': proxy.operating_system,
            'os_version': proxy.os_version,
            'version': proxy.version,
            'kopia_version': proxy.kopia_version,
            'uptime_seconds': uptime_seconds,

            # Hardware resources
            'cpu_cores': proxy.cpu_cores,
            'cpu_usage': proxy.cpu_usage,
            'memory_total': proxy.memory_total,
            'memory_usage': proxy.memory_usage,
            'disk_total': proxy.disk_total,
            'disk_usage': proxy.disk_usage,

            # Network
            'last_heartbeat': proxy.last_heartbeat.isoformat() if proxy.last_heartbeat else None,
            'heartbeat_interval': proxy.heartbeat_interval,

            # Capabilities and labels
            'capabilities': proxy.capabilities or {},
            'labels': proxy.labels or [],
            
            # Stats
            'stats': {
                'heartbeats_24h': total_heartbeats,
                'expected_24h': expected_heartbeats,
                'missed_heartbeats': max(0, expected_heartbeats - total_heartbeats),
                'avg_cpu': round(avg_cpu, 2),
                'avg_memory': round(avg_memory, 2),
                'avg_disk': round(avg_disk, 2),
            },
            
            # Task stats
            'task_stats': {
                'total': total_tasks,
                'completed': completed_tasks,
                'failed': failed_tasks,
                'running': running_tasks,
            },
        }
        
        return Response(data)

    @extend_schema(
        summary='Get proxy monitor stats',
        description='Get monitoring statistics for a specific proxy.',
    )
    @action(detail=True, methods=['get'])
    def monitor(self, request, pk=None):
        """Get monitoring statistics for a proxy with optimized query."""
        proxy = self.get_object()
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timezone.timedelta(hours=hours)

        # Get heartbeats in time range
        heartbeats = proxy.heartbeats.filter(timestamp__gte=since).order_by('timestamp')

        # Calculate stats
        total_heartbeats = heartbeats.count()

        # Task statistics - optimized with single query using annotations
        proxy_with_task_stats = ProxyNode.objects.filter(id=proxy.id).annotate(
            total_tasks=Count('tasks'),
            completed_tasks=Count('tasks', filter=Q(tasks__status='completed')),
            failed_tasks=Count('tasks', filter=Q(tasks__status='failed')),
            running_tasks=Count('tasks', filter=Q(tasks__status__in=['pending', 'running'])),
        ).first()

        total_tasks = proxy_with_task_stats.total_tasks
        completed_tasks = proxy_with_task_stats.completed_tasks
        failed_tasks = proxy_with_task_stats.failed_tasks
        running_tasks = proxy_with_task_stats.running_tasks

        # Calculate average values from heartbeats
        avg_cpu = 0
        avg_memory = 0
        avg_disk = 0

        if total_heartbeats > 0:
            avg_cpu = sum(h.cpu_usage or 0 for h in heartbeats) / total_heartbeats
            avg_memory = sum(h.memory_usage or 0 for h in heartbeats) / total_heartbeats
            avg_disk = sum(h.disk_usage or 0 for h in heartbeats) / total_heartbeats

        # Get last 100 heartbeats for chart data
        chart_heartbeats = list(heartbeats.order_by('-timestamp')[:100])

        # Format chart data for each metric
        cpu_usage_data = []
        memory_usage_data = []
        disk_usage_data = []
        network_io_data = []  # {timestamp, interface, bytes_in, bytes_out, packets_in, packets_out, drop_in, errs_in}
        disk_io_data = []  # {timestamp, disk, read_bytes, write_bytes, read_count, write_count, utilization, await}

        for h in reversed(chart_heartbeats):
            timestamp = h.timestamp.isoformat()
            cpu_usage_data.append({'timestamp': timestamp, 'value': h.cpu_usage or 0})
            memory_usage_data.append({'timestamp': timestamp, 'value': h.memory_usage or 0})
            disk_usage_data.append({'timestamp': timestamp, 'value': h.disk_usage or 0})

            # Extract network and disk IO data from metadata
            metadata = h.metadata or {}

            # Flatten network interfaces - each interface as a separate record
            for ni in metadata.get('network_interfaces', []):
                network_io_data.append({
                    'timestamp': timestamp,
                    'interface': ni.get('name'),
                    'rx_bytes': ni.get('bytes_in', 0),
                    'tx_bytes': ni.get('bytes_out', 0),
                    'rx_packets': ni.get('packets_in', 0),
                    'tx_packets': ni.get('packets_out', 0),
                    'rx_drop': ni.get('drop_in', 0),
                    'tx_drop': ni.get('drop_out', 0),
                    'rx_errs': ni.get('errs_in', 0),
                    'tx_errs': ni.get('errs_out', 0),
                })

            # Flatten disk IO stats - each disk as a separate record
            for disk in metadata.get('disk_io_stats', []):
                disk_io_data.append({
                    'timestamp': timestamp,
                    'disk': disk.get('name'),
                    'read_bytes': disk.get('read_bytes', 0),
                    'write_bytes': disk.get('write_bytes', 0),
                    'read_count': disk.get('read_count', 0),
                    'write_count': disk.get('write_count', 0),
                    'utilization': disk.get('utilization', 0),
                    'await': disk.get('await', 0),
                    'io_time_ms': disk.get('io_time_ms', 0),
                    # Calculate IOPS and throughput rates
                    'r_s': disk.get('read_count', 0),
                    'w_s': disk.get('write_count', 0),
                    'rkB_s': disk.get('read_bytes', 0) / 1024,
                    'wkB_s': disk.get('write_bytes', 0) / 1024,
                })

        # Calculate uptime from registered_at
        uptime_seconds = None
        if proxy.registered_at:
            uptime_seconds = int((timezone.now() - proxy.registered_at).total_seconds())

        data = {
            'proxy_id': str(proxy.id),
            'status': proxy.status,
            'is_online': proxy.is_online(),
            'uptime_seconds': uptime_seconds,
            'last_heartbeat': proxy.last_heartbeat.isoformat() if proxy.last_heartbeat else None,

            # Current resource usage
            'current': {
                'cpu_usage': proxy.cpu_usage,
                'memory_usage': proxy.memory_usage,
                'disk_usage': proxy.disk_usage,
                'cpu_cores': proxy.cpu_cores,
                'memory_total_gb': round(proxy.memory_total / (1024**3), 2) if proxy.memory_total else None,
                'disk_total_gb': round(proxy.disk_total / (1024**3), 2) if proxy.disk_total else None,
            },

            # Average values
            'averages': {
                'cpu_usage': round(avg_cpu, 2),
                'memory_usage': round(avg_memory, 2),
                'disk_usage': round(avg_disk, 2),
            },

            # Heartbeat stats
            'heartbeat_stats': {
                'total_24h': total_heartbeats,
                'expected_24h': hours * 6,  # Assuming 10 second interval
                'missed_heartbeats': max(0, hours * 6 - total_heartbeats),
            },

            # Task stats
            'task_stats': {
                'total': total_tasks,
                'completed': completed_tasks,
                'failed': failed_tasks,
                'running': running_tasks,
            },

            # Chart data (formatted for frontend charts)
            'cpu_usage': cpu_usage_data,
            'memory_usage': memory_usage_data,
            'disk_usage': disk_usage_data,
            'network_io': network_io_data,
            'disk_io': disk_io_data,

            # Network interfaces - consolidated with stats
            'network_interfaces': {
                'interfaces': [
                    {
                        'name': ni.get('name'),
                        'ip_address': ni.get('ip_addresses', [])[0] if ni.get('ip_addresses') else None,
                        'mac_address': ni.get('mac'),
                        'bytes_in': ni.get('bytes_in', 0),
                        'bytes_out': ni.get('bytes_out', 0),
                    }
                    for ni in (proxy.network_interfaces or [])
                ],
                'total_bytes_in': proxy.network_bytes_recv or sum(ni.get('bytes_in', 0) for ni in (proxy.network_interfaces or [])),
                'total_bytes_out': proxy.network_bytes_sent or sum(ni.get('bytes_out', 0) for ni in (proxy.network_interfaces or [])),
                'total_bytes_in_gb': round((proxy.network_bytes_recv or 0) / (1024**3), 2),
                'total_bytes_out_gb': round((proxy.network_bytes_sent or 0) / (1024**3), 2),
            },
        }

        return Response(data)

    @extend_schema(
        summary='Receive proxy heartbeat',
        description='Receive heartbeat from a specific proxy by ID.',
        request=ProxyHeartbeatCreateSerializer,
        responses={200: ProxyNodeSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def heartbeat(self, request, pk=None):
        """Receive heartbeat from a specific proxy."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            proxy = ProxyNode.objects.get(id=pk)
        except ProxyNode.DoesNotExist:
            return Response(
                {'error': 'Proxy not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Debug logging
        logger.info(f"[Heartbeat] Received data keys: {list(request.data.keys())}")
        logger.info(f"[Heartbeat] network_interfaces: {request.data.get('network_interfaces', 'NOT FOUND')}")
        logger.info(f"[Heartbeat] disk_io_stats: {request.data.get('disk_io_stats', 'NOT FOUND')}")

        # Validate API token
        api_token = request.data.get('api_token')
        if not api_token:
            # Try to get from header
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Token '):
                api_token = auth_header[6:]

        if not api_token or api_token != proxy.api_token:
            return Response(
                {'error': 'Invalid API token'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        data = request.data

        # Update proxy heartbeat with network interfaces data
        proxy.update_heartbeat({
            'version': data.get('version'),
            'kopia_version': data.get('kopia_version'),
            'hostname': data.get('hostname'),
            'internal_ip': data.get('internal_ip'),
            'os': data.get('os'),
            'os_version': data.get('os_version'),
            'cpu_cores': data.get('cpu_cores'),
            'memory_total': data.get('memory_total'),
            'disk_total': data.get('disk_total'),
            'cpu_usage': data.get('cpu_usage'),
            'memory_usage': data.get('memory_usage'),
            'disk_usage': data.get('disk_usage'),
            'active_tasks': data.get('active_tasks', 0),
            'capabilities': data.get('capabilities', {}),
            'network_interfaces': data.get('network_interfaces', []),
            'network_bytes_sent': data.get('network_bytes_sent'),
            'network_bytes_recv': data.get('network_bytes_recv'),
        })

        # Create heartbeat record with network and disk IO data in metadata
        heartbeat_metadata = data.get('metadata', {})
        if data.get('network_interfaces'):
            heartbeat_metadata['network_interfaces'] = data.get('network_interfaces')
        if data.get('disk_io_stats'):
            heartbeat_metadata['disk_io_stats'] = data.get('disk_io_stats')

        ProxyHeartbeat.objects.create(
            proxy=proxy,
            cpu_usage=data.get('cpu_usage'),
            memory_usage=data.get('memory_usage'),
            disk_usage=data.get('disk_usage'),
            network_in=data.get('network_in'),
            network_out=data.get('network_out'),
            active_tasks=data.get('active_tasks', 0),
            completed_tasks=data.get('completed_tasks', 0),
            failed_tasks=data.get('failed_tasks', 0),
            metadata=heartbeat_metadata
        )
        evaluate_proxy_metric_alerts(proxy)

        return Response({
            'status': 'ok',
            'node_id': str(proxy.id),
            'timestamp': timezone.now().isoformat(),
        })

    @extend_schema(
        summary='Update proxy status',
        description='Update the status of a specific proxy.',
    )
    @action(detail=True, methods=['post'])
    def set_status(self, request, pk=None):
        """Update proxy status."""
        proxy = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(ProxyNode.NodeStatus.choices):
            return Response(
                {'error': 'Invalid status value.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        proxy.status = new_status
        proxy.save(update_fields=['status', 'updated_at'])
        serializer = ProxyNodeSerializer(proxy)
        return Response(serializer.data)

    @extend_schema(
        summary='Register proxy',
        description='Register a proxy using install_token to get api_token.',
        request=ProxyRegisterSerializer,
        responses={200: OpenApiResponse(description='Registration successful')}
    )
    @action(detail=False, methods=['post'], authentication_classes=[], permission_classes=[])
    def register(self, request):
        """
        Register a proxy using proxy_id and install_token.
        
        This is called by the proxy during installation to:
        1. Verify the installation is authorized
        2. Get the api_token for ongoing communication
        3. Report system information
        
        Flow:
        1. User creates proxy in Web UI → gets install command with proxy_id and install_token
        2. Install script calls this API with proxy_id, install_token, and system info
        3. Server verifies and returns api_token
        4. Proxy saves api_token locally for future communication
        """
        serializer = ProxyRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        proxy = data['proxy']
        
        # Verify proxy_id matches (additional security check)
        if 'node_id' in data and str(proxy.id) != str(data['node_id']):
            return Response(
                {'error': 'Proxy ID mismatch'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update proxy with registration info
        proxy.hostname = data.get('hostname', '')
        proxy.internal_ip = data.get('internal_ip', '')
        proxy.os_type = data.get('os', '')
        proxy.os_version = data.get('os_version', '')
        proxy.version = data.get('version', '')
        proxy.kopia_version = data.get('kopia_version', '')
        proxy.cpu_cores = data.get('cpu_cores')
        proxy.memory_total = data.get('memory_total')
        proxy.disk_total = data.get('disk_total')
        if data.get('capabilities'):
            proxy.capabilities = data['capabilities']
        proxy.status = ProxyNode.NodeStatus.ONLINE
        proxy.install_token_used = True  # Mark install token as used
        proxy.save()
        
        return Response({
            'proxy_id': str(proxy.id),
            'node_id': str(proxy.id),
            'tenant_id': str(proxy.tenant_id) if proxy.tenant else None,
            'api_token': proxy.api_token,
            'name': proxy.name,
            'role': proxy.role,
            'server_url': request.build_absolute_uri('/').rstrip('/'),
            'message': 'Registration successful'
        })

    @extend_schema(
        summary='Regenerate API token',
        description='Regenerate the API token for a proxy.',
    )
    @action(detail=True, methods=['post'])
    def regenerate_token(self, request, pk=None):
        """
        Regenerate API token and install token.
        
        Returns new tokens and installation command.
        Useful when:
        1. Token is lost or compromised
        2. Need to reinstall the proxy
        3. Installation failed and need to retry
        """
        import secrets
        proxy = self.get_object()
        
        # Regenerate both tokens
        proxy.api_token = secrets.token_urlsafe(32)
        proxy.install_token = secrets.token_urlsafe(32)
        
        # Get server URL from settings or request
        server_url = getattr(settings, 'PROXY_SERVER_URL', None)
        if not server_url:
            server_url = request.build_absolute_uri('/').rstrip('/')
        
        # Use saved target_os or default to linux
        os_type = proxy.target_os or 'linux'
        
        # Generate installation command using the unified method
        install_cmd = self._build_install_command(
            server_url=server_url,
            role=proxy.role,
            proxy_id=proxy.id,
            install_token=proxy.install_token,
            os_type=os_type,
            name=proxy.name
        )
        
        # Update install_command in database
        proxy.install_command = install_cmd
        proxy.save(update_fields=['api_token', 'install_token', 'install_command'])
        
        # Record audit log
        AuditService.log_proxy_token_regenerate(request, proxy, result='success')
        
        return Response({
            'id': str(proxy.id),
            'proxy_id': str(proxy.id),
            'name': proxy.name,
            'role': proxy.role,
            'status': proxy.status,
            'api_token': proxy.api_token,
            'install_token': proxy.install_token,
            'install_command': install_cmd,
            'install_token_used': proxy.install_token_used,
            'message': 'Tokens regenerated successfully'
        })


class ProxyHeartbeatView(APIView):
    """
    View for receiving proxy heartbeats.

    This endpoint is called by proxies to report their status.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary='Receive proxy heartbeat',
        description='Receive and process heartbeat data from a proxy.',
        request=ProxyHeartbeatCreateSerializer,
        responses={
            200: ProxyNodeSerializer,
            401: OpenApiResponse(description='Invalid credentials'),
        }
    )
    def post(self, request):
        """Receive heartbeat from proxy."""
        serializer = ProxyHeartbeatCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        proxy = serializer.validated_data['proxy']
        data = serializer.validated_data

        # Update proxy heartbeat with network interfaces data
        update_data = {
            'version': data.get('version'),
            'kopia_version': data.get('kopia_version'),
            'hostname': data.get('hostname'),
            'internal_ip': data.get('internal_ip'),
            'os': data.get('os'),
            'os_version': data.get('os_version'),
            'cpu_cores': data.get('cpu_cores'),
            'memory_total': data.get('memory_total'),
            'disk_total': data.get('disk_total'),
            'cpu_usage': data.get('cpu_usage'),
            'memory_usage': data.get('memory_usage'),
            'disk_usage': data.get('disk_usage'),
            'active_tasks': data.get('active_tasks', 0),
            'capabilities': data.get('capabilities', {}),
            'network_interfaces': data.get('network_interfaces', []),
            'network_bytes_sent': data.get('network_bytes_sent'),
            'network_bytes_recv': data.get('network_bytes_recv'),
        }
        proxy.update_heartbeat(update_data)

        # Create heartbeat record with network and disk IO data in metadata
        heartbeat_metadata = data.get('metadata', {})
        if data.get('network_interfaces'):
            heartbeat_metadata['network_interfaces'] = data.get('network_interfaces')
        if data.get('disk_io_stats'):
            heartbeat_metadata['disk_io_stats'] = data.get('disk_io_stats')

        ProxyHeartbeat.objects.create(
            proxy=proxy,
            cpu_usage=data.get('cpu_usage'),
            memory_usage=data.get('memory_usage'),
            disk_usage=data.get('disk_usage'),
            network_in=data.get('network_in'),
            network_out=data.get('network_out'),
            active_tasks=data.get('active_tasks', 0),
            completed_tasks=data.get('completed_tasks', 0),
            failed_tasks=data.get('failed_tasks', 0),
            metadata=heartbeat_metadata
        )
        evaluate_proxy_metric_alerts(proxy)

        return Response({
            'status': 'ok',
            'node_id': str(proxy.id),
            'server_time': timezone.now()
        })

def build_global_task_items(request):
    """Build a normalized task list across proxy, backup, and recovery tasks."""
    from backup_tasks.models import BackupTask
    from recovery_tasks.models import RecoveryTask

    user = request.user
    status_filter = request.query_params.get('status')
    source_filter = request.query_params.get('source')
    search = (request.query_params.get('search') or '').lower()

    tasks = []

    def allowed_proxy_queryset():
        qs = ProxyTask.objects.select_related('proxy').order_by('-created_at')
        if user.is_superuser:
            return qs
        if getattr(user, 'tenant', None):
            return qs.filter(proxy__tenant=user.tenant)
        return qs.filter(proxy__owner=user)

    def append_task(item):
        if status_filter and item['status'] != status_filter:
            return
        if source_filter and item['source'] != source_filter:
            return
        searchable = item.get('name', '') + item.get('message', '') + item.get('proxy_name', '')
        if search and search not in searchable.lower():
            return
        tasks.append(item)

    for task in allowed_proxy_queryset():
        append_task({
            'id': str(task.id),
            'source': 'proxy',
            'name': f"{task.get_task_type_display()} - {task.proxy.name}",
            'task_type': task.task_type,
            'status': task.status,
            'progress': task.progress,
            'message': task.progress_message or task.error_message or '',
            'proxy_id': str(task.proxy_id),
            'proxy_name': task.proxy.name,
            'repository_id': str(task.repository_id) if task.repository_id else None,
            'source_resource_id': str(task.source_resource_id) if task.source_resource_id else None,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'duration_seconds': ProxyTaskSerializer().get_duration_seconds(task),
            'parameters': task.parameters,
            'result': task.result,
            'error_message': task.error_message,
        })

    backup_qs = BackupTask.objects.select_related('source_resource', 'target_repository', 'user').order_by('-created_at')
    if not user.is_superuser:
        if getattr(user, 'tenant', None):
            backup_qs = backup_qs.filter(tenant=user.tenant)
        else:
            backup_qs = backup_qs.filter(user=user)
    for task in backup_qs:
        execution_node = task.execution_node if task.source_resource else None
        append_task({
            'id': str(task.id),
            'source': 'backup',
            'name': task.name,
            'task_type': task.task_type,
            'status': task.status,
            'progress': task.progress,
            'message': task.status_message or task.error_message or '',
            'proxy_id': str(execution_node.id) if execution_node else None,
            'proxy_name': execution_node.name if execution_node else '',
            'repository_id': str(task.target_repository_id),
            'source_resource_id': str(task.source_resource_id) if task.source_resource_id else None,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'duration_seconds': task.duration,
            'parameters': {'backup_paths': task.backup_paths, 'exclude_patterns': task.exclude_patterns},
            'result': {
                'total_files': task.total_files,
                'processed_files': task.backed_up_files,
                'total_bytes': task.total_size,
                'processed_bytes': task.backed_up_size,
                'failed_files': task.failed_files,
                'skipped_files': task.skipped_files,
            },
            'error_message': task.error_message,
        })

    recovery_qs = RecoveryTask.objects.select_related('snapshot', 'target_node', 'user').order_by('-created_at')
    if not user.is_superuser:
        if getattr(user, 'tenant', None):
            recovery_qs = recovery_qs.filter(tenant=user.tenant)
        else:
            recovery_qs = recovery_qs.filter(user=user)
    for task in recovery_qs:
        append_task({
            'id': str(task.id),
            'source': 'recovery',
            'name': task.name,
            'task_type': task.recovery_type,
            'status': task.status,
            'progress': task.progress,
            'message': task.error_message or '',
            'proxy_id': str(task.target_node_id) if task.target_node_id else None,
            'proxy_name': task.target_node.name if task.target_node_id else '',
            'repository_id': str(task.snapshot.repository_id) if task.snapshot_id and getattr(task.snapshot, 'repository_id', None) else None,
            'source_resource_id': None,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'duration_seconds': task.duration,
            'parameters': {'target_path': task.target_path, 'file_patterns': task.file_patterns},
            'result': {
                'total_files': task.total_files,
                'processed_files': task.restored_files,
                'total_bytes': task.total_size,
                'processed_bytes': task.restored_size,
                'failed_files': task.failed_files,
                'skipped_files': task.skipped_files,
            },
            'error_message': task.error_message,
        })

    tasks.sort(key=lambda item: item['created_at'], reverse=True)

    for item in tasks:
        for key in ['created_at', 'started_at', 'completed_at']:
            if item[key]:
                item[key] = item[key].isoformat()

    return tasks


class ProxyTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for managing proxy tasks with optimized queries."""

    serializer_class = ProxyTaskSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['proxy', 'task_type', 'status']

    def get_queryset(self):
        """Return tasks for proxies the user has access to with optimized query."""
        user = self.request.user
        base_queryset = ProxyTask.objects.select_related('proxy').order_by('-created_at')

        if user.is_superuser:
            return base_queryset
        return base_queryset.filter(proxy__owner=user)

    def perform_create(self, serializer):
        """Create a task with cache invalidation."""
        task = serializer.save()
        # Invalidate cache for the proxy
        if task.proxy:
            invalidate_cache(str(task.proxy.id))
        return task

    def perform_update(self, serializer):
        """Update a task with cache invalidation."""
        instance = serializer.save()
        # Invalidate cache for the proxy
        if instance.proxy:
            invalidate_cache(str(instance.proxy.id))
        return instance

    def perform_destroy(self, instance):
        """Delete a task with cache invalidation."""
        proxy_id = str(instance.proxy.id) if instance.proxy else None
        instance.delete()
        # Invalidate cache for the proxy
        if proxy_id:
            invalidate_cache(proxy_id)

    @extend_schema(
        summary='Create and dispatch task',
        description='Create a new task and dispatch it to the proxy.',
        request=ProxyTaskCreateSerializer,
        responses={201: ProxyTaskSerializer}
    )
    def create(self, request, *args, **kwargs):
        """Create and dispatch a task."""
        serializer = ProxyTaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = serializer.save()

        # TODO: Dispatch task via WebSocket
        # For now, just mark as dispatched
        task.dispatch()

        return Response(
            ProxyTaskSerializer(task).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary='Cancel task',
        description='Cancel a pending or running task.',
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel the task."""
        task = self.get_object()

        if task.status in ['completed', 'failed', 'cancelled']:
            return Response(
                {'error': 'Cannot cancel completed or failed task'},
                status=status.HTTP_400_BAD_REQUEST
            )

        task.cancel()

        # Invalidate cache for the proxy
        if task.proxy:
            invalidate_cache(str(task.proxy.id))

        # TODO: Send cancel signal via WebSocket

        return Response(ProxyTaskSerializer(task).data)

    def _get_global_task_items(self, request):
        """Build a normalized task list across task-producing modules."""
        return build_global_task_items(request)


class TaskManagementViewSet(viewsets.ViewSet):
    """Global task management API across all task-producing modules."""

    permission_classes = [IsAuthenticated]

    def _get_pagination_params(self, request):
        page_param = request.query_params.get('page', 1)
        page_size_param = request.query_params.get('page_size') or request.query_params.get('limit') or 20

        try:
            page = max(int(page_param), 1)
        except (TypeError, ValueError):
            page = 1

        try:
            page_size = max(int(page_size_param), 1)
        except (TypeError, ValueError):
            page_size = 20

        return page, min(page_size, 500)

    def _build_page_url(self, request, page):
        params = request.query_params.copy()
        params['page'] = page
        return request.build_absolute_uri(f'{request.path}?{params.urlencode()}')

    def list(self, request):
        """Return global tasks at /api/v1/tasks/."""
        tasks = build_global_task_items(request)
        page, page_size = self._get_pagination_params(request)
        count = len(tasks)
        start = (page - 1) * page_size
        end = start + page_size
        results = tasks[start:end]

        next_url = self._build_page_url(request, page + 1) if end < count else None
        previous_url = self._build_page_url(request, page - 1) if page > 1 and count > 0 else None

        return Response({
            'count': count,
            'next': next_url,
            'previous': previous_url,
            'page': page,
            'page_size': page_size,
            'results': results,
        })

    def retrieve(self, request, pk=None):
        """Return a single normalized task item."""
        for task in build_global_task_items(request):
            if task['id'] == str(pk):
                return Response(task)
        return Response({'detail': 'Task not found.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Return global task counters at /api/v1/tasks/stats/."""
        data = build_global_task_items(request)
        by_status = {}
        by_source = {}
        for task in data:
            by_status[task['status']] = by_status.get(task['status'], 0) + 1
            by_source[task['source']] = by_source.get(task['source'], 0) + 1
        running_statuses = {'pending', 'dispatched', 'accepted', 'running'}
        return Response({
            'total': len(data),
            'running': sum(1 for task in data if task['status'] in running_statuses),
            'completed': by_status.get('completed', 0),
            'failed': by_status.get('failed', 0),
            'cancelled': by_status.get('cancelled', 0),
            'by_status': by_status,
            'by_source': by_source,
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a ProxyTask through the global task endpoint."""
        task = ProxyTask.objects.filter(id=pk).select_related('proxy').first()
        if not task:
            return Response(
                {'detail': 'Only proxy tasks can be cancelled from this endpoint.'},
                status=status.HTTP_404_NOT_FOUND
            )
        if not request.user.is_superuser:
            if getattr(request.user, 'tenant', None):
                if task.proxy.tenant_id != request.user.tenant_id:
                    return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
            elif task.proxy.owner_id != request.user.id:
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if task.status in ['completed', 'failed', 'cancelled']:
            return Response(
                {'error': 'Cannot cancel completed or failed task'},
                status=status.HTTP_400_BAD_REQUEST
            )
        task.cancel()
        if task.proxy:
            invalidate_cache(str(task.proxy.id))
        return Response(ProxyTaskSerializer(task).data)


class NodeConnectionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing proxy connection history."""

    serializer_class = NodeConnectionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['proxy', 'status']

    def get_queryset(self):
        """Return connections for proxies the user has access to."""
        user = self.request.user
        if user.is_superuser:
            return NodeConnection.objects.all()
        return NodeConnection.objects.filter(proxy__owner=user)
