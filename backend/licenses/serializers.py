"""
License Serializers for HyperFileLens
"""

from rest_framework import serializers
from .models import License, LicenseHistory, MachineCode, QuotaUsage


class LicenseSerializer(serializers.ModelSerializer):
    """Serializer for License model."""
    
    tenant_name = serializers.SerializerMethodField()
    
    class Meta:
        model = License
        fields = [
            'id', 'license_key', 'version', 'change_type', 'change_reason',
            'machine_code', 'tenant', 'tenant_name',
            'max_tenants', 'max_users', 'max_proxies', 'max_storage_gb',
            'max_gateways', 'ai_insights_quota',
            'max_backup_tasks', 'max_recovery_tasks', 'max_source_resources',
            'max_policies', 'max_repositories',
            'issued_at', 'expires_at', 'activated_at', 'updated_at',
            'status', 'is_valid', 'is_expired', 'is_perpetual', 'days_until_expiry',
            'verification_status', 'verification_message', 'payload_hash',
            'last_verified_at', 'highest_seen_version',
        ]
        read_only_fields = [
            'id', 'license_key', 'version', 'change_type', 'change_reason',
            'machine_code', 'tenant', 'tenant_name',
            'issued_at', 'activated_at', 'updated_at',
        ]
    
    def get_tenant_name(self, obj):
        return obj.tenant.name if obj.tenant else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.update(instance.get_limits())
        return data


class LicenseHistorySerializer(serializers.ModelSerializer):
    """Serializer for License history (audit)."""
    
    is_perpetual = serializers.SerializerMethodField()
    limits = serializers.SerializerMethodField()
    
    class Meta:
        model = LicenseHistory
        fields = [
            'id', 'license_key', 'version',
            'machine_code', 'tenant',
            'limits',
            'max_tenants', 'max_users', 'max_proxies', 'max_storage_gb',
            'max_gateways', 'ai_insights_quota',
            'max_backup_tasks', 'max_recovery_tasks', 'max_source_resources',
            'max_policies', 'max_repositories',
            'issued_at', 'expires_at', 'activated_at', 'archived_at',
            'status', 'is_perpetual', 'change_type', 'change_reason',
        ]
        read_only_fields = fields
    
    def get_is_perpetual(self, obj):
        """Check if the license was perpetual."""
        return obj.expires_at is None
    
    def get_limits(self, obj):
        """Return limits as a nested object."""
        return {
            'max_tenants': obj.max_tenants,
            'max_users': obj.max_users,
            'max_proxies': obj.max_proxies,
            'max_storage_gb': obj.max_storage_gb,
            'max_gateways': obj.max_gateways,
            'ai_insights_quota': obj.ai_insights_quota,
            'max_backup_tasks': obj.max_backup_tasks,
            'max_recovery_tasks': obj.max_recovery_tasks,
            'max_source_resources': obj.max_source_resources,
            'max_policies': obj.max_policies,
            'max_repositories': obj.max_repositories,
        }


class MachineCodeSerializer(serializers.ModelSerializer):
    """Serializer for MachineCode model."""
    
    class Meta:
        model = MachineCode
        fields = [
            'id', 'code', 'tenant', 'user',
            'mac_address', 'cpu_id', 'hostname',
            'created_at',
        ]
        read_only_fields = fields


class QuotaUsageSerializer(serializers.ModelSerializer):
    """Serializer for QuotaUsage model."""
    
    class Meta:
        model = QuotaUsage
        fields = [
            'users_count', 'proxies_count', 'gateways_count',
            'backup_tasks_count', 'recovery_tasks_count',
            'source_resources_count', 'policies_count', 'repositories_count',
            'storage_used_gb', 'ai_insights_used', 'ai_reset_date',
            'last_updated',
        ]
        read_only_fields = fields


class LicenseLimitsSerializer(serializers.Serializer):
    """Serializer for license limits (for validation)."""
    
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
