"""
Serializers for Proxy Nodes

This module provides serializers for proxy management,
heartbeat tracking, and task assignment.
"""

from rest_framework import serializers
from django.utils import timezone
from django.conf import settings
from .models import (
    ProxyNode, ProxyHeartbeat, ProxyTask, NodeConnection
)


class ProxyHeartbeatSerializer(serializers.ModelSerializer):
    """Serializer for proxy heartbeat data."""

    class Meta:
        model = ProxyHeartbeat
        fields = [
            'id', 'timestamp', 'cpu_usage', 'memory_usage',
            'disk_usage', 'network_in', 'network_out',
            'active_tasks', 'completed_tasks', 'failed_tasks', 'metadata'
        ]
        read_only_fields = ['id', 'timestamp']


class ProxyTaskSerializer(serializers.ModelSerializer):
    """Serializer for proxy tasks."""

    proxy_name = serializers.CharField(source='proxy.name', read_only=True)
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = ProxyTask
        fields = [
            'id', 'proxy', 'proxy_name', 'task_type', 'status',
            'parameters', 'created_at', 'dispatched_at', 'started_at',
            'completed_at', 'timeout_seconds', 'progress', 'progress_message',
            'result', 'error_message', 'repository_id', 'source_resource_id',
            'duration_seconds'
        ]
        read_only_fields = [
            'id', 'dispatched_at', 'started_at', 'completed_at',
            'result', 'error_message'
        ]

    def get_duration_seconds(self, obj):
        """Calculate task duration."""
        if obj.started_at:
            end = obj.completed_at or timezone.now()
            return (end - obj.started_at).total_seconds()
        return None


class ProxyTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating proxy tasks."""

    class Meta:
        model = ProxyTask
        fields = ['proxy', 'task_type', 'parameters', 'timeout_seconds',
                  'repository_id', 'source_resource_id']


class ProxyNodeSerializer(serializers.ModelSerializer):
    """Serializer for ProxyNode model."""

    is_online = serializers.SerializerMethodField()
    uptime_seconds = serializers.SerializerMethodField()
    heartbeat_count = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    capabilities_display = serializers.SerializerMethodField()

    class Meta:
        model = ProxyNode
        fields = [
            'id', 'name', 'role', 'role_display', 'hostname', 'internal_ip',
            'operating_system', 'os_version', 'version', 'kopia_version',
            'cpu_cores', 'memory_total', 'disk_total',
            'status', 'status_display', 'last_heartbeat', 'heartbeat_interval',
            'cpu_usage', 'memory_usage', 'disk_usage', 'active_tasks',
            'capabilities', 'capabilities_display', 'mount_types',
            'tags', 'labels', 'metadata',
            'created_at', 'updated_at', 'registered_at', 'installed_at',
            'owner', 'is_online', 'uptime_seconds', 'heartbeat_count'
        ]
        read_only_fields = [
            'id', 'api_token', 'status', 'created_at', 'updated_at',
            'registered_at', 'last_heartbeat', 'installed_at'
        ]

    def get_is_online(self, obj):
        """Check if proxy is online."""
        return obj.is_online()

    def get_uptime_seconds(self, obj):
        """Calculate uptime since registration."""
        if not obj.registered_at:
            return None
        return (timezone.now() - obj.registered_at).total_seconds()

    def get_heartbeat_count(self, obj):
        """Get count of recent heartbeats."""
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        return obj.heartbeats.filter(timestamp__gte=one_hour_ago).count()

    def get_capabilities_display(self, obj):
        """Get capabilities with defaults."""
        return obj.get_capabilities_display()


class ProxyNodeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new proxy."""

    class Meta:
        model = ProxyNode
        fields = [
            'name', 'role', 'hostname', 'heartbeat_interval',
            'tags', 'labels', 'metadata'
        ]

    def create(self, validated_data):
        """Create a new proxy with generated credentials."""
        import secrets

        # Generate API token
        validated_data['api_token'] = secrets.token_urlsafe(32)
        validated_data['install_token'] = secrets.token_urlsafe(32)

        return super().create(validated_data)


class ProxyNodeUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating proxy information."""

    class Meta:
        model = ProxyNode
        fields = [
            'name', 'hostname', 'heartbeat_interval',
            'capabilities', 'mount_types', 'tags', 'labels', 'metadata'
        ]


class ProxyNodeDetailSerializer(ProxyNodeSerializer):
    """Detailed serializer for proxy with related data."""

    recent_heartbeats = serializers.SerializerMethodField()
    recent_tasks = serializers.SerializerMethodField()
    active_tasks_list = serializers.SerializerMethodField()

    class Meta(ProxyNodeSerializer.Meta):
        fields = ProxyNodeSerializer.Meta.fields + [
            'recent_heartbeats', 'recent_tasks', 'active_tasks_list'
        ]

    def get_recent_heartbeats(self, obj):
        """Get recent heartbeats."""
        heartbeats = obj.heartbeats.all()[:10]
        return ProxyHeartbeatSerializer(heartbeats, many=True).data

    def get_recent_tasks(self, obj):
        """Get recent tasks."""
        tasks = obj.tasks.all()[:10]
        return ProxyTaskSerializer(tasks, many=True).data

    def get_active_tasks_list(self, obj):
        """Get active tasks."""
        tasks = obj.tasks.filter(
            status__in=['pending', 'dispatched', 'accepted', 'running']
        )[:5]
        return ProxyTaskSerializer(tasks, many=True).data


class ProxyRegisterSerializer(serializers.Serializer):
    """Serializer for proxy registration."""

    install_token = serializers.CharField()
    node_id = serializers.UUIDField()
    hostname = serializers.CharField()
    internal_ip = serializers.GenericIPAddressField(required=False)
    os = serializers.CharField()
    os_version = serializers.CharField(required=False)
    version = serializers.CharField()
    kopia_version = serializers.CharField()
    cpu_cores = serializers.IntegerField(required=False)
    memory_total = serializers.BigIntegerField(required=False)
    disk_total = serializers.BigIntegerField(required=False)
    capabilities = serializers.JSONField(required=False, default=dict)

    def validate(self, attrs):
        """Validate install token and get proxy."""
        try:
            proxy = ProxyNode.objects.get(install_token=attrs['install_token'])
            if proxy.status != ProxyNode.NodeStatus.PENDING:
                raise serializers.ValidationError('Proxy already registered')
            attrs['proxy'] = proxy
        except ProxyNode.DoesNotExist:
            raise serializers.ValidationError('Invalid install token')
        return attrs


class ProxyHeartbeatCreateSerializer(serializers.Serializer):
    """Serializer for receiving heartbeat updates from proxies."""

    node_id = serializers.UUIDField()
    api_token = serializers.CharField()
    version = serializers.CharField(required=False)
    kopia_version = serializers.CharField(required=False)
    hostname = serializers.CharField(required=False)
    internal_ip = serializers.GenericIPAddressField(required=False)
    os = serializers.CharField(required=False)
    os_version = serializers.CharField(required=False)
    cpu_cores = serializers.IntegerField(required=False)
    memory_total = serializers.BigIntegerField(required=False)
    disk_total = serializers.BigIntegerField(required=False)
    cpu_usage = serializers.FloatField(required=False)
    memory_usage = serializers.FloatField(required=False)
    disk_usage = serializers.FloatField(required=False)
    network_in = serializers.IntegerField(required=False)
    network_out = serializers.IntegerField(required=False)
    active_tasks = serializers.IntegerField(required=False, default=0)
    completed_tasks = serializers.IntegerField(required=False, default=0)
    failed_tasks = serializers.IntegerField(required=False, default=0)
    capabilities = serializers.JSONField(required=False, default=dict)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate(self, attrs):
        """Validate proxy credentials."""
        try:
            proxy = ProxyNode.objects.get(
                id=attrs['node_id'],
                api_token=attrs['api_token']
            )
        except ProxyNode.DoesNotExist:
            raise serializers.ValidationError('Invalid proxy credentials.')

        attrs['proxy'] = proxy
        return attrs


class InstallCommandSerializer(serializers.Serializer):
    """Serializer for generating installation command."""

    role = serializers.ChoiceField(choices=ProxyNode.Role.choices)
    os = serializers.ChoiceField(choices=['linux', 'windows', 'macos'])
    name = serializers.CharField(max_length=255)
    server_url = serializers.URLField(required=False)
    labels = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )


class InstallCommandResponseSerializer(serializers.Serializer):
    """Response for installation command generation."""

    proxy_id = serializers.UUIDField()
    name = serializers.CharField()
    role = serializers.CharField()
    install_token = serializers.CharField()
    api_token = serializers.CharField()
    install_command = serializers.CharField()
    windows_command = serializers.CharField()
    config_yaml = serializers.CharField()
    expires_at = serializers.DateTimeField()


class ProxyStatsSerializer(serializers.Serializer):
    """Serializer for proxy statistics summary."""

    total_proxies = serializers.IntegerField()
    online_proxies = serializers.IntegerField()
    offline_proxies = serializers.IntegerField()
    agent_proxies = serializers.IntegerField()
    sync_proxies = serializers.IntegerField()
    proxies_by_status = serializers.DictField()
    proxies_by_os = serializers.DictField()
    average_uptime = serializers.FloatField()
    total_active_tasks = serializers.IntegerField()


class NodeConnectionSerializer(serializers.ModelSerializer):
    """Serializer for proxy connection records."""

    proxy_name = serializers.CharField(source='proxy.name', read_only=True)

    class Meta:
        model = NodeConnection
        fields = [
            'id', 'connection_id', 'proxy', 'proxy_name', 'status',
            'remote_address', 'user_agent', 'connected_at',
            'disconnected_at', 'last_message_at', 'message_count'
        ]
        read_only_fields = fields
