"""
Alert manager for the alerts module.

This module provides the AlertManager class for creating, evaluating,
and managing alerts across all platforms and services.
"""

from typing import Optional, List, Dict, Any
from datetime import timedelta
from django.utils import timezone
from django.db import transaction, models
from django.core.cache import cache
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
import logging

from .models import Alert, AlertRule
from .types import (
    AlertType,
    AlertSeverity,
    AlertStatus,
    AlertThresholds,
    get_alert_message,
    normalize_alert_type,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class AlertManager:
    """
    Manager for creating and managing alerts.

    This is a singleton instance that provides methods for creating,
    evaluating, and managing alerts across the application.
    """

    # Cache keys
    _CACHE_PREFIX = "alert_cooldown:"
    _CACHE_TIMEOUT = 300  # 5 minutes

    def __init__(self):
        self.channel_layer = get_channel_layer()

    @transaction.atomic
    def create_alert(
        self,
        alert_type: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
        title: str = None,
        message: str = None,
        entity_type: str = None,
        entity_id: str = None,
        entity_name: str = None,
        proxy=None,
        task=None,
        backup_task=None,
        repository=None,
        details: dict = None,
        metric_value: float = None,
        threshold_value: float = None,
        deduplicate: bool = True,
        source: str = None,
    ) -> Optional[Alert]:
        """
        Create a new alert.

        Args:
            alert_type: Type of alert (string value)
            severity: Alert severity
            title: Alert title
            message: Alert message
            entity_type: Type of related entity
            entity_id: ID of related entity
            entity_name: Human-readable name of entity
            proxy: Related proxy node
            task: Related task
            backup_task: Related backup task
            repository: Related repository
            details: Additional details
            metric_value: Value that triggered the alert
            threshold_value: Threshold value that was exceeded
            deduplicate: Whether to deduplicate similar active alerts
            source: Source of the alert (module/service)

        Returns:
            Created alert or existing alert if deduplicated
        """
        # Normalize alert type for backward compatibility
        alert_type = normalize_alert_type(alert_type)

        # Generate default title and message if not provided
        if not title:
            title = f"{alert_type.replace('_', ' ').title()} Alert"

        if not message:
            message = self._get_default_message(alert_type, entity_name)

        # Check for deduplication
        if deduplicate:
            existing_alert = self._find_duplicate_alert(
                alert_type, entity_type, entity_id
            )
            if existing_alert:
                existing_alert.increment_occurrence()
                logger.info(
                    f"Incremented alert {existing_alert.id} occurrence to {existing_alert.occurrence_count}"
                )
                return existing_alert

        # Create new alert
        alert = Alert.objects.create(
            alert_type=alert_type,
            severity=severity.value,
            status=AlertStatus.ACTIVE.value,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            proxy=proxy,
            task=task,
            backup_task=backup_task,
            repository=repository,
            title=title,
            message=message,
            details=details or {},
            metric_value=metric_value,
            threshold_value=threshold_value,
            source=source,
            first_occurrence_at=timezone.now(),
            last_occurrence_at=timezone.now(),
        )

        logger.info(f"Created alert {alert.id}: {title}")

        # Broadcast alert
        self._broadcast_alert(alert)

        return alert

    def _get_default_message(
        self, alert_type: str, entity_name: str = None
    ) -> str:
        """Get default message for alert type."""
        kwargs = {}
        if entity_name:
            kwargs['entity_name'] = entity_name
        try:
            return get_alert_message(AlertType(alert_type), **kwargs)
        except ValueError:
            return f"Alert: {alert_type}"

    def _find_duplicate_alert(
        self,
        alert_type: str,
        entity_type: str = None,
        entity_id: str = None,
    ) -> Optional[Alert]:
        """Find existing active alert with same type and entity."""
        queryset = Alert.objects.filter(
            alert_type=alert_type,
            status=AlertStatus.ACTIVE.value,
        )

        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)

        # Only consider it duplicate if created within the last 5 minutes
        queryset = queryset.filter(
            triggered_at__gte=timezone.now() - timedelta(minutes=5)
        )

        return queryset.first()

    def _broadcast_alert(self, alert: Alert):
        """Broadcast alert to relevant channels."""
        if not self.channel_layer:
            return

        try:
            # Broadcast to proxy group if proxy exists
            if alert.proxy:
                self.channel_layer.group_send(
                    f'proxy_{alert.proxy.id}',
                    {
                        'type': 'alert.created',
                        'data': self._alert_to_dict(alert),
                    }
                )

            # Broadcast to alerts group for admin panel
            self.channel_layer.group_send(
                'alerts',
                {
                    'type': 'alert.created',
                    'data': self._alert_to_dict(alert),
                }
            )
        except Exception as e:
            logger.error(f"Failed to broadcast alert: {e}")

    def _alert_to_dict(self, alert: Alert) -> dict:
        """Convert alert to dictionary."""
        return {
            'id': str(alert.id),
            'type': alert.alert_type,
            'severity': alert.severity,
            'status': alert.status,
            'title': alert.title,
            'message': alert.message,
            'details': alert.details,
            'entity_type': alert.entity_type,
            'entity_id': alert.entity_id,
            'entity_name': alert.entity_name,
            'proxy_id': str(alert.proxy.id) if alert.proxy else None,
            'proxy_name': alert.proxy.name if alert.proxy else None,
            'task_id': str(alert.task.id) if alert.task else None,
            'metric_value': alert.metric_value,
            'threshold_value': alert.threshold_value,
            'triggered_at': alert.triggered_at.isoformat(),
            'occurrence_count': alert.occurrence_count,
        }

    # ==================== Node/Proxy specific methods ====================

    def check_node_offline(self, node) -> Optional[Alert]:
        """
        Check if node should trigger offline alert.

        Args:
            node: Proxy node to check

        Returns:
            Created alert if node is offline, None otherwise
        """
        # Check if node has status attribute (ProxyNode)
        if hasattr(node, 'status'):
            if node.status != node.NodeStatus.OFFLINE:
                return None
        else:
            # Fallback: check if node has is_online attribute
            if hasattr(node, 'is_online') and node.is_online:
                return None

        # Check cooldown
        cache_key = f"{self._CACHE_PREFIX}node_offline:{node.id}"
        if cache.get(cache_key):
            return None

        alert = self.create_alert(
            alert_type=AlertType.NODE_OFFLINE.value,
            severity=AlertSeverity.WARNING,
            entity_type='nodes.ProxyNode',
            entity_id=str(node.id),
            entity_name=node.name,
            proxy=node,
            source='nodes',
        )

        # Set cooldown
        cache.set(cache_key, True, self._CACHE_TIMEOUT)
        return alert

    # Legacy method for backward compatibility
    def check_proxy_offline(self, proxy) -> Optional[Alert]:
        """Legacy method - delegates to check_node_offline."""
        return self.check_node_offline(proxy)

    def check_node_timeout(self, node) -> Optional[Alert]:
        """
        Check if node heartbeat has timed out.

        Args:
            node: Proxy node to check

        Returns:
            Created alert if timeout detected, None otherwise
        """
        if not hasattr(node, 'last_heartbeat') or not node.last_heartbeat:
            return None

        heartbeat_interval = getattr(node, 'heartbeat_interval', 30)
        timeout_threshold = heartbeat_interval * AlertThresholds.HEARTBEAT_TIMEOUT_MULTIPLIER
        time_since_heartbeat = (timezone.now() - node.last_heartbeat).total_seconds()

        if time_since_heartbeat > timeout_threshold:
            cache_key = f"{self._CACHE_PREFIX}node_timeout:{node.id}"
            if cache.get(cache_key):
                return None

            alert = self.create_alert(
                alert_type=AlertType.NODE_TIMEOUT.value,
                severity=AlertSeverity.WARNING,
                entity_type='nodes.ProxyNode',
                entity_id=str(node.id),
                entity_name=node.name,
                proxy=node,
                details={
                    'last_heartbeat': node.last_heartbeat.isoformat(),
                    'timeout_seconds': int(time_since_heartbeat),
                },
                source='nodes',
            )

            cache.set(cache_key, True, self._CACHE_TIMEOUT)
            return alert

        return None

    # Legacy method for backward compatibility
    def check_proxy_timeout(self, proxy) -> Optional[Alert]:
        """Legacy method - delegates to check_node_timeout."""
        return self.check_node_timeout(proxy)

    def check_task_failed(self, task, error: str = None) -> Optional[Alert]:
        """
        Check if task should trigger failed alert.

        Args:
            task: Failed task
            error: Error message

        Returns:
            Created alert
        """
        entity_name = task.proxy.name if hasattr(task, 'proxy') and task.proxy else str(task.id)
        error_message = error or (task.error_message if hasattr(task, 'error_message') else 'Unknown error')

        return self.create_alert(
            alert_type=AlertType.TASK_FAILED.value,
            severity=AlertSeverity.WARNING,
            entity_type='nodes.ProxyTask',
            entity_id=str(task.id),
            entity_name=entity_name,
            proxy=getattr(task, 'proxy', None),
            task=task,
            details={
                'task_type': getattr(task, 'task_type', 'unknown'),
                'parameters': getattr(task, 'parameters', {}),
            },
            source='nodes',
        )

    def check_task_timeout(self, task) -> Optional[Alert]:
        """
        Check if task has timed out.

        Args:
            task: Task to check

        Returns:
            Created alert if timeout detected, None otherwise
        """
        if not hasattr(task, 'started_at') or not task.started_at:
            return None

        timeout_seconds = getattr(task, 'timeout_seconds', AlertThresholds.TASK_TIMEOUT_DEFAULT)
        elapsed = (timezone.now() - task.started_at).total_seconds()

        if elapsed > timeout_seconds:
            entity_name = task.proxy.name if hasattr(task, 'proxy') and task.proxy else str(task.id)

            return self.create_alert(
                alert_type=AlertType.TASK_TIMEOUT.value,
                severity=AlertSeverity.CRITICAL,
                entity_type='nodes.ProxyTask',
                entity_id=str(task.id),
                entity_name=entity_name,
                proxy=getattr(task, 'proxy', None),
                task=task,
                details={
                    'elapsed_seconds': int(elapsed),
                    'timeout_seconds': timeout_seconds,
                },
                metric_value=elapsed,
                threshold_value=timeout_seconds,
                source='nodes',
            )

        return None

    def check_resource_alerts(self, node, metrics: dict) -> List[Alert]:
        """
        Check all resource alerts for a node.

        Args:
            node: Proxy node
            metrics: Dictionary with 'cpu_usage', 'memory_usage', 'disk_usage'

        Returns:
            List of created alerts
        """
        alerts = []
        entity_name = getattr(node, 'name', str(node.id))

        # CPU alert
        cpu_usage = metrics.get('cpu_usage', 0)
        if cpu_usage >= AlertThresholds.CPU_CRITICAL:
            severity = AlertSeverity.CRITICAL
            threshold = AlertThresholds.CPU_CRITICAL
        elif cpu_usage >= AlertThresholds.CPU_WARNING:
            severity = AlertSeverity.WARNING
            threshold = AlertThresholds.CPU_WARNING
        else:
            severity = None

        if severity:
            alert = self.create_alert(
                alert_type=AlertType.CPU_HIGH.value,
                severity=severity,
                entity_type='nodes.ProxyNode',
                entity_id=str(node.id),
                entity_name=entity_name,
                proxy=node,
                metric_value=cpu_usage,
                threshold_value=threshold,
                source='nodes',
            )
            alerts.append(alert)

        # Memory alert
        memory_usage = metrics.get('memory_usage', 0)
        if memory_usage >= AlertThresholds.MEMORY_CRITICAL:
            severity = AlertSeverity.CRITICAL
            threshold = AlertThresholds.MEMORY_CRITICAL
        elif memory_usage >= AlertThresholds.MEMORY_WARNING:
            severity = AlertSeverity.WARNING
            threshold = AlertThresholds.MEMORY_WARNING
        else:
            severity = None

        if severity:
            alert = self.create_alert(
                alert_type=AlertType.MEMORY_HIGH.value,
                severity=severity,
                entity_type='nodes.ProxyNode',
                entity_id=str(node.id),
                entity_name=entity_name,
                proxy=node,
                metric_value=memory_usage,
                threshold_value=threshold,
                source='nodes',
            )
            alerts.append(alert)

        # Disk alert
        disk_usage = metrics.get('disk_usage', 0)
        if disk_usage >= AlertThresholds.DISK_CRITICAL:
            severity = AlertSeverity.CRITICAL
            threshold = AlertThresholds.DISK_CRITICAL
        elif disk_usage >= AlertThresholds.DISK_WARNING:
            severity = AlertSeverity.WARNING
            threshold = AlertThresholds.DISK_WARNING
        else:
            severity = None

        if severity:
            alert = self.create_alert(
                alert_type=AlertType.DISK_HIGH.value,
                severity=severity,
                entity_type='nodes.ProxyNode',
                entity_id=str(node.id),
                entity_name=entity_name,
                proxy=node,
                metric_value=disk_usage,
                threshold_value=threshold,
                source='nodes',
            )
            alerts.append(alert)

        return alerts

    def check_error_rate(self, node, error_rate: int) -> Optional[Alert]:
        """
        Check if error rate exceeds threshold.

        Args:
            node: Proxy node
            error_rate: Errors per minute

        Returns:
            Created alert if threshold exceeded, None otherwise
        """
        if error_rate >= AlertThresholds.ERROR_RATE_CRITICAL:
            severity = AlertSeverity.CRITICAL
            threshold = AlertThresholds.ERROR_RATE_CRITICAL
        elif error_rate >= AlertThresholds.ERROR_RATE_WARNING:
            severity = AlertSeverity.WARNING
            threshold = AlertThresholds.ERROR_RATE_WARNING
        else:
            return None

        entity_name = getattr(node, 'name', str(node.id))

        return self.create_alert(
            alert_type=AlertType.ERROR_RATE_HIGH.value,
            severity=severity,
            entity_type='nodes.ProxyNode',
            entity_id=str(node.id),
            entity_name=entity_name,
            proxy=node,
            metric_value=error_rate,
            threshold_value=threshold,
            source='nodes',
        )

    # ==================== General alert management methods ====================

    def evaluate_rules(self, entity, metrics: dict) -> List[Alert]:
        """
        Evaluate all alert rules for an entity.

        Args:
            entity: The entity being evaluated
            metrics: Current metrics dictionary

        Returns:
            List of triggered alerts
        """
        alerts = []

        # Determine entity type and ID
        entity_type = None
        entity_id = None
        if hasattr(entity, '_meta'):
            entity_type = f"{entity._meta.app_label}.{entity._meta.model_name}"
            entity_id = str(entity.id)

        # Get enabled rules that apply to this entity
        rules = AlertRule.objects.filter(enabled=True).filter(
            models.Q(applies_to_all_entities=True) |
            (models.Q(entity_type=entity_type) & models.Q(target_ids__contains=entity_id))
        )

        for rule in rules:
            should_trigger, value = rule.evaluate(entity, metrics)
            if should_trigger:
                alert = self.create_alert(
                    alert_type=rule.alert_type,
                    severity=AlertSeverity(rule.severity),
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=getattr(entity, 'name', str(entity.id)),
                    title=rule.name,
                    message=rule.description or f"Alert rule '{rule.name}' triggered",
                    details={
                        'rule_id': str(rule.id),
                        'condition': rule.condition,
                    },
                    metric_value=value,
                    threshold_value=rule.threshold_value,
                    source=rule.source or 'rules',
                )

                # Update rule's last triggered time
                rule.last_triggered_at = timezone.now()
                rule.save(update_fields=['last_triggered_at'])

                alerts.append(alert)

        return alerts

    def get_active_alerts(
        self,
        entity_type: str = None,
        entity_id: str = None,
        severity: AlertSeverity = None,
        source: str = None,
        limit: int = 100,
    ) -> List[Alert]:
        """
        Get active alerts.

        Args:
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            severity: Filter by severity
            source: Filter by source
            limit: Maximum number of alerts to return

        Returns:
            List of active alerts
        """
        queryset = Alert.objects.filter(status=AlertStatus.ACTIVE.value)

        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        if severity:
            queryset = queryset.filter(severity=severity.value)
        if source:
            queryset = queryset.filter(source=source)

        return queryset.select_related('proxy', 'task').order_by('-triggered_at')[:limit]

    def acknowledge_alert(self, alert_id, user, note: str = None) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID
            user: User acknowledging the alert
            note: Optional acknowledgment note

        Returns:
            True if successful, False otherwise
        """
        try:
            alert = Alert.objects.get(id=alert_id)
            alert.acknowledged_at = timezone.now()
            alert.acknowledged_by = user
            alert.acknowledgment_note = note or ''
            alert.status = AlertStatus.ACKNOWLEDGED.value
            alert.save()
            return True
        except Alert.DoesNotExist:
            logger.error(f"Alert {alert_id} not found")
            return False

    def resolve_alert(self, alert_id, user, note: str = None) -> bool:
        """
        Resolve an alert.

        Args:
            alert_id: Alert ID
            user: User resolving the alert
            note: Optional resolution note

        Returns:
            True if successful, False otherwise
        """
        try:
            alert = Alert.objects.get(id=alert_id)
            alert.resolved_at = timezone.now()
            alert.resolved_by = user
            alert.resolution_note = note or ''
            alert.status = AlertStatus.RESOLVED.value
            alert.save()
            return True
        except Alert.DoesNotExist:
            logger.error(f"Alert {alert_id} not found")
            return False

    def silence_alert(self, alert_id, user, until: timezone.datetime = None) -> bool:
        """
        Silence an alert.

        Args:
            alert_id: Alert ID
            user: User silencing the alert
            until: Optional time until when to silence

        Returns:
            True if successful, False otherwise
        """
        try:
            alert = Alert.objects.get(id=alert_id)
            alert.silenced_until = until
            alert.silenced_by = user
            alert.status = AlertStatus.SILENCED.value
            alert.save()
            return True
        except Alert.DoesNotExist:
            logger.error(f"Alert {alert_id} not found")
            return False


# Global alert manager instance
alert_manager = AlertManager()
