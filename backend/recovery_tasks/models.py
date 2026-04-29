"""
HyperFileLens Backend - Recovery Tasks Models

This module defines the data models for recovery operations:
- RecoveryTask: Main recovery task model
"""

import uuid
from django.db import models
from django.utils import timezone
from accounts.models import User


class RecoveryTask(models.Model):
    """
    Represents a recovery task for restoring data from backups.
    """
    
    # Status choices
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
    
    # Recovery type choices
    TYPE_ORIGINAL = 'original'
    TYPE_NEW_LOCATION = 'new_location'
    TYPE_EXPORT = 'export'
    
    TYPE_CHOICES = [
        (TYPE_ORIGINAL, 'Original Location'),
        (TYPE_NEW_LOCATION, 'New Location'),
        (TYPE_EXPORT, 'Export'),
    ]
    
    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Recovery task name")
    description = models.TextField(blank=True, help_text="Task description")
    
    # Source information
    snapshot = models.ForeignKey(
        'backup_tasks.BackupSnapshot',
        on_delete=models.CASCADE,
        related_name='recovery_tasks',
        help_text="Source snapshot for recovery"
    )
    
    # Target information
    target_node = models.ForeignKey(
        'nodes.Node',
        on_delete=models.CASCADE,
        related_name='recovery_tasks',
        help_text="Target node for recovery"
    )
    recovery_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_ORIGINAL,
        help_text="Type of recovery"
    )
    target_path = models.CharField(
        max_length=4096,
        blank=True,
        help_text="Target path for new location recovery"
    )
    
    # File filters
    file_patterns = models.JSONField(
        default=list,
        blank=True,
        help_text="File patterns to include in recovery"
    )
    exclude_patterns = models.JSONField(
        default=list,
        blank=True,
        help_text="File patterns to exclude"
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
    
    # Metadata
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recovery_tasks',
        help_text="User who initiated the recovery"
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='recovery_tasks',
        help_text='Tenant this task belongs to'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Statistics
    total_files = models.IntegerField(default=0)
    restored_files = models.IntegerField(default=0)
    total_size = models.BigIntegerField(default=0)
    restored_size = models.BigIntegerField(default=0)
    skipped_files = models.IntegerField(default=0)
    failed_files = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'recovery_tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['target_node', 'status']),
            models.Index(fields=['snapshot', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    @property
    def duration(self):
        """Calculate task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
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
