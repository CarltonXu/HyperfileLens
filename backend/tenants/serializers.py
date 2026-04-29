"""
Serializers for Tenants API
"""

from rest_framework import serializers
from .models import Tenant, TenantInvitation
from accounts.serializers import UserProfileSerializer


class TenantSerializer(serializers.ModelSerializer):
    """
    Serializer for Tenant model.
    """

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'plan', 'status',
            'max_proxies', 'max_repositories', 'max_storage_gb',
            'max_users', 'max_backup_tasks',
            'contact_email', 'contact_phone', 'logo_url',
            'settings', 'created_at', 'updated_at',
            'trial_ends_at', 'subscription_ends_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_slug(self, value):
        """Validate slug is unique."""
        if Tenant.objects.filter(slug=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("A tenant with this slug already exists.")
        return value


class TenantListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing tenants.
    """

    user_count = serializers.SerializerMethodField()
    proxy_count = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'plan', 'status',
            'max_proxies', 'max_users',
            'user_count', 'proxy_count',
            'created_at', 'subscription_ends_at'
        ]

    def get_user_count(self, obj):
        return obj.users.count()

    def get_proxy_count(self, obj):
        from nodes.models import ProxyNode
        return ProxyNode.objects.filter(tenant=obj).count()


class TenantDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for tenant with quota usage.
    """

    quota_usage = serializers.SerializerMethodField()
    is_within_quota = serializers.SerializerMethodField()
    users = UserProfileSerializer(many=True, read_only=True)

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'plan', 'status',
            'max_proxies', 'max_repositories', 'max_storage_gb',
            'max_users', 'max_backup_tasks',
            'contact_email', 'contact_phone', 'logo_url',
            'settings', 'created_at', 'updated_at',
            'trial_ends_at', 'subscription_ends_at',
            'quota_usage', 'is_within_quota', 'users'
        ]

    def get_quota_usage(self, obj):
        return obj.get_quota_usage()

    def get_is_within_quota(self, obj):
        return obj.is_within_quota()


class TenantInvitationSerializer(serializers.ModelSerializer):
    """
    Serializer for TenantInvitation model.
    """

    invited_by_name = serializers.CharField(source='invited_by.get_full_name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = TenantInvitation
        fields = [
            'id', 'tenant', 'tenant_name', 'email', 'role',
            'invited_by', 'invited_by_name', 'status',
            'created_at', 'expires_at', 'accepted_at'
        ]
        read_only_fields = ['id', 'token', 'created_at', 'accepted_at', 'invited_by']


class AcceptInvitationSerializer(serializers.Serializer):
    """
    Serializer for accepting an invitation.
    """

    token = serializers.CharField()
    password = serializers.CharField(write_only=True, required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)


class TenantQuotaSerializer(serializers.Serializer):
    """
    Serializer for tenant quota information.
    """

    max_proxies = serializers.IntegerField()
    max_repositories = serializers.IntegerField()
    max_storage_gb = serializers.IntegerField()
    max_users = serializers.IntegerField()
    max_backup_tasks = serializers.IntegerField()
    current_proxies = serializers.IntegerField()
    current_repositories = serializers.IntegerField()
    current_users = serializers.IntegerField()
    current_storage_gb = serializers.FloatField()
