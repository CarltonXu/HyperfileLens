"""
Serializers for System Settings Application
"""

from rest_framework import serializers
from .models import SystemSetting, SMTPConfig, EmailTemplate


class SystemSettingSerializer(serializers.ModelSerializer):
    """Serializer for SystemSetting model."""
    
    class Meta:
        model = SystemSetting
        fields = ['id', 'key', 'value', 'description', 'is_secret', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """Hide secret values in API response."""
        data = super().to_representation(instance)
        if instance.is_secret:
            data['value'] = '********'
        return data


class SMTPConfigSerializer(serializers.ModelSerializer):
    """Serializer for SMTPConfig model."""
    
    class Meta:
        model = SMTPConfig
        fields = [
            'id', 'name', 'host', 'port', 'username', 'password',
            'use_tls', 'use_ssl', 'from_email', 'from_name',
            'is_active', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True}
        }


class SMTPConfigBriefSerializer(serializers.ModelSerializer):
    """Brief serializer for SMTPConfig (without sensitive data)."""
    
    class Meta:
        model = SMTPConfig
        fields = ['id', 'name', 'host', 'port', 'is_active', 'is_default']


class SMTPTestSerializer(serializers.Serializer):
    """Serializer for SMTP connection test."""
    
    to_email = serializers.EmailField(help_text='Email address to send test email')


class EmailTemplateSerializer(serializers.ModelSerializer):
    """Serializer for EmailTemplate model."""
    
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'template_type', 'subject',
            'html_body', 'text_body', 'variables',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
