"""
Gateway Serializers for HyperFileLens
"""

from rest_framework import serializers
from .models import Gateway


class GatewaySerializer(serializers.ModelSerializer):
    """Serializer for Gateway model."""
    
    is_online = serializers.ReadOnlyField()
    uptime_seconds = serializers.SerializerMethodField()
    memory_total_gb = serializers.SerializerMethodField()
    disk_total_gb = serializers.SerializerMethodField()
    
    class Meta:
        model = Gateway
        fields = [
            'id', 'name', 'description', 'hostname', 'internal_ip', 'ssh_port',
            'status', 'os_version', 'version', 'kopia_version',
            'cpu_cores', 'memory_total', 'disk_total',
            'cpu_usage', 'memory_usage', 'disk_usage', 'active_mounts',
            'mount_base_path', 'max_concurrent_mounts',
            # Kopia Server
            'kopia_server_status', 'kopia_server_port', 'kopia_server_tls',
            # AI & Index
            'ai_enabled', 'indexer_status', 'last_index_time',
            'index_status', 'index_total_files', 'indexed_files',
            # Status
            'last_heartbeat', 'heartbeat_interval', 'is_online',
            'uptime_seconds', 'memory_total_gb', 'disk_total_gb',
            'tags', 'labels', 'metadata', 'capabilities',
            'created_at', 'updated_at', 'registered_at', 'installed_at'
        ]
        read_only_fields = [
            'id', 'api_token', 'install_token', 'install_token_used',
            'created_at', 'updated_at', 'registered_at', 'installed_at'
        ]
    
    def get_uptime_seconds(self, obj):
        """Calculate uptime in seconds."""
        if not obj.registered_at:
            return None
        from django.utils import timezone
        return (timezone.now() - obj.registered_at).total_seconds()
    
    def get_memory_total_gb(self, obj):
        """Convert memory to GB."""
        if obj.memory_total:
            return round(obj.memory_total / (1024 ** 3), 2)
        return None
    
    def get_disk_total_gb(self, obj):
        """Convert disk to GB."""
        if obj.disk_total:
            return round(obj.disk_total / (1024 ** 3), 2)
        return None


class GatewayCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new Gateway."""
    
    class Meta:
        model = Gateway
        fields = ['name', 'description', 'ssh_port', 'mount_base_path', 
                  'max_concurrent_mounts', 'ai_enabled', 'tags', 'labels']
    
    def create(self, validated_data):
        """Create a new gateway with auto-generated tokens."""
        gateway = Gateway.objects.create(**validated_data)
        gateway.generate_api_token()
        gateway.generate_install_token()
        gateway.save()
        return gateway


class GatewayInstallCommandSerializer(serializers.Serializer):
    """Serializer for generating install command."""
    install_command = serializers.CharField()


class GatewayInstallSerializer(serializers.Serializer):
    """Serializer for generating installation command for a new gateway."""
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    ai_enabled = serializers.BooleanField(required=False, default=True)
    tags = serializers.DictField(required=False, default=dict)
    labels = serializers.ListField(required=False, default=list)
    server_url = serializers.URLField(required=False)


class GatewayHeartbeatSerializer(serializers.Serializer):
    """Serializer for gateway heartbeat."""
    hostname = serializers.CharField(required=False)
    internal_ip = serializers.IPAddressField(required=False)
    version = serializers.CharField(required=False)
    kopia_version = serializers.CharField(required=False)
    cpu_cores = serializers.IntegerField(required=False)
    memory_total = serializers.IntegerField(required=False)
    disk_total = serializers.IntegerField(required=False)
    cpu_usage = serializers.FloatField(required=False)
    memory_usage = serializers.FloatField(required=False)
    disk_usage = serializers.FloatField(required=False)
    active_mounts = serializers.IntegerField(required=False)
    network_interfaces = serializers.ListField(required=False)
    network_bytes_sent = serializers.IntegerField(required=False)
    network_bytes_recv = serializers.IntegerField(required=False)
    capabilities = serializers.DictField(required=False)
