"""
Alert type definitions for the alerts module.

This module defines the types of alerts that can be triggered
across all platforms and services.
"""

from enum import Enum


class AlertType(str, Enum):
    """Alert type enumeration - Base types that apply to all platforms."""

    # Node/Proxy alerts
    NODE_OFFLINE = "node_offline"
    NODE_TIMEOUT = "node_timeout"
    NODE_ERROR = "node_error"
    NODE_HEALTH_DEGRADED = "node_health_degraded"

    # Legacy alias for NODE alerts (for backward compatibility)
    PROXY_OFFLINE = "node_offline"  # Alias for NODE_OFFLINE
    PROXY_TIMEOUT = "node_timeout"  # Alias for NODE_TIMEOUT
    PROXY_ERROR = "node_error"  # Alias for NODE_ERROR

    # Task alerts
    TASK_FAILED = "task_failed"
    TASK_TIMEOUT = "task_timeout"
    TASK_CANCELLED = "task_cancelled"
    TASK_STUCK = "task_stuck"

    # Resource alerts
    CPU_HIGH = "cpu_high"
    MEMORY_HIGH = "memory_high"
    DISK_HIGH = "disk_high"
    BANDWIDTH_EXCEEDED = "bandwidth_exceeded"

    # System alerts
    CONNECTION_LOST = "connection_lost"
    ERROR_RATE_HIGH = "error_rate_high"
    STORAGE_UNAVAILABLE = "storage_unavailable"
    SERVICE_UNAVAILABLE = "service_unavailable"

    # Security alerts
    AUTH_FAILED = "auth_failed"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

    # Backup/Restore alerts
    BACKUP_FAILED = "backup_failed"
    BACKUP_TIMEOUT = "backup_timeout"
    RESTORE_FAILED = "restore_failed"
    SNAPSHOT_FAILED = "snapshot_failed"

    # Repository alerts
    REPOSITORY_CORRUPTED = "repository_corrupted"
    REPOSITORY_FULL = "repository_full"
    REPOSITORY_ACCESS_DENIED = "repository_access_denied"
    REPOSITORY_QUOTA_EXCEEDED = "repository_quota_exceeded"

    # Notification alerts
    NOTIFICATION_FAILED = "notification_failed"
    NOTIFICATION_QUEUE_FULL = "notification_queue_full"

    def __str__(self):
        return self.value


class AlertSeverity(str, Enum):
    """Alert severity enumeration."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"

    def __str__(self):
        return self.value

    @classmethod
    def from_value(cls, value: int):
        """Get severity from numeric value."""
        if value >= 90:
            return cls.FATAL
        elif value >= 70:
            return cls.CRITICAL
        elif value >= 50:
            return cls.WARNING
        else:
            return cls.INFO


class AlertStatus(str, Enum):
    """Alert status enumeration."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SILENCED = "silenced"

    def __str__(self):
        return self.value


# Alert thresholds
class AlertThresholds:
    """Default alert threshold values."""

    # CPU thresholds (percentage)
    CPU_WARNING = 75.0
    CPU_CRITICAL = 90.0

    # Memory thresholds (percentage)
    MEMORY_WARNING = 80.0
    MEMORY_CRITICAL = 95.0

    # Disk thresholds (percentage)
    DISK_WARNING = 80.0
    DISK_CRITICAL = 90.0

    # Task timeout (seconds)
    TASK_TIMEOUT_DEFAULT = 3600

    # Heartbeat timeout (seconds multiplier)
    HEARTBEAT_TIMEOUT_MULTIPLIER = 3

    # Error rate (errors per minute)
    ERROR_RATE_WARNING = 5
    ERROR_RATE_CRITICAL = 10

    # Rate limit (requests per minute)
    RATE_LIMIT_WARNING = 1000
    RATE_LIMIT_CRITICAL = 2000


