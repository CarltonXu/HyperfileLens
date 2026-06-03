"""
Serializers for System Settings Application
"""

from rest_framework import serializers
from .models import SMTPConfig, EmailTemplate


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
            'username': {'required': False, 'allow_blank': True},
            'password': {'required': False, 'allow_blank': True},
            'from_name': {'required': False, 'allow_blank': True},
        }


class SMTPConfigBriefSerializer(serializers.ModelSerializer):
    """Brief serializer for SMTPConfig."""
    
    class Meta:
        model = SMTPConfig
        fields = [
            'id', 'name', 'host', 'port', 'username', 'password',
            'use_tls', 'use_ssl', 'from_email', 'from_name',
            'is_active', 'is_default'
        ]


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
