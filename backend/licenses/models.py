"""
License Models for HyperFileLens

This module defines license management for product authorization.

Security Features:
- Digital signature verification (RSA)
- Hardware fingerprint binding
- Checksum validation
- Tamper detection
"""

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
import json
import hashlib
from datetime import timedelta

from .crypto import LicenseSigner, LicenseEncoder, HardwareFingerprint


class License(models.Model):
    """
    License model for product authorization.

    SECURITY MODEL:
    1. License data is generated offline with private key signature
    2. Signature is verified on import using embedded public key
    3. Critical fields are protected by checksum
    4. Optional hardware binding prevents license transfer
    5. All modifications invalidate the signature
    """

    class EditionType(models.TextChoices):
        """Product edition types."""
        COMMUNITY = 'community', 'Community Edition'
        PRO = 'pro', 'Professional Edition'
        ENTERPRISE = 'enterprise', 'Enterprise Edition'

    class LicenseStatus(models.TextChoices):
        """License status options."""
        INACTIVE = 'inactive', 'Inactive'  # Imported but not activated
        ACTIVE = 'active', 'Active'  # Activated and bound to machine
        EXPIRED = 'expired', 'Expired'
        REVOKED = 'revoked', 'Revoked'
        TRIAL = 'trial', 'Trial'
        INVALID = 'invalid', 'Invalid'

    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Unique license identifier'
    )
    
    # License key (encrypted/hashed for security)
    license_key = models.CharField(
        max_length=64,
        unique=True,
        help_text='License key (stored as hash)'
    )
    
    # Licensee information
    licensee_name = models.CharField(
        max_length=200,
        help_text='Name of the licensed organization'
    )
    licensee_email = models.EmailField(
        help_text='Contact email for the licensee'
    )
    licensee_company = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='Company name'
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
        help_text='When the license was imported'
    )
    starts_at = models.DateTimeField(
        help_text='When the license becomes valid'
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the license expires (null = perpetual)'
    )
    activated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the license was activated (bound to machine)'
    )
    
    # Resource limits - PROTECTED BY SIGNATURE
    max_tenants = models.PositiveIntegerField(
        default=1,
        help_text='Maximum number of tenants allowed'
    )
    max_users_per_tenant = models.PositiveIntegerField(
        default=10,
        help_text='Maximum users per tenant'
    )
    max_proxies_per_tenant = models.PositiveIntegerField(
        default=5,
        help_text='Maximum proxies per tenant'
    )
    max_repositories_per_tenant = models.PositiveIntegerField(
        default=5,
        help_text='Maximum repositories per tenant'
    )
    max_storage_gb = models.PositiveIntegerField(
        default=100,
        help_text='Maximum storage in GB'
    )
    
    # Feature flags - PROTECTED BY SIGNATURE
    features = models.JSONField(
        default=dict,
        blank=True,
        help_text='Feature flags'
    )
    
    # Security fields
    signature = models.TextField(
        default='',
        blank=True,
        help_text='Digital signature (RSA)'
    )
    checksum = models.CharField(
        max_length=64,
        default='',
        blank=True,
        help_text='SHA256 checksum of critical fields'
    )
    machine_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text='Hardware fingerprint for machine binding'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=LicenseStatus.choices,
        default=LicenseStatus.ACTIVE,
        help_text='License status'
    )
    
    # Tamper detection
    original_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Original imported license data (for verification)'
    )
    tamper_detected = models.BooleanField(
        default=False,
        help_text='Whether tampering was detected'
    )
    
    class Meta:
        ordering = ['-issued_at']
        verbose_name = 'License'
        verbose_name_plural = 'Licenses'
    
    def __str__(self):
        return f'{self.licensee_name} - {self.get_edition_display()}'
    
    def clean(self):
        """Validate license integrity."""
        super().clean()
        
        # Verify signature on save
        if not self.verify_integrity():
            raise ValidationError("License signature verification failed. Data may have been tampered with.")
        
        # Verify machine fingerprint if bound
        if self.machine_fingerprint:
            if not HardwareFingerprint.verify_machine_id(self.machine_fingerprint):
                raise ValidationError("License is bound to a different machine.")
    
    def save(self, *args, **kwargs):
        """Override save to enforce integrity check."""
        # Skip integrity check for certain operations
        skip_check = kwargs.pop('skip_integrity_check', False)
        
        if not skip_check:
            self.full_clean()
        
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self) -> bool:
        """Check if license is currently valid."""
        # Check status
        if self.status != self.LicenseStatus.ACTIVE:
            return False
        
        # Check if activated
        if not self.activated_at:
            return False
        
        # Check time validity
        now = timezone.now()
        if self.starts_at > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        
        # Check integrity
        if not self.verify_integrity():
            return False
        
        # Check machine binding
        if self.machine_fingerprint:
            if not HardwareFingerprint.verify_machine_id(self.machine_fingerprint):
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
    
    @property
    def machine_bound(self) -> bool:
        """Check if this license is bound to a specific machine."""
        return bool(self.machine_fingerprint)
    
    def verify_integrity(self) -> bool:
        """
        Verify license data integrity.
        
        Checks:
        1. Signature is valid
        2. Checksum matches current data
        3. No tampering detected
        
        Returns:
            True if license is intact
        """
        if self.tamper_detected:
            return False
        
        # Verify signature
        if not LicenseSigner.verify_signature(self.original_data, self.signature):
            self._mark_tampered("Signature verification failed")
            return False
        
        # Verify checksum
        current_checksum = self._calculate_checksum()
        if current_checksum != self.checksum:
            self._mark_tampered(f"Checksum mismatch: expected {self.checksum[:16]}..., got {current_checksum[:16]}...")
            return False
        
        return True
    
    def _mark_tampered(self, reason: str = "Tampering detected"):
        """Mark license as tampered and save to prevent future use."""
        self.tamper_detected = True
        self.status = 'revoked'
        # Use update to avoid triggering save() validation
        License.objects.filter(pk=self.pk).update(
            tamper_detected=True,
            status='revoked'
        )
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum of current critical fields."""
        # MUST match the fields in generate_license.py calculate_checksum()
        critical_fields = {
            "license_key": self.license_key,
            "edition": self.edition,
            "limits": {
                "max_tenants": self.max_tenants,
                "max_users_per_tenant": self.max_users_per_tenant,
                "max_proxies_per_tenant": self.max_proxies_per_tenant,
                "max_repositories_per_tenant": self.max_repositories_per_tenant,
                "max_storage_gb": self.max_storage_gb,
            },
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "machine_id": self.machine_fingerprint,
        }
        
        serialized = json.dumps(critical_fields, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def has_feature(self, feature_name: str) -> bool:
        """
        Check if a feature is enabled in this license.
        
        Args:
            feature_name: Name of the feature to check
        
        Returns:
            True if feature is enabled
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
        """Get all license limits."""
        return {
            'max_tenants': self.max_tenants,
            'max_users_per_tenant': self.max_users_per_tenant,
            'max_proxies_per_tenant': self.max_proxies_per_tenant,
            'max_repositories_per_tenant': self.max_repositories_per_tenant,
            'max_storage_gb': self.max_storage_gb,
        }
    
    def check_quota(self, resource_type: str, current_count: int) -> tuple[bool, str]:
        """
        Check if a resource quota is exceeded.
        
        Args:
            resource_type: Type of resource (tenants, users, proxies, etc.)
            current_count: Current count of the resource
        
        Returns:
            Tuple of (is_within_limit, error_message)
        """
        limits = {
            'tenants': self.max_tenants,
            'users': self.max_users_per_tenant,
            'proxies': self.max_proxies_per_tenant,
            'repositories': self.max_repositories_per_tenant,
        }
        
        limit = limits.get(resource_type)
        if limit is None:
            return True, ""
        
        if current_count >= limit:
            return False, f"License limit exceeded: {resource_type} ({current_count}/{limit})"
        
        return True, ""
    
    @classmethod
    def import_license(cls, encoded_license: str) -> 'License':
        """
        Import a license from encoded string.
        
        This is the ONLY way to create a valid license.
        Direct database manipulation will fail signature verification.
        
        Args:
            encoded_license: Encoded license string
        
        Returns:
            Created License instance
        
        Raises:
            ValueError: If license is invalid
        """
        # Decode license
        license_data, signature = LicenseEncoder.decode(encoded_license)
        
        # Verify signature
        if not LicenseSigner.verify_signature(license_data, signature):
            raise ValueError("License signature verification failed")
        
        # Check if license key already exists
        license_key = license_data.get("license_key")
        if cls.objects.filter(license_key=license_key).exists():
            raise ValueError("License key already imported")
        
        # Extract limits
        limits = license_data.get("limits", {})
        
        # Parse dates
        starts_at = None
        if license_data.get("starts_at"):
            from datetime import datetime
            starts_at = datetime.fromisoformat(license_data["starts_at"].replace('Z', '+00:00'))
        else:
            starts_at = timezone.now()
        
        expires_at = None
        if license_data.get("expires_at"):
            from datetime import datetime
            expires_at = datetime.fromisoformat(license_data["expires_at"].replace('Z', '+00:00'))
        
        # Calculate checksum from original data
        checksum = LicenseSigner.calculate_checksum(license_data)
        
        # Create license (INACTIVE until activated)
        license = cls(
            license_key=license_key,
            licensee_name=license_data.get("licensee", {}).get("name", "Unknown"),
            licensee_email=license_data.get("licensee", {}).get("email", "unknown@example.com"),
            edition=license_data.get("edition", "community"),
            starts_at=starts_at,
            expires_at=expires_at,
            max_tenants=limits.get("max_tenants", 1),
            max_users_per_tenant=limits.get("max_users_per_tenant", 10),
            max_proxies_per_tenant=limits.get("max_proxies_per_tenant", 5),
            max_repositories_per_tenant=limits.get("max_repositories_per_tenant", 5),
            max_storage_gb=limits.get("max_storage_gb", 100),
            features=license_data.get("features", {}),
            signature=signature,
            checksum=checksum,
            machine_fingerprint=license_data.get("machine_id"),  # Pre-bound machine ID (optional)
            original_data=license_data,
            status=cls.LicenseStatus.INACTIVE,  # Requires activation
        )
        
        # Save with integrity check
        license.save()
        
        return license
    
    def activate(self, machine_id: str = None) -> tuple[bool, str]:
        """
        Activate license and bind to current machine.
        
        This is the SECOND step after import_license().
        Once activated, the license is bound to this machine and cannot be used elsewhere.
        
        Args:
            machine_id: Optional machine fingerprint. If not provided, uses current machine.
        
        Returns:
            (success, message) tuple
        """
        if self.status == self.LicenseStatus.ACTIVE:
            # Already active, verify machine fingerprint
            if self.machine_fingerprint:
                from .crypto import HardwareFingerprint
                current_machine = machine_id or HardwareFingerprint.get_machine_id()
                if current_machine != self.machine_fingerprint:
                    return False, "License is bound to a different machine"
            return True, "License already active on this machine"
        
        if self.status == self.LicenseStatus.REVOKED:
            return False, "License has been revoked"
        
        # Bind to machine
        from .crypto import HardwareFingerprint
        self.machine_fingerprint = machine_id or HardwareFingerprint.get_machine_id()
        self.status = self.LicenseStatus.ACTIVE
        self.activated_at = timezone.now()
        
        # Recalculate checksum to include machine binding
        self.checksum = LicenseSigner.calculate_checksum({
            **self.original_data,
            "machine_id": self.machine_fingerprint,
            "activated_at": self.activated_at.isoformat(),
        })
        
        self.save()
        
        # Create audit log
        LicenseAuditLog.objects.create(
            license=self,
            action="activated",
            details={"machine_fingerprint": self.machine_fingerprint}
        )
        
        return True, f"License activated successfully. Bound to machine: {self.machine_fingerprint[:16]}..."
    
    def deactivate(self) -> tuple[bool, str]:
        """
        Deactivate license (for migration to another machine).
        
        WARNING: This should be used carefully and may require
        authorization from the license server in production.
        
        Returns:
            (success, message) tuple
        """
        if self.status != self.LicenseStatus.ACTIVE:
            return False, "License is not active"
        
        old_fingerprint = self.machine_fingerprint
        self.status = self.LicenseStatus.INACTIVE
        self.machine_fingerprint = None
        self.save()
        
        # Create audit log
        LicenseAuditLog.objects.create(
            license=self,
            action="deactivated",
            details={"previous_machine": old_fingerprint}
        )
        
        return True, "License deactivated. Can be activated on another machine."
    
    @classmethod
    def import_from_data(cls, license_data: dict, signature: str) -> 'License':
        """
        Import a license from data dict and signature.
        
        Alternative to import_license() for direct JSON import.
        
        Args:
            license_data: License data dictionary
            signature: License signature
            
        Returns:
            Created License instance
            
        Raises:
            ValueError: If license is invalid
        """
        # Verify signature
        if not LicenseSigner.verify_signature(license_data, signature):
            raise ValueError("License signature verification failed")
        
        # Check if license key already exists
        license_key = license_data.get("license_key")
        if cls.objects.filter(license_key=license_key).exists():
            raise ValueError("License key already imported")
        
        # Extract limits
        limits = license_data.get("limits", {})
        
        # Parse dates
        starts_at = timezone.now()
        expires_at = None
        if license_data.get("expires_at"):
            from datetime import datetime
            expires_at = datetime.fromisoformat(license_data["expires_at"].replace('Z', '+00:00'))
        
        # Calculate checksum
        checksum = LicenseSigner.calculate_checksum(license_data)
        
        # Create license
        license = cls(
            license_key=license_key,
            licensee_name=license_data.get("licensee", {}).get("name", "Unknown"),
            licensee_email=license_data.get("licensee", {}).get("email", "unknown@example.com"),
            edition=license_data.get("edition", "community"),
            starts_at=starts_at,
            expires_at=expires_at,
            max_tenants=limits.get("max_tenants", 1),
            max_users_per_tenant=limits.get("max_users_per_tenant", 10),
            max_proxies_per_tenant=limits.get("max_proxies_per_tenant", 5),
            max_repositories_per_tenant=limits.get("max_repositories_per_tenant", 5),
            max_storage_gb=limits.get("max_storage_gb", 100),
            features=license_data.get("features", {}),
            signature=signature,
            checksum=checksum,
            machine_fingerprint=license_data.get("machine_id"),
            original_data=license_data,
            status=cls.LicenseStatus.ACTIVE,
        )
        
        # Save with integrity check
        license.save()
        
        return license
    
    @classmethod
    def get_active_license(cls) -> 'License':
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
    
    def revoke(self, reason: str = ""):
        """
        Revoke this license.
        
        Args:
            reason: Reason for revocation
        """
        self.status = self.LicenseStatus.REVOKED
        self.save(skip_integrity_check=True)
        
        # Log the revocation
        LicenseAuditLog.objects.create(
            license=self,
            action='revoked',
            details={'reason': reason}
        )


