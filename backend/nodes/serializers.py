"""
Serializers for Nodes Application

This module provides serializers for node management,
heartbeat tracking, and task assignment.
"""

from rest_framework import serializers
from django.utils import timezone
from .models import (
    Node, SourceProxyNode, TargetGatewayNode,
    NodeHeartbeat, NodeConnection, NodeTaskAssignment
)


class NodeHeartbeatSerializer(serializers.ModelSerializer):
    """
    Serializer for node heartbeat data.
    """

    class Meta:
        model = NodeHeartbeat
        fields = [
            'id', 'timestamp', 'cpu_usage', 'memory_usage',
            'disk_usage', 'network_in', 'network_out',
            'active_tasks', 'metadata'
        ]
        read_only_fields = ['id', 'timestamp']


class NodeSerializer(serializers.ModelSerializer):
    """
    Serializer for Node model.

    Provides read and write access to node data.
    """

    is_online = serializers.SerializerMethodField()
    uptime_seconds = serializers.SerializerMethodField()
    heartbeat_count = serializers.SerializerMethodField()

    class Meta:
        model = Node
        fields = [
            'id', 'node_id', 'name', 'node_type', 'hostname', 'port',
            'protocol', 'operating_system', 'version', 'cpu_cores',
            'memory_total', 'disk_total', 'status', 'last_heartbeat',
            'heartbeat_interval', 'capabilities', 'tags', 'metadata',
            'created_at', 'updated_at', 'registered_at', 'owner',
            'is_online', 'uptime_seconds', 'heartbeat_count'
        ]
        read_only_fields = [
            'id', 'node_id', 'status', 'created_at', 'updated_at',
            'registered_at', 'last_heartbeat'
        ]

    def get_is_online(self, obj):
        """
        Check if node is online.

        Args:
            obj: Node instance

        Returns:
            Boolean indicating if node is online
        """
        return obj.is_online()

    def get_uptime_seconds(self, obj):
        """
        Calculate uptime since registration.

        Args:
            obj: Node instance

        Returns:
            Uptime in seconds, or None if not registered
        """
        if not obj.registered_at:
            return None
        return (timezone.now() - obj.registered_at).total_seconds()

    def get_heartbeat_count(self, obj):
        """
        Get count of recent heartbeats.

        Args:
            obj: Node instance

        Returns:
            Count of heartbeats in last hour
        """
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        return obj.heartbeats.filter(timestamp__gte=one_hour_ago).count()


class SourceProxyNodeSerializer(NodeSerializer):
    """
    Serializer for SourceProxyNode model.
    """

    class Meta(NodeSerializer.Meta):
        model = SourceProxyNode
        fields = NodeSerializer.Meta.fields + ['mount_points']


class TargetGatewayNodeSerializer(NodeSerializer):
    """
    Serializer for TargetGatewayNode model.
    """

    class Meta(NodeSerializer.Meta):
        model = TargetGatewayNode
        fields = NodeSerializer.Meta.fields + ['backup_repositories']


class NodeCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new node.
    """

    class Meta:
        model = Node
        fields = [
            'name', 'node_type', 'hostname', 'port', 'protocol',
            'operating_system', 'heartbeat_interval', 'tags', 'metadata'
        ]

    def create(self, validated_data):
        """
        Create a new node with generated credentials.

        Args:
            validated_data: Validated data from the serializer

        Returns:
            The created node instance
        """
        import secrets
        import uuid

        # Generate API key
        validated_data['api_key'] = secrets.token_hex(32)
        validated_data['api_secret'] = secrets.token_urlsafe(32)

        # Generate node ID
        validated_data['node_id'] = uuid.uuid4()

        return super().create(validated_data)


class NodeUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating node information.
    """

    class Meta:
        model = Node
        fields = [
            'name', 'hostname', 'port', 'protocol',
            'heartbeat_interval', 'capabilities', 'tags', 'metadata'
        ]


class NodeHeartbeatCreateSerializer(serializers.Serializer):
    """
    Serializer for receiving heartbeat updates from nodes.
    """

    node_id = serializers.UUIDField()
    api_key = serializers.CharField()
    version = serializers.CharField(required=False)
    cpu_usage = serializers.FloatField(required=False)
    memory_usage = serializers.FloatField(required=False)
    disk_usage = serializers.FloatField(required=False)
    network_in = serializers.IntegerField(required=False)
    network_out = serializers.IntegerField(required=False)
    active_tasks = serializers.IntegerField(required=False, default=0)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate(self, attrs):
        """
        Validate node credentials.

        Args:
            attrs: Input data

        Returns:
            Validated data

        Raises:
            ValidationError: If credentials are invalid
        """
        from .models import Node

        try:
            node = Node.objects.get(
                node_id=attrs['node_id'],
                api_key=attrs['api_key']
            )
        except Node.DoesNotExist:
            raise serializers.ValidationError('Invalid node credentials.')

        attrs['node'] = node
        return attrs


class NodeConnectionSerializer(serializers.ModelSerializer):
    """
    Serializer for node connection records.
    """

    node_name = serializers.CharField(source='node.name', read_only=True)

    class Meta:
        model = NodeConnection
        fields = [
            'id', 'connection_id', 'node', 'node_name', 'status',
            'remote_address', 'user_agent', 'connected_at',
            'disconnected_at', 'last_message_at', 'message_count'
        ]
        read_only_fields = fields


class NodeTaskAssignmentSerializer(serializers.ModelSerializer):
    """
    Serializer for node task assignments.
    """

    node_name = serializers.CharField(source='node.name', read_only=True)

    class Meta:
        model = NodeTaskAssignment
        fields = [
            'id', 'task_id', 'task_type', 'node', 'node_name',
            'status', 'assigned_at', 'accepted_at', 'started_at',
            'completed_at', 'progress', 'result', 'error'
        ]
        read_only_fields = [
            'id', 'task_id', 'assigned_at', 'accepted_at',
            'started_at', 'completed_at', 'result', 'error'
        ]


class NodeStatsSerializer(serializers.Serializer):
    """
    Serializer for node statistics summary.
    """

    total_nodes = serializers.IntegerField()
    online_nodes = serializers.IntegerField()
    offline_nodes = serializers.IntegerField()
    nodes_by_type = serializers.DictField()
    nodes_by_status = serializers.DictField()
    average_uptime = serializers.FloatField()
