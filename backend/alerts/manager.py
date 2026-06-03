"""Compatibility adapter for modules that emit alert events directly."""

import uuid

from django.utils import timezone

from .choices import AlertSeverity, AlertStatus
from .models import AlertRecord


class AlertManager:
    def create_alert(
        self,
        alert_type,
        severity=AlertSeverity.WARNING,
        title="Alert",
        message="",
        entity_type=None,
        entity_id=None,
        entity_name="",
        details=None,
        metric_value=None,
        threshold_value=None,
        source="system",
        **kwargs,
    ):
        now = timezone.now()
        severity = severity.value if hasattr(severity, "value") else severity
        if severity == "fatal":
            severity = AlertSeverity.CRITICAL

        fingerprint = f"compat:{source}:{alert_type}:{entity_type}:{entity_id}:{title}"
        tenant = kwargs.get("tenant") or getattr(kwargs.get("user"), "tenant", None) or getattr(kwargs.get("owner"), "tenant", None)
        active_alert = AlertRecord.objects.filter(
            tenant=tenant,
            fingerprint=fingerprint,
            status__in=[AlertStatus.PENDING, AlertStatus.FIRING, AlertStatus.ACKNOWLEDGED],
        ).first()
        if active_alert:
            active_alert.status = AlertStatus.FIRING
            active_alert.severity = severity if severity in AlertSeverity.values else AlertSeverity.WARNING
            active_alert.title = title
            active_alert.message = message
            active_alert.current_value = metric_value
            active_alert.threshold_value = threshold_value
            active_alert.metadata = {**(details or {}), "alert_type": str(alert_type), "source": source}
            active_alert.last_triggered_at = now
            active_alert.save(update_fields=[
                "status",
                "severity",
                "title",
                "message",
                "current_value",
                "threshold_value",
                "metadata",
                "last_triggered_at",
                "updated_at",
            ])
            return active_alert

        return AlertRecord.objects.create(
            tenant=tenant,
            policy_id=None,
            type="event" if source not in {"repository", "proxy"} else "metric",
            severity=severity if severity in AlertSeverity.values else AlertSeverity.WARNING,
            status=AlertStatus.FIRING,
            resource_type=self._resource_type(entity_type, source),
            resource_id=self._uuid_or_none(entity_id),
            resource_name=entity_name or "",
            title=title,
            message=message,
            current_value=metric_value,
            threshold_value=threshold_value,
            fingerprint=fingerprint,
            metadata={**(details or {}), "alert_type": str(alert_type), "source": source},
            first_triggered_at=now,
            last_triggered_at=now,
        )

    def check_task_failed(self, task, error=None):
        return self.create_alert(
            alert_type="job_failed",
            severity=AlertSeverity.CRITICAL,
            title=f"Task Failed: {getattr(task, 'id', '')}",
            message=error or getattr(task, "error_message", "") or "Task failed",
            entity_type="nodes.ProxyTask",
            entity_id=str(getattr(task, "id", "")),
            entity_name=str(getattr(task, "task_type", "task")),
            details={"error": error},
            source="job",
        )

    def check_task_timeout(self, task):
        return self.create_alert(
            alert_type="job_timeout",
            severity=AlertSeverity.WARNING,
            title=f"Task Timeout: {getattr(task, 'id', '')}",
            message="Task timed out",
            entity_type="nodes.ProxyTask",
            entity_id=str(getattr(task, "id", "")),
            entity_name=str(getattr(task, "task_type", "task")),
            source="job",
        )

    def check_node_offline(self, node):
        return self.create_alert(
            alert_type="node_offline",
            severity=AlertSeverity.CRITICAL,
            title=f"Proxy Offline: {getattr(node, 'name', '')}",
            message="Proxy is offline",
            entity_type="nodes.ProxyNode",
            entity_id=str(getattr(node, "id", "")),
            entity_name=getattr(node, "name", ""),
            source="proxy",
        )

    def check_proxy_offline(self, proxy):
        return self.check_node_offline(proxy)

    def check_node_timeout(self, node):
        """
        Legacy heartbeat timeout hook.

        Proxy availability is evaluated by user-configured Availability Alert
        policies. Creating policy-less heartbeat alerts here duplicates the
        policy engine and bypasses user thresholds/channels.
        """
        return None

    def check_proxy_timeout(self, proxy):
        return self.check_node_timeout(proxy)

    def check_resource_alerts(self, node, metrics):
        """
        Legacy metric threshold hook.

        Metric alerts are now evaluated exclusively by AlertPolicy through
        alerts.services.metric_evaluator. Keeping hardcoded defaults here would
        create policy-less alerts such as cpu_usage >= 95% even when no user
        policy exists.
        """
        return None

    def check_error_rate(self, node, error_rate):
        if error_rate:
            return self.create_alert(
                alert_type="error_rate_high",
                severity=AlertSeverity.WARNING,
                title=f"Error Rate High: {getattr(node, 'name', '')}",
                message=f"Error rate is {error_rate}",
                entity_type="nodes.ProxyNode",
                entity_id=str(getattr(node, "id", "")),
                entity_name=getattr(node, "name", ""),
                metric_value=error_rate,
                source="proxy",
            )
        return None

    def _resource_type(self, entity_type, source):
        if source == "repository" or entity_type == "repository.Repository":
            return "backup_repository"
        if entity_type == "nodes.ProxyTask":
            return "job"
        if entity_type == "nodes.ProxyNode":
            return "sync_proxy"
        return "system_service"

    def _uuid_or_none(self, value):
        if not value:
            return None
        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError):
            return None


alert_manager = AlertManager()
