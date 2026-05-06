"""
Gateway ViewSets for HyperFileLens
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Gateway
from .serializers import (
    GatewaySerializer,
    GatewayCreateSerializer,
    GatewayHeartbeatSerializer
)
from accounts.models import User


class GatewayViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Gateway nodes.
    
    Gateways are independent nodes that:
    - Mount backup data via Kopia
    - Provide AI Insights capabilities
    - Run on Ubuntu 22.04
    """
    
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
        return GatewaySerializer
    
    def perform_create(self, serializer):
        """Set owner and tenant when creating a gateway."""
        user: User = self.request.user
        serializer.save(owner=user, tenant=user.tenant)
    
    @action(detail=True, methods=['get'])
    def install_command(self, request, pk=None):
        """Get installation command for a gateway."""
        gateway = self.get_object()
        
        if gateway.status != 'pending':
            return Response({
                'error': 'Install command only available for pending gateways'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'install_command': gateway.get_install_command()
        })
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a gateway."""
        gateway = self.get_object()
        
        if gateway.status not in ['pending', 'inactive', 'maintenance']:
            return Response({
                'error': 'Can only activate pending, inactive, or maintenance gateways'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        gateway.status = 'active'
        gateway.save()
        
        return Response(GatewaySerializer(gateway).data)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a gateway."""
        gateway = self.get_object()
        
        if gateway.status != 'active':
            return Response({
                'error': 'Can only deactivate active gateways'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        gateway.status = 'inactive'
        gateway.save()
        
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
            
            # Update status to active if it was offline
            if gateway.status in ['offline', 'pending']:
                gateway.status = 'active'
                if not gateway.registered_at:
                    gateway.registered_at = gateway.last_heartbeat
                gateway.save()
            
            return Response({'status': 'ok'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
