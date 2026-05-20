"""
HyperFileLens Backend - Recovery Tasks Serializers
"""

from rest_framework import serializers
from .models import RecoveryExport, RecoveryRun, RecoveryTask
from backup_tasks.models import BackupSnapshot
from nodes.models import Node


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
    target_node_status = serializers.CharField(
        source='target_node.status',
        read_only=True
    )
    repository_name = serializers.CharField(
        source='snapshot.repository.name',
        read_only=True
    )
    repository_id = serializers.UUIDField(
        source='snapshot.repository.id',
        read_only=True
    )
    backup_task_name = serializers.CharField(
        source='snapshot.task.name',
        read_only=True
    )
    snapshot_storage_path = serializers.CharField(
        source='snapshot.storage_path',
        read_only=True
    )
    snapshot_manifest_path = serializers.CharField(
        source='snapshot.manifest_path',
        read_only=True
    )
    snapshot_status = serializers.CharField(
        source='snapshot.snapshot_status',
        read_only=True
    )
    snapshot_size = serializers.IntegerField(
        source='snapshot.total_size',
        read_only=True
    )
    snapshot_file_count = serializers.IntegerField(
        source='snapshot.file_count',
        read_only=True
    )
    snapshot_created_at = serializers.DateTimeField(
        source='snapshot.created_at',
        read_only=True
    )
    snapshot_source_path = serializers.SerializerMethodField()
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    
    class Meta:
        model = RecoveryTask
        fields = [
            'id', 'name', 'description', 'snapshot', 'snapshot_name',
            'target_node', 'target_node_name', 'target_node_status',
            'repository_id', 'repository_name', 'backup_task_name', 'snapshot_storage_path',
            'snapshot_manifest_path', 'snapshot_status', 'snapshot_size',
            'snapshot_file_count', 'snapshot_created_at', 'snapshot_source_path',
            'recovery_type',
            'target_path', 'restore_scope', 'selected_paths',
            'conflict_policy', 'priority', 'file_patterns',
            'exclude_patterns', 'options', 'proxy_task',
            'status', 'progress', 'status_message', 'error_message',
            'current_file', 'speed_mbps', 'eta', 'user', 'user_email',
            'created_at', 'updated_at', 'started_at', 'completed_at',
            'total_files', 'restored_files', 'total_size', 'restored_size',
            'skipped_files', 'failed_files', 'metadata'
        ]
        read_only_fields = [
            'id', 'status', 'progress', 'error_message', 'user',
            'status_message', 'current_file', 'speed_mbps', 'eta',
            'proxy_task', 'created_at', 'updated_at', 'started_at',
            'completed_at'
        ]

    def get_snapshot_source_path(self, obj):
        metadata = getattr(obj.snapshot, 'metadata', None) or {}
        return metadata.get('source_path') or metadata.get('kopia_source_path') or ''


class RecoveryRunSerializer(serializers.ModelSerializer):
    """Serializer for individual recovery execution attempts."""
    task_name = serializers.CharField(source='task.name', read_only=True)
    snapshot_name = serializers.CharField(source='snapshot.name', read_only=True)
    target_node_name = serializers.CharField(source='target_node.name', read_only=True)
    proxy_task_status = serializers.CharField(source='proxy_task.status', read_only=True)

    class Meta:
        model = RecoveryRun
        fields = [
            'id', 'task', 'task_name', 'proxy_task', 'proxy_task_status',
            'snapshot', 'snapshot_name', 'target_node', 'target_node_name',
            'trigger_type', 'status', 'progress', 'message', 'error_message',
            'parameters', 'result', 'current_file', 'total_files',
            'restored_files', 'total_size', 'restored_size', 'skipped_files',
            'failed_files', 'speed_mbps', 'eta', 'created_at',
            'dispatched_at', 'started_at', 'completed_at', 'duration',
        ]
        read_only_fields = fields


class RecoveryTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating recovery tasks."""
    snapshot_id = serializers.PrimaryKeyRelatedField(
        queryset=BackupSnapshot.objects.all(),
        source='snapshot',
        write_only=True,
        required=False
    )
    node = serializers.PrimaryKeyRelatedField(
        queryset=Node.objects.all(),
        source='target_node',
        write_only=True,
        required=False
    )
    repository = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = RecoveryTask
        fields = [
            'name', 'description', 'snapshot', 'snapshot_id',
            'target_node', 'node', 'repository', 'recovery_type',
            'target_path', 'restore_scope', 'selected_paths',
            'conflict_policy', 'priority', 'file_patterns',
            'exclude_patterns', 'options', 'metadata'
        ]
        extra_kwargs = {
            'snapshot': {'required': False},
            'target_node': {'required': False},
        }
    
    def validate_snapshot(self, value):
        """Validate that snapshot exists."""
        if not value:
            raise serializers.ValidationError("Snapshot is required")
        return value
    
    def validate(self, attrs):
        """Cross-field validation."""
        attrs.pop('repository', None)
        if not attrs.get('snapshot'):
            raise serializers.ValidationError({'snapshot': 'Snapshot is required'})
        if not attrs.get('target_node'):
            raise serializers.ValidationError({'target_node': 'Target node is required'})
        snapshot = attrs.get('snapshot')
        if snapshot and snapshot.snapshot_status != BackupSnapshot.STATUS_AVAILABLE:
            raise serializers.ValidationError({
                'snapshot': 'Only available snapshots can be restored'
            })
        if attrs.get('recovery_type') == 'new_location' and not attrs.get('target_path'):
            raise serializers.ValidationError({
                'target_path': 'Target path is required for new location recovery'
            })
        if attrs.get('restore_scope') == RecoveryTask.SCOPE_SELECTED_PATHS and not attrs.get('selected_paths'):
            raise serializers.ValidationError({
                'selected_paths': 'Selected paths are required for granular recovery'
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('repository', None)
        return super().create(validated_data)


class RecoveryExportSerializer(serializers.ModelSerializer):
    """Serializer for downloadable recovery exports."""

    snapshot_name = serializers.CharField(source='snapshot.name', read_only=True)
    snapshot_storage_path = serializers.CharField(source='snapshot.storage_path', read_only=True)
    snapshot_manifest_path = serializers.CharField(source='snapshot.manifest_path', read_only=True)
    snapshot_status = serializers.CharField(source='snapshot.snapshot_status', read_only=True)
    snapshot_created_at = serializers.DateTimeField(source='snapshot.created_at', read_only=True)
    snapshot_source_path = serializers.SerializerMethodField()
    repository_name = serializers.CharField(source='repository.name', read_only=True)
    executor_node_name = serializers.CharField(source='executor_node.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    download_url = serializers.SerializerMethodField()
    share_url = serializers.SerializerMethodField()
    has_share_password = serializers.SerializerMethodField()
    is_downloadable = serializers.BooleanField(read_only=True)

    class Meta:
        model = RecoveryExport
        fields = [
            'id', 'name', 'description', 'snapshot', 'snapshot_name',
            'snapshot_storage_path', 'snapshot_manifest_path', 'snapshot_status',
            'snapshot_created_at', 'snapshot_source_path', 'repository',
            'repository_name', 'selected_paths', 'package_format', 'status',
            'progress', 'status_message', 'error_message', 'current_file',
            'total_files', 'processed_files', 'total_size', 'processed_size',
            'speed_mbps', 'eta', 'package_size', 'checksum', 'file_name', 'executor_node',
            'executor_node_name', 'proxy_task', 'user', 'user_email',
            'download_count', 'last_downloaded_at', 'share_enabled',
            'share_token', 'share_expires_at', 'share_url',
            'has_share_password', 'metadata', 'expires_at', 'created_at',
            'updated_at', 'started_at', 'completed_at', 'download_url',
            'is_downloadable',
        ]
        read_only_fields = [
            'id', 'repository', 'status', 'progress', 'status_message',
            'error_message', 'current_file', 'total_files', 'processed_files',
            'total_size', 'processed_size', 'speed_mbps', 'eta', 'package_size', 'checksum',
            'file_name', 'executor_node', 'proxy_task', 'user', 'metadata',
            'download_count', 'last_downloaded_at', 'share_token',
            'created_at', 'updated_at', 'started_at', 'completed_at',
        ]

    def get_snapshot_source_path(self, obj):
        metadata = getattr(obj.snapshot, 'metadata', None) or {}
        return metadata.get('source_path') or metadata.get('kopia_source_path') or ''

    def get_download_url(self, obj):
        if not obj.is_downloadable:
            return ''
        request = self.context.get('request')
        url = f'/api/v1/recovery-tasks/exports/{obj.id}/download/'
        return request.build_absolute_uri(url) if request else url

    def get_share_url(self, obj):
        if not obj.share_enabled or not obj.share_token:
            return ''
        request = self.context.get('request')
        url = f'/shared/recovery-export/{obj.id}?token={obj.share_token}'
        return request.build_absolute_uri(url) if request else url

    def get_has_share_password(self, obj):
        return bool(obj.share_password_hash)


class RecoveryExportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating downloadable recovery exports."""

    snapshot_id = serializers.PrimaryKeyRelatedField(
        queryset=BackupSnapshot.objects.all(),
        source='snapshot',
        write_only=True,
    )
    expires_in_hours = serializers.IntegerField(write_only=True, required=False, min_value=1, max_value=168)

    class Meta:
        model = RecoveryExport
        fields = [
            'name', 'description', 'snapshot_id', 'selected_paths',
            'package_format', 'expires_in_hours',
        ]

    def validate(self, attrs):
        snapshot = attrs.get('snapshot')
        if snapshot and snapshot.snapshot_status != BackupSnapshot.STATUS_AVAILABLE:
            raise serializers.ValidationError({
                'snapshot_id': 'Only available snapshots can be exported'
            })
        if not attrs.get('selected_paths'):
            raise serializers.ValidationError({
                'selected_paths': 'Select at least one file or folder to export'
            })
        if attrs.get('package_format') and attrs['package_format'] != RecoveryExport.FORMAT_ZIP:
            raise serializers.ValidationError({
                'package_format': 'Only ZIP export is currently supported'
            })
        return attrs
