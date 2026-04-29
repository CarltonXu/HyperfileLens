"""
Serializers for Accounts Application

This module provides serializers for user authentication,
registration, and profile management.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Role, APIToken, UserSession


User = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    """
    Serializer for Role model.

    Provides read-only access to role data including permissions.
    """

    class Meta:
        model = Role
        fields = [
            'id', 'name', 'code', 'description',
            'permissions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.

    Handles validation and creation of new user accounts.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone'
        ]
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'phone': {'required': False},
        }

    def validate(self, attrs):
        """
        Validate that passwords match.

        Raises:
            ValidationError: If passwords don't match
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': "Passwords don't match."
            })
        return attrs

    def create(self, validated_data):
        """
        Create a new user account with auto-created tenant and license.

        This method:
        1. Creates a new tenant using email prefix as name
        2. Creates the user as tenant owner
        3. Creates a default Free license for the tenant

        Args:
            validated_data: Validated data from the serializer

        Returns:
            The created user instance
        """
        from tenants.models import Tenant
        from licenses.models import License
        from django.utils import timezone
        import uuid
        import secrets
        import hashlib

        validated_data.pop('password_confirm')
        email = validated_data['email']

        # Generate tenant name from email prefix
        email_prefix = email.split('@')[0]
        # Clean the prefix to be a valid name/slug
        tenant_name = ''.join(c if c.isalnum() or c in '-_' else '-' for c in email_prefix)
        tenant_slug = f"{tenant_name}-{secrets.token_hex(4)}"

        # Create tenant
        tenant = Tenant.objects.create(
            name=tenant_name,
            slug=tenant_slug,
            plan=Tenant.PlanType.FREE,
            status=Tenant.TenantStatus.ACTIVE,
            contact_email=email,
            # Free plan defaults
            max_users=10,
            max_proxies=5,
            max_repositories=3,
            max_storage_gb=100,
            max_backup_tasks=50,
        )

        # Create user as tenant owner
        user = User.objects.create_user(
            **validated_data,
            tenant=tenant,
            tenant_role=User.TenantRole.OWNER,
        )

        # Generate unique license key and machine code
        license_key = f"FREE-{secrets.token_hex(16).upper()}"
        machine_code = hashlib.sha256(
            f"{tenant.id}-{user.id}-{secrets.token_hex(8)}".encode()
        ).hexdigest()[:64]

        # Create default Free license
        License.objects.create(
            license_key=license_key,
            tenant=tenant,
            activated_by=user,
            machine_code=machine_code,
            change_type=License.ChangeType.INITIAL,
            change_reason='Auto-created on registration',
            # Free plan limits
            max_tenants=1,
            max_users=10,
            max_proxies=5,
            max_storage_gb=100,
            max_gateways=1,
            ai_insights_quota=100,
            max_backup_tasks=10,
            max_recovery_tasks=10,
            max_source_resources=20,
            max_policies=50,
            max_repositories=5,
            issued_at=timezone.now(),
            expires_at=None,  # Perpetual for free plan
            signature='auto-generated-free-license',
            status=License.LicenseStatus.ACTIVE,
        )

        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile data.

    Provides read and update access to user profile information.
    """

    role = RoleSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'full_name', 'role', 'permissions', 'phone', 'avatar',
            'preferences', 'date_joined', 'last_login_at', 'is_active',
            'is_superuser', 'tenant_role', 'tenant', 'tenant_name'
        ]
        read_only_fields = [
            'id', 'email', 'role', 'date_joined', 'last_login_at',
            'is_superuser', 'tenant_role', 'tenant', 'tenant_name'
        ]

    def get_full_name(self, obj):
        """
        Get the user's full name.

        Args:
            obj: The user instance

        Returns:
            User's full name
        """
        return obj.get_full_name()

    def get_tenant_name(self, obj):
        """
        Get the tenant name.

        Args:
            obj: The user instance

        Returns:
            Tenant name or None
        """
        return obj.tenant.name if obj.tenant else None

    def get_permissions(self, obj):
        """
        Get the user's permissions via their role.

        Args:
            obj: The user instance

        Returns:
            Dictionary of permission codes and their granted status
        """
        return obj.get_permissions()


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.

    Allows users to update their own profile information.
    """

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name',
            'phone', 'avatar', 'preferences'
        ]

    def update(self, instance, validated_data):
        """
        Update user profile.

        Args:
            instance: The user instance to update
            validated_data: Validated data from the serializer

        Returns:
            The updated user instance
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change.

    Validates old password and ensures new password meets requirements.
    """

    old_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )

    def validate_old_password(self, value):
        """
        Validate that the old password is correct.

        Args:
            value: The old password value

        Raises:
            ValidationError: If old password is incorrect

        Returns:
            The validated old password
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value

    def validate(self, attrs):
        """
        Validate that new passwords match.

        Raises:
            ValidationError: If new passwords don't match
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "New passwords don't match."
            })
        return attrs

    def save(self):
        """
        Save the new password.

        Returns:
            The updated user instance
        """
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class APITokenSerializer(serializers.ModelSerializer):
    """
    Serializer for API token management.

    Handles creation and management of API tokens.
    """

    class Meta:
        model = APIToken
        fields = [
            'id', 'name', 'prefix', 'scopes', 'rate_limit',
            'is_active', 'created_at', 'last_used_at', 'expires_at'
        ]
        read_only_fields = [
            'id', 'prefix', 'created_at', 'last_used_at'
        ]

    def create(self, validated_data):
        """
        Create a new API token.

        Args:
            validated_data: Validated data from the serializer

        Returns:
            The created token instance (with full key for display)
        """
        user = self.context['request'].user
        token = APIToken.objects.create(user=user, **validated_data)
        return token


class APITokenCreateResponseSerializer(serializers.Serializer):
    """
    Serializer for API token creation response.

    Includes the full token key which is only shown once at creation.
    """

    id = serializers.IntegerField()
    name = serializers.CharField()
    key = serializers.CharField(
        help_text='Full token key - only shown once, store securely'
    )
    prefix = serializers.CharField()
    scopes = serializers.ListField()
    rate_limit = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField(allow_null=True)


class UserSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for user session management.
    """

    class Meta:
        model = UserSession
        fields = [
            'id', 'ip_address', 'user_agent', 'created_at',
            'last_activity', 'is_active'
        ]
        read_only_fields = fields
