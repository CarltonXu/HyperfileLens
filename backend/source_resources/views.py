"""
HyperFileLens Backend - Source Resource Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import time

from licenses.quota import QuotaCheckMixin
from audit_log.services import AuditService
from nodes.models import ProxyTask
from nodes.proxy_service import ProxyService
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
        queryset = SourceResource.objects.select_related('bound_node', 'user', 'tenant')
        
        # Superuser can see all resources
        if user.is_superuser:
            pass
        # Filter by tenant for tenant users
        elif user.tenant:
            queryset = queryset.filter(tenant=user.tenant)
        else:
            # Users without tenant can only see their own resources
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
        if resource.bound_node.status != resource.bound_node.NodeStatus.ONLINE:
            return Response({
                'success': False,
                'message': f'Bound node "{resource.bound_node.name}" is not online.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result_response, response_status = self._run_storage_test(
            resource.bound_node,
            resource.resource_type,
            resource.config or {},
            resource.credentials or {},
            resource_id=str(resource.id),
        )

        resource.last_connection_test = timezone.now()
        resource.connection_test_result = result_response.get('message') or result_response.get('error') or ''
        resource.status = SourceResource.STATUS_ACTIVE if result_response.get('success') else SourceResource.STATUS_ERROR
        resource.status_message = resource.connection_test_result
        details = result_response.get('details') or {}
        if details.get('space_info'):
            resource.total_size = details['space_info'].get('total_bytes') or resource.total_size
        resource.save()

        return Response(result_response, status=response_status)

    @action(detail=False, methods=['post'], url_path='test-draft')
    def test_draft(self, request):
        """Test a source resource draft before it is saved."""
        from nodes.models import Node

        node_id = request.data.get('bound_node') or request.data.get('bound_node_id')
        resource_type = request.data.get('resource_type')
        config = request.data.get('config') or {}
        credentials = request.data.get('credentials') or {}

        if not node_id:
            return Response({'success': False, 'message': 'bound_node is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not resource_type:
            return Response({'success': False, 'message': 'resource_type is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            node = Node.objects.get(id=node_id)
        except Node.DoesNotExist:
            return Response({'success': False, 'message': 'Node not found.'}, status=status.HTTP_404_NOT_FOUND)

        if node.status != node.NodeStatus.ONLINE:
            return Response({'success': False, 'message': f'Node "{node.name}" is not online.'}, status=status.HTTP_400_BAD_REQUEST)

        result_response, response_status = self._run_storage_test(node, resource_type, config, credentials)
        return Response(result_response, status=response_status)
    
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
        if node.status != Node.NodeStatus.ONLINE:
            return Response({
                'success': False,
                'message': f'Node "{node.name}" is not online.',
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
        
        path = request.query_params.get('path')
        if not path:
            if resource.resource_type == SourceResource.TYPE_LOCAL:
                path = (resource.config or {}).get('root_path') or (resource.config or {}).get('path') or '/'
            else:
                path = resource.mount_point or '/'

        task = ProxyTask.objects.create(
            proxy=resource.bound_node,
            task_type=ProxyTask.TaskType.VERIFY,
            parameters={'operation': 'source_scan', 'source_resource_id': str(resource.id), 'path': path},
            status=ProxyTask.TaskStatus.PENDING,
            timeout_seconds=30,
        )
        task.dispatch()
        ProxyService.send_list_directory_command(str(resource.bound_node.id), path, task_id=str(task.id))

        task = self._wait_for_proxy_task(task, timeout=8)
        if task.status == ProxyTask.TaskStatus.COMPLETED:
            result = task.result or {}
            return Response({
                'success': True,
                'path': result.get('path') or path,
                'entries': result.get('directories') or [],
                'directories': result.get('directories') or [],
                'task_id': str(task.id),
            })

        return Response({
            'success': False,
            'message': task.error_message or 'Source scan timed out.',
            'task_id': str(task.id),
        }, status=status.HTTP_400_BAD_REQUEST if task.status == ProxyTask.TaskStatus.FAILED else status.HTTP_504_GATEWAY_TIMEOUT)

    def _run_storage_test(self, node, resource_type, config, credentials, resource_id=None):
        storage_type, storage_config = self._storage_config(resource_type, config, credentials)
        task = ProxyTask.objects.create(
            proxy=node,
            task_type=ProxyTask.TaskType.TEST_STORAGE,
            parameters={
                'operation': 'source_resource_test',
                'source_resource_id': resource_id,
                'storage_type': storage_type,
                'storage_config': storage_config,
            },
            status=ProxyTask.TaskStatus.PENDING,
            timeout_seconds=60,
        )
        task.dispatch()
        ProxyService.send_test_storage_command(
            proxy_id=str(node.id),
            repository_id='',
            storage_type=storage_type,
            storage_config=storage_config,
            test_write=False,
            task_id=str(task.id),
        )

        task = self._wait_for_proxy_task(task, timeout=15)
        if task.status == ProxyTask.TaskStatus.COMPLETED:
            result = task.result or {}
            return {
                'success': result.get('success', True),
                'message': result.get('message') or 'Connection test successful',
                'details': result,
                'task_id': str(task.id),
            }, status.HTTP_200_OK

        return {
            'success': False,
            'message': task.error_message or 'Connection test failed',
            'error': task.error_message,
            'task_id': str(task.id),
        }, status.HTTP_400_BAD_REQUEST if task.status == ProxyTask.TaskStatus.FAILED else status.HTTP_504_GATEWAY_TIMEOUT

    def _storage_config(self, resource_type, config, credentials):
        if resource_type == SourceResource.TYPE_LOCAL:
            return 'local', {'path': config.get('root_path') or config.get('path') or '/'}
        if resource_type in (SourceResource.TYPE_NAS, SourceResource.TYPE_NFS):
            return 'nas', {
                'server': config.get('server', ''),
                'path': config.get('export_path') or config.get('share') or '',
                'mount_type': config.get('protocol') or 'nfs',
                'mount_options': config.get('mount_options', ''),
            }
        if resource_type == SourceResource.TYPE_CIFS:
            return 'smb', {
                'server': config.get('server', ''),
                'share': config.get('share', ''),
                'username': credentials.get('username', ''),
                'password': credentials.get('password', ''),
                'mount_options': config.get('mount_options', ''),
            }
        if resource_type == SourceResource.TYPE_S3:
            return 's3', {
                'endpoint': config.get('endpoint', ''),
                'bucket': config.get('bucket', ''),
                'region': config.get('region') or 'us-east-1',
                'access_key': credentials.get('access_key', ''),
                'secret_key': credentials.get('secret_key', ''),
            }
        return resource_type, config

    def _wait_for_proxy_task(self, task, timeout=10):
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
