"""
HyperFileLens Backend - Repository Serializers
"""

from rest_framework import serializers
from .models import Repository


class RepositorySerializer(serializers.ModelSerializer):
    """Serializer for Repository model."""
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    repo_type_display = serializers.CharField(
        source='get_repo_type_display',
        read_only=True
    )
    available_space_formatted = serializers.SerializerMethodField()
    usage_percentage_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Repository
        fields = [
            'id', 'name', 'description', 'repo_type', 'repo_type_display',
            'config', 'path', 'capacity', 'used_space', 'available_space_formatted',
            'usage_percentage_formatted', 'status', 'last_sync_at',
            'supports_compression', 'supports_encryption', 'is_readonly',
            'user', 'user_email', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'used_space', 'status', 'last_sync_at', 'user', 'created_at', 'updated_at'
        ]
    
    def get_available_space_formatted(self, obj):
        available = obj.available_space
        if available is None:
            return 'Unlimited'
        return _format_bytes(available)
    
    def get_usage_percentage_formatted(self, obj):
        usage = obj.usage_percentage
        if usage is None:
            return 'N/A'
        return f"{usage:.1f}%"


class RepositoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating repositories."""
    
    class Meta:
        model = Repository
        fields = [
            'name', 'description', 'repo_type', 'config', 'path',
            'capacity', 'supports_compression', 'supports_encryption', 'is_readonly'
        ]
    
    def validate_config(self, value):
        """Validate repository configuration."""
        repo_type = self.initial_data.get('repo_type')
        
        if repo_type in ['s3', 'azure', 'gcs']:
            # Require credentials for cloud storage
            if 'credentials' not in value:
                raise serializers.ValidationError("Credentials are required for cloud storage")
        
        return value


class RepositoryUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating repositories."""
    
    class Meta:
        model = Repository
        fields = [
            'name', 'description', 'config', 'path', 'capacity',
            'supports_compression', 'supports_encryption', 'is_readonly'
        ]


def _format_bytes(bytes_value):
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"
