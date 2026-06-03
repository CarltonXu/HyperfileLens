"""Control-plane system alert evaluation."""

from django.db import connection

from alerts.models import SystemMetric
from alerts.services.evaluator import fire_alert, resolve_policy_alerts


def evaluate_system_policy(policy):
    rule = policy.trigger_rule or {}
    check_type = rule.get("check_type")

    if check_type == "disk_space_low":
        _evaluate_disk_space(policy)
    elif check_type in ("database_unreachable", "service_health"):
        _evaluate_database(policy)
    elif check_type in ("celery_worker_down", "scheduler_down", "api_service_down"):
        # If this code is running from the scheduled evaluator, the Django app
        # and at least one Celery worker are alive. External health checks can
        # extend this branch later.
        resolve_policy_alerts(policy, alert_key=f"system:{check_type}")


def _evaluate_disk_space(policy):
    rule = policy.trigger_rule or {}
    threshold = float(rule.get("threshold") or 90)
    metric = SystemMetric.objects.filter(tenant=policy.tenant).order_by("-timestamp").first()
    if not metric:
        return
    disks = metric.disks or []
    if not disks:
        return
    worst = max(disks, key=lambda item: item.get("percent") or 0)
    current = float(worst.get("percent") or 0)
    alert_key = "system:disk_space_low"
    if current >= threshold:
        fire_alert(
            policy,
            title=f"{policy.name}: disk space low",
            message=f"{worst.get('mountpoint') or worst.get('device')} usage is {current:.2f}%, threshold >= {threshold}%.",
            current_value=current,
            alert_key=alert_key,
            metadata={"disk": worst},
        )
    elif _is_recovered(policy, current):
        resolve_policy_alerts(policy, alert_key=alert_key)


def _evaluate_database(policy):
    check_type = (policy.trigger_rule or {}).get("check_type") or "database_unreachable"
    alert_key = f"system:{check_type}"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        fire_alert(
            policy,
            title=f"{policy.name}: database unreachable",
            message=str(exc),
            alert_key=alert_key,
            metadata={"check_type": check_type},
        )
    else:
        resolve_policy_alerts(policy, alert_key=alert_key)


def _is_recovered(policy, current):
    rule = policy.recovery_rule or {}
    if rule.get("enabled") is False:
        return False
    threshold = rule.get("threshold")
    if threshold is not None:
        return current < float(threshold)
    trigger_threshold = (policy.trigger_rule or {}).get("threshold")
    return trigger_threshold is not None and current < float(trigger_threshold)
