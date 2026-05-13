"""Core alert lifecycle helpers and periodic evaluator entrypoint."""

from decimal import Decimal

from django.utils import timezone

from alerts.choices import AlertStatus, NotificationStatus
from alerts.models import AlertPolicy, AlertRecord, NotificationLog
from alerts.services.fingerprint import build_fingerprint
from alerts.services.notifier import send_notification, send_resolved_notification


def fire_alert(policy, resource=None, title="", message="", current_value=None, alert_key="default", metadata=None):
    resource_id = getattr(resource, "id", None)
    resource_name = getattr(resource, "name", None) or getattr(resource, "hostname", None)
    fingerprint = build_fingerprint(policy, resource_id, alert_key)
    now = timezone.now()

    alert = AlertRecord.objects.filter(
        fingerprint=fingerprint,
        status__in=[AlertStatus.PENDING, AlertStatus.FIRING, AlertStatus.ACKNOWLEDGED],
    ).first()
    if alert:
        previous_status = alert.status
        alert.status = AlertStatus.FIRING
        alert.last_triggered_at = now
        if current_value is not None:
            alert.current_value = Decimal(str(current_value))
        threshold = (policy.trigger_rule or {}).get("threshold")
        if threshold is None:
            threshold = (policy.trigger_rule or {}).get("timeout_seconds")
        if threshold is not None:
            alert.threshold_value = Decimal(str(threshold))
        alert.unit = (policy.trigger_rule or {}).get("unit") or ("s" if (policy.trigger_rule or {}).get("timeout_seconds") is not None else alert.unit)
        alert.title = title or alert.title
        alert.message = message or alert.message
        alert.metadata = metadata or alert.metadata
        alert.save(update_fields=["status", "last_triggered_at", "current_value", "threshold_value", "unit", "title", "message", "metadata", "updated_at"])
        if previous_status != AlertStatus.FIRING or _should_retry_firing_notification(alert):
            send_notification(alert)
        return alert

    threshold = (policy.trigger_rule or {}).get("threshold")
    if threshold is None:
        threshold = (policy.trigger_rule or {}).get("timeout_seconds")
    alert = AlertRecord.objects.create(
        policy_id=policy.id,
        type=policy.type,
        severity=policy.severity,
        status=AlertStatus.FIRING,
        resource_type=policy.resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        title=title,
        message=message,
        current_value=Decimal(str(current_value)) if current_value is not None else None,
        threshold_value=Decimal(str(threshold)) if threshold is not None else None,
        unit=(policy.trigger_rule or {}).get("unit") or ("s" if (policy.trigger_rule or {}).get("timeout_seconds") is not None else None),
        fingerprint=fingerprint,
        metadata=metadata or {},
        first_triggered_at=now,
        last_triggered_at=now,
    )
    send_notification(alert)
    return alert


def resolve_alert(alert):
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = timezone.now()
    alert.save(update_fields=["status", "resolved_at", "updated_at"])
    send_resolved_notification(alert)
    return alert


def active_alerts_for_policy(policy, resource=None, alert_key="default"):
    resource_id = getattr(resource, "id", None)
    fingerprint = build_fingerprint(policy, resource_id, alert_key)
    return AlertRecord.objects.filter(
        fingerprint=fingerprint,
        status__in=[AlertStatus.PENDING, AlertStatus.FIRING, AlertStatus.ACKNOWLEDGED],
    )


def resolve_policy_alerts(policy, resource=None, alert_key="default"):
    for alert in active_alerts_for_policy(policy, resource=resource, alert_key=alert_key):
        resolve_alert(alert)


def _should_retry_firing_notification(alert, cooldown_seconds=300):
    """Retry notification for long-lived firing alerts that have not been delivered."""
    logs = NotificationLog.objects.filter(alert_record_id=alert.id).order_by("-sent_at")
    if logs.filter(status=NotificationStatus.SUCCESS).exists():
        return False

    latest = logs.first()
    if not latest:
        return True
    return (timezone.now() - latest.sent_at).total_seconds() >= cooldown_seconds


def evaluate_alert_policies():
    """Evaluate policies that are expected to be scanned periodically."""
    from .availability_evaluator import evaluate_availability_policy
    from .metric_evaluator import evaluate_metric_policy
    from .system_evaluator import evaluate_system_policy

    for policy in AlertPolicy.objects.filter(enabled=True):
        if policy.type == "metric":
            evaluate_metric_policy(policy)
        elif policy.type == "availability":
            evaluate_availability_policy(policy)
        elif policy.type == "system":
            evaluate_system_policy(policy)
