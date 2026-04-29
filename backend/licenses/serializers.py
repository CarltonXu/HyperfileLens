"""
License Serializers for HyperFileLens
"""

from rest_framework import serializers
from .models import License, MachineCode, QuotaUsage, LicenseAuditLog


class LicenseSerializer(serializers.ModelSerializer):
    """Serializer for License model."""
    
    is_valid = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    is_perpetual = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    activated_by_name = serializers.CharField(source='activated_by.username', read_only=True)
    
    class Meta:
        model = License
        fields = [
            'id', 'license_key', 'machine_code',
            'tenant', 'tenant_name', 'activated_by', 'activated_by_name',
            'max_tenants', 'max_users', 'max_proxies', 'max_storage_gb',
            'max_gateways', 'ai_insights_quota',
            'max_backup_tasks', 'max_recovery_tasks',
            'max_source_resources', 'max_policies', 'max_repositories',
            'issued_at', 'expires_at', 'activated_at',
            'status', 'is_valid', 'is_expired', 'is_perpetual', 'days_until_expiry',
        ]
        read_only_fields = [
            'id', 'license_key', 'machine_code',
            'tenant', 'activated_by',
            'issued_at', 'activated_at', 'signature'
        ]


class LicenseLimitsSerializer(serializers.Serializer):
    """Serializer for license limits."""
    
    max_tenants = serializers.IntegerField()
    max_users = serializers.IntegerField()
    max_proxies = serializers.IntegerField()
    max_storage_gb = serializers.IntegerField()
    max_gateways = serializers.IntegerField()
    ai_insights_quota = serializers.IntegerField()
    max_backup_tasks = serializers.IntegerField()
    max_recovery_tasks = serializers.IntegerField()
    max_source_resources = serializers.IntegerField()
    max_policies = serializers.IntegerField()
    max_repositories = serializers.IntegerField()


class MachineCodeSerializer(serializers.ModelSerializer):
    """Serializer for MachineCode model."""
    
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    is_used = serializers.SerializerMethodField()
    
    class Meta:
        model = MachineCode
        fields = [
            'id', 'code', 'tenant', 'tenant_name', 'user', 'user_name',
            'mac_address', 'cpu_id', 'hostname',
            'created_at', 'used_at', 'is_used'
        ]
        read_only_fields = ['id', 'code', 'created_at', 'used_at']
    
    def get_is_used(self, obj):
        return obj.used_at is not None


class QuotaUsageSerializer(serializers.ModelSerializer):
    """Serializer for QuotaUsage model."""
    
    class Meta:
        model = QuotaUsage
        fields = [
            'users_count', 'proxies_count', 'storage_used_gb',
            'gateways_count', 'backup_tasks_count', 'recovery_tasks_count',
            'source_resources_count', 'policies_count', 'repositories_count',
            'ai_insights_used', 'ai_insights_period', 'ai_insights_reset_at',
            'updated_at'
        ]


class ActivationSerializer(serializers.Serializer):
    """Serializer for activation request."""
    
    activation_code = serializers.CharField(
        max_length=1024,
        help_text='Activation code from sales team'
    )


class LicenseStatusSerializer(serializers.Serializer):
    """Serializer for license status response."""
    
    is_valid = serializers.BooleanField()
    license = LicenseSerializer(required=False)
    limits = LicenseLimitsSerializer(required=False)
    usage = QuotaUsageSerializer(required=False)
    days_until_expiry = serializers.IntegerField(required=False)
    is_perpetual = serializers.BooleanField(required=False)
    message = serializers.CharField(required=False)


class LicenseAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for LicenseAuditLog model."""
    
    license_key = serializers.CharField(source='license.license_key', read_only=True)
    
    class Meta:
        model = LicenseAuditLog
        fields = [
            'id', 'license', 'license_key', 'action',
            'details', 'ip_address', 'created_at'
        ]
