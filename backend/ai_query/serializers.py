"""
HyperFileLens Backend - AI Query Serializers
"""

from rest_framework import serializers
from .models import AIQuery, AIFeature


class AIQuerySerializer(serializers.ModelSerializer):
    """Serializer for AIQuery model."""
    query_type_display = serializers.CharField(
        source='get_query_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = AIQuery
        fields = [
            'id', 'query_text', 'query_type', 'query_type_display',
            'target_paths', 'file_types', 'status', 'status_display',
            'result', 'error_message', 'model_used', 'tokens_used',
            'user', 'user_email', 'created_at', 'completed_at', 'duration_formatted'
        ]
        read_only_fields = [
            'id', 'status', 'result', 'error_message', 'model_used',
            'tokens_used', 'user', 'created_at', 'completed_at'
        ]
    
    def get_duration_formatted(self, obj):
        duration = obj.duration
        if duration is None:
            return None
        return f"{duration:.2f}s"


class AIQueryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating AI queries."""
    
    class Meta:
        model = AIQuery
        fields = [
            'query_text', 'query_type', 'target_paths', 'file_types'
        ]


class AIQueryResultSerializer(serializers.Serializer):
    """Serializer for AI query results."""
    results = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of matching results"
    )
    summary = serializers.CharField(
        help_text="Summary of results"
    )
    suggestions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Follow-up suggestions"
    )
