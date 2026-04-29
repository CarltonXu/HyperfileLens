"""
License Models for HyperFileLens

This module defines license management for product authorization.

Features:
- License key validation
- Feature gating
- Expiration management
- Digital signature verification
"""

from django.db import models
from django.utils import timezone
import uuid
import json
import hashlib
from datetime import timedelta


class License(models.Model):
    """
    License model for product authorization.

    Controls product features, tenant limits, and expiration.
    """

    class EditionType(models.TextChoices):
        """Product edition types."""
        COMMUNITY = 'community', 'Community Edition'
        PRO = 'pro', 'Professional Edition'
        ENTERPRISE = 'enterprise', 'Enterprise Edition'

    class LicenseStatus(models.TextChoices):
        """License status options."""
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        REVOKED = 'revoked', 'Revoked'
        TRIAL = 'trial', 'Trial'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Unique license identifier'
    )
    license_key = models.CharField(
        max_length=64,
        unique=True,
        help_text='Encrypted license key'
    )
    
    # Licensee information
    licensee_name = models.CharField(
        max_length=200,
        help_text='Name of the licensed organization/individual'
    )
    licensee_email = models.EmailField(
        help_text='Contact email for the licensee'
    )
    licensee_company = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='Company name (if applicable)'
    )
    
    # Product information
    product = models.CharField(
        max_length=50,
        default='HyperFileLens',
        help_text='Product name'
    )
    edition = models.CharField(
        max_length=20,
        choices=EditionType.choices,
        default=EditionType.COMMUNITY,
        help_text='Product edition'
    )
    version = models.CharField(
        max_length=20,
        default='1.0',
        help_text='Licensed version'
    )
    
    # Time constraints
    issued_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the license was issued'
    )
    starts_at = models.DateTimeField(
        default=timezone.now,
        help_text='When the license becomes valid'
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the license expires (null = perpetual)'
    )
    
    # Limits
    max_tenants = models.PositiveIntegerField(
        default=1,
        help_text='Maximum number of tenants allowed'
    )
    max_users_per_tenant = models.PositiveIntegerField(
        default=10,
        help_text='Maximum users per tenant'
    )
    max_proxies_per_tenant = models.PositiveIntegerField(
        default=10,
        help_text='Maximum proxies per tenant'
    )
    max_repositories_per_tenant = models.PositiveIntegerField(
        default=5,
        help_text='Maximum repositories per tenant'
    )
    max_storage_gb = models.PositiveIntegerField(
        default=100,
        help_text='Maximum total storage in GB'
    )
    
    # Features
    features = models.JSONField(
        default=dict,
        help_text='Feature flags and their enabled status'
    )
    modules = models.JSONField(
        default=list,
        help_text='List of enabled modules'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=LicenseStatus.choices,
        default=LicenseStatus.ACTIVE,
        help_text='Current license status'
    )
    
    # Security
    signature = models.TextField(
        blank=True,
        null=True,
        help_text='Digital signature for verification'
    )
    fingerprint = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text='Machine fingerprint for binding'
    )
    
    # Metadata
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Internal notes about this license'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'licenses_license'
        verbose_name = 'License'
        verbose_name_plural = 'Licenses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['license_key']),
            models.Index(fields=['status']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f'{self.licensee_name} - {self.get_edition_display()}'

    @property
    def is_valid(self) -> bool:
        """Check if license is currently valid."""
        if self.status != self.LicenseStatus.ACTIVE:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.starts_at > timezone.now():
            return False
        return True

    @property
    def days_until_expiry(self) -> int:
        """Get number of days until license expires."""
        if not self.expires_at:
            return -1  # Perpetual
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)

    @property
    def is_perpetual(self) -> bool:
        """Check if this is a perpetual license."""
        return self.expires_at is None

    def has_feature(self, feature_name: str) -> bool:
        """
        Check if a feature is enabled in this license.

        Args:
            feature_name: Name of the feature to check

        Returns:
            True if feature is enabled, False otherwise
        """
        # Community edition has limited features
        if self.edition == self.EditionType.COMMUNITY:
            community_features = [
                'basic_backup',
                'basic_recovery',
                'proxy_management',
                'monitoring',
            ]
            return feature_name in community_features

        # Pro edition has most features
        if self.edition == self.EditionType.PRO:
            pro_features = [
                'basic_backup',
                'basic_recovery',
                'proxy_management',
                'monitoring',
                'advanced_backup',
                'advanced_recovery',
                'ai_query',
                'policy_management',
                'audit_log',
            ]
            return feature_name in pro_features

        # Enterprise edition has all features
        if self.edition == self.EditionType.ENTERPRISE:
            return True

        return self.features.get(feature_name, False)

    def get_limits(self) -> dict:
        """
        Get all license limits.

        Returns:
            Dictionary of limit names and values
        """
        return {
            'max_tenants': self.max_tenants,
            'max_users_per_tenant': self.max_users_per_tenant,
            'max_proxies_per_tenant': self.max_proxies_per_tenant,
            'max_repositories_per_tenant': self.max_repositories_per_tenant,
            'max_storage_gb': self.max_storage_gb,
        }

    def verify_signature(self, public_key: str = None) -> bool:
        """
        Verify the license signature.

        Args:
            public_key: Public key for verification (optional)

        Returns:
            True if signature is valid, False otherwise
        """
        # TODO: Implement actual signature verification
        # For now, return True if signature exists
        return bool(self.signature)

    @classmethod
    def get_active_license(cls):
        """
        Get the currently active license.

        Returns:
            Active License object or None
        """
        try:
            return cls.objects.filter(
                status=cls.LicenseStatus.ACTIVE,
                starts_at__lte=timezone.now()
            ).exclude(
                expires_at__lt=timezone.now()
            ).first()
        except cls.DoesNotExist:
            return None


class LicenseAuditLog(models.Model):
    """
    Audit log for license-related events.
    """

    class EventType(models.TextChoices):
        CREATED = 'created', 'License Created'
        ACTIVATED = 'activated', 'License Activated'
        EXPIRED = 'expired', 'License Expired'
        REVOKED = 'revoked', 'License Revoked'
        RENEWED = 'renewed', 'License Renewed'
        VERIFIED = 'verified', 'License Verified'
        FAILED = 'failed', 'Verification Failed'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    license = models.ForeignKey(
        License,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        help_text='Related license'
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        help_text='Type of event'
    )
    message = models.TextField(
        help_text='Event description'
    )
    details = models.JSONField(
        default=dict,
        help_text='Additional event details'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the request'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'licenses_audit_log'
        verbose_name = 'License Audit Log'
        verbose_name_plural = 'License Audit Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.license.license_key[:8]}... - {self.event_type}'
