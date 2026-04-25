"""
HyperFileLens Backend - Source Resource Models

Source resources are the data sources for backup operations.
They can be NAS, NFS, CIFS, Object Storage, or Local Filesystem.
"""

import uuid
from django.db import models
from accounts.models import User
from nodes.models import Node


class SourceResource(models.Model):
    """
    Represents a backup source resource where data originates from.
    
    Types:
    - NAS: Network Attached Storage
    - NFS: Network File System share
    - CIFS: Common Internet File System (SMB)
    - S3: Object storage as source (for migration scenarios)
    - LOCAL: Local filesystem (Node installed directly on source machine)
    """
    
    # Resource type choices
    TYPE_NAS = 'nas'
    TYPE_NFS = 'nfs'
    TYPE_CIFS = 'cifs'
    TYPE_S3 = 's3'
    TYPE_LOCAL = 'local'
    
    TYPE_CHOICES = [
        (TYPE_NAS, 'NAS Storage'),
        (TYPE_NFS, 'NFS Share'),
        (TYPE_CIFS, 'CIFS/SMB Share'),
        (TYPE_S3, 'Object Storage'),
        (TYPE_LOCAL, 'Local Filesystem'),
    ]
    
    # Mount status choices
    MOUNT_UNMOUNTED = 'unmounted'
    MOUNT_MOUNTED = 'mounted'
    MOUNT_ERROR = 'error'
    
    MOUNT_STATUS_CHOICES = [
        (MOUNT_UNMOUNTED, 'Unmounted'),
        (MOUNT_MOUNTED, 'Mounted'),
        (MOUNT_ERROR, 'Mount Error'),
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
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic information
    name = models.CharField(max_length=255, unique=True, help_text="Resource name")
    description = models.TextField(blank=True, help_text="Resource description")
    resource_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_NFS,
        help_text="Resource type"
    )
    
    # Connection configuration (JSON, varies by type)
    # NFS: { "server": "192.168.1.100", "export_path": "/data", "mount_options": "rw,hard" }
    # CIFS: { "server": "192.168.1.100", "share": "share1", "domain": "DOMAIN", "mount_options": "" }
    # NAS: { "server": "192.168.1.100", "share": "share1", "protocol": "nfs|cifs", ... }
    # S3: { "endpoint": "https://s3.amazonaws.com", "bucket": "source-bucket", "prefix": "data/", "region": "us-east-1" }
    # LOCAL: {} (empty, paths specified in backup tasks)
    config = models.JSONField(
        default=dict,
        help_text="Connection configuration"
    )
    
    # Credentials (encrypted in production, JSON for now)
    # NFS: {} (usually no credentials, or Kerberos)
    # CIFS: { "username": "user", "password": "encrypted_password" }
    # S3: { "access_key": "AKIA...", "secret_key": "encrypted_secret" }
    # LOCAL: {} (no credentials needed)
    credentials = models.JSONField(
        default=dict,
        help_text="Encrypted credentials for authentication"
    )
    
    # Bound Node for mounting and operations
    bound_node = models.ForeignKey(
        Node,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_resources',
        help_text="Node that mounts and accesses this resource"
    )
    
    # Mount information (reported by Node)
    mount_status = models.CharField(
        max_length=20,
        choices=MOUNT_STATUS_CHOICES,
        default=MOUNT_UNMOUNTED,
        help_text="Current mount status on bound node"
    )
    mount_point = models.CharField(
        max_length=512,
        blank=True,
        help_text="Mount point path on the node, e.g., /mnt/hyperfilelens/source-001"
    )
    mount_error = models.TextField(
        blank=True,
        help_text="Mount error message if any"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        help_text="Resource status"
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
    
    # Statistics (reported by Node)
    total_size = models.BigIntegerField(
        default=0,
        help_text="Total size of the source in bytes"
    )
    file_count = models.BigIntegerField(
        default=0,
        help_text="Total number of files"
    )
    
    # Metadata
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='source_resources',
        help_text="Resource owner"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'source_resources'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['resource_type']),
            models.Index(fields=['status']),
            models.Index(fields=['bound_node']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_resource_type_display()})"
    
    @property
    def is_mounted(self):
        """Check if the resource is currently mounted."""
        return self.mount_status == self.MOUNT_MOUNTED
    
    @property
    def requires_mount(self):
        """Check if this resource type requires mounting."""
        return self.resource_type in [self.TYPE_NAS, self.TYPE_NFS, self.TYPE_CIFS]
    
    def get_effective_mount_point(self):
        """Get the mount point path for this resource."""
        if self.mount_point:
            return self.mount_point
        # Default mount point pattern
        return f"/mnt/hyperfilelens/source-{str(self.id)[:8]}"
