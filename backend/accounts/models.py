"""
User Models for HyperFileLens

This module defines custom user models and related entities
for authentication and authorization in the HyperFileLens platform.

Features:
- Custom user model with email as primary identifier
- Role-based access control (RBAC)
- API token management
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.conf import settings
import secrets
import uuid


class UserManager(BaseUserManager):
    """
    Custom user manager for HyperFileLens.

    This manager handles user creation and management,
    using email as the primary identifier instead of username.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.

        Args:
            email: User's email address (required, unique)
            password: User's password (optional, will be hashed)
            **extra_fields: Additional fields to set on the user

        Returns:
            The created user instance

        Raises:
            ValueError: If email is not provided
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.

        Args:
            email: User's email address (required, unique)
            password: User's password (required)
            **extra_fields: Additional fields to set on the superuser

        Returns:
            The created superuser instance

        Raises:
            ValueError: If is_staff or is_superuser is not True
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class Role(models.Model):
    """
    Role model for role-based access control (RBAC).

    Roles define a collection of permissions that can be assigned to users.
    """

    class RoleType(models.TextChoices):
        """Predefined role types for common use cases."""
        ADMIN = 'admin', 'Administrator'
        OPERATOR = 'operator', 'Operator'
        VIEWER = 'viewer', 'Viewer'
        AUDITOR = 'auditor', 'Auditor'

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Unique name for the role'
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        choices=RoleType.choices,
        help_text='Code identifier for the role type'
    )
    description = models.TextField(
        blank=True,
        help_text='Human-readable description of the role'
    )
    permissions = models.JSONField(
        default=dict,
        help_text='JSON object containing permission codes and their granted status'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_role'
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'

    def has_permission(self, permission_code: str) -> bool:
        """
        Check if this role has a specific permission.

        Args:
            permission_code: The permission code to check

        Returns:
            True if the permission is granted, False otherwise
        """
        return self.permissions.get(permission_code, False)

    def grant_permission(self, permission_code: str) -> None:
        """
        Grant a permission to this role.

        Args:
            permission_code: The permission code to grant
        """
        self.permissions[permission_code] = True
        self.save(update_fields=['permissions', 'updated_at'])

    def revoke_permission(self, permission_code: str) -> None:
        """
        Revoke a permission from this role.

        Args:
            permission_code: The permission code to revoke
        """
        self.permissions[permission_code] = False
        self.save(update_fields=['permissions', 'updated_at'])


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for HyperFileLens.

    This model extends Django's permission system and uses email
    as the primary identifier for authentication.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Unique identifier (UUID4 format)'
    )
    email = models.EmailField(
        unique=True,
        max_length=255,
        help_text='User email address (used for login)'
    )
    username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text='Optional username for display purposes'
    )
    first_name = models.CharField(
        max_length=150,
        blank=True,
        help_text='User first name'
    )
    last_name = models.CharField(
        max_length=150,
        blank=True,
        help_text='User last name'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text='User role for RBAC'
    )
    
    # Multi-tenancy support
    class TenantRole(models.TextChoices):
        """Role within a tenant."""
        ADMIN = 'admin', 'Administrator'  # 租户管理员
        MEMBER = 'member', 'Member'  # 租户用户
    
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
        help_text='Tenant this user belongs to'
    )
    tenant_role = models.CharField(
        max_length=20,
        choices=TenantRole.choices,
        default=TenantRole.MEMBER,
        help_text='Role within the tenant'
    )
    
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='hfl_user_set',  # Custom related name to avoid clash
        related_query_name='hfl_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='hfl_user_set',  # Custom related name to avoid clash
        related_query_name='hfl_user',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this user account is active'
    )
    is_staff = models.BooleanField(
        default=False,
        help_text='Whether this user can access the admin site'
    )
    is_system = models.BooleanField(
        default=False,
        help_text='Whether this is a system account (for node authentication)'
    )
    date_joined = models.DateTimeField(default=timezone.now)
    last_login_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last time user logged in'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='User phone number'
    )
    avatar = models.URLField(
        blank=True,
        null=True,
        help_text='URL to user avatar image'
    )
    preferences = models.JSONField(
        default=dict,
        help_text='User preferences and settings'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f'{self.first_name} {self.last_name}'.strip()
        return full_name or self.email

    def get_short_name(self):
        """
        Return the short name for the user.
        """
        return self.first_name or self.email.split('@')[0]

    def has_permission(self, permission_code: str) -> bool:
        """
        Check if user has a specific permission.

        Args:
            permission_code: The permission code to check

        Returns:
            True if user has permission (via role or system status), False otherwise
        """
        # System accounts have all permissions
        if self.is_system:
            return True
        # Check role permissions
        if self.role:
            return self.role.has_permission(permission_code)
        return False

    def get_permissions(self) -> dict:
        """
        Get all permissions for this user.

        Returns:
            Dictionary of permission codes and their granted status
        """
        if self.role:
            return self.role.permissions.copy()
        return {}


class APIToken(models.Model):
    """
    API Token model for programmatic access to the HyperFileLens API.

    Tokens are associated with users and can have expiration dates.
    """

    name = models.CharField(
        max_length=100,
        help_text='Descriptive name for this token'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_tokens',
        help_text='User who owns this token'
    )
    key = models.CharField(
        max_length=64,
        unique=True,
        help_text='The actual token value (stored hashed in production)'
    )
    prefix = models.CharField(
        max_length=8,
        help_text='Prefix of the key for display purposes'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this token is active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last time this token was used'
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this token expires (null = never)'
    )
    scopes = models.JSONField(
        default=list,
        help_text='List of permission scopes for this token'
    )
    rate_limit = models.IntegerField(
        default=100,
        help_text='Maximum requests per minute allowed with this token'
    )

    class Meta:
        db_table = 'accounts_api_token'
        verbose_name = 'API Token'
        verbose_name_plural = 'API Tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} ({self.prefix}...)'

    def save(self, *args, **kwargs):
        """
        Generate a new key if not set, and calculate the prefix.
        """
        if not self.key:
            self.key = secrets.token_hex(32)
            self.prefix = self.key[:8]
        super().save(*args, **kwargs)

    def is_valid(self) -> bool:
        """
        Check if this token is valid for use.

        Returns:
            True if token is active and not expired, False otherwise
        """
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    def update_last_used(self) -> None:
        """
        Update the last_used_at timestamp to the current time.
        """
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at', ])


class UserSession(models.Model):
    """
    User session model for tracking active user sessions.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sessions',
        help_text='User who owns this session'
    )
    session_key = models.CharField(
        max_length=40,
        unique=True,
        help_text='Django session key'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the client'
    )
    user_agent = models.TextField(
        blank=True,
        help_text='User agent string of the client'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(
        default=timezone.now,
        help_text='Last activity timestamp'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this session is still active'
    )

    class Meta:
        db_table = 'accounts_user_session'
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
        ]

    def __str__(self):
        return f'{self.user.email} - {self.ip_address}'
