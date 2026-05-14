"""
HyperFileLens Backend - Source Resource Serializers
"""

from rest_framework import serializers
from .models import SourceResource


class SourceResourceSerializer(serializers.ModelSerializer):
    """Serializer for SourceResource with all details."""
    
    resource_type_display = serializers.CharField(
        source='get_resource_type_display',
        read_only=True
    )
    mount_status_display = serializers.CharField(
        source='get_mount_status_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    bound_node_name = serializers.CharField(
        source='bound_node.name',
        read_only=True,
        allow_null=True
    )
    bound_node_status = serializers.CharField(
        source='bound_node.status',
        read_only=True,
        allow_null=True
    )
    is_mounted = serializers.ReadOnlyField()
    requires_mount = serializers.ReadOnlyField()
    
    class Meta:
        model = SourceResource
        fields = [
            'id', 'name', 'description', 'resource_type', 'resource_type_display',
            'config', 'credentials',
            'bound_node', 'bound_node_name', 'bound_node_status',
            'mount_status', 'mount_status_display', 'mount_point', 'mount_error',
            'status', 'status_display', 'status_message',
            'last_connection_test', 'connection_test_result',
            'total_size', 'file_count',
            'is_mounted', 'requires_mount',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'mount_status', 'mount_point', 'mount_error',
            'last_connection_test', 'connection_test_result',
            'total_size', 'file_count',
            'created_at', 'updated_at'
        ]


class SourceResourceListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views."""
    
    resource_type_display = serializers.CharField(
        source='get_resource_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    bound_node_name = serializers.CharField(
        source='bound_node.name',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = SourceResource
        fields = [
            'id', 'name', 'description', 'resource_type', 'resource_type_display',
            'config', 'bound_node', 'bound_node_name', 'bound_node_status',
            'mount_status', 'mount_point', 'status', 'status_display',
            'total_size', 'file_count',
            'last_connection_test', 'created_at'
        ]


class SourceResourceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating SourceResource."""
    
    class Meta:
        model = SourceResource
        fields = [
            'name', 'description', 'resource_type',
            'config', 'credentials', 'bound_node', 'status'
        ]
    
    def validate_name(self, value):
        """Ensure name is unique."""
        if SourceResource.objects.filter(name=value).exists():
            raise serializers.ValidationError("A source resource with this name already exists.")
        return value
    
    def validate(self, data):
        """Validate config based on resource type."""
        resource_type = data.get('resource_type')
        config = data.get('config', {})
        credentials = data.get('credentials', {})
        
        if resource_type == SourceResource.TYPE_NFS:
            if 'server' not in config:
                raise serializers.ValidationError({
                    'config': 'NFS requires "server" in config'
                })
            if 'export_path' not in config:
                raise serializers.ValidationError({
                    'config': 'NFS requires "export_path" in config'
                })
        
        elif resource_type == SourceResource.TYPE_CIFS:
            if 'server' not in config:
                raise serializers.ValidationError({
                    'config': 'CIFS requires "server" in config'
                })
            if 'share' not in config:
                raise serializers.ValidationError({
                    'config': 'CIFS requires "share" in config'
                })
            if 'username' not in credentials or 'password' not in credentials:
                raise serializers.ValidationError({
                    'credentials': 'CIFS requires "username" and "password" in credentials'
                })
        
        elif resource_type == SourceResource.TYPE_S3:
            if 'endpoint' not in config:
                raise serializers.ValidationError({
                    'config': 'S3 requires "endpoint" in config'
                })
            if 'bucket' not in config:
                raise serializers.ValidationError({
                    'config': 'S3 requires "bucket" in config'
                })
            if 'access_key' not in credentials or 'secret_key' not in credentials:
                raise serializers.ValidationError({
                    'credentials': 'S3 requires "access_key" and "secret_key" in credentials'
                })
        
        elif resource_type == SourceResource.TYPE_LOCAL:
            # LOCAL type doesn't require config or credentials
            # Paths are specified in backup tasks
            pass
        
        return data


class SourceResourceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating SourceResource."""
    
    class Meta:
        model = SourceResource
        fields = [
            'name', 'description', 'config', 'credentials',
            'bound_node', 'status'
        ]
    
    def validate_name(self, value):
        """Ensure name is unique (excluding current instance)."""
        instance = self.instance
        if SourceResource.objects.filter(name=value).exclude(id=instance.id).exists():
            raise serializers.ValidationError("A source resource with this name already exists.")
        return value


class ConnectionTestSerializer(serializers.Serializer):
    """Serializer for connection test request."""
    pass


class ConnectionTestResultSerializer(serializers.Serializer):
    """Serializer for connection test result."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    details = serializers.DictField(required=False)