class LicenseAuditLog(models.Model):
    """
    Audit log for license operations.
    
    Tracks all license-related actions for security and compliance.
    """
    
    class ActionType(models.TextChoices):
        IMPORTED = 'imported', 'Imported'
        ACTIVATED = 'activated', 'Activated'
        REVOKED = 'revoked', 'Revoked'
        EXPIRED = 'expired', 'Expired'
        TAMPER_DETECTED = 'tamper_detected', 'Tamper Detected'
        QUOTA_EXCEEDED = 'quota_exceeded', 'Quota Exceeded'
    
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
    action = models.CharField(
        max_length=30,
        choices=ActionType.choices,
        default=ActionType.IMPORTED,
        help_text='Action type'
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional details'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the action'
    )
    user_agent = models.CharField(
        max_length=255,
        blank=True,
        help_text='User agent'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the action occurred'
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'License Audit Log'
        verbose_name_plural = 'License Audit Logs'
    
    def __str__(self):
        return f'{self.license.license_key} - {self.get_action_display()}'


class QuotaUsage(models.Model):
    """
    Track quota usage for enforcement.
    
    This model provides real-time quota tracking separate from
    the actual resource counts, preventing race conditions and
    providing audit trail.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    license = models.OneToOneField(
        License,
        on_delete=models.CASCADE,
        related_name='quota_usage'
    )
    
    # Current usage counts
    tenants_count = models.PositiveIntegerField(default=0)
    total_users = models.PositiveIntegerField(default=0)
    total_proxies = models.PositiveIntegerField(default=0)
    total_repositories = models.PositiveIntegerField(default=0)
    storage_used_gb = models.PositiveIntegerField(default=0)
    
    # Last sync time
    last_synced = models.DateTimeField(
        auto_now=True,
        help_text='When usage was last synced'
    )
    
    class Meta:
        verbose_name = 'Quota Usage'
        verbose_name_plural = 'Quota Usage'
    
    def sync(self):
        """Sync usage counts from actual data."""
        from tenants.models import Tenant
        from accounts.models import User
        from nodes.models import ProxyNode
        from repository.models import Repository
        
        self.tenants_count = Tenant.objects.filter(is_active=True).count()
        self.total_users = User.objects.filter(is_active=True).count()
        self.total_proxies = ProxyNode.objects.filter(status='online').count()
        self.total_repositories = Repository.objects.count()
        # Storage would need to be calculated from actual usage
        
        self.save()
    
    def check_limits(self) -> dict:
        """
        Check if any limits are exceeded.
        
        Returns:
            Dictionary of limit status
        """
        license = self.license
        return {
            'tenants': {
                'used': self.tenants_count,
                'limit': license.max_tenants,
                'exceeded': self.tenants_count >= license.max_tenants,
            },
            'users': {
                'used': self.total_users,
                'limit': license.max_users_per_tenant,
                'exceeded': self.total_users >= license.max_users_per_tenant,
            },
            'proxies': {
                'used': self.total_proxies,
                'limit': license.max_proxies_per_tenant,
                'exceeded': self.total_proxies >= license.max_proxies_per_tenant,
            },
            'repositories': {
                'used': self.total_repositories,
                'limit': license.max_repositories_per_tenant,
                'exceeded': self.total_repositories >= license.max_repositories_per_tenant,
            },
            'storage': {
                'used': self.storage_used_gb,
                'limit': license.max_storage_gb,
                'exceeded': self.storage_used_gb >= license.max_storage_gb,
            },
        }