# Predefined alert messages templates
ALERT_MESSAGES = {
    # Node/Proxy alerts
    AlertType.NODE_OFFLINE: "Node {entity_name} has gone offline",
    AlertType.PROXY_OFFLINE: "Node {entity_name} has gone offline",  # Same as NODE_OFFLINE
    AlertType.NODE_TIMEOUT: "Node {entity_name} heartbeat timeout",
    AlertType.PROXY_TIMEOUT: "Node {entity_name} heartbeat timeout",  # Same as NODE_TIMEOUT
    AlertType.NODE_ERROR: "Node {entity_name} reported an error: {error}",
    AlertType.PROXY_ERROR: "Node {entity_name} reported an error: {error}",  # Same as NODE_ERROR
    AlertType.NODE_HEALTH_DEGRADED: "Node {entity_name} health degraded: {reason}",

    # Task alerts
    AlertType.TASK_FAILED: "Task {task_id} failed on {entity_name}: {error}",
    AlertType.TASK_TIMEOUT: "Task {task_id} timed out on {entity_name}",
    AlertType.TASK_CANCELLED: "Task {task_id} was cancelled on {entity_name}",
    AlertType.TASK_STUCK: "Task {task_id} appears to be stuck on {entity_name}",

    # Resource alerts
    AlertType.CPU_HIGH: "{entity_name} CPU usage is {value:.1f}% (threshold: {threshold:.1f}%)",
    AlertType.MEMORY_HIGH: "{entity_name} memory usage is {value:.1f}% (threshold: {threshold:.1f}%)",
    AlertType.DISK_HIGH: "{entity_name} disk usage is {value:.1f}% (threshold: {threshold:.1f}%)",
    AlertType.BANDWIDTH_EXCEEDED: "{entity_name} exceeded bandwidth limit: {value} KB/s",

    # System alerts
    AlertType.CONNECTION_LOST: "Connection lost with {entity_name}",
    AlertType.ERROR_RATE_HIGH: "{entity_name} error rate is {value}/min (threshold: {threshold})",
    AlertType.STORAGE_UNAVAILABLE: "Storage {storage_name} is unavailable for {entity_name}",
    AlertType.SERVICE_UNAVAILABLE: "Service {service_name} is unavailable",

    # Security alerts
    AlertType.AUTH_FAILED: "Authentication failed for {user} from {source}",
    AlertType.RATE_LIMIT_EXCEEDED: "Rate limit exceeded for {entity_name}: {value} req/min",
    AlertType.SUSPICIOUS_ACTIVITY: "Suspicious activity detected: {description}",

    # Backup/Restore alerts
    AlertType.BACKUP_FAILED: "Backup failed for {source_name}: {error}",
    AlertType.BACKUP_TIMEOUT: "Backup timed out for {source_name}",
    AlertType.RESTORE_FAILED: "Restore failed to {destination_name}: {error}",
    AlertType.SNAPSHOT_FAILED: "Snapshot failed for {repository_name}: {error}",

    # Repository alerts
    AlertType.REPOSITORY_CORRUPTED: "Repository {repository_name} appears to be corrupted",
    AlertType.REPOSITORY_FULL: "Repository {repository_name} is full",
    AlertType.REPOSITORY_ACCESS_DENIED: "Access denied to repository {repository_name}",
    AlertType.REPOSITORY_QUOTA_EXCEEDED: "Repository {repository_name} has exceeded {percentage:.1f}% of quota (used: {used_gb:.2f}GB, quota: {quota_gb:.2f}GB)",

    # Notification alerts
    AlertType.NOTIFICATION_FAILED: "Failed to send notification to {channel}: {error}",
    AlertType.NOTIFICATION_QUEUE_FULL: "Notification queue is full, {pending_count} messages pending",
}


def get_alert_message(alert_type: AlertType, **kwargs) -> str:
    """Get formatted alert message for the given type."""
    # Handle legacy proxy types by mapping to node types
    type_key = alert_type
    if alert_type in [AlertType.PROXY_OFFLINE, AlertType.PROXY_TIMEOUT, AlertType.PROXY_ERROR]:
        type_key = AlertType(f"node_{alert_type.value.replace('proxy_', '')}")

    template = ALERT_MESSAGES.get(type_key, f"Alert: {alert_type}")
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError) as e:
        # If formatting fails, return template with placeholders
        return template


def register_alert_message(alert_type: str, template: str):
    """Register a custom alert message for an alert type."""
    ALERT_MESSAGES[alert_type] = template


# Legacy compatibility - map old ProxyNode alert types to new Node types
PROXY_ALERT_TYPE_MAPPING = {
    'proxy_offline': AlertType.NODE_OFFLINE.value,
    'proxy_timeout': AlertType.NODE_TIMEOUT.value,
    'proxy_error': AlertType.NODE_ERROR.value,
}


def normalize_alert_type(alert_type: str) -> str:
    """
    Normalize legacy alert type to new alert type.

    For backward compatibility, this function maps old proxy_* types to node_* types.
    """
    return PROXY_ALERT_TYPE_MAPPING.get(alert_type, alert_type)
