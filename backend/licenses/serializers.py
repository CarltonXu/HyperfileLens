"""
Serializers for Licenses API
"""

from rest_framework import serializers
from .models import License, LicenseAuditLog


class LicenseSerializer(serializers.ModelSerializer):
    """
    Serializer for License model.
    """

    is_valid = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    is_perpetual = serializers.ReadOnlyField()

    class Meta:
        model = License
        fields = [
            'id', 'license_key', 'licensee_name', 'licensee_email', 'licensee_company',
            'product', 'edition', 'version',
            'issued_at', 'starts_at', 'expires_at',
            'max_tenants', 'max_users_per_tenant', 'max_proxies_per_tenant',
            'max_repositories_per_tenant', 'max_storage_gb',
            'features', 'modules', 'status',
            'is_valid', 'days_until_expiry', 'is_perpetual',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'issued_at', 'created_at', 'updated_at']


class LicenseListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing licenses.
    """

    is_valid = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()

    class Meta:
        model = License
        fields = [
            'id', 'license_key', 'licensee_name', 'edition',
            'status', 'expires_at', 'is_valid', 'days_until_expiry',
            'created_at'
        ]


class LicenseDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for license with all information.
    """

    is_valid = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    is_perpetual = serializers.ReadOnlyField()
    limits = serializers.SerializerMethodField()

    class Meta:
        model = License
        fields = [
            'id', 'license_key', 'licensee_name', 'licensee_email', 'licensee_company',
            'product', 'edition', 'version',
            'issued_at', 'starts_at', 'expires_at',
            'max_tenants', 'max_users_per_tenant', 'max_proxies_per_tenant',
            'max_repositories_per_tenant', 'max_storage_gb',
            'features', 'modules', 'status',
            'signature', 'fingerprint', 'notes',
            'is_valid', 'days_until_expiry', 'is_perpetual', 'limits',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'issued_at', 'created_at', 'updated_at']

    def get_limits(self, obj):
        return obj.get_limits()


class LicenseCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new license.
    """

    class Meta:
        model = License
        fields = [
            'licensee_name', 'licensee_email', 'licensee_company',
            'edition', 'version',
            'starts_at', 'expires_at',
            'max_tenants', 'max_users_per_tenant', 'max_proxies_per_tenant',
            'max_repositories_per_tenant', 'max_storage_gb',
            'features', 'modules',
            'notes'
        ]

    def create(self, validated_data):
        # Generate license key
        import secrets
        license_key = secrets.token_hex(32)
        validated_data['license_key'] = license_key
        return super().create(validated_data)


class LicenseVerifySerializer(serializers.Serializer):
    """
    Serializer for license verification.
    """

    license_key = serializers.CharField()
    fingerprint = serializers.CharField(required=False)


class LicenseStatusSerializer(serializers.Serializer):
    """
    Serializer for license status check.
    """

    is_valid = serializers.BooleanField()
    edition = serializers.CharField()
    licensee_name = serializers.CharField()
    expires_at = serializers.DateTimeField(allow_null=True)
    days_until_expiry = serializers.IntegerField()
    features = serializers.DictField()
    limits = serializers.DictField()
    warnings = serializers.ListField()


class LicenseAuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for license audit logs.
    """

    license_key = serializers.CharField(source='license.license_key', read_only=True)

    class Meta:
        model = LicenseAuditLog
        fields = [
            'id', 'license', 'license_key', 'event_type', 'message',
            'details', 'ip_address', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
