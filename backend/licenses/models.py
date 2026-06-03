"""
License Models for HyperFileLens

Design Principles:
1. One tenant = One active license
2. New activation code renews (extends expiry) or upgrades (increases limits)
3. License history is preserved for audit
4. Machine binding: MAC + CPU ID + Tenant ID + User ID
"""

from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid
import json
import hashlib
import base64
import subprocess
import platform
import secrets
import os


class License(models.Model):
    """
    Active License for a tenant.
    
    Only one active license per tenant.
    New activation will archive the current license to history.
    """
    
    class LicenseStatus(models.TextChoices):
        """License status options."""
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        REVOKED = 'revoked', 'Revoked'
    
    class ChangeType(models.TextChoices):
        """Type of license change."""
        INITIAL = 'initial', 'Initial Activation'
        RENEWAL = 'renewal', 'Renewal (Extended Expiry)'
        UPGRADE = 'upgrade', 'Upgrade (Increased Limits)'
    
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
    
    # Version tracking
    version = models.PositiveIntegerField(
        default=1,
        help_text='License version (increments on each renewal/upgrade)'
    )
    change_type = models.CharField(
        max_length=20,
        choices=ChangeType.choices,
        default=ChangeType.INITIAL,
        help_text='Type of the latest change'
    )
    change_reason = models.CharField(
        max_length=200,
        blank=True,
        help_text='Reason for the latest change'
    )
    
    # Binding information
    machine_code = models.CharField(
        max_length=64,
        unique=True,
        help_text='Machine code: MAC + CPU + Tenant + User'
    )
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='license',
        help_text='Tenant this license is bound to (one-to-one)'
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
        help_text='Maximum number of users'
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
        help_text='Monthly AI insights quota'
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
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='When the license was last updated'
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
        return f'{self.license_key[:20]}... ({self.tenant.name}, v{self.version})'
    
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
    
    def archive_to_history(self, change_type: str, reason: str = '', changed_by=None):
        """
        Archive current license to history before renewal/upgrade.
        
        Args:
            change_type: Type of change (renewal/upgrade/revoke)
            reason: Reason for archiving
            changed_by: User who made the change (optional)
        """
        from .models import LicenseHistory  # Avoid circular import
        
        LicenseHistory.objects.create(
            # Original license info
            license_key=self.license_key,
            version=self.version,
            
            # Binding
            machine_code=self.machine_code,
            tenant=self.tenant,
            activated_by=self.activated_by,
            changed_by=changed_by,
            
            # Limits (snapshot)
            max_tenants=self.max_tenants,
            max_users=self.max_users,
            max_proxies=self.max_proxies,
            max_storage_gb=self.max_storage_gb,
            max_gateways=self.max_gateways,
            ai_insights_quota=self.ai_insights_quota,
            max_backup_tasks=self.max_backup_tasks,
            max_recovery_tasks=self.max_recovery_tasks,
            max_source_resources=self.max_source_resources,
            max_policies=self.max_policies,
            max_repositories=self.max_repositories,
            
            # Time
            issued_at=self.issued_at,
            expires_at=self.expires_at,
            activated_at=self.activated_at,
            archived_at=timezone.now(),
            
            # Status & change info
            status=self.status,
            signature=self.signature,
            change_type=change_type,
            change_reason=reason,
        )
    
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
            # Use the one-to-one relation
            license = getattr(tenant, 'license', None)
            if license and license.is_valid:
                return license
        except Exception:
            pass
        
        return None
    
    def check_quota(self, resource_type: str, additional: int = 1) -> tuple[bool, str]:
        """
        Check if creating additional resources would exceed the license quota.
        
        Args:
            resource_type: Type of resource to check (e.g., 'users', 'proxies', 'repositories')
            additional: Number of additional resources to create
            
        Returns:
            tuple: (is_allowed: bool, message: str)
        """
        from accounts.models import User
        from nodes.models import ProxyNode
        from repository.models import Repository
        from backup_tasks.models import BackupTask
        from recovery_tasks.models import RecoveryTask
        from source_resources.models import SourceResource
        from policies.models import BackupPolicy
        from tenants.models import Tenant
        from ai_query.models import AIQuery
        from gateways.models import Gateway
        from alerts.models import AlertPolicy
        from licenses.quota import SYSTEM_TENANT_NAME, get_platform_tenant_count

        def repository_reserved_storage_gb():
            total_bytes = 0
            for repo in Repository.objects.filter(tenant=self.tenant):
                if repo.quota_enabled and repo.quota_bytes > 0:
                    total_bytes += repo.quota_bytes
                elif repo.capacity > 0:
                    total_bytes += repo.capacity
                else:
                    total_bytes += repo.used_space
            return total_bytes / (1024 ** 3)
        
        # Mapping of resource types to limit fields and query functions
        quota_mapping = {
            'tenants': {
                'limit': 'max_tenants',
                'current': lambda: (
                    get_platform_tenant_count()
                    if self.tenant and self.tenant.name == SYSTEM_TENANT_NAME
                    else 0
                ),
                'name': 'tenants'
            },
            'users': {
                'limit': 'max_users',
                'current': lambda: User.objects.filter(tenant=self.tenant).count(),
                'name': 'users'
            },
            'proxies': {
                'limit': 'max_proxies',
                'current': lambda: ProxyNode.objects.filter(tenant=self.tenant).count(),
                'name': 'proxies'
            },
            'storage': {
                'limit': 'max_storage_gb',
                'current': repository_reserved_storage_gb,
                'name': 'storage (GB)'
            },
            'gateways': {
                'limit': 'max_gateways',
                'current': lambda: Gateway.objects.filter(tenant=self.tenant).count(),
                'name': 'gateways'
            },
            'ai_insights': {
                'limit': 'ai_insights_quota',
                'current': lambda: AIQuery.objects.filter(tenant=self.tenant).count(),
                'name': 'AI insights'
            },
            'backup_tasks': {
                'limit': 'max_backup_tasks',
                'current': lambda: BackupTask.objects.filter(tenant=self.tenant).count(),
                'name': 'backup tasks'
            },
            'recovery_tasks': {
                'limit': 'max_recovery_tasks',
                'current': lambda: RecoveryTask.objects.filter(tenant=self.tenant).count(),
                'name': 'recovery tasks'
            },
            'source_resources': {
                'limit': 'max_source_resources',
                'current': lambda: SourceResource.objects.filter(tenant=self.tenant).count(),
                'name': 'source resources'
            },
            'policies': {
                'limit': 'max_policies',
                'current': lambda: (
                    BackupPolicy.objects.filter(tenant=self.tenant).count()
                    + AlertPolicy.objects.filter(tenant=self.tenant).count()
                ),
                'name': 'policies'
            },
            'repositories': {
                'limit': 'max_repositories',
                'current': lambda: Repository.objects.filter(tenant=self.tenant).count(),
                'name': 'repositories'
            },
        }
        
        if resource_type not in quota_mapping:
            return True, ""
        
        mapping = quota_mapping[resource_type]
        limit = getattr(self, mapping['limit'], 0)
        
        # Unlimited (-1 means unlimited)
        if limit == -1:
            return True, ""
        
        current = mapping['current']()
        new_total = current + additional
        
        if new_total > limit:
            return False, f"Quota exceeded for {mapping['name']}. Current: {current:g}/{limit}, Requested: +{additional:g}"
        
        return True, ""


