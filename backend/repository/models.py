"""
HyperFileLens Backend - Repository Models

This module defines the data models for backup repository management.
Repository is the target storage for backup data, managed by Kopia.
"""

import uuid
from django.db import models
from accounts.models import User
from nodes.models import Node


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
    # Encryption password is stored encrypted in production
    
    # Storage information
    path = models.CharField(
        max_length=1024,
        blank=True,
        help_text="Storage path or bucket name (deprecated, use config)"
    )
    capacity = models.BigIntegerField(
        default=0,
        help_text="Total capacity in bytes (0 = unlimited)"
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
        help_text="Connection test result"
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
    
    # Statistics (updated by Node reports)
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
    
    def sync_space_usage(self):
        """Synchronize space usage with actual storage."""
        # In production, this would query the Node for actual space usage
        pass
