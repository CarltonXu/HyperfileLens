"""
HyperFileLens Backend - Repository Models

This module defines the data models for backup repository management.
Repository is the target storage for backup data, managed by Kopia.
"""

import uuid
import logging
from django.db import models
from accounts.models import User
from nodes.models import Node
from common.encryption import encrypt_value, decrypt_value, is_encrypted


logger = logging.getLogger(__name__)


class Repository(models.Model):
    """
    Represents a backup repository where backup data is stored.
    
    This is a Kopia repository that stores backup snapshots.
    It needs to be initialized before use and bound to a Node for operations.
    """
    
    # Repository type choices
    TYPE_LOCAL = 'local'
    TYPE_NFS = 'nfs'
    TYPE_NAS = 'nas'  # NAS/NFS/CIFS unified type
    TYPE_S3 = 's3'
    TYPE_AZURE = 'azure'
    TYPE_GCS = 'gcs'
    
    TYPE_CHOICES = [
        (TYPE_LOCAL, 'Local Filesystem'),
        (TYPE_NFS, 'NFS Share'),
        (TYPE_NAS, 'NAS/NFS/CIFS'),
        (TYPE_S3, 'Amazon S3'),
        (TYPE_AZURE, 'Azure Blob Storage'),
        (TYPE_GCS, 'Google Cloud Storage'),
    ]
    
    # Status choices
    STATUS_INITIALIZING = 'initializing'
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_ERROR = 'error'
    
    STATUS_CHOICES = [
        (STATUS_INITIALIZING, 'Initializing'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_ERROR, 'Error'),
    ]
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic information
    name = models.CharField(
        max_length=255, 
        unique=True,
        help_text="Repository name"
    )
    description = models.TextField(
        blank=True, 
        help_text="Repository description"
    )
    
    # Type and configuration
    repo_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_S3,
        help_text="Repository type"
    )
    
    # Connection configuration (JSON, varies by type)
    # S3: { "endpoint": "https://s3.amazonaws.com", "bucket": "backup-bucket", "region": "us-east-1", "prefix": "" }
    # NFS: { "server": "192.168.1.200", "export_path": "/backup" }
    # LOCAL: { "path": "/backup/hyperfilelens" }
    # Azure: { "account": "", "container": "", "prefix": "" }
    # GCS: { "bucket": "", "prefix": "" }
    config = models.JSONField(
        default=dict,
        help_text="Connection configuration"
    )
    
    # Credentials (encrypted in production)
    # S3: { "access_key": "AKIA...", "secret_key": "encrypted_secret" }
    # Azure: { "connection_string": "..." }
    # GCS: { "credentials_json": "..." }
    # NFS/LOCAL: {} (no credentials usually needed)
    credentials = models.JSONField(
        default=dict,
        help_text="Encrypted credentials for authentication"
    )
    
    # Bound Node for operations
    bound_node = models.ForeignKey(
        Node,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='repositories',
        help_text="Node that performs operations on this repository"
    )
    
    # Kopia repository state
    kopia_initialized = models.BooleanField(
        default=False,
        help_text="Whether Kopia repository has been initialized"
    )
    kopia_repository_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Kopia repository unique identifier"
    )
    encryption_algorithm = models.CharField(
        max_length=50,
        blank=True,
        default='AES256-GCM-HMAC-SHA256',
        help_text="Encryption algorithm used by Kopia"
    )
    kopia_password = models.TextField(
        blank=True,
        help_text="Encrypted Kopia repository password for non-interactive operations"
    )
    
    # Storage information
    path = models.CharField(
        max_length=1024,
        blank=True,
        help_text="Storage path or bucket name (deprecated, use config)"
    )
    # Actual capacity detected from storage (via test connection)
    capacity = models.BigIntegerField(
        default=0,
        help_text="Actual total capacity in bytes detected from storage (0 = not detected)"
    )
    used_space = models.BigIntegerField(
        default=0,
        help_text="Used space in bytes"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_INACTIVE,
        help_text="Repository status"
    )
    status_message = models.TextField(
        blank=True,
        help_text="Status message or error details"
    )
    
    # Connection test
    last_connection_test = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last connection test timestamp"
    )
    connection_test_result = models.TextField(
        blank=True,
        help_text="Connection test result summary"
    )
    connection_test_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed connection test results (connectivity, write_test, space_info)"
    )
    
    # Features
    supports_compression = models.BooleanField(
        default=True,
        help_text="Supports data compression"
    )
    supports_encryption = models.BooleanField(
        default=True,
        help_text="Supports data encryption"
    )
    compression_type = models.CharField(
        max_length=50,
        blank=True,
        default='zstd',
        help_text="Compression algorithm used"
    )
    is_readonly = models.BooleanField(
        default=False,
        help_text="Repository is read-only"
    )

    # === Quota Management ===
    # User-defined quota for capacity planning and alerts (separate from actual capacity)
    quota_enabled = models.BooleanField(
        default=False,
        help_text="Enable quota management and alerts"
    )
    quota_bytes = models.BigIntegerField(
        default=0,
        help_text="User-defined quota limit in bytes for capacity planning and alerts (0 = unlimited)"
    )
    quota_warning_threshold = models.IntegerField(
        default=80,
        help_text="Quota warning threshold percentage (alert when usage >= this % of quota, default: 80%)"
    )

    # === Health Monitoring ===
    last_health_check = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last health check timestamp"
    )
    health_status = models.CharField(
        max_length=20,
        default='unknown',
        choices=[
            ('healthy', 'Healthy'),
            ('warning', 'Warning'),
            ('error', 'Error'),
            ('unknown', 'Unknown')
        ],
        help_text="Overall health status"
    )
    health_score = models.IntegerField(
        default=100,
        help_text="Health score (0-100)"
    )
    health_check_results = models.JSONField(
        default=dict,
        blank=True,
        help_text="Last health check results"
    )

    # === Auto Cleanup ===
    auto_cleanup_enabled = models.BooleanField(
        default=False,
        help_text="Enable automatic cleanup of old snapshots"
    )
    cleanup_threshold_percent = models.IntegerField(
        default=90,
        help_text="Cleanup threshold percentage"
    )
    cleanup_retention_days = models.IntegerField(
        default=90,
        help_text="Retention days for snapshots"
    )
    last_cleanup_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last cleanup timestamp"
    )

    # === Replication ===
    replication_enabled = models.BooleanField(
        default=False,
        help_text="Enable replication to secondary storage"
    )
    replication_target = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replica_sources',
        help_text="Target repository for replication"
    )
    replication_status = models.CharField(
        max_length=20,
        default='disabled',
        choices=[
            ('disabled', 'Disabled'),
            ('pending', 'Pending'),
            ('syncing', 'Syncing'),
            ('error', 'Error'),
            ('uptodate', 'Up to date')
        ],
        help_text="Replication status"
    )
    last_replication_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful replication timestamp"
    )

    # === Statistics ===
    snapshot_count = models.IntegerField(
        default=0,
        help_text="Number of snapshots in repository"
    )
    last_backup_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last backup timestamp"
    )
    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last synchronization time"
    )
    
    # Metadata
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='repositories',
        help_text="Repository owner"
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='repositories',
        help_text='Tenant this repository belongs to'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'repositories'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['repo_type']),
            models.Index(fields=['status']),
            models.Index(fields=['bound_node']),
            models.Index(fields=['kopia_initialized']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_repo_type_display()})"
    
    @property
    def available_space(self):
        """Calculate available space in bytes."""
        if self.capacity == 0:
            return None  # Unlimited
        return max(0, self.capacity - self.used_space)
    
    @property
    def usage_percentage(self):
        """Calculate storage usage percentage."""
        if self.capacity == 0:
            return None  # Unlimited
        return (self.used_space / self.capacity) * 100 if self.capacity > 0 else 0
    
    @property
    def is_ready(self):
        """Check if repository is ready for backup operations."""
        return (
            self.status == self.STATUS_ACTIVE and
            self.kopia_initialized and
            self.bound_node is not None
        )
    
    def update_usage(self, used_space):
        """Update used space."""
        self.used_space = used_space
        self.save(update_fields=['used_space', 'updated_at'])

    def set_kopia_password(self, password):
        """Encrypt and store the Kopia repository password."""
        self.kopia_password = encrypt_value(password) if password else ''

    def get_kopia_password(self):
        """Return the decrypted Kopia repository password."""
        if not self.kopia_password:
            return ''
        if not is_encrypted(self.kopia_password):
            return self.kopia_password
        try:
            return decrypt_value(self.kopia_password)
        except Exception as exc:
            logger.warning(
                "Failed to decrypt Kopia repository password repository_id=%s: %s",
                self.id,
                exc,
            )
            return ''
    
    def sync_space_usage(self):
        """Synchronize space usage with actual storage."""
        # In production, this would query the Node for actual space usage
        pass
    
    def save(self, *args, **kwargs):
        """
        Override save to automatically encrypt sensitive credential fields.
        
        The following fields are encrypted before storage:
        - credentials.secret_key (for S3)
        - credentials.password (for NAS/CIFS)
        """
        # Encrypt sensitive fields in credentials
        if self.credentials:
            credentials = self.credentials.copy()  # Don't modify original
            
            # Encrypt secret_key if present and not already encrypted
            if 'secret_key' in credentials and credentials['secret_key']:
                if not is_encrypted(credentials['secret_key']):
                    credentials['secret_key'] = encrypt_value(credentials['secret_key'])
            
            # Encrypt password if present and not already encrypted
            if 'password' in credentials and credentials['password']:
                if not is_encrypted(credentials['password']):
                    credentials['password'] = encrypt_value(credentials['password'])
            
            # Update credentials with encrypted values
            self.credentials = credentials
        
        super().save(*args, **kwargs)
    
    def get_decrypted_credentials(self):
        """
        Get credentials with decrypted sensitive fields.
        
        This method should only be used when passing credentials to
        authorized components (like Proxy nodes for backup operations).
        
        Returns:
            dict: Credentials with decrypted secret_key and password
        """
        if not self.credentials:
            return {}
        
        credentials = self.credentials.copy()
        
        # Decrypt secret_key
        if 'secret_key' in credentials and credentials['secret_key']:
            try:
                credentials['secret_key'] = decrypt_value(credentials['secret_key'])
            except Exception:
                # If decryption fails, the value might not be encrypted (legacy data)
                pass
        
        # Decrypt password
        if 'password' in credentials and credentials['password']:
            try:
                credentials['password'] = decrypt_value(credentials['password'])
            except Exception:
                # If decryption fails, the value might not be encrypted (legacy data)
                pass
        
        return credentials
    
    def get_masked_credentials(self):
        """
        Get credentials with masked sensitive fields for display.
        
        Returns:
            dict: Credentials with masked secret_key and password,
                  suitable for API responses and UI display.
        """
        if not self.credentials:
            return {}
        
        credentials = self.credentials.copy()
        
        # Mask secret_key (show first 4 and last 4 characters)
        if 'secret_key' in credentials and credentials['secret_key']:
            key = credentials['secret_key']
            if len(key) > 8:
                credentials['secret_key'] = f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"
            else:
                credentials['secret_key'] = '****'
        
        # Remove password entirely (never show even masked)
        if 'password' in credentials:
            credentials['password'] = '****'
        
        return credentials
