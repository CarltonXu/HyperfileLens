"""Serializers for the global alert center."""

from rest_framework import serializers

from .choices import AlertType, PolicyScope, ResourceType
from .models import AlertPolicy, AlertRecord, NotificationChannel, NotificationLog


class AlertPolicySerializer(serializers.ModelSerializer):
    notification_channels = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AlertPolicy
        fields = [
            "id",
            "name",
            "description",
            "type",
            "severity",
            "enabled",
            "resource_type",
            "scope",
            "resource_ids",
            "trigger_rule",
            "recovery_rule",
            "notification_channel_ids",
            "notification_channels",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "notification_channels"]

    def validate(self, attrs):
        data = {**getattr(self.instance, "__dict__", {}), **attrs}
        alert_type = data.get("type")
        scope = data.get("scope", PolicyScope.SELECTED)
        resource_ids = data.get("resource_ids") or []
        resource_type = data.get("resource_type")
        trigger_rule = data.get("trigger_rule") or {}

        if not resource_type:
            raise serializers.ValidationError({"resource_type": "This field is required."})

        if scope == PolicyScope.SELECTED and alert_type != AlertType.EVENT and resource_type != ResourceType.SYSTEM and not resource_ids:
            raise serializers.ValidationError({"resource_ids": "This field is required when scope is selected."})

        required_by_type = {
            AlertType.METRIC: ["metric_key", "operator", "threshold", "duration_seconds", "evaluation_interval_seconds"],
            AlertType.AVAILABILITY: ["check_type", "timeout_seconds", "duration_seconds"],
            AlertType.JOB: ["job_type", "event_type"],
            AlertType.EVENT: ["event_category", "event_types"],
            AlertType.SYSTEM: ["check_type", "duration_seconds"],
        }
        missing = [key for key in required_by_type.get(alert_type, []) if trigger_rule.get(key) in (None, "", [])]
        if missing:
            raise serializers.ValidationError({"trigger_rule": f"Missing required fields: {', '.join(missing)}"})

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        if user and user.is_authenticated:
            validated_data["created_by"] = user.id
        return super().create(validated_data)

    def get_notification_channels(self, obj):
        ids = obj.notification_channel_ids or []
        if not ids:
            return []
        channels = NotificationChannel.objects.filter(id__in=ids)
        return [{"id": str(channel.id), "name": channel.name, "type": channel.type, "enabled": channel.enabled} for channel in channels]


class AlertRecordSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.IntegerField(read_only=True)

    class Meta:
        model = AlertRecord
        fields = [
            "id",
            "policy_id",
            "type",
            "severity",
            "status",
            "resource_type",
            "resource_id",
            "resource_name",
            "title",
            "message",
            "current_value",
            "threshold_value",
            "unit",
            "fingerprint",
            "metadata",
            "first_triggered_at",
            "last_triggered_at",
            "acknowledged_at",
            "acknowledged_by",
            "resolved_at",
            "duration_seconds",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AlertRecordActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True)


class NotificationChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationChannel
        fields = ["id", "name", "type", "enabled", "config", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_config(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Config must be an object.")
        return value

    def update(self, instance, validated_data):
        """
        Handle update with special handling for sensitive fields like passwords.
        If a sensitive field is an empty string in the update, keep the existing value.
        """
        config = validated_data.get('config')
        if config and isinstance(config, dict):
            # Get existing config to preserve sensitive fields
            existing_config = instance.config or {}

            # Sensitive fields that should not be overwritten with empty strings
            sensitive_fields = ['smtp_password', 'token', 'secret', 'authorization', 'api_key']

            # For each sensitive field, if the new value is empty string, keep the old value
            for field in sensitive_fields:
                if config.get(field) == '':
                    if existing_config.get(field):
                        config[field] = existing_config[field]
                # Also remove the field if it's None
                elif config.get(field) is None:
                    if existing_config.get(field):
                        config[field] = existing_config[field]

            validated_data['config'] = config

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        config = dict(data.get("config") or {})
        for key in ["smtp_password", "token", "secret", "authorization", "api_key"]:
            if config.get(key):
                config[key] = "********"
        headers = config.get("headers")
        if isinstance(headers, dict):
            for key in list(headers.keys()):
                if key.lower() in {"authorization", "x-api-key"}:
                    headers[key] = "********"
        data["config"] = config
        return data


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = ["id", "alert_record_id", "channel_id", "status", "error_message", "sent_at"]
        read_only_fields = fields
