"""
HyperFileLens Backend - AI Query Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import AIQuery
from .serializers import AIQuerySerializer, AIQueryCreateSerializer
from .tasks import execute_ai_query


class AIQueryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing AI queries."""
    queryset = AIQuery.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AIQueryCreateSerializer
        return AIQuerySerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return AIQuery.objects.all()
        return AIQuery.objects.filter(user=user)
    
    def create(self, request, *args, **kwargs):
        """Create a new AI query and execute it asynchronously."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create query instance
        query = AIQuery.objects.create(
            user=request.user,
            **serializer.validated_data
        )
        
        # Execute asynchronously
        execute_ai_query.delay(str(query.id))
        
        # Return the created query
        return Response(
            AIQuerySerializer(query).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed query."""
        query = self.get_object()
        
        if query.status not in ['failed']:
            return Response(
                {'error': 'Only failed queries can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reset status and execute
        query.status = 'pending'
        query.error_message = ''
        query.save(update_fields=['status', 'error_message'])
        
        execute_ai_query.delay(str(query.id))
        
        return Response({'message': 'Query retry started'})
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get user's query history."""
        queries = self.get_queryset()[:20]
        serializer = AIQuerySerializer(queries, many=True)
        return Response(serializer.data)
