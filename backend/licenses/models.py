"""
License Models for HyperFileLens

Simplified License model that focuses on quantity limits only.
Machine binding ensures license can only be used on specific machine + tenant + user.
"""

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
import uuid
import json
import hashlib
import base64
import subprocess
import platform
import secrets


class License(models.Model):
    """
    License model for product authorization.
    
    Design Principles:
    1. No feature restrictions - only quantity limits
    2. Machine binding: MAC + CPU ID + Tenant ID + User ID
    3. Activation code required for binding
    4. One machine code can only activate one license
    """
    
    class LicenseStatus(models.TextChoices):
        """License status options."""
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        REVOKED = 'revoked', 'Revoked'
    
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Unique license identifier'
    )
    
    # License key (from activation code)
    license_key = models.CharField(
        max_length=64,
        unique=True,
        help_text='License key from activation code'
    )
    
    # Binding information
    machine_code = models.CharField(
        max_length=64,
        unique=True,
        help_text='Machine code: MAC + CPU + Tenant + User'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='licenses',
        help_text='Tenant this license is bound to'
    )
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activated_licenses',
        help_text='User who activated this license'
    )
    
    # Quantity limits - All features unlocked, only quantities limited
    max_tenants = models.PositiveIntegerField(
        default=1,
        help_text='Maximum number of tenants'
    )
    max_users = models.PositiveIntegerField(
        default=10,
        help_text='Maximum number of users (total across all tenants)'
    )
    max_proxies = models.PositiveIntegerField(
        default=5,
        help_text='Maximum number of proxies'
    )
    max_storage_gb = models.PositiveIntegerField(
        default=100,
        help_text='Maximum storage capacity in GB'
    )
    max_gateways = models.PositiveIntegerField(
        default=1,
        help_text='Maximum number of gateway nodes'
    )
    ai_insights_quota = models.PositiveIntegerField(
        default=100,
        help_text='Monthly AI insights quota (free tier)'
    )
    max_backup_tasks = models.PositiveIntegerField(
        default=10,
        help_text='Maximum concurrent backup tasks'
    )
    max_recovery_tasks = models.PositiveIntegerField(
        default=10,
        help_text='Maximum concurrent recovery tasks'
    )
    max_source_resources = models.PositiveIntegerField(
        default=20,
        help_text='Maximum number of source resources'
    )
    max_policies = models.PositiveIntegerField(
        default=50,
        help_text='Maximum number of backup policies'
    )
    max_repositories = models.PositiveIntegerField(
        default=5,
        help_text='Maximum number of backup repositories'
    )
    
    # Time information
    issued_at = models.DateTimeField(
        help_text='When the license was issued'
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the license expires (null = perpetual)'
    )
    activated_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the license was activated'
    )
    
    # Security
    signature = models.TextField(
        help_text='Digital signature for verification'
    )
    status = models.CharField(
        max_length=20,
        choices=LicenseStatus.choices,
        default=LicenseStatus.ACTIVE,
        help_text='License status'
    )
    
    class Meta:
        ordering = ['-activated_at']
        verbose_name = 'License'
        verbose_name_plural = 'Licenses'
    
    def __str__(self):
        return f'{self.license_key[:20]}... ({self.tenant.name})'
    
    @property
    def is_valid(self) -> bool:
        """Check if license is currently valid."""
        if self.status != self.LicenseStatus.ACTIVE:
            return False
        
        if self.expires_at and self.expires_at < timezone.now():
            return False
        
        return True
    
    @property
    def is_expired(self) -> bool:
        """Check if license is expired."""
        if not self.expires_at:
            return False
        return self.expires_at < timezone.now()
    
    @property
    def days_until_expiry(self) -> int:
        """Get number of days until license expires."""
        if not self.expires_at:
            return -1  # Perpetual
        
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)
    
    @property
    def is_perpetual(self) -> bool:
        """Check if license is perpetual (no expiration)."""
        return self.expires_at is None
    
    @classmethod
    def get_active_license(cls, tenant=None):
        """Get the active license for a tenant."""
        from tenants.models import Tenant as TenantModel
        
        if tenant is None:
            # Get default tenant
            tenant = TenantModel.objects.first()
        
        if not tenant:
            return None
        
        try:
            license = cls.objects.filter(
                tenant=tenant,
                status=cls.LicenseStatus.ACTIVE
            ).first()
            
            if license and license.is_valid:
                return license
        except cls.DoesNotExist:
            pass
        
        return None
    
    def get_limits(self) -> dict:
        """Get all limit values as a dictionary."""
        return {
            'max_tenants': self.max_tenants,
            'max_users': self.max_users,
            'max_proxies': self.max_proxies,
            'max_storage_gb': self.max_storage_gb,
            'max_gateways': self.max_gateways,
            'ai_insights_quota': self.ai_insights_quota,
            'max_backup_tasks': self.max_backup_tasks,
            'max_recovery_tasks': self.max_recovery_tasks,
            'max_source_resources': self.max_source_resources,
            'max_policies': self.max_policies,
            'max_repositories': self.max_repositories,
        }


