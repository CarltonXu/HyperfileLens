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
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from .models import Gateway
from .serializers import (
    GatewaySerializer,
    GatewayCreateSerializer,
    GatewayHeartbeatSerializer,
    GatewayInstallSerializer
)
from accounts.models import User
from audit_log.services import AuditService


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
        if self.action == 'generate_install':
            return GatewayInstallSerializer
        return GatewaySerializer
    
    def perform_create(self, serializer):
        """Set owner and tenant when creating a gateway."""
        user: User = self.request.user
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
        server_url = getattr(settings, 'GATEWAY_SERVER_URL', None)
        if not server_url:
            server_url = self.request.build_absolute_uri('/').rstrip('/')
        
        install_command = self._build_install_command(
            server_url=server_url,
            gateway_id=gateway.id,
            install_token=gateway.install_token,
            name=gateway.name
        )
        
        gateway.install_command = install_command
        gateway.installed_by = self.request.user
        gateway.save(update_fields=['install_command', 'installed_by'])
    
    def _build_install_command(self, server_url, gateway_id, install_token, name):
        """Build the installation command string for Ubuntu 22.04."""
        return f'''# Gateway Installation Script for Ubuntu 22.04
# Run this script on your Ubuntu 22.04 server

# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install dependencies
sudo apt install -y curl wget unzip python3 python3-pip python3-venv

# 3. Download and run the Gateway installer
curl -sSL {server_url}/static/downloads/install-gateway.sh | bash -s -- \\
  --gateway-id {gateway_id} \\
  --server {server_url} \\
  --token {install_token} \\
  --name "{name}"

# After installation, the gateway will automatically register with the control plane.
# You can check the status with:
# systemctl status hyperfilelens-gateway
'''
    
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
  api_token: "{install_token}"

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
    @action(detail=False, methods=['post'])
    def generate_install(self, request):
        """
        Generate installation command for a new gateway.
        
        This creates a pending gateway and returns the installation command.
        """
        serializer = GatewayInstallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
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
        
        # Get server URL
        server_url = data.get('server_url') or getattr(
            settings, 'GATEWAY_SERVER_URL',
            request.build_absolute_uri('/').rstrip('/')
        )
        
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
            'ai_insights_enabled': old_instance.ai_insights_enabled,
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
            'ai_insights_enabled': instance.ai_insights_enabled,
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
        
        # Generate command if not exists
        if not gateway.install_command:
            server_url = getattr(settings, 'GATEWAY_SERVER_URL', None)
            if not server_url:
                server_url = request.build_absolute_uri('/').rstrip('/')
            
            install_command = self._build_install_command(
                server_url=server_url,
                gateway_id=gateway.id,
                install_token=gateway.install_token,
                name=gateway.name
            )
            gateway.install_command = install_command
            gateway.save(update_fields=['install_command'])
        
        return Response({
            'install_command': gateway.install_command
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
        """Regenerate API token for a gateway."""
        gateway = self.get_object()
        new_token = gateway.generate_api_token()
        
        return Response({
            'api_token': new_token
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
        
        # Serialize heartbeat data
        data = [{
            'timestamp': hb.timestamp.isoformat(),
            'cpu_usage': hb.cpu_usage,
            'memory_usage': hb.memory_usage,
            'disk_usage': hb.disk_usage,
            'active_mounts': hb.active_mounts,
            'network_bytes_sent': hb.network_bytes_sent,
            'network_bytes_recv': hb.network_bytes_recv,
        } for hb in heartbeats]
        
        return Response({
            'gateway_id': str(gateway.id),
            'gateway_name': gateway.name,
            'hours': hours,
            'data_points': len(data),
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
