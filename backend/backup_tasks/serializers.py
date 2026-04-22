"""
HyperFileLens Backend - Backup Tasks Serializers

This module provides serializers for the backup tasks API.
"""

from rest_framework import serializers
from .models import BackupTask, BackupSnapshot, BackupFile


class BackupFileSerializer(serializers.ModelSerializer):
    """Serializer for BackupFile model."""
    
    class Meta:
        model = BackupFile
        fields = [
            'id', 'snapshot', 'original_path', 'relative_path',
            'file_name', 'size', 'checksum', 'mime_type', 'status',
            'backed_up_at', 'modified_at'
        ]
        read_only_fields = ['id', 'backed_up_at']


class BackupSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for BackupSnapshot model."""
    files = BackupFileSerializer(many=True, read_only=True)
    
    class Meta:
        model = BackupSnapshot
        fields = [
            'id', 'task', 'name', 'description', 'version',
            'parent_snapshot', 'repository', 'storage_path',
            'manifest_path', 'total_size', 'file_count',
            'created_at', 'expires_at', 'checksum', 'metadata', 'files'
        ]
        read_only_fields = ['id', 'created_at']


class BackupSnapshotListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for snapshot lists."""
    
    class Meta:
        model = BackupSnapshot
        fields = [
            'id', 'name', 'version', 'total_size', 'file_count',
            'created_at', 'expires_at'
        ]


class BackupTaskSerializer(serializers.ModelSerializer):
    """Serializer for BackupTask model."""
    source_node_name = serializers.CharField(
        source='source_node.name',
        read_only=True
    )
    target_repository_name = serializers.CharField(
        source='target_repository.name',
        read_only=True
    )
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = BackupTask
        fields = [
            'id', 'name', 'description', 'source_node', 'source_node_name',
            'target_repository', 'target_repository_name', 'task_type',
            'paths', 'exclude_patterns', 'compression_enabled',
            'encryption_enabled', 'schedule', 'next_run_time',
            'status', 'progress', 'error_message', 'retention_days',
            'max_snapshots', 'user', 'user_email', 'created_at',
            'updated_at', 'started_at', 'completed_at', 'duration_formatted',
            'total_files', 'backed_up_files', 'total_size', 'backed_up_size',
            'skipped_files', 'failed_files'
        ]
        read_only_fields = [
            'id', 'status', 'progress', 'error_message', 'user',
            'created_at', 'updated_at', 'started_at', 'completed_at',
            'total_files', 'backed_up_files', 'total_size', 'backed_up_size',
            'skipped_files', 'failed_files'
        ]
    
    def get_duration_formatted(self, obj):
        """Format duration in human-readable format."""
        duration = obj.duration
        if duration is None:
            return None
        
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


class BackupTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating backup tasks."""
    
    class Meta:
        model = BackupTask
        fields = [
            'name', 'description', 'source_node', 'target_repository',
            'task_type', 'paths', 'exclude_patterns', 'compression_enabled',
            'encryption_enabled', 'schedule', 'retention_days', 'max_snapshots'
        ]
    
    def validate_paths(self, value):
        """Validate that paths is a non-empty list."""
        if not value or not isinstance(value, list):
            raise serializers.ValidationError("Paths must be a non-empty list")
        return value
    
    def validate(self, attrs):
        """Cross-field validation."""
        if attrs.get('schedule') and not attrs['schedule'].is_active:
            raise serializers.ValidationError({
                'schedule': 'Selected policy is not active'
            })
        return attrs


class BackupTaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating backup tasks."""
    
    class Meta:
        model = BackupTask
        fields = [
            'name', 'description', 'paths', 'exclude_patterns',
            'compression_enabled', 'encryption_enabled', 'schedule',
            'retention_days', 'max_snapshots'
        ]


class BackupTaskExecuteSerializer(serializers.Serializer):
    """Serializer for executing backup tasks."""
    force = serializers.BooleanField(
        default=False,
        help_text="Force execution even if a task is already running"
    )
