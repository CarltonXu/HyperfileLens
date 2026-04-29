"""
License Serializers for HyperFileLens
"""

from rest_framework import serializers
from .models import License, LicenseAuditLog, QuotaUsage


class LicenseSerializer(serializers.ModelSerializer):
    """Serializer for License model."""
    
    is_valid = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    is_perpetual = serializers.ReadOnlyField()
    machine_bound = serializers.ReadOnlyField()
    
    class Meta:
        model = License
        fields = [
            'id', 'license_key', 'licensee_name', 'licensee_email',
            'licensee_company', 'product', 'edition', 'version',
            'issued_at', 'starts_at', 'expires_at', 'activated_at',
            'max_tenants', 'max_users_per_tenant', 'max_proxies_per_tenant',
            'max_repositories_per_tenant', 'max_storage_gb',
            'features', 'status',
            'is_valid', 'days_until_expiry', 'is_perpetual',
            'machine_fingerprint', 'machine_bound',
        ]
        read_only_fields = [
            'id', 'license_key', 'issued_at',
            'signature', 'checksum', 'original_data',
        ]


class LicenseImportSerializer(serializers.Serializer):
    """Serializer for license import."""
    
    encoded_license = serializers.CharField(
        required=False,
        help_text='Encoded license string from license file'
    )
    license_data = serializers.DictField(
        required=False,
        help_text='License data (alternative to encoded_license)'
    )
    signature = serializers.CharField(
        required=False,
        help_text='License signature (required if license_data provided)'
    )
    
    def validate(self, attrs):
        if not attrs.get('encoded_license') and not attrs.get('license_data'):
            raise serializers.ValidationError("Either encoded_license or license_data is required")
        if attrs.get('license_data') and not attrs.get('signature'):
            raise serializers.ValidationError("signature is required when using license_data")
        return attrs


class LicenseStatusSerializer(serializers.Serializer):
    """Serializer for comprehensive license status."""
    
    is_valid = serializers.BooleanField()
    license_key = serializers.CharField()
    edition = serializers.CharField()
    licensee_name = serializers.CharField()
    licensee_email = serializers.EmailField()
    days_until_expiry = serializers.IntegerField()
    is_perpetual = serializers.BooleanField()
    
    features = serializers.DictField()
    limits = serializers.DictField()
    usage = serializers.DictField()
    
    warnings = serializers.ListField(child=serializers.CharField())
    
    def __init__(self, *args, **kwargs):
        data = kwargs.get('data', args[0] if args else {})
        
        if isinstance(data, dict) and 'license' in data:
            license = data['license']
            quota = data.get('quota')
            
            status_data = {
                'is_valid': license.is_valid,
                'license_key': license.license_key,
                'edition': license.edition,
                'licensee_name': license.licensee_name,
                'licensee_email': license.licensee_email,
                'days_until_expiry': license.days_until_expiry,
                'is_perpetual': license.is_perpetual,
                'features': license.features,
                'limits': license.get_limits(),
                'usage': quota.check_limits() if quota else {},
                'warnings': self._get_warnings(license),
            }
            
            kwargs['data'] = status_data
        
        super().__init__(*args, **kwargs)
    
    def _get_warnings(self, license):
        """Get license warnings."""
        warnings = []
        
        if license.days_until_expiry >= 0 and license.days_until_expiry <= 30:
            warnings.append(f'License expires in {license.days_until_expiry} days')
        
        if license.machine_fingerprint:
            warnings.append('License is bound to specific hardware')
        
        return warnings


class QuotaUsageSerializer(serializers.ModelSerializer):
    """Serializer for QuotaUsage model."""
    
    limits = serializers.SerializerMethodField()
    utilization = serializers.SerializerMethodField()
    
    class Meta:
        model = QuotaUsage
        fields = [
            'tenants_count', 'total_users', 'total_proxies',
            'total_repositories', 'storage_used_gb',
            'last_synced', 'limits', 'utilization',
        ]
    
    def get_limits(self, obj):
        """Get license limits."""
        return obj.license.get_limits()
    
    def get_utilization(self, obj):
        """Calculate utilization percentages."""
        limits = obj.license.get_limits()
        return {
            'tenants': round(obj.tenants_count / limits['max_tenants'] * 100, 1) if limits['max_tenants'] > 0 else 0,
            'users': round(obj.total_users / limits['max_users_per_tenant'] * 100, 1) if limits['max_users_per_tenant'] > 0 else 0,
            'proxies': round(obj.total_proxies / limits['max_proxies_per_tenant'] * 100, 1) if limits['max_proxies_per_tenant'] > 0 else 0,
            'repositories': round(obj.total_repositories / limits['max_repositories_per_tenant'] * 100, 1) if limits['max_repositories_per_tenant'] > 0 else 0,
            'storage': round(obj.storage_used_gb / limits['max_storage_gb'] * 100, 1) if limits['max_storage_gb'] > 0 else 0,
        }


class LicenseAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for LicenseAuditLog model."""
    
    class Meta:
        model = LicenseAuditLog
        fields = [
            'id', 'action', 'details', 'ip_address',
            'user_agent', 'created_at',
        ]
