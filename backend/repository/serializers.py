"""
HyperFileLens Backend - Repository Serializers
"""

from rest_framework import serializers
from .models import Repository


def _format_bytes(bytes_value):
    """Format bytes to human-readable string."""
    if bytes_value is None:
        return 'N/A'
    if bytes_value == 0:
        return '0 B'
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} EB"


class RepositorySerializer(serializers.ModelSerializer):
    """Serializer for Repository model with full details."""
    
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    repo_type_display = serializers.CharField(
        source='get_repo_type_display',
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
    available_space_formatted = serializers.SerializerMethodField()
    usage_percentage_formatted = serializers.SerializerMethodField()
    capacity_formatted = serializers.SerializerMethodField()
    used_space_formatted = serializers.SerializerMethodField()
    is_ready = serializers.ReadOnlyField()
    # Masked credentials for display (access_key visible, secret_key/password masked)
    credentials_masked = serializers.SerializerMethodField()
    
    class Meta:
        model = Repository
        fields = [
            'id', 'name', 'description', 'repo_type', 'repo_type_display',
            'config', 'credentials_masked',
            'bound_node', 'bound_node_name', 'bound_node_status',
            'kopia_initialized', 'kopia_repository_id', 'encryption_algorithm',
            'capacity', 'capacity_formatted', 'used_space', 'used_space_formatted',
            'available_space_formatted', 'usage_percentage',
            'usage_percentage_formatted',
            'status', 'status_display', 'status_message',
            'last_connection_test', 'connection_test_result',
            'supports_compression', 'supports_encryption', 'compression_type',
            'is_readonly', 'is_ready',
            'snapshot_count', 'last_backup_at', 'last_sync_at',
            'user', 'user_email', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'used_space', 'kopia_initialized', 'kopia_repository_id',
            'status', 'status_message', 'last_connection_test', 'connection_test_result',
            'snapshot_count', 'last_backup_at', 'last_sync_at',
            'user', 'created_at', 'updated_at'
        ]
    
    def get_credentials_masked(self, obj):
        """Return credentials with sensitive fields masked."""
        return obj.get_masked_credentials()
    
    def get_available_space_formatted(self, obj):
        return _format_bytes(obj.available_space)
    
    def get_usage_percentage_formatted(self, obj):
        usage = obj.usage_percentage
        if usage is None:
            return 'N/A'
        return f"{usage:.1f}%"
    
    def get_capacity_formatted(self, obj):
        return _format_bytes(obj.capacity) if obj.capacity else 'Unlimited'
    
    def get_used_space_formatted(self, obj):
        return _format_bytes(obj.used_space)


class RepositoryListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views."""
    
    repo_type_display = serializers.CharField(
        source='get_repo_type_display',
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
    used_space_formatted = serializers.SerializerMethodField()
    usage_percentage_formatted = serializers.SerializerMethodField()
    capacity_formatted = serializers.SerializerMethodField()
    is_ready = serializers.ReadOnlyField()
    # Include config for display
    config = serializers.JSONField(read_only=True)
    # Include masked credentials (access_key visible, secret_key/password masked)
    credentials_masked = serializers.SerializerMethodField()
    
    class Meta:
        model = Repository
        fields = [
            'id', 'name', 'description', 'repo_type', 'repo_type_display',
            'config', 'credentials_masked',
            'bound_node', 'bound_node_name', 'bound_node_status',
            'kopia_initialized', 'status', 'status_display',
            'capacity', 'capacity_formatted', 'used_space', 'used_space_formatted',
            'usage_percentage_formatted', 'snapshot_count',
            'last_backup_at', 'last_connection_test',
            'is_ready', 'created_at', 'updated_at'
        ]
    
    def get_credentials_masked(self, obj):
        """Return credentials with sensitive fields masked."""
        return obj.get_masked_credentials()
    
    def get_used_space_formatted(self, obj):
        return _format_bytes(obj.used_space)
    
    def get_usage_percentage_formatted(self, obj):
        usage = obj.usage_percentage
        if usage is None:
            return 'N/A'
        return f"{usage:.1f}%"
    
    def get_capacity_formatted(self, obj):
        return _format_bytes(obj.capacity) if obj.capacity else 'Unlimited'


class RepositoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating repositories."""
    
    # Encryption password for Kopia repository initialization
    encryption_password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Password for Kopia repository encryption"
    )
    
    class Meta:
        model = Repository
        fields = [
            'name', 'description', 'repo_type', 'config', 'credentials',
            'bound_node', 'capacity', 'encryption_password'
        ]
    
    def validate_name(self, value):
        """Ensure name is unique."""
        if Repository.objects.filter(name=value).exists():
            raise serializers.ValidationError("A repository with this name already exists.")
        return value
    
    def validate(self, data):
        """Validate configuration based on repository type."""
        repo_type = data.get('repo_type')
        config = data.get('config', {})
        credentials = data.get('credentials', {})
        
        if repo_type == Repository.TYPE_S3:
            if 'bucket' not in config:
                raise serializers.ValidationError({
                    'config': 'S3 requires "bucket" in config'
                })
            if 'access_key' not in credentials or 'secret_key' not in credentials:
                raise serializers.ValidationError({
                    'credentials': 'S3 requires "access_key" and "secret_key" in credentials'
                })
        
        elif repo_type == Repository.TYPE_AZURE:
            if 'container' not in config:
                raise serializers.ValidationError({
                    'config': 'Azure requires "container" in config'
                })
        
        elif repo_type == Repository.TYPE_GCS:
            if 'bucket' not in config:
                raise serializers.ValidationError({
                    'config': 'GCS requires "bucket" in config'
                })
        
        elif repo_type == Repository.TYPE_NFS:
            if 'server' not in config or 'export_path' not in config:
                raise serializers.ValidationError({
                    'config': 'NFS requires "server" and "export_path" in config'
                })
        
        elif repo_type == Repository.TYPE_NAS:
            # NAS/NFS/CIFS unified type
            if 'server' not in config or 'export_path' not in config:
                raise serializers.ValidationError({
                    'config': 'NAS requires "server" and "export_path" in config'
                })
            mount_type = config.get('mount_type', 'nfs')
            if mount_type == 'cifs':
                if 'username' not in credentials or 'password' not in credentials:
                    raise serializers.ValidationError({
                        'credentials': 'CIFS mount requires "username" and "password" in credentials'
                    })
        
        elif repo_type == Repository.TYPE_LOCAL:
            if 'path' not in config:
                raise serializers.ValidationError({
                    'config': 'Local requires "path" in config'
                })
        
        return data


class RepositoryUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating repositories."""
    
    class Meta:
        model = Repository
        fields = [
            'name', 'description', 'config', 'credentials',
            'bound_node', 'capacity', 'status'
        ]
    
    def validate_name(self, value):
        """Ensure name is unique (excluding current instance)."""
        instance = self.instance
        if Repository.objects.filter(name=value).exclude(id=instance.id).exists():
            raise serializers.ValidationError("A repository with this name already exists.")
        return value


class RepositoryInitSerializer(serializers.Serializer):
    """Serializer for initializing Kopia repository."""
    
    encryption_password = serializers.CharField(
        required=True,
        help_text="Password for repository encryption"
    )
    confirm_password = serializers.CharField(
        required=True,
        help_text="Confirm encryption password"
    )
    
    def validate(self, data):
        if data['encryption_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        if len(data['encryption_password']) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters.")
        return data


class ConnectionTestSerializer(serializers.Serializer):
    """Serializer for connection test request."""
    pass


class ConnectionTestResultSerializer(serializers.Serializer):
    """Serializer for connection test result."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    details = serializers.DictField(required=False)
