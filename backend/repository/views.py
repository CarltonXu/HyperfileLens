"""
HyperFileLens Backend - Repository Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import Repository
from .serializers import (
    RepositorySerializer,
    RepositoryListSerializer,
    RepositoryCreateSerializer,
    RepositoryUpdateSerializer,
    RepositoryInitSerializer,
    ConnectionTestSerializer,
    ConnectionTestResultSerializer
)
from nodes.models import Node


class RepositoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing backup repositories.
    
    Repository is the target storage for backup data.
    It needs to be bound to a Node for operations and initialized
    with Kopia before use.
    """
    queryset = Repository.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RepositoryListSerializer
        if self.action == 'create':
            return RepositoryCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return RepositoryUpdateSerializer
        return RepositorySerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = Repository.objects.select_related('bound_node', 'user')
        
        # Role-based access
        if user.is_superuser or (user.role and user.role.code == 'admin'):
            pass  # Admin sees all
        else:
            queryset = queryset.filter(user=user)
        
        # Filter by type
        repo_type = self.request.query_params.get('repo_type')
        if repo_type:
            queryset = queryset.filter(repo_type=repo_type)
        
        # Filter by status
        repo_status = self.request.query_params.get('status')
        if repo_status:
            queryset = queryset.filter(status=repo_status)
        
        # Filter by bound node
        node_id = self.request.query_params.get('bound_node')
        if node_id:
            queryset = queryset.filter(bound_node_id=node_id)
        
        # Filter by initialization status
        initialized = self.request.query_params.get('initialized')
        if initialized is not None:
            is_init = initialized.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(kopia_initialized=is_init)
        
        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create a new repository."""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """
        Test repository connection through bound Node.
        
        This sends a test command to the bound Node to verify
        connectivity to the storage backend.
        """
        repo = self.get_object()
        
        if not repo.bound_node:
            return Response({
                'success': False,
                'message': 'No bound node configured. Please bind a node first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if repo.bound_node.status != Node.NodeStatus.ACTIVE:
            return Response({
                'success': False,
                'message': f'Bound node is {repo.bound_node.get_status_display()}. Node must be active.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # In production, this would send a WebSocket command to the Node
        # to test the connection. For now, we simulate the response.
        try:
            # Simulate connection test
            # TODO: Implement actual Node communication via WebSocket
            
            # Update repository status
            repo.last_connection_test = timezone.now()
            repo.connection_test_result = 'Connection successful'
            repo.status = Repository.STATUS_ACTIVE
            repo.save()
            
            return Response({
                'success': True,
                'message': 'Connection test successful',
                'details': {
                    'node': repo.bound_node.name,
                    'repo_type': repo.repo_type,
                    'tested_at': repo.last_connection_test.isoformat()
                }
            })
        except Exception as e:
            repo.status = Repository.STATUS_ERROR
            repo.status_message = str(e)
            repo.save()
            
            return Response({
                'success': False,
                'message': f'Connection test failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def initialize(self, request, pk=None):
        """
        Initialize Kopia repository.
        
        This creates the Kopia repository on the storage backend,
        setting up encryption and metadata structures.
        """
        repo = self.get_object()
        
        if repo.kopia_initialized:
            return Response({
                'success': False,
                'message': 'Repository is already initialized.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not repo.bound_node:
            return Response({
                'success': False,
                'message': 'No bound node configured. Please bind a node first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = RepositoryInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # In production, this would send a command to the Node
        # to initialize the Kopia repository
        try:
            # TODO: Implement actual Kopia initialization via Node
            
            repo.status = Repository.STATUS_INITIALIZING
            repo.save()
            
            # Simulate initialization
            import uuid as uuid_lib
            repo.kopia_initialized = True
            repo.kopia_repository_id = str(uuid_lib.uuid4())
            repo.status = Repository.STATUS_ACTIVE
            repo.save()
            
            return Response({
                'success': True,
                'message': 'Repository initialized successfully',
                'details': {
                    'repository_id': repo.kopia_repository_id,
                    'encryption_algorithm': repo.encryption_algorithm
                }
            })
        except Exception as e:
            repo.status = Repository.STATUS_ERROR
            repo.status_message = str(e)
            repo.save()
            
            return Response({
                'success': False,
                'message': f'Initialization failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def bind_node(self, request, pk=None):
        """
        Bind or change the Node for this repository.
        """
        repo = self.get_object()
        node_id = request.data.get('node_id')
        
        if not node_id:
            return Response({
                'success': False,
                'message': 'node_id is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            node = Node.objects.get(id=node_id)
        except Node.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Node not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if node.status != Node.NodeStatus.ACTIVE:
            return Response({
                'success': False,
                'message': f'Node is {node.get_status_display()}. Node must be active.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        repo.bound_node = node
        repo.save()
        
        return Response({
            'success': True,
            'message': f'Node "{node.name}" bound successfully.',
            'bound_node': {
                'id': str(node.id),
                'name': node.name,
                'status': node.status
            }
        })
    
    @action(detail=True, methods=['post'])
    def unbind_node(self, request, pk=None):
        """Unbind the Node from this repository."""
        repo = self.get_object()
        
        if not repo.bound_node:
            return Response({
                'success': False,
                'message': 'No node is currently bound.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        old_node_name = repo.bound_node.name
        repo.bound_node = None
        repo.save()
        
        return Response({
            'success': True,
            'message': f'Node "{old_node_name}" unbound successfully.'
        })
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Synchronize repository statistics."""
        repo = self.get_object()
        
        if not repo.bound_node:
            return Response({
                'success': False,
                'message': 'No bound node configured.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # In production, this would query the Node for actual stats
        # TODO: Implement actual sync via Node WebSocket
        
        repo.last_sync_at = timezone.now()
        repo.save()
        
        return Response({
            'success': True,
            'message': 'Repository synchronized',
            'details': {
                'used_space': repo.used_space,
                'snapshot_count': repo.snapshot_count,
                'synced_at': repo.last_sync_at.isoformat()
            }
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get repository statistics overview."""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'active': queryset.filter(status=Repository.STATUS_ACTIVE).count(),
            'inactive': queryset.filter(status=Repository.STATUS_INACTIVE).count(),
            'error': queryset.filter(status=Repository.STATUS_ERROR).count(),
            'initialized': queryset.filter(kopia_initialized=True).count(),
            'not_initialized': queryset.filter(kopia_initialized=False).count(),
            'bound': queryset.filter(bound_node__isnull=False).count(),
            'unbound': queryset.filter(bound_node__isnull=True).count(),
            'by_type': {},
            'total_capacity': sum(r.capacity for r in queryset if r.capacity > 0),
            'total_used': sum(r.used_space for r in queryset),
        }
        
        # Count by type
        for type_code, type_name in Repository.TYPE_CHOICES:
            stats['by_type'][type_code] = queryset.filter(repo_type=type_code).count()
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available repository types."""
        return Response([
            {'value': type_code, 'label': type_name}
            for type_code, type_name in Repository.TYPE_CHOICES
        ])
    
    @action(detail=True, methods=['get'])
    def snapshots(self, request, pk=None):
        """Get snapshots in this repository."""
        repo = self.get_object()
        
        # In production, this would query the Node for actual snapshots
        # TODO: Implement actual snapshot listing via Node
        
        return Response({
            'count': repo.snapshot_count,
            'results': []  # Placeholder for actual snapshots
        })
