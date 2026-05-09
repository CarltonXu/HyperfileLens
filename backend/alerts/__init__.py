"""
Alerts module for HyperFileLens.

This module provides a unified alert system for all platforms and services.
It supports various alert types, severity levels, and notification channels.
"""

# Import types directly (they don't require Django)
from .types import (
    AlertType,
    AlertSeverity,
    AlertStatus,
    AlertThresholds,
    get_alert_message,
    ALERT_MESSAGES,
    normalize_alert_type,
)

# Lazy imports for models and manager (require Django ready)
def get_models():
    """Get alert models (lazy import)."""
    from . import models
    return models.Alert, models.AlertRule


def get_manager():
    """Get alert manager (lazy import)."""
    from . import manager
    return manager.alert_manager


# Convenience accessor for manager
def create_alert(*args, **kwargs):
    """Convenience function to create an alert."""
    return get_manager().create_alert(*args, **kwargs)


# Convenience accessors for common node/proxy alerts
def check_node_offline(node):
    """Check if node is offline and create alert if needed."""
    return get_manager().check_node_offline(node)


def check_proxy_offline(proxy):
    """Legacy method - check if proxy is offline and create alert if needed."""
    return get_manager().check_node_offline(proxy)


def check_node_timeout(node):
    """Check if node heartbeat has timed out."""
    return get_manager().check_node_timeout(node)


def check_proxy_timeout(proxy):
    """Legacy method - check if proxy heartbeat has timed out."""
    return get_manager().check_node_timeout(proxy)


def check_resource_alerts(node, metrics):
    """Check resource alerts for a node."""
    return get_manager().check_resource_alerts(node, metrics)


def check_task_failed(task, error=None):
    """Check if task failed and create alert if needed."""
    return get_manager().check_task_failed(task, error)


def check_task_timeout(task):
    """Check if task has timed out."""
    return get_manager().check_task_timeout(task)


def check_error_rate(node, error_rate):
    """Check if error rate exceeds threshold."""
    return get_manager().check_error_rate(node, error_rate)


__all__ = [
    # Types
    'AlertType',
    'AlertSeverity',
    'AlertStatus',
    'AlertThresholds',
    'get_alert_message',
    'ALERT_MESSAGES',
    'normalize_alert_type',
    # Helper functions
    'get_models',
    'get_manager',
    'create_alert',
    # Node/Proxy specific helpers
    'check_node_offline',
    'check_proxy_offline',
    'check_node_timeout',
    'check_proxy_timeout',
    'check_resource_alerts',
    'check_task_failed',
    'check_task_timeout',
    'check_error_rate',
]
