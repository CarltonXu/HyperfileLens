"""
Alert models for the alerts module.

This module defines the database models for storing and managing alerts.
These models are designed to be used across all platforms and services.
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Alert(models.Model):
    """
    Alert model for storing system alerts.

    This model is platform-agnostic and can be used for any type of alert.
    """

    class AlertSeverity(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        CRITICAL = 'critical', 'Critical'
        FATAL = 'fatal', 'Fatal'

    class AlertStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        ACKNOWLEDGED = 'acknowledged', 'Acknowledged'
        RESOLVED = 'resolved', 'Resolved'
        SILENCED = 'silenced', 'Silenced'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Unique alert identifier'
    )

    # Alert details
    alert_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text='Type of alert (e.g., "node_offline", "task_failed")'
    )

    severity = models.CharField(
        max_length=20,
        choices=AlertSeverity.choices,
        default=AlertSeverity.WARNING,
        db_index=True,
        help_text='Alert severity level'
    )

    status = models.CharField(
        max_length=20,
        choices=AlertStatus.choices,
        default=AlertStatus.ACTIVE,
        db_index=True,
        help_text='Alert status'
    )

    # Related entities (generic - can be any model)
    entity_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Type of related entity (e.g., "nodes.ProxyNode", "backup_tasks.BackupTask")'
    )

    entity_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text='ID of related entity'
    )

    entity_name = models.CharField(
        max_length=255,
        blank=True,
        help_text='Human-readable name of related entity'
    )

    # Optional specific foreign keys for common entities
    proxy = models.ForeignKey(
        'nodes.ProxyNode',
        on_delete=models.CASCADE,
        related_name='alerts',
        null=True,
        blank=True,
        help_text='Related proxy node (if applicable)'
    )

    task = models.ForeignKey(
        'nodes.ProxyTask',
        on_delete=models.CASCADE,
        related_name='alerts',
        null=True,
        blank=True,
        help_text='Related task (if applicable)'
    )

    backup_task = models.ForeignKey(
        'backup_tasks.BackupTask',
        on_delete=models.CASCADE,
        related_name='alerts',
        null=True,
        blank=True,
        help_text='Related backup task (if applicable)'
    )

    repository = models.ForeignKey(
        'repository.Repository',
        on_delete=models.CASCADE,
        related_name='alerts',
        null=True,
        blank=True,
        help_text='Related repository (if applicable)'
    )

    # Alert content
    title = models.CharField(
        max_length=255,
        help_text='Alert title'
    )

    message = models.TextField(
        help_text='Detailed alert message'
    )

    details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional alert details (JSON format)'
    )

    # Metrics
    metric_value = models.FloatField(
        null=True,
        blank=True,
        help_text='Metric value that triggered the alert'
    )

    threshold_value = models.FloatField(
        null=True,
        blank=True,
        help_text='Threshold value that was exceeded'
    )

    # Timestamps
    triggered_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text='When the alert was triggered'
    )

    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the alert was acknowledged'
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the alert was resolved'
    )

    # Acknowledgment
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts',
        help_text='User who acknowledged the alert'
    )

    acknowledgment_note = models.TextField(
        blank=True,
        help_text='Note added when acknowledging the alert'
    )

    # Resolution
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts',
        help_text='User who resolved the alert'
    )

    resolution_note = models.TextField(
        blank=True,
        help_text='Note added when resolving the alert'
    )

    # Notification
    notification_sent = models.BooleanField(
        default=False,
        help_text='Whether notification was sent'
    )

    notification_channels = models.JSONField(
        default=list,
        blank=True,
        help_text='Channels where notification was sent'
    )

    # Silencing
    silenced_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Alert is silenced until this time'
    )

    silenced_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='silenced_alerts',
        help_text='User who silenced the alert'
    )

    # Repetition
    occurrence_count = models.IntegerField(
        default=1,
        help_text='Number of times this alert has occurred'
    )

    first_occurrence_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='First time this alert occurred'
    )

    last_occurrence_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Most recent occurrence of this alert'
    )

    # Source identification
    source = models.CharField(
        max_length=100,
        blank=True,
        help_text='Source of the alert (e.g., "nodes", "backup_tasks", "api")'
    )

    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional metadata'
    )

    class Meta:
        db_table = 'alerts_alert'
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'
        ordering = ['-triggered_at']
        indexes = [
            models.Index(fields=['alert_type', 'status']),
            models.Index(fields=['severity', 'status']),
            models.Index(fields=['source']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['triggered_at']),
        ]

    def __str__(self):
        return f'{self.alert_type} - {self.title}'

    def acknowledge(self, user, note: str = None):
        """Acknowledge the alert."""
        self.status = self.AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = user
        self.acknowledgment_note = note or ''
        self.save()

    def resolve(self, user, note: str = None):
        """Resolve the alert."""
        self.status = self.AlertStatus.RESOLVED
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.resolution_note = note or ''
        self.save()

    def silence(self, user, until: timezone.datetime = None):
        """Silence the alert until a certain time."""
        self.status = self.AlertStatus.SILENCED
        self.silenced_until = until
        self.silenced_by = user
        self.save()

    def is_active(self) -> bool:
        """Check if alert is active."""
        return self.status == self.AlertStatus.ACTIVE

    def is_silenced(self) -> bool:
        """Check if alert is silenced."""
        if self.status == self.AlertStatus.SILENCED:
            return True
        if self.silenced_until and self.silenced_until > timezone.now():
            return True
        return False

    def can_be_resolved(self) -> bool:
        """Check if alert can be resolved."""
        return self.status in [self.AlertStatus.ACTIVE, self.AlertStatus.ACKNOWLEDGED]

    def get_duration(self) -> float:
        """Get alert duration in seconds."""
        if self.resolved_at:
            return (self.resolved_at - self.triggered_at).total_seconds()
        return (timezone.now() - self.triggered_at).total_seconds()

    def increment_occurrence(self):
        """Increment occurrence count."""
        self.occurrence_count += 1
        self.last_occurrence_at = timezone.now()
        if self.first_occurrence_at is None:
            self.first_occurrence_at = self.triggered_at
        self.save(update_fields=['occurrence_count', 'last_occurrence_at', 'first_occurrence_at'])


class AlertRule(models.Model):
    """
    Alert rule model for defining alert conditions.

    This model allows creating custom alert rules that can be
    evaluated periodically or on-demand.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text='Rule name'
    )

    description = models.TextField(
        blank=True,
        help_text='Rule description'
    )

    alert_type = models.CharField(
        max_length=50,
        help_text='Type of alert this rule triggers'
    )

    severity = models.CharField(
        max_length=20,
        choices=Alert.AlertSeverity.choices,
        default=Alert.AlertSeverity.WARNING,
        help_text='Alert severity'
    )

    # Conditions
    condition = models.JSONField(
        default=dict,
        help_text='Alert conditions (JSON format)'
    )

    # Target specification
    applies_to_all_entities = models.BooleanField(
        default=True,
        help_text='Whether rule applies to all entities'
    )

    entity_type = models.CharField(
        max_length=50,
        blank=True,
        help_text='Type of entity this rule applies to'
    )

    target_ids = models.JSONField(
        default=list,
        blank=True,
        help_text='List of entity IDs this rule applies to'
    )

    # Thresholds
    threshold_value = models.FloatField(
        null=True,
        blank=True,
        help_text='Threshold value'
    )

    threshold_operator = models.CharField(
        max_length=10,
        choices=[
            ('>', 'Greater than'),
            ('>=', 'Greater than or equal'),
            ('<', 'Less than'),
            ('<=', 'Less than or equal'),
            ('==', 'Equal to'),
            ('!=', 'Not equal to'),
        ],
        default='>=',
        help_text='Threshold comparison operator'
    )

    # Timing
    evaluation_interval = models.IntegerField(
        default=60,
        help_text='How often to evaluate this rule (seconds)'
    )

    cooldown_period = models.IntegerField(
        default=300,
        help_text='Minimum time between alerts for this rule (seconds)'
    )

    # Notification
    notification_enabled = models.BooleanField(
        default=True,
        help_text='Whether to send notifications for this rule'
    )

    notification_channels = models.JSONField(
        default=list,
        blank=True,
        help_text='Notification channels (email, slack, webhook, etc.)'
    )

    # Status
    enabled = models.BooleanField(
        default=True,
        help_text='Whether this rule is enabled'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_triggered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last time this rule triggered an alert'
    )

    # Source identification
    source = models.CharField(
        max_length=100,
        blank=True,
        help_text='Source module/service for this rule'
    )

    class Meta:
        db_table = 'alerts_rule'
        verbose_name = 'Alert Rule'
        verbose_name_plural = 'Alert Rules'
        ordering = ['name']

    def __str__(self):
        return self.name

    def evaluate(self, entity, metrics: dict) -> tuple:
        """
        Evaluate if this rule should trigger an alert.

        Args:
            entity: The entity being evaluated
            metrics: Dictionary of current metrics

        Returns:
            Tuple of (should_trigger, current_value)
        """
        if not self.enabled:
            return False, 0.0

        # Check cooldown period
        if self.last_triggered_at:
            cooldown_elapsed = (timezone.now() - self.last_triggered_at).total_seconds()
            if cooldown_elapsed < self.cooldown_period:
                return False, 0.0

        # Extract value based on alert type
        value = 0.0
        if self.alert_type == 'cpu_high':
            value = metrics.get('cpu_usage', 0.0)
        elif self.alert_type == 'memory_high':
            value = metrics.get('memory_usage', 0.0)
        elif self.alert_type == 'disk_high':
            value = metrics.get('disk_usage', 0.0)
        elif self.alert_type == 'error_rate_high':
            value = metrics.get('error_rate', 0)
        elif self.alert_type == 'rate_limit_exceeded':
            value = metrics.get('request_rate', 0)

        # Check threshold
        if self.threshold_value is not None:
            import operator
            ops = {
                '>': operator.gt,
                '>=': operator.ge,
                '<': operator.lt,
                '<=': operator.le,
                '==': operator.eq,
                '!=': operator.ne,
            }
            should_trigger = ops[self.threshold_operator](value, self.threshold_value)
            return should_trigger, value

        return False, value