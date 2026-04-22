"""
HyperFileLens Backend - Recovery Tasks Serializers
"""

from rest_framework import serializers
from .models import RecoveryTask


class RecoveryTaskSerializer(serializers.ModelSerializer):
    """Serializer for RecoveryTask model."""
    snapshot_name = serializers.CharField(
        source='snapshot.name',
        read_only=True
    )
    target_node_name = serializers.CharField(
        source='target_node.name',
        read_only=True
    )
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    
    class Meta:
        model = RecoveryTask
        fields = [
            'id', 'name', 'description', 'snapshot', 'snapshot_name',
            'target_node', 'target_node_name', 'recovery_type',
            'target_path', 'file_patterns', 'exclude_patterns',
            'status', 'progress', 'error_message', 'user', 'user_email',
            'created_at', 'updated_at', 'started_at', 'completed_at',
            'total_files', 'restored_files', 'total_size', 'restored_size',
            'skipped_files', 'failed_files'
        ]
        read_only_fields = [
            'id', 'status', 'progress', 'error_message', 'user',
            'created_at', 'updated_at', 'started_at', 'completed_at'
        ]


class RecoveryTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating recovery tasks."""
    
    class Meta:
        model = RecoveryTask
        fields = [
            'name', 'description', 'snapshot', 'target_node',
            'recovery_type', 'target_path', 'file_patterns', 'exclude_patterns'
        ]
    
    def validate_snapshot(self, value):
        """Validate that snapshot exists."""
        if not value:
            raise serializers.ValidationError("Snapshot is required")
        return value
    
    def validate(self, attrs):
        """Cross-field validation."""
        if attrs.get('recovery_type') == 'new_location' and not attrs.get('target_path'):
            raise serializers.ValidationError({
                'target_path': 'Target path is required for new location recovery'
            })
        return attrs
