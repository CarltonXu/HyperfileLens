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
    STATUS_PAUSED = 'paused'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_PAUSED, 'Paused'),
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

    SCOPE_ENTIRE_SNAPSHOT = 'entire_snapshot'
    SCOPE_SELECTED_PATHS = 'selected_paths'

    SCOPE_CHOICES = [
        (SCOPE_ENTIRE_SNAPSHOT, 'Entire Snapshot'),
        (SCOPE_SELECTED_PATHS, 'Selected Files and Folders'),
    ]

    CONFLICT_SKIP = 'skip'
    CONFLICT_OVERWRITE = 'overwrite'
    CONFLICT_RENAME = 'rename'

    CONFLICT_CHOICES = [
        (CONFLICT_SKIP, 'Skip Existing Files'),
        (CONFLICT_OVERWRITE, 'Overwrite Existing Files'),
        (CONFLICT_RENAME, 'Restore With New Name'),
    ]

    PRIORITY_LOW = 'low'
    PRIORITY_NORMAL = 'normal'
    PRIORITY_HIGH = 'high'
    PRIORITY_CRITICAL = 'critical'

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_NORMAL, 'Normal'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_CRITICAL, 'Critical'),
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

    restore_scope = models.CharField(
        max_length=24,
        choices=SCOPE_CHOICES,
        default=SCOPE_ENTIRE_SNAPSHOT,
        help_text="Whether to restore the whole snapshot or selected paths"
    )
    selected_paths = models.JSONField(
        default=list,
        blank=True,
        help_text="Selected snapshot-relative paths for granular recovery"
    )
    conflict_policy = models.CharField(
        max_length=20,
        choices=CONFLICT_CHOICES,
        default=CONFLICT_SKIP,
        help_text="How to handle files that already exist at the target"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_NORMAL,
        help_text="Recovery execution priority"
    )
    options = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional recovery options"
    )
    proxy_task = models.ForeignKey(
        'nodes.ProxyTask',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recovery_tasks',
        help_text="Latest proxy task dispatched for this recovery"
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
    status_message = models.TextField(
        blank=True,
        help_text="Human readable execution status"
    )
    current_file = models.CharField(
        max_length=1024,
        blank=True,
        help_text="Current file being restored"
    )
    speed_mbps = models.FloatField(
        default=0.0,
        help_text="Current restore speed in MB/s"
    )
    eta = models.CharField(
        max_length=64,
        blank=True,
        help_text="Estimated time remaining"
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
    metadata = models.JSONField(default=dict, blank=True)
    
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
    
    def mark_running(self, message='Recovery command dispatched to proxy'):
        """Mark task as running."""
        self.status = self.STATUS_RUNNING
        self.started_at = timezone.now()
        self.completed_at = None
        self.progress = 0
        self.error_message = ''
        self.status_message = message
        self.save(update_fields=[
            'status', 'started_at', 'completed_at', 'progress',
            'error_message', 'status_message', 'updated_at'
        ])
    
    def mark_completed(self):
        """Mark task as completed."""
        self.status = self.STATUS_COMPLETED
        self.completed_at = timezone.now()
        self.progress = 100
        self.status_message = 'Recovery completed'
        self.save(update_fields=[
            'status', 'completed_at', 'progress', 'status_message', 'updated_at'
        ])
    
    def mark_failed(self, error_message):
        """Mark task as failed with error message."""
        self.status = self.STATUS_FAILED
        self.error_message = error_message
        self.status_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=[
            'status', 'error_message', 'status_message', 'completed_at', 'updated_at'
        ])


class RecoveryRun(models.Model):
    """A single execution attempt of a recovery task."""

    TRIGGER_MANUAL = 'manual'
    TRIGGER_RETRY = 'retry'
    TRIGGER_PRECHECK = 'precheck'

    TRIGGER_CHOICES = [
        (TRIGGER_MANUAL, 'Manual'),
        (TRIGGER_RETRY, 'Retry'),
        (TRIGGER_PRECHECK, 'Precheck'),
    ]

    STATUS_PENDING = RecoveryTask.STATUS_PENDING
    STATUS_DISPATCHED = 'dispatched'
    STATUS_RUNNING = RecoveryTask.STATUS_RUNNING
    STATUS_COMPLETED = RecoveryTask.STATUS_COMPLETED
    STATUS_FAILED = RecoveryTask.STATUS_FAILED
    STATUS_CANCELLED = RecoveryTask.STATUS_CANCELLED
    STATUS_PAUSED = RecoveryTask.STATUS_PAUSED

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_DISPATCHED, 'Dispatched'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_PAUSED, 'Paused'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        RecoveryTask,
        on_delete=models.CASCADE,
        related_name='runs',
        help_text='Recovery task this execution belongs to',
    )
    proxy_task = models.ForeignKey(
        'nodes.ProxyTask',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recovery_runs',
    )
    snapshot = models.ForeignKey(
        'backup_tasks.BackupSnapshot',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recovery_runs',
    )
    target_node = models.ForeignKey(
        'nodes.Node',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recovery_runs',
    )
    trigger_type = models.CharField(
        max_length=20,
        choices=TRIGGER_CHOICES,
        default=TRIGGER_MANUAL,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    progress = models.IntegerField(default=0)
    message = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    parameters = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    current_file = models.CharField(max_length=1024, blank=True)
    total_files = models.IntegerField(default=0)
    restored_files = models.IntegerField(default=0)
    total_size = models.BigIntegerField(default=0)
    restored_size = models.BigIntegerField(default=0)
    skipped_files = models.IntegerField(default=0)
    failed_files = models.IntegerField(default=0)
    speed_mbps = models.FloatField(default=0.0)
    eta = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'recovery_task_runs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['proxy_task']),
        ]

    def __str__(self):
        return f"{self.task.name} run ({self.status})"

    @property
    def duration(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class RecoveryExport(models.Model):
    """A downloadable export package generated from selected snapshot paths."""

    STATUS_PENDING = 'pending'
    STATUS_DISPATCHED = 'dispatched'
    STATUS_RUNNING = 'running'
    STATUS_PACKAGING = 'packaging'
    STATUS_READY = 'ready'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_EXPIRED = 'expired'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_DISPATCHED, 'Dispatched'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_PACKAGING, 'Packaging'),
        (STATUS_READY, 'Ready'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    FORMAT_ZIP = 'zip'
    FORMAT_CHOICES = [
        (FORMAT_ZIP, 'ZIP'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text='Export job name')
    description = models.TextField(blank=True)
    snapshot = models.ForeignKey(
        'backup_tasks.BackupSnapshot',
        on_delete=models.CASCADE,
        related_name='recovery_exports',
    )
    repository = models.ForeignKey(
        'repository.Repository',
        on_delete=models.CASCADE,
        related_name='recovery_exports',
    )
    selected_paths = models.JSONField(default=list, blank=True)
    package_format = models.CharField(max_length=16, choices=FORMAT_CHOICES, default=FORMAT_ZIP)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    progress = models.IntegerField(default=0)
    status_message = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    current_file = models.CharField(max_length=1024, blank=True)
    total_files = models.IntegerField(default=0)
    processed_files = models.IntegerField(default=0)
    total_size = models.BigIntegerField(default=0)
    processed_size = models.BigIntegerField(default=0)
    package_size = models.BigIntegerField(default=0)
    checksum = models.CharField(max_length=128, blank=True)
    file_path = models.CharField(max_length=4096, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    proxy_task = models.ForeignKey(
        'nodes.ProxyTask',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recovery_exports',
    )
    executor_node = models.ForeignKey(
        'nodes.Node',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recovery_exports',
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recovery_exports')
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='recovery_exports',
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'recovery_exports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['snapshot', '-created_at']),
            models.Index(fields=['tenant', '-created_at']),
        ]

    def __str__(self):
        return f'{self.name} ({self.status})'

    @property
    def is_downloadable(self):
        return bool(
            self.status == self.STATUS_READY
            and self.file_path
            and (not self.expires_at or self.expires_at > timezone.now())
        )
