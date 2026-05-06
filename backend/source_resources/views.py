"""
HyperFileLens Backend - Source Resource Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from licenses.quota import QuotaCheckMixin
from audit_log.services import AuditService
from .models import SourceResource
from .serializers import (
    SourceResourceSerializer,
    SourceResourceListSerializer,
    SourceResourceCreateSerializer,
    SourceResourceUpdateSerializer,
    ConnectionTestSerializer,
    ConnectionTestResultSerializer
)


class SourceResourceViewSet(QuotaCheckMixin, viewsets.ModelViewSet):
    """ViewSet for managing source resources."""
    
    queryset = SourceResource.objects.all()
    permission_classes = [IsAuthenticated]
    quota_resource_type = 'source_resources'  # 配额类型
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SourceResourceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SourceResourceUpdateSerializer
        elif self.action == 'list':
            return SourceResourceListSerializer
        return SourceResourceSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = SourceResource.objects.select_related('bound_node', 'user')
        
        # Filter by user role
        if not (user.is_superuser or user.role == 'admin'):
            queryset = queryset.filter(user=user)
        
        # Filter by resource type
        resource_type = self.request.query_params.get('resource_type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        
        # Filter by status
        resource_status = self.request.query_params.get('status')
        if resource_status:
            queryset = queryset.filter(status=resource_status)
        
        # Filter by bound node
        node_id = self.request.query_params.get('bound_node')
        if node_id:
            queryset = queryset.filter(bound_node_id=node_id)
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create a new source resource."""
        self.check_quota_before_create()
        resource = serializer.save(user=self.request.user, tenant=self.request.user.tenant)
        AuditService.log_source_resource_create(self.request, resource, result='success')
    
    def perform_update(self, serializer):
        """Update a source resource."""
        resource = serializer.save()
        changed_fields = list(serializer.validated_data.keys())
        AuditService.log_source_resource_update(self.request, resource, changed_fields=changed_fields, result='success')
    
    def perform_destroy(self, instance):
        """Delete a source resource."""
        AuditService.log_source_resource_delete(self.request, instance, result='success')
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """
        Test connection to the source resource.
        
        This will send a command to the bound node to test connectivity.
        For now, returns a simulated result.
        """
        resource = self.get_object()
        
        # Check if resource has a bound node
        if not resource.bound_node:
            return Response({
                'success': False,
                'message': 'No bound node configured. Please bind a node first.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if node is online
        if resource.bound_node.status != 'active':
            return Response({
                'success': False,
                'message': f'Bound node "{resource.bound_node.name}" is not active.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # TODO: In production, send WebSocket command to node
        # For now, simulate a successful connection test
        resource.last_connection_test = timezone.now()
        resource.connection_test_result = 'Connection successful'
        resource.status = SourceResource.STATUS_ACTIVE
        resource.status_message = 'Connection test passed'
        resource.save()
        
        return Response({
            'success': True,
            'message': 'Connection test successful',
            'details': {
                'resource_name': resource.name,
                'resource_type': resource.resource_type,
                'bound_node': resource.bound_node.name,
                'tested_at': resource.last_connection_test.isoformat(),
            }
        })
    
    @action(detail=True, methods=['post'])
    def mount(self, request, pk=None):
        """
        Mount the source resource on the bound node.
        
        Only applicable for NFS, CIFS, NAS types.
        """
        resource = self.get_object()
        
        if not resource.requires_mount:
            return Response({
                'success': False,
                'message': f'{resource.get_resource_type_display()} does not require mounting.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not resource.bound_node:
            return Response({
                'success': False,
                'message': 'No bound node configured.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # TODO: Send WebSocket command to node to mount
        # For now, simulate successful mount
        resource.mount_status = SourceResource.MOUNT_MOUNTED
        resource.mount_point = resource.get_effective_mount_point()
        resource.mount_error = ''
        resource.save()
        
        return Response({
            'success': True,
            'message': 'Resource mounted successfully',
            'mount_point': resource.mount_point,
        })
    
    @action(detail=True, methods=['post'])
    def unmount(self, request, pk=None):
        """
        Unmount the source resource from the bound node.
        """
        resource = self.get_object()
        
        if resource.mount_status != SourceResource.MOUNT_MOUNTED:
            return Response({
                'success': False,
                'message': 'Resource is not currently mounted.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # TODO: Send WebSocket command to node to unmount
        # For now, simulate successful unmount
        resource.mount_status = SourceResource.MOUNT_UNMOUNTED
        resource.mount_error = ''
        resource.save()
        
        return Response({
            'success': True,
            'message': 'Resource unmounted successfully',
        })
    
    @action(detail=True, methods=['post'])
    def bind_node(self, request, pk=None):
        """
        Bind the resource to a specific node.
        """
        from nodes.models import Node
        
        resource = self.get_object()
        node_id = request.data.get('node_id')
        
        if not node_id:
            return Response({
                'success': False,
                'message': 'node_id is required.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            node = Node.objects.get(id=node_id)
        except Node.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Node not found.',
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check node status
        if node.status != Node.NodeStatus.ACTIVE:
            return Response({
                'success': False,
                'message': f'Node "{node.name}" is not active.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        resource.bound_node = node
        resource.mount_status = SourceResource.MOUNT_UNMOUNTED
        resource.mount_point = ''
        resource.save()
        
        return Response({
            'success': True,
            'message': f'Resource bound to node "{node.name}" successfully.',
            'bound_node': {
                'id': str(node.id),
                'name': node.name,
                'status': node.status,
            }
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get source resource statistics."""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'active': queryset.filter(status=SourceResource.STATUS_ACTIVE).count(),
            'inactive': queryset.filter(status=SourceResource.STATUS_INACTIVE).count(),
            'error': queryset.filter(status=SourceResource.STATUS_ERROR).count(),
            'mounted': queryset.filter(mount_status=SourceResource.MOUNT_MOUNTED).count(),
            'by_type': {},
            'total_size': sum(r.total_size for r in queryset),
            'total_files': sum(r.file_count for r in queryset),
        }
        
        # Count by type
        for type_code, type_name in SourceResource.TYPE_CHOICES:
            stats['by_type'][type_code] = queryset.filter(resource_type=type_code).count()
        
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def scan(self, request, pk=None):
        """
        Scan the source resource for files and directories.
        
        Returns a list of top-level directories/files.
        """
        resource = self.get_object()
        
        if not resource.bound_node:
            return Response({
                'success': False,
                'message': 'No bound node configured.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # TODO: Send WebSocket command to node to scan
        # For now, return simulated data
        return Response({
            'success': True,
            'path': resource.mount_point or '/',
            'entries': [
                {'name': 'documents', 'type': 'directory', 'size': 0},
                {'name': 'projects', 'type': 'directory', 'size': 0},
                {'name': 'databases', 'type': 'directory', 'size': 0},
                {'name': 'readme.txt', 'type': 'file', 'size': 1024},
            ]
        })
