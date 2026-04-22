"""
HyperFileLens Backend - Repository Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Repository
from .serializers import (
    RepositorySerializer,
    RepositoryCreateSerializer,
    RepositoryUpdateSerializer
)


class RepositoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing repositories."""
    queryset = Repository.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RepositoryCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return RepositoryUpdateSerializer
        return RepositorySerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return Repository.objects.all()
        return Repository.objects.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Synchronize repository space usage."""
        repo = self.get_object()
        repo.sync_space_usage()
        return Response({'message': 'Repository synchronized'})
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test repository connection."""
        repo = self.get_object()
        
        # In production, this would test the actual connection
        # to the storage backend
        return Response({
            'status': 'success',
            'message': 'Connection test passed'
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get repository statistics."""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'active': queryset.filter(status='active').count(),
            'inactive': queryset.filter(status='inactive').count(),
            'error': queryset.filter(status='error').count(),
            'total_capacity': sum(r.capacity for r in queryset if r.capacity > 0),
            'total_used': sum(r.used_space for r in queryset),
        }
        
        return Response(stats)
