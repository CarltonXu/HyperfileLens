"""
HyperFileLens Backend - Repository Models

This module defines the data models for backup repository management.
"""

import uuid
from django.db import models
from accounts.models import User


class Repository(models.Model):
    """
    Represents a backup repository where backup data is stored.
    """
    
    # Repository type choices
    TYPE_LOCAL = 'local'
    TYPE_NFS = 'nfs'
    TYPE_S3 = 's3'
    TYPE_AZURE = 'azure'
    TYPE_GCS = 'gcs'
    
    TYPE_CHOICES = [
        (TYPE_LOCAL, 'Local Filesystem'),
        (TYPE_NFS, 'NFS Share'),
        (TYPE_S3, 'Amazon S3'),
        (TYPE_AZURE, 'Azure Blob Storage'),
        (TYPE_GCS, 'Google Cloud Storage'),
    ]
    
    # Status choices
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_ERROR = 'error'
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_ERROR, 'Error'),
    ]
    
    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Repository name")
    description = models.TextField(blank=True, help_text="Repository description")
    
    # Type and configuration
    repo_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_LOCAL,
        help_text="Repository type"
    )
    config = models.JSONField(
        default=dict,
        help_text="Repository configuration (credentials, paths, etc.)"
    )
    
    # Storage information
    path = models.CharField(
        max_length=1024,
        blank=True,
        help_text="Storage path or bucket name"
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
        default=STATUS_ACTIVE,
        help_text="Repository status"
    )
    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last synchronization time"
    )
    
    # Features
    supports_compression = models.BooleanField(
        default=True,
        help_text="Supports data compression"
    )
    supports_encryption = models.BooleanField(
        default=False,
        help_text="Supports data encryption"
    )
    is_readonly = models.BooleanField(
        default=False,
        help_text="Repository is read-only"
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
    
    def update_usage(self, used_space):
        """Update used space."""
        self.used_space = used_space
        self.save(update_fields=['used_space', 'updated_at'])
    
    def sync_space_usage(self):
        """Synchronize space usage with actual storage."""
        # In production, this would calculate actual space used
        # by querying the storage backend
        pass
