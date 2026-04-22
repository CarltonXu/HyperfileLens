"""
Views for Nodes Application

This module provides API views for node management,
including CRUD operations, heartbeat handling, and statistics.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count, Avg
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from .models import (
    Node, SourceProxyNode, TargetGatewayNode,
    NodeHeartbeat, NodeConnection, NodeTaskAssignment
)
from .serializers import (
    NodeSerializer, NodeCreateSerializer, NodeUpdateSerializer,
    NodeHeartbeatSerializer, NodeConnectionSerializer,
    NodeTaskAssignmentSerializer, NodeStatsSerializer,
    NodeHeartbeatCreateSerializer
)


class NodeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for node management.

    Provides CRUD operations for source proxy and target gateway nodes.
    """

    permission_classes = [IsAuthenticated]
    filterset_fields = ['node_type', 'status', 'operating_system']
    search_fields = ['name', 'hostname']
    ordering_fields = ['name', 'created_at', 'last_heartbeat', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Return nodes filtered by user's access permissions.
        """
        user = self.request.user
        if user.is_superuser:
            return Node.objects.all()
        return Node.objects.filter(owner=user)

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'create':
            return NodeCreateSerializer
        if self.action in ['update', 'partial_update']:
            return NodeUpdateSerializer
        return NodeSerializer

    @extend_schema(
        summary='List all nodes',
        description='Retrieve a list of all registered nodes.',
        parameters=[
            OpenApiParameter(name='node_type', description='Filter by node type'),
            OpenApiParameter(name='status', description='Filter by status'),
            OpenApiParameter(name='search', description='Search by name or hostname'),
        ]
    )
    def list(self, request, *args, **kwargs):
        """List all nodes."""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Create a new node',
        description='Register a new source proxy or target gateway node.',
        responses={201: NodeSerializer}
    )
    def create(self, request, *args, **kwargs):
        """Create a new node."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        node = serializer.save()

        # Set owner to current user
        node.owner = request.user
        node.save(update_fields=['owner'])

        response_serializer = NodeSerializer(node)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary='Retrieve node details',
        description='Get detailed information about a specific node.',
    )
    def retrieve(self, request, *args, **kwargs):
        """Retrieve node details."""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary='Update node information',
        description='Update node configuration and settings.',
    )
    def update(self, request, *args, **kwargs):
        """Update node information."""
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary='Delete a node',
        description='Unregister and delete a node.',
        responses={204: OpenApiResponse(description='Node deleted')}
    )
    def destroy(self, request, *args, **kwargs):
        """Delete a node."""
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary='Get node statistics',
        description='Get statistics summary for all nodes.',
        responses={200: NodeStatsSerializer}
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get node statistics.

        Returns aggregated statistics about all nodes.
        """
        queryset = self.get_queryset()

        total = queryset.count()
        online = queryset.filter(
            last_heartbeat__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()
        offline = total - online

        # Group by type
        by_type = dict(
            queryset.values('node_type')
            .annotate(count=Count('id'))
            .values_list('node_type', 'count')
        )

        # Group by status
        by_status = dict(
            queryset.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )

        # Average uptime for active nodes
        avg_uptime = 0
        active_nodes = queryset.filter(status=Node.NodeStatus.ACTIVE)
        if active_nodes.exists():
            total_uptime = sum(
                (timezone.now() - n.registered_at).total_seconds()
                for n in active_nodes
                if n.registered_at
            )
            avg_uptime = total_uptime / active_nodes.count() if active_nodes.count() > 0 else 0

        data = {
            'total_nodes': total,
            'online_nodes': online,
            'offline_nodes': offline,
            'nodes_by_type': by_type,
            'nodes_by_status': by_status,
            'average_uptime': avg_uptime
        }

        serializer = NodeStatsSerializer(data)
        return Response(serializer.data)

    @extend_schema(
        summary='Get source proxy nodes',
        description='List all source proxy nodes.',
    )
    @action(detail=False, methods=['get'])
    def source_proxies(self, request):
        """
        List source proxy nodes.

        Returns only source proxy type nodes.
        """
        queryset = self.get_queryset().filter(
            node_type=Node.NodeType.SOURCE_PROXY
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = NodeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = NodeSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Get target gateway nodes',
        description='List all target gateway nodes.',
    )
    @action(detail=False, methods=['get'])
    def target_gateways(self, request):
        """
        List target gateway nodes.

        Returns only target gateway type nodes.
        """
        queryset = self.get_queryset().filter(
            node_type=Node.NodeType.TARGET_GATEWAY
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = NodeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = NodeSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Get node heartbeat history',
        description='Get heartbeat history for a specific node.',
        responses={200: NodeHeartbeatSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def heartbeats(self, request, pk=None):
        """
        Get heartbeat history for a node.

        Returns recent heartbeat records for the specified node.
        """
        node = self.get_object()
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timezone.timedelta(hours=hours)
        heartbeats = node.heartbeats.filter(timestamp__gte=since)
        serializer = NodeHeartbeatSerializer(heartbeats, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Update node status',
        description='Update the status of a specific node.',
    )
    @action(detail=True, methods=['post'])
    def set_status(self, request, pk=None):
        """
        Update node status.

        Allows changing node status (e.g., to maintenance mode).
        """
        node = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(Node.NodeStatus.choices):
            return Response(
                {'error': 'Invalid status value.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        node.update_status(new_status)
        serializer = NodeSerializer(node)
        return Response(serializer.data)


class NodeHeartbeatView(APIView):
    """
    View for receiving node heartbeats.

    This endpoint is called by nodes to report their status.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary='Receive node heartbeat',
        description='Receive and process heartbeat data from a node.',
        request=NodeHeartbeatCreateSerializer,
        responses={
            200: NodeSerializer,
            401: OpenApiResponse(description='Invalid credentials'),
        }
    )
    def post(self, request):
        """
        Receive heartbeat from node.

        Updates node status and creates heartbeat record.
        """
        serializer = NodeHeartbeatCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        node = serializer.validated_data['node']
        data = serializer.validated_data

        # Update node heartbeat
        node.last_heartbeat = timezone.now()
        if node.status == Node.NodeStatus.PENDING:
            node.status = Node.NodeStatus.ACTIVE
            node.registered_at = timezone.now()
        if data.get('version'):
            node.version = data['version']
        node.save()

        # Create heartbeat record
        heartbeat = NodeHeartbeat.objects.create(
            node=node,
            cpu_usage=data.get('cpu_usage'),
            memory_usage=data.get('memory_usage'),
            disk_usage=data.get('disk_usage'),
            network_in=data.get('network_in'),
            network_out=data.get('network_out'),
            active_tasks=data.get('active_tasks', 0),
            metadata=data.get('metadata', {})
        )

        return Response({
            'status': 'ok',
            'node': NodeSerializer(node).data,
            'server_time': timezone.now()
        })


class NodeConnectionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing node connection history.
    """

    serializer_class = NodeConnectionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['node', 'status']

    def get_queryset(self):
        """
        Return connections for nodes the user has access to.
        """
        user = self.request.user
        if user.is_superuser:
            return NodeConnection.objects.all()
        return NodeConnection.objects.filter(node__owner=user)


class NodeTaskAssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing task assignments to nodes.
    """

    serializer_class = NodeTaskAssignmentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['node', 'task_type', 'status']

    def get_queryset(self):
        """
        Return assignments for nodes the user has access to.
        """
        user = self.request.user
        if user.is_superuser:
            return NodeTaskAssignment.objects.all()
        return NodeTaskAssignment.objects.filter(node__owner=user)

    @extend_schema(
        summary='Get pending assignments',
        description='List all pending task assignments for a node.',
    )
    @action(detail=False, methods=['get'], url_path='node/(?P<node_id>[^/.]+)')
    def for_node(self, request, node_id=None):
        """
        Get pending assignments for a specific node.

        Returns task assignments waiting to be executed.
        """
        try:
            node = Node.objects.get(node_id=node_id)
        except Node.DoesNotExist:
            return Response(
                {'error': 'Node not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        assignments = self.get_queryset().filter(
            node=node,
            status__in=[
                NodeTaskAssignment.AssignmentStatus.PENDING,
                NodeTaskAssignment.AssignmentStatus.ASSIGNED
            ]
        )
        serializer = NodeTaskAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Accept a task assignment',
        description='Mark a task assignment as accepted by the node.',
    )
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """
        Accept a task assignment.

        Called by the node when it starts processing the task.
        """
        assignment = self.get_object()
        assignment.status = NodeTaskAssignment.AssignmentStatus.ACCEPTED
        assignment.accepted_at = timezone.now()
        assignment.save()
        return Response(NodeTaskAssignmentSerializer(assignment).data)

    @extend_schema(
        summary='Start task execution',
        description='Mark a task assignment as started.',
    )
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Start task execution.

        Called by the node when it begins executing the task.
        """
        assignment = self.get_object()
        assignment.status = NodeTaskAssignment.AssignmentStatus.ACCEPTED
        assignment.started_at = timezone.now()
        assignment.save()
        return Response(NodeTaskAssignmentSerializer(assignment).data)

    @extend_schema(
        summary='Update task progress',
        description='Update the progress of a task assignment.',
    )
    @action(detail=True, methods=['post'])
    def progress(self, request, pk=None):
        """
        Update task progress.

        Allows updating the progress percentage of the task.
        """
        assignment = self.get_object()
        progress = request.data.get('progress', 0)

        if not 0 <= progress <= 100:
            return Response(
                {'error': 'Progress must be between 0 and 100.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        assignment.progress = progress
        assignment.save()
        return Response(NodeTaskAssignmentSerializer(assignment).data)

    @extend_schema(
        summary='Complete task execution',
        description='Mark a task assignment as completed.',
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Complete task execution.

        Marks the task as completed with result data.
        """
        assignment = self.get_object()
        assignment.status = NodeTaskAssignment.AssignmentStatus.COMPLETED
        assignment.completed_at = timezone.now()
        assignment.progress = 100
        assignment.result = request.data.get('result', {})
        assignment.save()
        return Response(NodeTaskAssignmentSerializer(assignment).data)

    @extend_schema(
        summary='Fail task execution',
        description='Mark a task assignment as failed.',
    )
    @action(detail=True, methods=['post'])
    def fail(self, request, pk=None):
        """
        Mark task as failed.

        Records error information when task execution fails.
        """
        assignment = self.get_object()
        assignment.status = NodeTaskAssignment.AssignmentStatus.FAILED
        assignment.completed_at = timezone.now()
        assignment.error = request.data.get('error', 'Unknown error')
        assignment.save()
        return Response(NodeTaskAssignmentSerializer(assignment).data)
