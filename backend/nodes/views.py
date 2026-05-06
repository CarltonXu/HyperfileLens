"""
Views for Proxy Nodes Application

This module provides API views for proxy management,
including CRUD operations, installation, heartbeat handling, and statistics.
"""

import secrets

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count, Avg
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
from audit_log.services import AuditService


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
        """Return proxies filtered by user's access permissions."""
        user = self.request.user
        if user.is_superuser:
            return ProxyNode.objects.all()
        # Filter by tenant if user belongs to one
        if user.tenant:
            return ProxyNode.objects.filter(tenant=user.tenant)
        # Fallback to owner-based filtering
        return ProxyNode.objects.filter(owner=user)

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
        """List all proxies."""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Create a new proxy',
        description='Register a new agent or sync proxy.',
        responses={201: ProxyNodeSerializer}
    )
    def create(self, request, *args, **kwargs):
        """Create a new proxy."""
        # Check license quota
        from licenses.models import License
        from rest_framework.exceptions import PermissionDenied
        
        user = request.user
        tenant = getattr(user, 'tenant', None)
        
        if tenant:
            license = License.get_active_license(tenant)
            if license:
                is_allowed, message = license.check_quota('proxies')
                if not is_allowed:
                    AuditService.log_proxy_create(request, None, result='failure', error_message=f"License quota exceeded: {message}")
                    raise PermissionDenied(f"License quota exceeded: {message}")
        
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
        instance.delete()

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
        # Check license quota first
        from licenses.models import License
        from rest_framework.exceptions import PermissionDenied
        
        user = request.user
        tenant = getattr(user, 'tenant', None)
        
        if tenant:
            license = License.get_active_license(tenant)
            if license:
                is_allowed, message = license.check_quota('proxies')
                if not is_allowed:
                    raise PermissionDenied(f"License quota exceeded: {message}")
        
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
        """Get proxy statistics."""
        queryset = self.get_queryset()

        total = queryset.count()
        online = sum(1 for p in queryset if p.is_online())
        offline = total - online

        # Group by role
        agent_count = queryset.filter(role=ProxyNode.Role.AGENT).count()
        sync_count = queryset.filter(role=ProxyNode.Role.SYNC).count()

        # Group by status
        by_status = dict(
            queryset.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )

        # Group by OS
        by_os = dict(
            queryset.exclude(operating_system='')
            .values('operating_system')
            .annotate(count=Count('id'))
            .values_list('operating_system', 'count')
        )

        # Average uptime for active proxies
        avg_uptime = 0
        active_proxies = queryset.filter(status=ProxyNode.NodeStatus.ACTIVE)
        if active_proxies.exists():
            total_uptime = sum(
                (timezone.now() - p.registered_at).total_seconds()
                for p in active_proxies
                if p.registered_at
            )
            avg_uptime = total_uptime / active_proxies.count() if active_proxies.count() > 0 else 0

        # Total active tasks
        total_tasks = ProxyTask.objects.filter(
            proxy__in=queryset,
            status__in=['pending', 'dispatched', 'accepted', 'running']
        ).count()

        data = {
            'total_proxies': total,
            'online_proxies': online,
            'offline_proxies': offline,
            'agent_proxies': agent_count,
            'sync_proxies': sync_count,
            'proxies_by_status': by_status,
            'proxies_by_os': by_os,
            'average_uptime': avg_uptime,
            'total_active_tasks': total_tasks
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
        
        # Only Sync Proxies can browse directories
        if proxy.role != ProxyNode.Role.SYNC:
            return Response(
                {'error': 'Only Sync Proxy can browse directories.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if proxy is online
        if proxy.status != ProxyNode.NodeStatus.ACTIVE:
            return Response(
                {'error': 'Proxy is not online.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        path = request.query_params.get('path', '/')
        
        # TODO: In production, this would send a WebSocket message to the proxy
        # and wait for the response. For now, return mock data.
        # The actual implementation would be:
        # 1. Send a 'list_directory' command to the proxy via WebSocket
        # 2. Wait for the proxy to respond with the directory listing
        # 3. Return the result
        
        # Mock response for development
        mock_directories = self._get_mock_directories(path)
        return Response({
            'path': path,
            'directories': mock_directories
        })
    
    def _get_mock_directories(self, path: str) -> list:
        """Mock directory listing for development."""
        # This is just mock data for UI development
        # In production, this would be fetched from the actual Sync Proxy
        mock_structure = {
            '/': ['backup', 'data', 'home', 'mnt', 'opt', 'var'],
            '/backup': ['hyperfilelens', 'archives', 'temp'],
            '/data': ['databases', 'files', 'logs'],
            '/home': ['admin', 'user'],
            '/mnt': ['nas1', 'nas2', 'external'],
            '/opt': ['hyperfilelens', 'kopia'],
            '/var': ['lib', 'log', 'tmp'],
            '/backup/hyperfilelens': ['repo1', 'repo2', 'snapshots'],
        }
        return mock_structure.get(path, [])

    @extend_schema(
        summary='Get proxy tasks',
        description='Get task history for a specific proxy.',
        responses={200: ProxyTaskSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        """Get task history for a proxy."""
        proxy = self.get_object()
        limit = int(request.query_params.get('limit', 50))
        tasks = proxy.tasks.all()[:limit]
        
        # Task statistics
        total_tasks = proxy.tasks.count()
        completed_tasks = proxy.tasks.filter(status='completed').count()
        failed_tasks = proxy.tasks.filter(status='failed').count()
        running_tasks = proxy.tasks.filter(status__in=['pending', 'dispatched', 'accepted', 'running']).count()
        
        serializer = ProxyTaskSerializer(tasks, many=True)
        return Response({
            'tasks': serializer.data,
            'stats': {
                'total': total_tasks,
                'completed': completed_tasks,
                'failed': failed_tasks,
                'running': running_tasks,
            }
        })

    @extend_schema(
        summary='Get proxy overview',
        description='Get overview data for a specific proxy including system info, resources, and stats.',
    )
    @action(detail=True, methods=['get'])
    def overview(self, request, pk=None):
        """Get overview data for a proxy."""
        proxy = self.get_object()
        since = timezone.now() - timezone.timedelta(hours=24)
        heartbeats = proxy.heartbeats.filter(timestamp__gte=since).order_by('timestamp')

        # Calculate uptime
        uptime_seconds = None
        if proxy.registered_at:
            uptime_seconds = int((timezone.now() - proxy.registered_at).total_seconds())

        # Task statistics
        total_tasks = proxy.tasks.count()
        completed_tasks = proxy.tasks.filter(status='completed').count()
        failed_tasks = proxy.tasks.filter(status='failed').count()
        running_tasks = proxy.tasks.filter(status__in=['pending', 'dispatched', 'accepted', 'running']).count()

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
        """Get monitoring statistics for a proxy."""
        proxy = self.get_object()
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timezone.timedelta(hours=hours)

        # Get heartbeats in time range
        heartbeats = proxy.heartbeats.filter(timestamp__gte=since).order_by('timestamp')

        # Calculate stats
        total_heartbeats = heartbeats.count()

        # Task statistics
        total_tasks = proxy.tasks.count()
        completed_tasks = proxy.tasks.filter(status='completed').count()
        failed_tasks = proxy.tasks.filter(status='failed').count()
        running_tasks = proxy.tasks.filter(status__in=['pending', 'running']).count()

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
        proxy.status = ProxyNode.NodeStatus.ACTIVE
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

        return Response({
            'status': 'ok',
            'node_id': str(proxy.id),
            'server_time': timezone.now()
        })


class ProxyTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for managing proxy tasks."""

    serializer_class = ProxyTaskSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['proxy', 'task_type', 'status']

    def get_queryset(self):
        """Return tasks for proxies the user has access to."""
        user = self.request.user
        if user.is_superuser:
            return ProxyTask.objects.all()
        return ProxyTask.objects.filter(proxy__owner=user)

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

        # TODO: Send cancel signal via WebSocket

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
