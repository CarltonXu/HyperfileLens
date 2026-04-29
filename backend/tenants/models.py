"""
Tenant Models for HyperFileLens

This module defines multi-tenancy support for the HyperFileLens platform.

Features:
- Tenant isolation for data and resources
- Quota management per tenant
- Tenant-level user roles
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
import secrets


class Tenant(models.Model):
    """
    Tenant model for multi-tenancy support.

    Each tenant represents an isolated organization/company with
    its own resources, users, and settings.
    """

    class PlanType(models.TextChoices):
        """Available subscription plans."""
        FREE = 'free', 'Free'
        BASIC = 'basic', 'Basic'
        PRO = 'pro', 'Professional'
        ENTERPRISE = 'enterprise', 'Enterprise'

    class TenantStatus(models.TextChoices):
        """Tenant status options."""
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'
        TRIAL = 'trial', 'Trial'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Unique tenant identifier'
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Tenant name (organization/company name)'
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text='URL-friendly identifier'
    )
    plan = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        default=PlanType.FREE,
        help_text='Subscription plan type'
    )
    status = models.CharField(
        max_length=20,
        choices=TenantStatus.choices,
        default=TenantStatus.ACTIVE,
        help_text='Current tenant status'
    )
    
    # Quota limits
    max_proxies = models.PositiveIntegerField(
        default=5,
        help_text='Maximum number of proxies allowed'
    )
    max_repositories = models.PositiveIntegerField(
        default=3,
        help_text='Maximum number of storage repositories allowed'
    )
    max_storage_gb = models.PositiveIntegerField(
        default=100,
        help_text='Maximum storage in GB'
    )
    max_users = models.PositiveIntegerField(
        default=10,
        help_text='Maximum number of users allowed'
    )
    max_backup_tasks = models.PositiveIntegerField(
        default=50,
        help_text='Maximum concurrent backup tasks'
    )
    
    # Contact information
    contact_email = models.EmailField(
        help_text='Primary contact email for this tenant'
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Primary contact phone number'
    )
    
    # Settings and metadata
    settings = models.JSONField(
        default=dict,
        help_text='Tenant-specific settings and configurations'
    )
    logo_url = models.URLField(
        blank=True,
        null=True,
        help_text='URL to tenant logo image'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    trial_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Trial period end date'
    )
    subscription_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Subscription end date'
    )

    class Meta:
        db_table = 'tenants_tenant'
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.name

    @property
    def is_active(self) -> bool:
        """Check if tenant is active and usable."""
        if self.status != self.TenantStatus.ACTIVE:
            return False
        if self.subscription_ends_at and self.subscription_ends_at < timezone.now():
            return False
        return True

    def get_quota_usage(self) -> dict:
        """
        Get current resource usage for this tenant.

        Returns:
            Dictionary with current usage statistics
        """
        from nodes.models import ProxyNode
        from repository.models import Repository
        from accounts.models import User

        return {
            'proxies': ProxyNode.objects.filter(tenant=self).count(),
            'repositories': Repository.objects.filter(tenant=self).count(),
            'users': User.objects.filter(tenant=self).count(),
            'storage_used_gb': 0,  # TODO: Calculate actual storage
        }

    def is_within_quota(self) -> bool:
        """Check if tenant is within all quota limits."""
        usage = self.get_quota_usage()
        return (
            usage['proxies'] <= self.max_proxies and
            usage['repositories'] <= self.max_repositories and
            usage['users'] <= self.max_users
        )


class TenantInvitation(models.Model):
    """
    Invitation for a user to join a tenant.
    """

    class InvitationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'
        EXPIRED = 'expired', 'Expired'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='invitations',
        help_text='Tenant the invitation is for'
    )
    email = models.EmailField(
        help_text='Email address of the invited user'
    )
    role = models.CharField(
        max_length=20,
        default='member',
        help_text='Role to assign to the user'
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        help_text='User who sent the invitation'
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        default=secrets.token_hex(32),
        help_text='Unique token for accepting the invitation'
    )
    status = models.CharField(
        max_length=20,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING,
        help_text='Current status of the invitation'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text='When the invitation expires'
    )
    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the invitation was accepted'
    )

    class Meta:
        db_table = 'tenants_invitation'
        verbose_name = 'Tenant Invitation'
        verbose_name_plural = 'Tenant Invitations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'tenant']),
            models.Index(fields=['token']),
        ]

    def __str__(self):
        return f'{self.email} -> {self.tenant.name}'

    def is_valid(self) -> bool:
        """Check if invitation is still valid."""
        return (
            self.status == self.InvitationStatus.PENDING and
            self.expires_at > timezone.now()
        )
