from rest_framework import serializers

from .models import SnapshotAIJob, SnapshotFileIndex, SnapshotIndexJob, SnapshotInsight


class SnapshotIndexJobSerializer(serializers.ModelSerializer):
    snapshot_name = serializers.CharField(source='snapshot.name', read_only=True)
    gateway_name = serializers.CharField(source='gateway.name', read_only=True)

    class Meta:
        model = SnapshotIndexJob
        fields = [
            'id', 'snapshot', 'snapshot_name', 'gateway', 'gateway_name',
            'status', 'progress', 'total_files', 'indexed_files',
            'total_bytes', 'indexed_bytes', 'current_path', 'error_message',
            'task_id', 'metadata', 'started_at', 'completed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class SnapshotFileIndexSerializer(serializers.ModelSerializer):
    class Meta:
        model = SnapshotFileIndex
        fields = [
            'id', 'snapshot', 'path', 'name', 'extension', 'category',
            'size', 'modified_time', 'is_directory', 'depth',
            'content_hash', 'metadata', 'indexed_at',
        ]
        read_only_fields = fields


class SnapshotInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = SnapshotInsight
        fields = [
            'id', 'snapshot', 'insight_type', 'severity', 'title',
            'summary', 'evidence', 'related_paths', 'recommended_actions',
            'generated_by', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class SnapshotAIJobSerializer(serializers.ModelSerializer):
    snapshot_name = serializers.CharField(source='snapshot.name', read_only=True)
    gateway_name = serializers.CharField(source='gateway.name', read_only=True)

    class Meta:
        model = SnapshotAIJob
        fields = [
            'id', 'snapshot', 'snapshot_name', 'gateway', 'gateway_name',
            'job_type', 'status', 'progress', 'query', 'provider', 'model',
            'language', 'result', 'error_message', 'task_id',
            'started_at', 'completed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = fields
