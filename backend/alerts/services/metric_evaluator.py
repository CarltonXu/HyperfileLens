"""Metric alert evaluation."""

from django.utils import timezone

from alerts.choices import ResourceType
from alerts.services.evaluator import fire_alert, resolve_policy_alerts


def evaluate_metric_policy(policy):
    rule = policy.trigger_rule or {}
    metric_key = rule.get("metric_key")
    operator = rule.get("operator", ">=")
    threshold = rule.get("threshold")
    if not metric_key or threshold is None:
        return

    for resource in _resources_for_policy(policy):
        value = _metric_value(resource, policy.resource_type, metric_key, rule)
        if value is None:
            continue

        alert_key = f"metric:{metric_key}"
        if _compare(value, operator, float(threshold)):
            fire_alert(
                policy,
                resource=resource,
                title=f"{policy.name}: {metric_key}",
                message=(
                    f"{getattr(resource, 'name', resource)} {metric_key} "
                    f"is {value:.2f}{rule.get('unit', '')}, threshold {operator} {threshold}."
                ),
                current_value=value,
                alert_key=alert_key,
                metadata={"metric_key": metric_key, "operator": operator},
            )
        elif _is_recovered(policy, value):
            resolve_policy_alerts(policy, resource=resource, alert_key=alert_key)


def _resources_for_policy(policy):
    resource_type = policy.resource_type
    ids = policy.resource_ids or []

    if resource_type in (ResourceType.SYNC_PROXY, ResourceType.AGENT_PROXY):
        from nodes.models import ProxyNode

        role = "sync" if resource_type == ResourceType.SYNC_PROXY else "agent"
        qs = ProxyNode.objects.filter(role=role)
    elif resource_type == ResourceType.GATEWAY:
        from gateways.models import Gateway

        qs = Gateway.objects.all()
    elif resource_type == ResourceType.BACKUP_REPOSITORY:
        from repository.models import Repository

        qs = Repository.objects.all()
    elif resource_type == ResourceType.SOURCE_RESOURCE:
        from source_resources.models import SourceResource

        qs = SourceResource.objects.all()
    else:
        return []

    if policy.scope == "selected":
        qs = qs.filter(id__in=ids)
    return qs


def _metric_value(resource, resource_type, metric_key, rule):
    if resource_type in (ResourceType.SYNC_PROXY, ResourceType.AGENT_PROXY):
        return _proxy_metric_value(resource, metric_key, rule)
    if resource_type == ResourceType.GATEWAY:
        return _gateway_metric_value(resource, metric_key, rule)
    if resource_type == ResourceType.BACKUP_REPOSITORY:
        return _repository_metric_value(resource, metric_key)
    if resource_type == ResourceType.SOURCE_RESOURCE:
        return _source_resource_metric_value(resource, metric_key)
    return None


def _proxy_metric_value(proxy, metric_key, rule):
    field_map = {
        "cpu_usage": "cpu_usage",
        "memory_usage": "memory_usage",
        "disk_usage": "disk_usage",
        "network_rx": "network_in",
        "network_tx": "network_out",
    }
    field = field_map.get(metric_key)
    if not field:
        return None
    duration = int(rule.get("duration_seconds") or 0)
    if duration > 0:
        since = timezone.now() - timezone.timedelta(seconds=duration)
        values = [
            getattr(item, field, None)
            for item in proxy.heartbeats.filter(timestamp__gte=since)
            if getattr(item, field, None) is not None
        ]
        if values:
            return sum(values) / len(values)
    current_field = "network_bytes_recv" if metric_key == "network_rx" else "network_bytes_sent" if metric_key == "network_tx" else field
    return _number_or_none(getattr(proxy, current_field, None))


def _gateway_metric_value(gateway, metric_key, rule):
    field_map = {
        "cpu_usage": "cpu_usage",
        "memory_usage": "memory_usage",
        "disk_usage": "disk_usage",
        "network_rx": "network_bytes_recv",
        "network_tx": "network_bytes_sent",
    }
    field = field_map.get(metric_key)
    if not field:
        return None
    duration = int(rule.get("duration_seconds") or 0)
    if duration > 0:
        since = timezone.now() - timezone.timedelta(seconds=duration)
        values = [
            getattr(item, field, None)
            for item in gateway.heartbeats.filter(timestamp__gte=since)
            if getattr(item, field, None) is not None
        ]
        if values:
            return sum(values) / len(values)
    return _number_or_none(getattr(gateway, field, None))


def _repository_metric_value(repository, metric_key):
    if metric_key == "capacity_usage":
        total = repository.quota_bytes if repository.quota_enabled and repository.quota_bytes else repository.capacity
        return (repository.used_space / total) * 100 if total else None
    if metric_key == "used_size":
        return _number_or_none(repository.used_space)
    if metric_key == "free_size":
        return _number_or_none(repository.available_space)
    return None


def _source_resource_metric_value(resource, metric_key):
    if metric_key == "data_size":
        return _number_or_none(resource.total_size)
    if metric_key == "file_count":
        return _number_or_none(resource.file_count)
    return None


def _is_recovered(policy, value):
    rule = policy.recovery_rule or {}
    if rule.get("enabled") is False:
        return False
    operator = rule.get("operator")
    threshold = rule.get("threshold")
    if operator and threshold is not None:
        return _compare(value, operator, float(threshold))
    trigger = policy.trigger_rule or {}
    return not _compare(value, trigger.get("operator", ">="), float(trigger.get("threshold")))


def _compare(value, operator, threshold):
    if operator == ">":
        return value > threshold
    if operator == ">=":
        return value >= threshold
    if operator == "<":
        return value < threshold
    if operator == "<=":
        return value <= threshold
    if operator == "==":
        return value == threshold
    if operator == "!=":
        return value != threshold
    return False


def _number_or_none(value):
    if value is None:
        return None
    return float(value)