class LicenseHistory(models.Model):
    """
    Historical record of licenses for audit purposes.
    
    Created when:
    - License is renewed (new expiry date)
    - License is upgraded (new limits)
    - License is revoked
    """
    
    class ChangeType(models.TextChoices):
        INITIAL = 'initial', 'Initial Activation'
        RENEWAL = 'renewal', 'Renewal'
        UPGRADE = 'upgrade', 'Upgrade'
        REVOKED = 'revoked', 'Revoked'
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Original license info
    license_key = models.CharField(max_length=64, db_index=True)
    version = models.PositiveIntegerField(default=1)
    
    # Binding (tenant may be deleted, keep reference)
    machine_code = models.CharField(max_length=64)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        related_name='license_history'
    )
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='license_history'
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='license_changes'
    )
    
    # Limits snapshot
    max_tenants = models.PositiveIntegerField()
    max_users = models.PositiveIntegerField()
    max_proxies = models.PositiveIntegerField()
    max_storage_gb = models.PositiveIntegerField()
    max_gateways = models.PositiveIntegerField()
    ai_insights_quota = models.PositiveIntegerField()
    max_backup_tasks = models.PositiveIntegerField()
    max_recovery_tasks = models.PositiveIntegerField()
    max_source_resources = models.PositiveIntegerField()
    max_policies = models.PositiveIntegerField()
    max_repositories = models.PositiveIntegerField()
    
    # Time snapshot
    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField()
    archived_at = models.DateTimeField(help_text='When this license was archived')
    
    # Status & change info
    status = models.CharField(max_length=20)
    signature = models.TextField()
    change_type = models.CharField(max_length=20, choices=ChangeType.choices)
    change_reason = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-archived_at']
        verbose_name = 'License History'
        verbose_name_plural = 'License History'
    
    def __str__(self):
        return f'{self.license_key[:20]}... v{self.version} ({self.get_change_type_display()})'


