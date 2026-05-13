"""Availability alert evaluation."""

from django.utils import timezone

from alerts.choices import ResourceType
from alerts.services.evaluator import fire_alert, resolve_policy_alerts


def evaluate_availability_policy(policy):
    rule = policy.trigger_rule or {}
    check_type = rule.get("check_type")
    timeout_seconds = int(rule.get("timeout_seconds") or 60)

    for resource in _resources_for_policy(policy):
        down, message = _availability_state(resource, policy.resource_type, check_type, timeout_seconds)
        alert_key = f"availability:{check_type or 'default'}"
        if down:
            fire_alert(
                policy,
                resource=resource,
                title=f"{policy.name}: unavailable",
                message=message,
                alert_key=alert_key,
                metadata={"check_type": check_type, "timeout_seconds": timeout_seconds},
            )
        else:
            resolve_policy_alerts(policy, resource=resource, alert_key=alert_key)


def _resources_for_policy(policy):
    ids = policy.resource_ids or []
    if policy.resource_type in (ResourceType.SYNC_PROXY, ResourceType.AGENT_PROXY):
        from nodes.models import ProxyNode

        role = "sync" if policy.resource_type == ResourceType.SYNC_PROXY else "agent"
        qs = ProxyNode.objects.filter(role=role)
    elif policy.resource_type == ResourceType.GATEWAY:
        from gateways.models import Gateway

        qs = Gateway.objects.all()
    elif policy.resource_type == ResourceType.BACKUP_REPOSITORY:
        from repository.models import Repository

        qs = Repository.objects.all()
    elif policy.resource_type == ResourceType.SOURCE_RESOURCE:
        from source_resources.models import SourceResource

        qs = SourceResource.objects.all()
    else:
        return []

    if policy.scope == "selected":
        qs = qs.filter(id__in=ids)
    return qs


def _availability_state(resource, resource_type, check_type, timeout_seconds):
    if check_type == "heartbeat" and resource_type in (
        ResourceType.SYNC_PROXY,
        ResourceType.AGENT_PROXY,
        ResourceType.GATEWAY,
    ):
        last_heartbeat = getattr(resource, "last_heartbeat", None)
        if not last_heartbeat:
            return True, f"{resource.name} has never reported a heartbeat."
        age = (timezone.now() - last_heartbeat).total_seconds()
        if age > timeout_seconds:
            return True, f"{resource.name} heartbeat timeout: {int(age)}s > {timeout_seconds}s."
        return False, ""

    status = getattr(resource, "status", None)
    if resource_type == ResourceType.BACKUP_REPOSITORY:
        down = status not in ("active",)
        return down, f"{resource.name} repository status is {status}."
    if resource_type == ResourceType.SOURCE_RESOURCE:
        down = status not in ("active", "connected")
        return down, f"{resource.name} source resource status is {status}."
    return False, ""
