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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proxy = serializer.save()

        # Set owner to current user
        proxy.owner = request.user
        proxy.save(update_fields=['owner'])

        # Generate installation command
        self._generate_install_command(proxy, request)

        response_serializer = ProxyNodeSerializer(proxy)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def _generate_install_command(self, proxy, request):
        """Generate installation command for the proxy."""
        # Get server URL from settings or request
        server_url = getattr(settings, 'PROXY_SERVER_URL', None)
        if not server_url:
            server_url = request.build_absolute_uri('/').rstrip('/')

        os_type = 'linux'  # Default to Linux

        install_command = self._build_install_command(
            server_url=server_url,
            role=proxy.role,
            install_token=proxy.install_token,
            os_type=os_type,
            name=proxy.name
        )

        proxy.install_command = install_command
        proxy.installed_by = request.user
        proxy.save(update_fields=['install_command', 'installed_by'])

    def _build_install_command(self, server_url, role, install_token, os_type, name):
        """Build the installation command string."""
        if os_type == 'windows':
            return f'''# PowerShell (Run as Administrator)
Invoke-WebRequest -Uri "{server_url}/install.ps1" -OutFile "install.ps1"
./install.ps1 -Role {role} -Server "{server_url}" -Token "{install_token}" -Name "{name}"'''
        else:
            return f'''# Linux/macOS
curl -sSL {server_url}/install.sh | bash -s -- \\
  --role {role} \\
  --server {server_url} \\
  --token {install_token} \\
  --name "{name}"'''

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
            owner=request.user,
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
            install_token=proxy.install_token,
            os_type=data['os'],
            name=proxy.name
        )

        windows_command = self._build_install_command(
            server_url=server_url,
            role=proxy.role,
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
        responses={200: ProxyHeartbeatSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def heartbeats(self, request, pk=None):
        """Get heartbeat history for a proxy."""
        proxy = self.get_object()
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timezone.timedelta(hours=hours)
        heartbeats = proxy.heartbeats.filter(timestamp__gte=since)
        serializer = ProxyHeartbeatSerializer(heartbeats, many=True)
        return Response(serializer.data)

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
        serializer = ProxyTaskSerializer(tasks, many=True)
        return Response(serializer.data)

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
        summary='Regenerate API token',
        description='Regenerate the API token for a proxy.',
    )
    @action(detail=True, methods=['post'])
    def regenerate_token(self, request, pk=None):
        """Regenerate API token."""
        proxy = self.get_object()
        new_token = proxy.generate_api_token()
        return Response({
            'api_token': new_token,
            'message': 'API token regenerated successfully'
        })


class ProxyRegisterView(APIView):
    """
    View for proxy registration.

    Called by the proxy during installation to complete registration.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary='Register proxy',
        description='Complete proxy registration during installation.',
        request=ProxyRegisterSerializer,
        responses={
            200: ProxyNodeSerializer,
            400: OpenApiResponse(description='Invalid registration data'),
        }
    )
    def post(self, request):
        """Register a proxy."""
        serializer = ProxyRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        proxy = serializer.validated_data['proxy']
        data = serializer.validated_data

        # Clear install token (one-time use)
        proxy.install_token = ''

        # Update proxy info
        proxy.update_heartbeat({
            'hostname': data.get('hostname'),
            'internal_ip': data.get('internal_ip'),
            'os': data.get('os'),
            'os_version': data.get('os_version'),
            'version': data.get('version'),
            'kopia_version': data.get('kopia_version'),
            'cpu_cores': data.get('cpu_cores'),
            'memory_total': data.get('memory_total'),
            'disk_total': data.get('disk_total'),
            'capabilities': data.get('capabilities', {}),
        })

        return Response({
            'node_id': str(proxy.id),
            'api_token': proxy.api_token,
            'status': proxy.status,
            'message': 'Registration successful'
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

        # Update proxy heartbeat
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
        })

        # Create heartbeat record
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
            metadata=data.get('metadata', {})
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
