"""
HyperFileLens Backend - AI Query Serializers
"""

from rest_framework import serializers
from .models import AIProvider, AIQuery, AIFeature


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
    snapshot_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    repository_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    gateway_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    
    class Meta:
        model = AIQuery
        fields = [
            'query_text', 'query_type', 'target_paths', 'file_types',
            'snapshot_id', 'repository_id', 'gateway_id',
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


class AIProviderSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    api_key_masked = serializers.SerializerMethodField()

    class Meta:
        model = AIProvider
        fields = [
            'id', 'name', 'provider_type', 'base_url', 'api_key',
            'api_key_masked', 'default_model', 'timeout_seconds',
            'is_enabled', 'is_default', 'config', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'api_key_masked', 'created_at', 'updated_at']

    def get_api_key_masked(self, obj):
        return obj.get_masked_api_key()

    def validate(self, attrs):
        provider_type = attrs.get('provider_type', getattr(self.instance, 'provider_type', AIProvider.PROVIDER_OPENAI_COMPATIBLE))
        api_key = attrs.get('api_key')
        existing_key = getattr(self.instance, 'api_key', '')
        if provider_type != AIProvider.PROVIDER_LOCAL and not api_key and not existing_key:
            raise serializers.ValidationError({'api_key': 'API key is required for external AI providers.'})
        return attrs

    def update(self, instance, validated_data):
        if 'api_key' in validated_data and not validated_data['api_key']:
            validated_data.pop('api_key')
        return super().update(instance, validated_data)
