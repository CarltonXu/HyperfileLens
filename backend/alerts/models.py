"""Models for the global alert center."""

import uuid

from django.db import models

from .choices import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    NotificationChannelType,
    NotificationStatus,
    PolicyScope,
    ResourceType,
)


class AlertPolicy(models.Model):
    """A user-configured alert policy."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    type = models.CharField(max_length=50, choices=AlertType.choices)
    severity = models.CharField(max_length=50, choices=AlertSeverity.choices)
    enabled = models.BooleanField(default=True)

    resource_type = models.CharField(max_length=100, choices=ResourceType.choices, null=True, blank=True)
    scope = models.CharField(max_length=50, choices=PolicyScope.choices, default=PolicyScope.SELECTED)
    resource_ids = models.JSONField(default=list, blank=True)

    trigger_rule = models.JSONField()
    recovery_rule = models.JSONField(null=True, blank=True)
    notification_channel_ids = models.JSONField(default=list, blank=True)

    created_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "alert_policies"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["enabled"], name="idx_alert_policies_enabled"),
            models.Index(fields=["type"], name="idx_alert_policies_type"),
        ]

    def __str__(self):
        return self.name


class AlertRecord(models.Model):
    """A concrete alert instance generated from a policy or platform event."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    policy_id = models.UUIDField(null=True, blank=True)
    type = models.CharField(max_length=50, choices=AlertType.choices)
    severity = models.CharField(max_length=50, choices=AlertSeverity.choices)
    status = models.CharField(max_length=50, choices=AlertStatus.choices)

    resource_type = models.CharField(max_length=100, choices=ResourceType.choices, null=True, blank=True)
    resource_id = models.UUIDField(null=True, blank=True)
    resource_name = models.CharField(max_length=255, null=True, blank=True)

    title = models.CharField(max_length=255)
    message = models.TextField(null=True, blank=True)

    current_value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    threshold_value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    unit = models.CharField(max_length=50, null=True, blank=True)

    fingerprint = models.CharField(max_length=255, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    first_triggered_at = models.DateTimeField(null=True, blank=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.UUIDField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "alert_records"
        ordering = ["-last_triggered_at", "-created_at"]
        indexes = [
            models.Index(fields=["status"], name="idx_alert_records_status"),
            models.Index(fields=["type"], name="idx_alert_records_type"),
            models.Index(fields=["severity"], name="idx_alert_records_severity"),
            models.Index(fields=["fingerprint"], name="idx_alert_records_fingerprint"),
        ]

    def __str__(self):
        return self.title

    @property
    def duration_seconds(self):
        if not self.first_triggered_at:
            return None
        end_at = self.resolved_at or self.last_triggered_at or self.updated_at
        return int((end_at - self.first_triggered_at).total_seconds())


class NotificationChannel(models.Model):
    """Channel used to deliver alert notifications."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=NotificationChannelType.choices)
    enabled = models.BooleanField(default=True)
    config = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_channels"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.type})"


class NotificationLog(models.Model):
    """Delivery log for a notification attempt."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert_record_id = models.UUIDField()
    channel_id = models.UUIDField()
    status = models.CharField(max_length=50, choices=NotificationStatus.choices)
    error_message = models.TextField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notification_logs"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.channel_id} - {self.status}"


class SystemMetric(models.Model):
    """Control-plane host monitoring sample for the System Monitor page."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    cpu = models.JSONField(default=dict, blank=True)
    memory = models.JSONField(default=dict, blank=True)
    swap = models.JSONField(default=dict, blank=True)
    disks = models.JSONField(default=list, blank=True)
    disk_io = models.JSONField(default=list, blank=True)
    networks = models.JSONField(default=list, blank=True)
    load_average = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "alerts_system_metric"
        ordering = ["-timestamp"]

    def __str__(self):
        return str(self.timestamp)
