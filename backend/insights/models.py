import uuid

from django.db import models


class SnapshotIndexJob(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_DISPATCHED = 'dispatched'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_DISPATCHED, 'Dispatched'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    snapshot = models.ForeignKey(
        'backup_tasks.BackupSnapshot',
        on_delete=models.CASCADE,
        related_name='index_jobs',
    )
    gateway = models.ForeignKey(
        'gateways.Gateway',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='snapshot_index_jobs',
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='snapshot_index_jobs',
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='snapshot_index_jobs',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    progress = models.PositiveSmallIntegerField(default=0)
    total_files = models.BigIntegerField(default=0)
    indexed_files = models.BigIntegerField(default=0)
    total_bytes = models.BigIntegerField(default=0)
    indexed_bytes = models.BigIntegerField(default=0)
    current_path = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    task_id = models.CharField(max_length=64, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['snapshot', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['task_id']),
        ]


class SnapshotFileIndex(models.Model):
    CATEGORY_DOCUMENT = 'document'
    CATEGORY_IMAGE = 'image'
    CATEGORY_VIDEO = 'video'
    CATEGORY_AUDIO = 'audio'
    CATEGORY_ARCHIVE = 'archive'
    CATEGORY_CODE = 'code'
    CATEGORY_DATABASE = 'database'
    CATEGORY_DIRECTORY = 'directory'
    CATEGORY_OTHER = 'other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    snapshot = models.ForeignKey(
        'backup_tasks.BackupSnapshot',
        on_delete=models.CASCADE,
        related_name='file_indexes',
    )
    job = models.ForeignKey(
        SnapshotIndexJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='file_indexes',
    )
    path = models.TextField()
    name = models.CharField(max_length=1024, blank=True)
    extension = models.CharField(max_length=64, blank=True, db_index=True)
    category = models.CharField(max_length=32, default=CATEGORY_OTHER, db_index=True)
    size = models.BigIntegerField(default=0)
    modified_time = models.DateTimeField(null=True, blank=True)
    is_directory = models.BooleanField(default=False)
    depth = models.PositiveIntegerField(default=0)
    content_hash = models.CharField(max_length=128, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    indexed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['path']
        constraints = [
            models.UniqueConstraint(fields=['snapshot', 'path'], name='uniq_snapshot_file_index_path'),
        ]
        indexes = [
            models.Index(fields=['snapshot', 'category']),
            models.Index(fields=['snapshot', 'extension']),
            models.Index(fields=['snapshot', '-size']),
            models.Index(fields=['snapshot', 'content_hash']),
        ]


class SnapshotInsight(models.Model):
    TYPE_FILE_CATEGORIES = 'file_categories'
    TYPE_LARGE_FILES = 'large_files'
    TYPE_DUPLICATES = 'duplicates'
    TYPE_COLD_DATA = 'cold_data'
    TYPE_GROWTH = 'growth'
    TYPE_SUMMARY = 'summary'
    TYPE_AI_SUMMARY = 'ai_summary'

    SEVERITY_INFO = 'info'
    SEVERITY_WARNING = 'warning'
    SEVERITY_CRITICAL = 'critical'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    snapshot = models.ForeignKey(
        'backup_tasks.BackupSnapshot',
        on_delete=models.CASCADE,
        related_name='insights',
    )
    insight_type = models.CharField(max_length=64, db_index=True)
    severity = models.CharField(max_length=20, default=SEVERITY_INFO)
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    related_paths = models.JSONField(default=list, blank=True)
    recommended_actions = models.JSONField(default=list, blank=True)
    generated_by = models.CharField(max_length=20, default='rule')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['insight_type', '-created_at']
        constraints = [
            models.UniqueConstraint(fields=['snapshot', 'insight_type'], name='uniq_snapshot_insight_type'),
        ]
        indexes = [
            models.Index(fields=['snapshot', 'insight_type']),
            models.Index(fields=['severity']),
        ]


class SnapshotAIJob(models.Model):
    TYPE_SUMMARIZE = 'summarize'
    TYPE_SEARCH = 'search'

    STATUS_PENDING = 'pending'
    STATUS_DISPATCHED = 'dispatched'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    snapshot = models.ForeignKey(
        'backup_tasks.BackupSnapshot',
        on_delete=models.CASCADE,
        related_name='ai_jobs',
    )
    gateway = models.ForeignKey(
        'gateways.Gateway',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='snapshot_ai_jobs',
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='snapshot_ai_jobs',
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='snapshot_ai_jobs',
    )
    job_type = models.CharField(max_length=32, default=TYPE_SUMMARIZE)
    status = models.CharField(max_length=20, default=STATUS_PENDING)
    progress = models.PositiveSmallIntegerField(default=0)
    query = models.TextField(blank=True)
    provider = models.CharField(max_length=64, blank=True)
    model = models.CharField(max_length=128, blank=True)
    language = models.CharField(max_length=16, default='zh-CN')
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    task_id = models.CharField(max_length=64, blank=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['snapshot', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['job_type']),
            models.Index(fields=['task_id']),
        ]
