"""
HyperFileLens Backend - Backup Tasks Models

This module defines the data models for backup task management:
- BackupTask: Main backup task model
- BackupSnapshot: Snapshot/version information
- BackupFile: Individual file backup records
"""

import uuid
from django.db import models
from django.utils import timezone
from accounts.models import User


class BackupTask(models.Model):
    """
    Represents a backup task that defines what, when, and how to backup.
    """
    
    # Task status choices
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    
    # Task type choices
    TYPE_FULL = 'full'
    TYPE_INCREMENTAL = 'incremental'
    TYPE_DIFFERENTIAL = 'differential'
    
    TYPE_CHOICES = [
        (TYPE_FULL, 'Full Backup'),
        (TYPE_INCREMENTAL, 'Incremental Backup'),
        (TYPE_DIFFERENTIAL, 'Differential Backup'),
    ]
    
    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Task name")
    description = models.TextField(blank=True, help_text="Task description")
    
    # Source and target
    source_node = models.ForeignKey(
        'nodes.Node',
        on_delete=models.CASCADE,
        related_name='source_backup_tasks',
        help_text="Source node for backup"
    )
    target_repository = models.ForeignKey(
        'repository.Repository',
        on_delete=models.CASCADE,
        related_name='backup_tasks',
        help_text="Target repository for backup"
    )
    
    # Task configuration
    task_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_FULL,
        help_text="Type of backup"
    )
    paths = models.JSONField(
        default=list,
        help_text="List of paths to backup"
    )
    exclude_patterns = models.JSONField(
        default=list,
        blank=True,
        help_text="Patterns to exclude from backup"
    )
    compression_enabled = models.BooleanField(
        default=True,
        help_text="Enable compression"
    )
    encryption_enabled = models.BooleanField(
        default=False,
        help_text="Enable encryption"
    )
    
    # Scheduling
    schedule = models.ForeignKey(
        'policies.BackupPolicy',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        help_text="Associated backup policy"
    )
    next_run_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Next scheduled run time"
    )
    
    # Status and progress
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text="Current task status"
    )
    progress = models.IntegerField(
        default=0,
        help_text="Progress percentage (0-100)"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if failed"
    )
    
    # Retention
    retention_days = models.IntegerField(
        default=30,
        help_text="Number of days to retain snapshots"
    )
    max_snapshots = models.IntegerField(
        default=10,
        help_text="Maximum number of snapshots to keep"
    )
    
    # Metadata
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='backup_tasks',
        help_text="User who created the task"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Statistics
    total_files = models.IntegerField(default=0)
    backed_up_files = models.IntegerField(default=0)
    total_size = models.BigIntegerField(default=0)
    backed_up_size = models.BigIntegerField(default=0)
    skipped_files = models.IntegerField(default=0)
    failed_files = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'backup_tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['source_node', 'status']),
            models.Index(fields=['next_run_time']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    @property
    def duration(self):
        """Calculate task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def update_progress(self, backed_up_files, backed_up_size):
        """Update backup progress."""
        self.backed_up_files = backed_up_files
        self.backed_up_size = backed_up_size
        if self.total_files > 0:
            self.progress = int((backed_up_files / self.total_files) * 100)
        self.save(update_fields=['backed_up_files', 'backed_up_size', 'progress', 'updated_at'])
    
    def mark_running(self):
        """Mark task as running."""
        self.status = self.STATUS_RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])
    
    def mark_completed(self):
        """Mark task as completed."""
        self.status = self.STATUS_COMPLETED
        self.completed_at = timezone.now()
        self.progress = 100
        self.save(update_fields=['status', 'completed_at', 'progress', 'updated_at'])
    
    def mark_failed(self, error_message):
        """Mark task as failed with error message."""
        self.status = self.STATUS_FAILED
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])


class BackupSnapshot(models.Model):
    """
    Represents a point-in-time snapshot of backed up data.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        BackupTask,
        on_delete=models.CASCADE,
        related_name='snapshots',
        help_text="Parent backup task"
    )
    
    # Snapshot identification
    name = models.CharField(max_length=255, help_text="Snapshot name")
    description = models.TextField(blank=True, help_text="Snapshot description")
    
    # Version control
    version = models.CharField(max_length=50, help_text="Snapshot version")
    parent_snapshot = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_snapshots',
        help_text="Parent snapshot for incremental backups"
    )
    
    # Storage
    repository = models.ForeignKey(
        'repository.Repository',
        on_delete=models.CASCADE,
        related_name='snapshots',
        help_text="Repository containing this snapshot"
    )
    storage_path = models.CharField(
        max_length=1024,
        help_text="Path in the repository"
    )
    manifest_path = models.CharField(
        max_length=1024,
        blank=True,
        help_text="Path to snapshot manifest"
    )
    
    # Statistics
    total_size = models.BigIntegerField(
        default=0,
        help_text="Total size in bytes"
    )
    file_count = models.IntegerField(
        default=0,
        help_text="Number of files in snapshot"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiration date"
    )
    
    # Metadata
    checksum = models.CharField(
        max_length=128,
        blank=True,
        help_text="SHA-256 checksum of the snapshot"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata"
    )
    
    class Meta:
        db_table = 'backup_snapshots'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', '-created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class BackupFile(models.Model):
    """
    Represents an individual file within a backup snapshot.
    """
    
    STATUS_BACKED_UP = 'backed_up'
    STATUS_MODIFIED = 'modified'
    STATUS_DELETED = 'deleted'
    
    STATUS_CHOICES = [
        (STATUS_BACKED_UP, 'Backed Up'),
        (STATUS_MODIFIED, 'Modified'),
        (STATUS_DELETED, 'Deleted'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    snapshot = models.ForeignKey(
        BackupSnapshot,
        on_delete=models.CASCADE,
        related_name='files',
        help_text="Parent snapshot"
    )
    
    # File information
    original_path = models.CharField(
        max_length=4096,
        help_text="Original file path on source"
    )
    relative_path = models.CharField(
        max_length=4096,
        help_text="Relative path within backup"
    )
    file_name = models.CharField(
        max_length=255,
        help_text="File name"
    )
    
    # File metadata
    size = models.BigIntegerField(
        default=0,
        help_text="File size in bytes"
    )
    checksum = models.CharField(
        max_length=64,
        help_text="MD5/SHA checksum"
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="MIME type"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_BACKED_UP,
        help_text="File backup status"
    )
    
    # Timestamps
    backed_up_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the file was backed up"
    )
    modified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Original file modification time"
    )
    
    class Meta:
        db_table = 'backup_files'
        ordering = ['-backed_up_at']
        indexes = [
            models.Index(fields=['snapshot', 'relative_path']),
            models.Index(fields=['checksum']),
        ]
    
    def __str__(self):
        return self.relative_path
