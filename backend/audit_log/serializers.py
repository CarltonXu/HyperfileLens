"""
HyperFileLens Backend - Audit Log Serializers
"""

from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model."""
    action_display = serializers.CharField(
        source='get_action_display',
        read_only=True
    )
    user_email = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'timestamp', 'user', 'user_email', 'ip_address',
            'user_agent', 'action', 'action_display', 'resource_type',
            'resource_id', 'changes', 'details', 'result', 'error_message',
            'request_method', 'request_path'
        ]
    
    def get_user_email(self, obj):
        return obj.user.email if obj.user else 'System'


class AuditLogFilterSerializer(serializers.Serializer):
    """Serializer for filtering audit logs."""
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    action = serializers.ChoiceField(choices=AuditLog.ACTION_CHOICES, required=False)
    resource_type = serializers.CharField(required=False)
    user_id = serializers.IntegerField(required=False)
