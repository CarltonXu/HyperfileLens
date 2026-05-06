"""
HyperFileLens Backend - AI Query Views
"""

import requests
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import AIQuery
from .serializers import AIQuerySerializer, AIQueryCreateSerializer
from .tasks import execute_ai_query


# Gateway service URL (can be configured in settings)
GATEWAY_URL = getattr(settings, 'GATEWAY_URL', 'http://localhost:8001')


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
        queryset = AIQuery.objects.select_related('user', 'tenant')
        
        # Superuser can see all AI queries
        if user.is_superuser:
            return queryset
        # Filter by tenant for tenant users
        if user.tenant:
            return queryset.filter(tenant=user.tenant)
        # Users without tenant can only see their own queries
        return queryset.filter(user=user)
    
    def create(self, request, *args, **kwargs):
        """Create a new AI query and execute it asynchronously."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create query instance
        query = AIQuery.objects.create(
            user=request.user,
            tenant=request.user.tenant,
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


# ============== Gateway Proxy Views ==============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gateway_mount_status(request):
    """Proxy: Get mount status from Gateway service."""
    try:
        response = requests.get(f'{GATEWAY_URL}/mount/status', timeout=10)
        return Response(response.json(), status=response.status_code)
    except requests.exceptions.ConnectionError:
        return Response({'error': 'Gateway service unavailable', 'mounted': False}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except requests.exceptions.Timeout:
        return Response({'error': 'Gateway service timeout', 'mounted': False}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        return Response({'error': str(e), 'mounted': False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gateway_index_status(request):
    """Proxy: Get index status from Gateway service."""
    try:
        response = requests.get(f'{GATEWAY_URL}/index/status', timeout=10)
        return Response(response.json(), status=response.status_code)
    except requests.exceptions.ConnectionError:
        return Response({'error': 'Gateway service unavailable'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except requests.exceptions.Timeout:
        return Response({'error': 'Gateway service timeout'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def gateway_ai_query(request):
    """Proxy: Execute AI query through Gateway service."""
    try:
        response = requests.post(
            f'{GATEWAY_URL}/ai/query',
            json=request.data,
            timeout=60
        )
        return Response(response.json(), status=response.status_code)
    except requests.exceptions.ConnectionError:
        return Response({'error': 'Gateway service unavailable'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except requests.exceptions.Timeout:
        return Response({'error': 'Gateway service timeout'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def gateway_rebuild_index(request):
    """Proxy: Rebuild index through Gateway service."""
    try:
        response = requests.post(
            f'{GATEWAY_URL}/index/rebuild',
            json=request.data,
            timeout=30
        )
        return Response(response.json(), status=response.status_code)
    except requests.exceptions.ConnectionError:
        return Response({'error': 'Gateway service unavailable'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except requests.exceptions.Timeout:
        return Response({'error': 'Gateway service timeout'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gateway_list_files(request):
    """Proxy: List files from Gateway service."""
    try:
        response = requests.get(
            f'{GATEWAY_URL}/files',
            params=request.query_params,
            timeout=30
        )
        return Response(response.json(), status=response.status_code)
    except requests.exceptions.ConnectionError:
        return Response({'error': 'Gateway service unavailable'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except requests.exceptions.Timeout:
        return Response({'error': 'Gateway service timeout'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