class MachineCode(models.Model):
    """
    Machine code generation record.
    
    Stores the generated machine code for a tenant/user to track
    which machines have requested activation codes.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True, help_text='Generated machine code')
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='machine_codes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='machine_codes')
    
    # Machine components (for debugging/audit)
    mac_address = models.CharField(max_length=20, blank=True)
    cpu_id = models.CharField(max_length=100, blank=True)
    hostname = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True, help_text='When this code was used to activate')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.code[:20]}... ({self.tenant.name})'


class QuotaUsage(models.Model):
    """
    Track current usage against license limits.
    """
    
    class PeriodType(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        TOTAL = 'total', 'Total'
    
    license = models.OneToOneField(
        License,
        on_delete=models.CASCADE,
        related_name='quota_usage'
    )
    
    # Current usage counts
    users_count = models.PositiveIntegerField(default=0)
    proxies_count = models.PositiveIntegerField(default=0)
    storage_used_gb = models.FloatField(default=0)
    gateways_count = models.PositiveIntegerField(default=0)
    backup_tasks_count = models.PositiveIntegerField(default=0)
    recovery_tasks_count = models.PositiveIntegerField(default=0)
    source_resources_count = models.PositiveIntegerField(default=0)
    policies_count = models.PositiveIntegerField(default=0)
    repositories_count = models.PositiveIntegerField(default=0)
    
    # AI Insights usage (monthly reset)
    ai_insights_used = models.PositiveIntegerField(default=0)
    ai_insights_period = models.CharField(
        max_length=10,
        default=PeriodType.MONTHLY
    )
    ai_insights_reset_at = models.DateTimeField(null=True, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Quota Usage'
        verbose_name_plural = 'Quota Usages'
    
    def check_limit(self, limit_type: str, increment: int = 1) -> tuple[bool, str]:
        """
        Check if adding increment would exceed license limit.
        
        Returns:
            (allowed, error_message)
        """
        limits = self.license.get_limits()
        
        limit_mapping = {
            'users': ('users_count', 'max_users'),
            'proxies': ('proxies_count', 'max_proxies'),
            'storage_gb': ('storage_used_gb', 'max_storage_gb'),
            'gateways': ('gateways_count', 'max_gateways'),
            'backup_tasks': ('backup_tasks_count', 'max_backup_tasks'),
            'recovery_tasks': ('recovery_tasks_count', 'max_recovery_tasks'),
            'source_resources': ('source_resources_count', 'max_source_resources'),
            'policies': ('policies_count', 'max_policies'),
            'repositories': ('repositories_count', 'max_repositories'),
            'ai_insights': ('ai_insights_used', 'ai_insights_quota'),
        }
        
        if limit_type not in limit_mapping:
            return False, f"Unknown limit type: {limit_type}"
        
        usage_field, limit_field = limit_mapping[limit_type]
        current = getattr(self, usage_field)
        limit = limits[limit_field]
        
        if current + increment > limit:
            return False, f"License limit exceeded: {limit_type} (current: {current}, limit: {limit})"
        
        return True, ""
    
    def increment_usage(self, limit_type: str, amount: int = 1):
        """Increment usage for a limit type."""
        field_mapping = {
            'users': 'users_count',
            'proxies': 'proxies_count',
            'storage_gb': 'storage_used_gb',
            'gateways': 'gateways_count',
            'backup_tasks': 'backup_tasks_count',
            'recovery_tasks': 'recovery_tasks_count',
            'source_resources': 'source_resources_count',
            'policies': 'policies_count',
            'repositories': 'repositories_count',
            'ai_insights': 'ai_insights_used',
        }
        
        if limit_type in field_mapping:
            field = field_mapping[limit_type]
            setattr(self, field, getattr(self, field) + amount)
            self.save(update_fields=[field, 'updated_at'])
    
    def reset_monthly_usage(self):
        """Reset monthly usage counters (AI insights)."""
        from datetime import datetime
        self.ai_insights_used = 0
        self.ai_insights_reset_at = timezone.now()
        self.save(update_fields=['ai_insights_used', 'ai_insights_reset_at', 'updated_at'])


class LicenseAuditLog(models.Model):
    """
    Audit log for license operations.
    """
    
    class ActionType(models.TextChoices):
        GENERATED = 'generated', 'Machine Code Generated'
        ACTIVATED = 'activated', 'License Activated'
        EXPIRED = 'expired', 'License Expired'
        REVOKED = 'revoked', 'License Revoked'
        LIMIT_CHECKED = 'limit_checked', 'Limit Checked'
        LIMIT_EXCEEDED = 'limit_exceeded', 'Limit Exceeded'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    license = models.ForeignKey(
        License,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    machine_code = models.ForeignKey(
        MachineCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=ActionType.choices)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.get_action_display()} - {self.created_at}'
