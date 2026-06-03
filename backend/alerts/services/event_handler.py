"""Platform event alert handling."""

from alerts.models import AlertPolicy
from alerts.services.evaluator import fire_alert


def emit_platform_event(category, event_type, actor=None, target=None, metadata=None):
    tenant_id = getattr(actor, "tenant_id", None) or getattr(target, "tenant_id", None)
    handle_platform_event(
        {
            "category": category,
            "type": event_type,
            "actor": str(getattr(actor, "id", "")) if actor else None,
            "target": str(getattr(target, "id", "")) if target else None,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "metadata": metadata or {},
        }
    )


def handle_platform_event(event):
    policies = AlertPolicy.objects.filter(enabled=True, type="event")
    if event.get("tenant_id"):
        policies = policies.filter(tenant_id=event["tenant_id"])
    else:
        policies = policies.filter(tenant__name="administrator")

    for policy in policies:
        rule = policy.trigger_rule or {}
        if rule.get("event_category") == event["category"] and event["type"] in (rule.get("event_types") or []):
            fire_alert(
                policy=policy,
                resource=None,
                title=f"Event Alert: {event['type']}",
                message=f"Platform event triggered: {event['type']}",
                alert_key=event["type"],
                metadata=event,
            )
