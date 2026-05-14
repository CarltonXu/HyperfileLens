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
    task_name = serializers.CharField(source='task.name', read_only=True)
    repository_name = serializers.CharField(source='repository.name', read_only=True)
    
    class Meta:
        model = BackupSnapshot
        fields = [
            'id', 'task', 'task_name', 'name', 'description', 'version',
            'parent_snapshot', 'repository', 'repository_name', 'storage_path',
            'manifest_path', 'total_size', 'file_count',
            'created_at', 'expires_at', 'checksum', 'metadata', 'files'
        ]
        read_only_fields = ['id', 'created_at']


class BackupSnapshotListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for snapshot lists."""
    task_name = serializers.CharField(source='task.name', read_only=True)
    
    class Meta:
        model = BackupSnapshot
        fields = [
            'id', 'task', 'task_name', 'name', 'version', 'total_size', 'file_count',
            'created_at', 'expires_at'
        ]


class BackupTaskSerializer(serializers.ModelSerializer):
    """Serializer for BackupTask model."""
    
    # Source resource info
    source_resource_name = serializers.CharField(
        source='source_resource.name',
        read_only=True
    )
    source_resource_type = serializers.CharField(
        source='source_resource.resource_type',
        read_only=True
    )
    
    # Target repository info
    target_repository_name = serializers.CharField(
        source='target_repository.name',
        read_only=True
    )
    target_repository_type = serializers.CharField(
        source='target_repository.repo_type',
        read_only=True
    )
    
    # Execution node (from source resource)
    execution_node_name = serializers.SerializerMethodField()
    schedule_name = serializers.CharField(source='schedule.name', read_only=True)
    
    # User info
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    
    # Formatted fields
    duration_formatted = serializers.CharField(read_only=True)
    progress_percent = serializers.IntegerField(source='progress', read_only=True)
    
    # Snapshot count
    snapshot_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BackupTask
        fields = [
            'id', 'name', 'description',
            # Source and target
            'source_resource', 'source_resource_name', 'source_resource_type',
            'target_repository', 'target_repository_name', 'target_repository_type',
            'execution_node_name',
            # Task configuration
            'task_type', 'priority', 'is_enabled', 'backup_paths', 'exclude_patterns', 'include_patterns',
            'compression_enabled', 'compression_type', 'encryption_enabled',
            # Scheduling
            'schedule', 'schedule_name', 'next_run_time', 'last_run_time',
            # Status
            'status', 'status_message', 'progress', 'progress_percent', 'error_message',
            # Retention
            'retention_days', 'max_snapshots',
            # User and timestamps
            'user', 'user_email', 'created_at', 'updated_at', 'started_at', 'completed_at',
            # Statistics
            'total_files', 'backed_up_files', 'total_size', 'backed_up_size',
            'skipped_files', 'failed_files', 'bytes_per_second',
            # Execution controls
            'bandwidth_limit_kbps', 'enable_checkpoint', 'checkpoint_interval_minutes',
            'compression_level', 'max_concurrent_files', 'verify_checksum',
            'max_retries', 'retry_count', 'estimated_completion_at', 'parent_task',
            # Formatted
            'duration_formatted', 'snapshot_count',
            # Computed
            'is_running', 'is_completed', 'is_failed'
        ]
        read_only_fields = [
            'id', 'status', 'status_message', 'progress', 'error_message', 'user',
            'created_at', 'updated_at', 'started_at', 'completed_at',
            'total_files', 'backed_up_files', 'total_size', 'backed_up_size',
            'skipped_files', 'failed_files', 'bytes_per_second',
            'retry_count', 'estimated_completion_at', 'parent_task'
        ]
    
    def get_execution_node_name(self, obj):
        """Get the name of the execution node."""
        node = obj.execution_node
        return node.name if node else None
    
    def get_snapshot_count(self, obj):
        """Get the count of snapshots for this task."""
        return obj.snapshots.count()


class BackupTaskListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for task lists."""
    
    source_resource_name = serializers.CharField(source='source_resource.name', read_only=True)
    source_resource_type = serializers.CharField(source='source_resource.resource_type', read_only=True)
    target_repository_name = serializers.CharField(source='target_repository.name', read_only=True)
    target_repository_type = serializers.CharField(source='target_repository.repo_type', read_only=True)
    schedule_name = serializers.CharField(source='schedule.name', read_only=True)
    execution_node_name = serializers.SerializerMethodField()
    duration_formatted = serializers.CharField(read_only=True)
    snapshot_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BackupTask
        fields = [
            'id', 'name', 'description',
            'source_resource', 'source_resource_name',
            'source_resource_type',
            'target_repository', 'target_repository_name',
            'target_repository_type',
            'execution_node_name',
            'schedule', 'schedule_name',
            'task_type', 'priority', 'status', 'progress', 'is_enabled',
            'next_run_time', 'last_run_time',
            'created_at', 'started_at', 'completed_at',
            'duration_formatted',
            'total_files', 'total_size', 'snapshot_count',
            'enable_checkpoint', 'checkpoint_interval_minutes',
            'max_retries', 'retry_count', 'estimated_completion_at'
        ]
    
    def get_execution_node_name(self, obj):
        """Get the name of the execution node."""
        node = obj.execution_node
        return node.name if node else None

    def get_snapshot_count(self, obj):
        return obj.snapshots.count()


class BackupTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating backup tasks."""
    
    class Meta:
        model = BackupTask
        fields = [
            'name', 'description',
            'source_resource', 'target_repository',
            'task_type', 'priority', 'backup_paths', 'exclude_patterns', 'include_patterns',
            'compression_enabled', 'compression_type', 'encryption_enabled',
            'schedule', 'retention_days', 'max_snapshots', 'is_enabled',
            'bandwidth_limit_kbps', 'enable_checkpoint', 'checkpoint_interval_minutes',
            'compression_level', 'max_concurrent_files', 'verify_checksum',
            'max_retries'
        ]
    
    def validate_backup_paths(self, value):
        """Validate that backup_paths is a non-empty list."""
        if not value or not isinstance(value, list):
            raise serializers.ValidationError("Backup paths must be a non-empty list")
        for path in value:
            if not isinstance(path, str) or not path.strip():
                raise serializers.ValidationError("Each path must be a non-empty string")
        return value
    
    def validate(self, attrs):
        """Cross-field validation."""
        # Check that source resource and target repository are different
        source = attrs.get('source_resource')
        target = attrs.get('target_repository')
        
        if source and target:
            # Verify both are accessible
            if source.bound_node is None:
                raise serializers.ValidationError({
                    'source_resource': 'Source resource must have a bound node'
                })
            if target.bound_node is None:
                raise serializers.ValidationError({
                    'target_repository': 'Target repository must have a bound node'
                })
        
        # Check schedule is active if provided
        schedule = attrs.get('schedule')
        if schedule and not schedule.is_active:
            raise serializers.ValidationError({
                'schedule': 'Selected policy is not active'
            })
        
        return attrs


class BackupTaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating backup tasks."""
    
    class Meta:
        model = BackupTask
        fields = [
            'name', 'description',
            'backup_paths', 'exclude_patterns', 'include_patterns',
            'compression_enabled', 'compression_type', 'encryption_enabled',
            'schedule', 'retention_days', 'max_snapshots', 'priority', 'is_enabled',
            'bandwidth_limit_kbps', 'enable_checkpoint', 'checkpoint_interval_minutes',
            'compression_level', 'max_concurrent_files', 'verify_checksum',
            'max_retries'
        ]
    
    def validate_backup_paths(self, value):
        """Validate that backup_paths is a non-empty list."""
        if not value or not isinstance(value, list):
            raise serializers.ValidationError("Backup paths must be a non-empty list")
        return value


class BackupTaskExecuteSerializer(serializers.Serializer):
    """Serializer for executing backup tasks."""
    force = serializers.BooleanField(
        default=False,
        help_text="Force execution even if a task is already running"
    )
    task_type = serializers.ChoiceField(
        choices=BackupTask.TYPE_CHOICES,
        required=False,
        default=BackupTask.TYPE_INCREMENTAL,
        help_text="Override task type for this execution"
    )
    repository_password = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text="Optional Kopia repository password for this execution"
    )


class BackupTaskCancelSerializer(serializers.Serializer):
    """Serializer for canceling backup tasks."""
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Reason for cancellation"
    )


class BackupTaskStatisticsSerializer(serializers.Serializer):
    """Serializer for backup task statistics."""
    total_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    running_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    failed_tasks = serializers.IntegerField()
    cancelled_tasks = serializers.IntegerField()
    total_size = serializers.IntegerField()
    total_files = serializers.IntegerField()
    avg_duration = serializers.FloatField(allow_null=True)
