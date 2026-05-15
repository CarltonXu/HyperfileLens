"""
HyperFileLens Backend - Policies Serializers
"""

from rest_framework import serializers
from .models import BackupPolicy


class BackupPolicySerializer(serializers.ModelSerializer):
    """Serializer for BackupPolicy model."""
    frequency_display = serializers.CharField(
        source='get_frequency_display',
        read_only=True
    )
    backup_type_display = serializers.CharField(
        source='get_backup_type_display',
        read_only=True
    )
    next_run_time = serializers.SerializerMethodField()
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    
    class Meta:
        model = BackupPolicy
        fields = [
            'id', 'name', 'description', 'frequency', 'frequency_display',
            'backup_type', 'backup_type_display', 'schedule_time', 'schedule_day',
            'retention_days', 'retention_snapshots', 'retention_before_backup',
            'policy_scope', 'policy_target', 'snapshot_schedule',
            'retention_policy', 'file_policy', 'compression_policy',
            'advanced_policy',
            'compression_enabled', 'encryption_enabled', 'is_active',
            'user', 'user_email', 'created_at', 'updated_at', 'next_run_time'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_next_run_time(self, obj):
        """Get next scheduled run time."""
        return obj.get_next_run_time()


class BackupPolicyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating backup policies."""
    
    class Meta:
        model = BackupPolicy
        fields = [
            'name', 'description', 'frequency', 'backup_type',
            'schedule_time', 'schedule_day', 'retention_days',
            'retention_snapshots', 'retention_before_backup',
            'policy_scope', 'policy_target', 'snapshot_schedule',
            'retention_policy', 'file_policy', 'compression_policy',
            'advanced_policy',
            'compression_enabled', 'encryption_enabled', 'is_active'
        ]
    
    def validate(self, attrs):
        """Cross-field validation."""
        frequency = attrs.get('frequency')
        
        if frequency in ['weekly'] and attrs.get('schedule_day') is None:
            raise serializers.ValidationError({
                'schedule_day': 'Schedule day is required for weekly backups'
            })
        
        if frequency == 'manual' and not attrs.get('is_active'):
            # Manual policies can be inactive
            pass
        
        return attrs