class MachineCode(models.Model):
    """
    Machine code generation record.
    
    Stores the generated machine code for a tenant/user.
    One machine code per tenant (regenerated on request).
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True, help_text='Generated machine code')
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='machine_code_record'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='machine_codes'
    )
    
    # Machine components (for debugging/audit)
    mac_address = models.CharField(max_length=20, blank=True)
    cpu_id = models.CharField(max_length=100, blank=True)
    hostname = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.code} ({self.tenant.name if self.tenant else "N/A"})'


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
    gateways_count = models.PositiveIntegerField(default=0)
    backup_tasks_count = models.PositiveIntegerField(default=0)
    recovery_tasks_count = models.PositiveIntegerField(default=0)
    source_resources_count = models.PositiveIntegerField(default=0)
    policies_count = models.PositiveIntegerField(default=0)
    repositories_count = models.PositiveIntegerField(default=0)
    
    # Storage usage
    storage_used_gb = models.FloatField(default=0.0)
    
    # AI usage (reset monthly)
    ai_insights_used = models.PositiveIntegerField(default=0)
    ai_reset_date = models.DateField(null=True, blank=True, help_text='Date when AI quota was last reset')
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Quota Usage'
        verbose_name_plural = 'Quota Usage'
    
    def __str__(self):
        return f'Usage for {self.license.license_key[:20]}...'
    
    def check_limit(self, limit_type: str, requested: int = 1) -> tuple:
        """
        Check if requested amount is within limit.
        
        Returns:
            (is_within_limit, current_usage, limit)
        """
        limit_map = {
            'users': (self.users_count, self.license.max_users),
            'proxies': (self.proxies_count, self.license.max_proxies),
            'gateways': (self.gateways_count, self.license.max_gateways),
            'backup_tasks': (self.backup_tasks_count, self.license.max_backup_tasks),
            'recovery_tasks': (self.recovery_tasks_count, self.license.max_recovery_tasks),
            'source_resources': (self.source_resources_count, self.license.max_source_resources),
            'policies': (self.policies_count, self.license.max_policies),
            'repositories': (self.repositories_count, self.license.max_repositories),
            'storage_gb': (self.storage_used_gb, self.license.max_storage_gb),
            'ai_insights': (self.ai_insights_used, self.license.ai_insights_quota),
        }
        
        if limit_type not in limit_map:
            return (False, 0, 0)
        
        current, limit = limit_map[limit_type]
        is_within = (current + requested) <= limit
        
        return (is_within, current, limit)
    
    def reset_monthly_quotas(self):
        """Reset monthly quotas (AI insights)."""
        from django.utils import timezone
        today = timezone.now().date()
        
        if self.ai_reset_date.month != today.month or self.ai_reset_date.year != today.year:
            self.ai_insights_used = 0
            self.ai_reset_date = today
            self.save()


def generate_machine_code(tenant_id: str, user_id: str) -> tuple:
    """
    Generate a unique machine code based on hardware + tenant + user.
    
    Returns:
        (machine_code, components_dict)
    """
    components = {}
    
    # 1. Try to get cloud instance ID (AWS/GCP/Azure)
    cloud_id = _get_cloud_instance_id()
    if cloud_id:
        components['source'] = 'cloud'
        components['cloud_id'] = cloud_id
    else:
        # 2. Try motherboard UUID
        board_uuid = _get_board_uuid()
        if board_uuid:
            components['source'] = 'board_uuid'
            components['board_uuid'] = board_uuid
        else:
            # 3. Try disk serial
            disk_serial = _get_disk_serial()
            if disk_serial:
                components['source'] = 'disk_serial'
                components['disk_serial'] = disk_serial
            else:
                # 4. Fallback: MAC + hostname
                components['source'] = 'fallback'
                components['mac'] = _get_mac_address()
                components['hostname'] = platform.node()
    
    # Build unique identifier string with more entropy
    if components['source'] == 'cloud':
        unique_str = f"cloud:{components['cloud_id']}"
    elif components['source'] == 'board_uuid':
        unique_str = f"board:{components['board_uuid']}"
    elif components['source'] == 'disk_serial':
        unique_str = f"disk:{components['disk_serial']}"
    else:
        unique_str = f"mac:{components['mac']}:host:{components['hostname']}"
    
    # Add tenant and user binding
    unique_str += f":tenant:{tenant_id}:user:{user_id}"
    
    # Add timestamp for uniqueness (but stable within same day)
    from datetime import datetime
    date_str = datetime.now().strftime('%Y%m%d')
    unique_str += f":date:{date_str}"
    
    # Generate 128-bit (16 bytes) hash
    hash_bytes = hashlib.sha512(unique_str.encode()).digest()
    # Take first 16 bytes (128 bits)
    code_hex = hash_bytes[:16].hex().upper()
    
    # Format: HFL-MCH-XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX (128 bits = 32 hex chars)
    # Total: HFL-MCH- + 32 hex chars + 3 dashes = 39 chars
    machine_code = f"HFL-MCH-{code_hex[0:8]}-{code_hex[8:16]}-{code_hex[16:24]}-{code_hex[24:32]}"
    
    return machine_code, components


def _get_cloud_instance_id() -> str:
    """Try to get cloud provider instance ID."""
    # AWS
    try:
        result = subprocess.run(
            ['curl', '-s', '--max-time', '2', 'http://169.254.169.254/latest/meta-data/instance-id'],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.startswith('i-'):
            return f"aws:{result.stdout}"
    except Exception:
        pass
    
    # GCP
    try:
        result = subprocess.run(
            ['curl', '-s', '--max-time', '2', '-H', 'Metadata-Flavor: Google',
             'http://metadata.google.internal/computeMetadata/v1/instance/id'],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.isdigit():
            return f"gcp:{result.stdout}"
    except Exception:
        pass
    
    # Azure
    try:
        result = subprocess.run(
            ['curl', '-s', '--max-time', '2', '-H', 'Metadata: true',
             'http://169.254.169.254/metadata/instance/compute/vmId?api-version=2021-02-01&format=text'],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout:
            return f"azure:{result.stdout}"
    except Exception:
        pass
    
    return ""


def _get_board_uuid() -> str:
    """Get motherboard UUID (Linux only)."""
    try:
        if os.path.exists('/sys/class/dmi/id/board_uuid'):
            with open('/sys/class/dmi/id/board_uuid', 'r') as f:
                return f.read().strip()
    except Exception:
        pass
    
    # Try dmidecode
    try:
        result = subprocess.run(
            ['dmidecode', '-s', 'board-uuid'],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    
    return ""


def _get_disk_serial() -> str:
    """Get boot disk serial number."""
    try:
        # Linux
        if os.path.exists('/dev/sda'):
            result = subprocess.run(
                ['hdparm', '-I', '/dev/sda'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Serial Number:' in line:
                        return line.split(':')[1].strip()
    except Exception:
        pass
    
    return ""


def _get_mac_address() -> str:
    """Get primary MAC address."""
    try:
        # Linux
        if os.path.exists('/sys/class/net'):
            for iface in os.listdir('/sys/class/net'):
                if iface == 'lo':
                    continue
                addr_file = f'/sys/class/net/{iface}/address'
                if os.path.exists(addr_file):
                    with open(addr_file, 'r') as f:
                        mac = f.read().strip()
                        if mac and mac != '00:00:00:00:00:00':
                            return mac
    except Exception:
        pass
    
    # Fallback: use a random value (will change each time)
    return f"random:{secrets.token_hex(6)}"
