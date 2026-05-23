"""
Gateway ViewSets for HyperFileLens
"""

import secrets
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from core.install_distribution import (
    build_gateway_install_command,
    get_public_control_plane_url,
)

from .models import Gateway
from .serializers import (
    GatewaySerializer,
    GatewayCreateSerializer,
    GatewayHeartbeatSerializer,
    GatewayInstallSerializer
)
from accounts.models import User
from audit_log.services import AuditService
from licenses.quota import enforce_license_quota


class GatewayViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Gateway nodes.
    
    Gateways are independent nodes that:
    - Mount backup data via Kopia
    - Provide AI Insights capabilities
    - Run on Ubuntu 22.04
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['name', 'hostname', 'internal_ip']
    ordering_fields = ['name', 'created_at', 'last_heartbeat', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter gateways by tenant for non-superusers."""
        queryset = Gateway.objects.all()
        user: User = self.request.user
        
        if not user.is_superuser:
            if user.tenant:
                queryset = queryset.filter(tenant=user.tenant)
            else:
                queryset = queryset.none()
        
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return GatewayCreateSerializer
        if self.action == 'create_install_command':
            return GatewayInstallSerializer
        return GatewaySerializer
    
    def perform_create(self, serializer):
        """Set owner and tenant when creating a gateway."""
        user: User = self.request.user
        enforce_license_quota(user.tenant, 'gateways')
        gateway = serializer.save(
            owner=user, 
            tenant=user.tenant,
            api_token=secrets.token_urlsafe(32),
            install_token=secrets.token_urlsafe(32)
        )
        
        # Generate installation command
        self._generate_install_command(gateway)
        
        # Record audit log
        AuditService.log_gateway_create(self.request, gateway, result='success')
    
    def _generate_install_command(self, gateway):
        """Generate installation command for the gateway."""
        install_command = self._build_install_command(
            server_url=get_public_control_plane_url(self.request),
            gateway_id=gateway.id,
            install_token=gateway.install_token,
            name=gateway.name
        )
        
        gateway.install_command = install_command
        gateway.installed_by = self.request.user
        gateway.save(update_fields=['install_command', 'installed_by'])
    
    def _build_install_command(self, server_url, gateway_id, install_token, name):
        """Build the installation command string for Ubuntu 22.04."""
        return build_gateway_install_command(
            server_url=server_url,
            gateway_id=gateway_id,
            install_token=install_token,
            name=name,
        )
    
    def _build_config_yaml(self, server_url, gateway_id, install_token, name):
        """Generate config YAML for manual installation."""
        return f'''# HyperFileLens Gateway Configuration
# Save this as /opt/hyperfilelens/gateway/config.yaml

version: "1.0.0"

gateway:
  id: "{gateway_id}"
  name: "{name}"

server:
  url: "{server_url}"
  ws_url: "{server_url.replace('http://', 'ws://').replace('https://', 'wss://')}"
  api_token: ""

install:
  token: "{install_token}"

paths:
  kopia: "/usr/local/bin/kopia"
  mount_base: "/mnt/kopia"
  cache: "/var/lib/hyperfilelens/gateway/cache"
  logs: "/var/log/hyperfilelens/gateway"

logging:
  level: "info"
  file: "/var/log/hyperfilelens/gateway/gateway.log"
'''
    
    @extend_schema(
        summary='Generate installation command',
        description='Generate installation command for a new gateway. Creates a pending gateway and returns the installation command.',
        request=GatewayInstallSerializer,
        responses={200: OpenApiResponse(
            description='Installation information',
            response={
                'type': 'object',
                'properties': {
                    'gateway_id': {'type': 'string'},
                    'name': {'type': 'string'},
                    'install_token': {'type': 'string'},
                    'install_command': {'type': 'string'},
                    'config_yaml': {'type': 'string'},
                    'expires_at': {'type': 'string'},
                }
            }
        )}
    )
    @action(detail=False, methods=['post'], url_path='install_command')
    def create_install_command(self, request):
        """Create a pending gateway and return its installation command."""
        return self._create_install_command_response(request)

    def _create_install_command_response(self, request):
        """
        Generate installation command for a new gateway.
        
        This creates a pending gateway and returns the installation command.
        """
        serializer = GatewayInstallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        enforce_license_quota(getattr(request.user, 'tenant', None), 'gateways')
        
        # Check if name already exists
        if Gateway.objects.filter(name=data['name']).exists():
            return Response(
                {'error': f'Gateway with name "{data["name"]}" already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the gateway
        gateway = Gateway.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            ai_enabled=data.get('ai_enabled', True),
            tags=data.get('tags', {}),
            labels=data.get('labels', []),
            status=Gateway.GatewayStatus.PENDING,
            api_token=secrets.token_urlsafe(32),
            install_token=secrets.token_urlsafe(32),
            owner=request.user,
            tenant=getattr(request.user, 'tenant', None),
        )
        
        # Get public server URL
        server_url = data.get('server_url') or get_public_control_plane_url(request)
        
        # Build commands
        install_command = self._build_install_command(
            server_url=server_url,
            gateway_id=gateway.id,
            install_token=gateway.install_token,
            name=gateway.name
        )
        
        # Generate config YAML
        config_yaml = self._build_config_yaml(
            server_url=server_url,
            gateway_id=gateway.id,
            install_token=gateway.install_token,
            name=gateway.name
        )
        
        gateway.install_command = install_command
        gateway.installed_by = request.user
        gateway.save()
        
        # Record audit log
        AuditService.log_gateway_create(request, gateway, result='success')
        
        response_data = {
            'gateway_id': str(gateway.id),
            'name': gateway.name,
            'install_token': gateway.install_token,
            'api_token': gateway.api_token,
            'install_command': install_command,
            'config_yaml': config_yaml,
            'expires_at': timezone.now() + timezone.timedelta(hours=24)
        }
        
        return Response(response_data)
    
    def perform_update(self, serializer):
        """Update a gateway with audit logging."""
        # Get the old instance data before update
        old_instance = self.get_object()
        old_data = {
            'name': old_instance.name,
            'hostname': old_instance.hostname,
            'status': old_instance.status,
            'description': old_instance.description,
            'ai_insights_enabled': old_instance.ai_enabled,
        }
        
        # Save the updated instance
        instance = serializer.save()
        
        # Track changed fields
        changed_fields = []
        new_data = {
            'name': instance.name,
            'hostname': instance.hostname,
            'status': instance.status,
            'description': instance.description,
            'ai_insights_enabled': instance.ai_enabled,
        }
        
        for field in old_data.keys():
            if old_data[field] != new_data[field]:
                changed_fields.append(field)
        
        # Record audit log
        AuditService.log_gateway_update(
            self.request, instance, 
            changed_fields=changed_fields,
            before_data=old_data,
            after_data=new_data,
            result='success'
        )

    def perform_destroy(self, instance):
        """Delete a gateway with audit logging."""
        AuditService.log_gateway_delete(self.request, instance, result='success')
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def install_command(self, request, pk=None):
        """Get installation command for a gateway."""
        gateway = self.get_object()
        token_update_fields = []
        if not gateway.api_token:
            gateway.api_token = secrets.token_urlsafe(32)
            token_update_fields.append('api_token')
        if not gateway.install_token:
            gateway.install_token = secrets.token_urlsafe(32)
            token_update_fields.append('install_token')
        if gateway.install_token_used:
            gateway.install_token_used = False
            token_update_fields.append('install_token_used')
        if token_update_fields:
            token_update_fields.append('updated_at')
            gateway.save(update_fields=token_update_fields)

        server_url = get_public_control_plane_url(request)
        install_command = self._build_install_command(
            server_url=server_url,
            gateway_id=gateway.id,
            install_token=gateway.install_token,
            name=gateway.name
        )
        gateway.install_command = install_command
        gateway.save(update_fields=['install_command'])
        
        return Response({
            'install_command': install_command,
            'install_token': gateway.install_token,
            'api_token': gateway.api_token,
            'server_url': server_url,
            'script_url': f'{server_url}/downloads/install-gateway.sh',
            'install_token_used': gateway.install_token_used,
        })
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a gateway."""
        gateway = self.get_object()
        
        if gateway.status not in ['pending', 'inactive', 'maintenance']:
            AuditService.log_gateway_activate(request, gateway, result='failure',
                error_message='Can only activate pending, inactive, or maintenance gateways')
            return Response({
                'error': 'Can only activate pending, inactive, or maintenance gateways'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        gateway.status = 'active'
        gateway.save()
        
        # Record audit log
        AuditService.log_gateway_activate(request, gateway, result='success')
        
        return Response(GatewaySerializer(gateway).data)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a gateway."""
        gateway = self.get_object()
        
        if gateway.status != 'active':
            AuditService.log_gateway_deactivate(request, gateway, result='failure',
                error_message='Can only deactivate active gateways')
            return Response({
                'error': 'Can only deactivate active gateways'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        gateway.status = 'inactive'
        gateway.save()
        
        # Record audit log
        AuditService.log_gateway_deactivate(request, gateway, result='success')
        
        return Response(GatewaySerializer(gateway).data)
    
    @action(detail=True, methods=['post'])
    def maintenance(self, request, pk=None):
        """Put gateway into maintenance mode."""
        gateway = self.get_object()
        gateway.status = 'maintenance'
        gateway.save()
        
        return Response(GatewaySerializer(gateway).data)
    
    @action(detail=True, methods=['post'])
    def regenerate_token(self, request, pk=None):
        """Regenerate API and install tokens for a gateway."""
        gateway = self.get_object()
        gateway.api_token = secrets.token_urlsafe(32)
        gateway.install_token = secrets.token_urlsafe(32)
        gateway.install_token_used = False

        server_url = get_public_control_plane_url(request)
        install_command = self._build_install_command(
            server_url=server_url,
            gateway_id=gateway.id,
            install_token=gateway.install_token,
            name=gateway.name
        )
        gateway.install_command = install_command
        gateway.save(update_fields=[
            'api_token',
            'install_token',
            'install_token_used',
            'install_command',
            'updated_at',
        ])
        
        return Response({
            'api_token': gateway.api_token,
            'install_token': gateway.install_token,
            'install_command': install_command,
            'server_url': server_url,
            'script_url': f'{server_url}/downloads/install-gateway.sh',
            'install_token_used': gateway.install_token_used,
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get gateway statistics."""
        queryset = self.get_queryset()
        
        total = queryset.count()
        active = queryset.filter(status='active').count()
        offline = queryset.filter(status='offline').count()
        pending = queryset.filter(status='pending').count()
        error = queryset.filter(status='error').count()
        
        # Calculate total mounts
        total_mounts = sum(g.active_mounts for g in queryset if g.active_mounts)
        
        return Response({
            'total': total,
            'active': active,
            'offline': offline,
            'pending': pending,
            'error': error,
            'total_mounts': total_mounts
        })
    
    @action(detail=True, methods=['post'])
    def heartbeat(self, request, pk=None):
        """Receive heartbeat from gateway."""
        gateway = self.get_object()
        serializer = GatewayHeartbeatSerializer(data=request.data)
        
        if serializer.is_valid():
            gateway.update_heartbeat(serializer.validated_data)
            
            # Create heartbeat history record
            from .models import GatewayHeartbeat
            GatewayHeartbeat.objects.create(
                gateway=gateway,
                cpu_usage=serializer.validated_data.get('cpu_usage'),
                memory_usage=serializer.validated_data.get('memory_usage'),
                disk_usage=serializer.validated_data.get('disk_usage'),
                active_mounts=serializer.validated_data.get('active_mounts', 0),
                network_bytes_sent=serializer.validated_data.get('network_bytes_sent', 0),
                network_bytes_recv=serializer.validated_data.get('network_bytes_recv', 0),
                load_average=serializer.validated_data.get('load_average'),
                process_count=serializer.validated_data.get('process_count'),
                metadata=serializer.validated_data,
            )
            
            # Clean up old heartbeats (keep last 24 hours = 1440 records at 1-minute interval)
            # Assuming heartbeat_interval is 60 seconds
            from django.utils import timezone
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(hours=24)
            GatewayHeartbeat.objects.filter(
                gateway=gateway,
                timestamp__lt=cutoff
            ).delete()
            
            # Update status to active if it was offline
            if gateway.status in ['offline', 'pending']:
                gateway.status = 'active'
                if not gateway.registered_at:
                    gateway.registered_at = gateway.last_heartbeat
                gateway.save()
            
            return Response({'status': 'ok'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def monitoring(self, request, pk=None):
        """Get monitoring data for a gateway (heartbeat history)."""
        gateway = self.get_object()
        
        # Get time range from query params
        hours = int(request.query_params.get('hours', 24))
        
        from django.utils import timezone
        from datetime import timedelta
        from .models import GatewayHeartbeat
        
        cutoff = timezone.now() - timedelta(hours=hours)
        heartbeats = GatewayHeartbeat.objects.filter(
            gateway=gateway,
            timestamp__gte=cutoff
        ).order_by('timestamp')
        heartbeat_rows = [hb for hb in heartbeats if hb.metadata]

        network_io_data = []
        disk_io_data = []
        previous_disk_stats = {}
        for hb in heartbeat_rows:
            timestamp = hb.timestamp.isoformat()
            metadata = hb.metadata or {}
            interfaces_payload = metadata.get('network_interfaces') or {}
            interfaces = interfaces_payload.get('interfaces') if isinstance(interfaces_payload, dict) else interfaces_payload
            for ni in interfaces or []:
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
            for disk in metadata.get('disk_io') or []:
                disk_name = disk.get('name')
                previous = previous_disk_stats.get(disk_name)
                elapsed_seconds = (
                    (hb.timestamp - previous['timestamp']).total_seconds()
                    if previous else 0
                )
                read_count = disk.get('read_count', 0) or 0
                write_count = disk.get('write_count', 0) or 0
                read_bytes = disk.get('read_bytes', 0) or 0
                write_bytes = disk.get('write_bytes', 0) or 0
                if previous and elapsed_seconds > 0:
                    read_iops = max(read_count - previous['read_count'], 0) / elapsed_seconds
                    write_iops = max(write_count - previous['write_count'], 0) / elapsed_seconds
                    read_kbps = max(read_bytes - previous['read_bytes'], 0) / 1024 / elapsed_seconds
                    write_kbps = max(write_bytes - previous['write_bytes'], 0) / 1024 / elapsed_seconds
                else:
                    read_iops = 0
                    write_iops = 0
                    read_kbps = 0
                    write_kbps = 0
                disk_io_data.append({
                    'timestamp': timestamp,
                    'disk': disk_name,
                    'read_bytes': read_bytes,
                    'write_bytes': write_bytes,
                    'read_count': read_count,
                    'write_count': write_count,
                    'io_time_ms': disk.get('io_time_ms', 0),
                    'r_s': read_iops,
                    'w_s': write_iops,
                    'rkB_s': read_kbps,
                    'wkB_s': write_kbps,
                })
                previous_disk_stats[disk_name] = {
                    'timestamp': hb.timestamp,
                    'read_count': read_count,
                    'write_count': write_count,
                    'read_bytes': read_bytes,
                    'write_bytes': write_bytes,
                }
        
        # Serialize heartbeat data
        data = [{
            'timestamp': hb.timestamp.isoformat(),
            'cpu_usage': hb.cpu_usage,
            'memory_usage': hb.memory_usage,
            'disk_usage': hb.disk_usage,
            'active_mounts': hb.active_mounts,
            'network_bytes_sent': hb.network_bytes_sent,
            'network_bytes_recv': hb.network_bytes_recv,
            'network_packets_sent': (hb.metadata or {}).get('network_packets_sent', 0),
            'network_packets_recv': (hb.metadata or {}).get('network_packets_recv', 0),
            'load_average': hb.load_average,
            'process_count': hb.process_count,
            'memory_total': (hb.metadata or {}).get('memory_total'),
            'memory_used': (hb.metadata or {}).get('memory_used'),
            'memory_free': (hb.metadata or {}).get('memory_free'),
            'disk_total': (hb.metadata or {}).get('disk_total'),
            'disk_used': (hb.metadata or {}).get('disk_used'),
            'disk_free': (hb.metadata or {}).get('disk_free'),
            'cpu_cores': (hb.metadata or {}).get('cpu_cores'),
            'cpu_physical': (hb.metadata or {}).get('cpu_physical'),
            'uptime': (hb.metadata or {}).get('uptime'),
            'network_interfaces': (hb.metadata or {}).get('network_interfaces'),
            'disk_io': (hb.metadata or {}).get('disk_io', []),
            'metadata': hb.metadata or {},
        } for hb in heartbeat_rows]
        latest = data[-1] if data else None
        
        return Response({
            'gateway_id': str(gateway.id),
            'gateway_name': gateway.name,
            'hours': hours,
            'data_points': len(data),
            'current': {
                'cpu_usage': gateway.cpu_usage,
                'memory_usage': gateway.memory_usage,
                'disk_usage': gateway.disk_usage,
                'cpu_cores': gateway.cpu_cores,
                'memory_total': gateway.memory_total,
                'memory_total_gb': round(gateway.memory_total / (1024 ** 3), 2) if gateway.memory_total else None,
                'disk_total': gateway.disk_total,
                'disk_total_gb': round(gateway.disk_total / (1024 ** 3), 2) if gateway.disk_total else None,
                'network_bytes_sent': gateway.network_bytes_sent,
                'network_bytes_recv': gateway.network_bytes_recv,
                'network_interfaces': (gateway.metadata or {}).get('metrics', {}).get('network_interfaces') or {'interfaces': gateway.network_interfaces or []},
                'disk_io': (gateway.metadata or {}).get('metrics', {}).get('disk_io', []),
                'process_count': (gateway.metadata or {}).get('metrics', {}).get('process_count'),
                'uptime': (gateway.metadata or {}).get('metrics', {}).get('uptime'),
                **((latest or {}).get('metadata') or {}),
            },
            'last_heartbeat': gateway.last_heartbeat.isoformat() if gateway.last_heartbeat else None,
            'uptime_seconds': (gateway.metadata or {}).get('metrics', {}).get('uptime'),
            'network_io': network_io_data,
            'disk_io': disk_io_data,
            'data': data
        })
    
    @action(detail=True, methods=['get'])
    def mounts(self, request, pk=None):
        """Get active mounts for a gateway."""
        gateway = self.get_object()
        
        # TODO: Implement actual mount listing from gateway
        # For now, return placeholder data
        return Response({
            'gateway_id': str(gateway.id),
            'active_mounts': gateway.active_mounts,
            'max_mounts': gateway.max_concurrent_mounts,
            'mount_base_path': gateway.mount_base_path,
            'mounts': []  # Will be populated from gateway agent
        })
