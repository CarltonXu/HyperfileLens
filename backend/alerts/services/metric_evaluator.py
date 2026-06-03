"""Metric alert evaluation."""

import uuid
from types import SimpleNamespace

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
        _evaluate_metric_policy_for_resource(policy, resource)


def evaluate_metric_policies_for_resource(resource):
    """Evaluate enabled metric policies that target one freshly updated resource."""
    from alerts.models import AlertPolicy

    resource_type = _resource_type_for_instance(resource)
    if not resource_type:
        return

    policies = AlertPolicy.objects.filter(
        enabled=True,
        type="metric",
        resource_type=resource_type,
        tenant=getattr(resource, "tenant", None),
    )
    for policy in policies:
        if policy.scope == "selected" and str(getattr(resource, "id", "")) not in {str(item) for item in policy.resource_ids or []}:
            continue
        _evaluate_metric_policy_for_resource(policy, resource)


def _evaluate_metric_policy_for_resource(policy, resource):
    rule = policy.trigger_rule or {}
    metric_key = rule.get("metric_key")
    operator = rule.get("operator", ">=")
    threshold = rule.get("threshold")
    if not metric_key or threshold is None:
        return

    value = _metric_value(resource, policy.resource_type, metric_key, rule, tenant=policy.tenant)
    if value is None:
        return

    alert_key = f"metric:{metric_key}"
    metric_label = _metric_label(metric_key)
    resource_name = getattr(resource, "name", resource)
    if _compare(value, operator, float(threshold)):
        fire_alert(
            policy,
            resource=resource,
            title=f"{metric_label} - {resource_name}",
            message=(
                f"{resource_name} 的 {metric_label} 当前为 {value:.2f}{rule.get('unit', '')}，"
                f"已满足触发条件：{metric_label} {operator} {threshold}{rule.get('unit', '')}。"
            ),
            current_value=value,
            alert_key=alert_key,
            metadata={"metric_key": metric_key, "metric_label": metric_label, "operator": operator},
        )
    elif _is_recovered(policy, value):
        resolve_policy_alerts(policy, resource=resource, alert_key=alert_key)


def _resource_type_for_instance(resource):
    model_name = resource.__class__.__name__
    if model_name == "ProxyNode":
        return ResourceType.SYNC_PROXY if getattr(resource, "role", None) == "sync" else ResourceType.AGENT_PROXY
    if model_name == "Gateway":
        return ResourceType.GATEWAY
    if model_name == "Repository":
        return ResourceType.BACKUP_REPOSITORY
    if model_name == "SourceResource":
        return ResourceType.SOURCE_RESOURCE
    return None


def _metric_label(metric_key):
    labels = {
        "cpu_usage": "CPU 利用率告警",
        "memory_usage": "内存利用率告警",
        "disk_usage": "磁盘利用率告警",
        "network_rx": "网络入流量告警",
        "network_tx": "网络出流量告警",
        "capacity_usage": "容量利用率告警",
        "used_size": "已用容量告警",
        "free_size": "可用容量告警",
        "data_size": "数据量告警",
        "file_count": "文件数量告警",
        "swap_usage": "Swap 利用率告警",
        "disk_read_bytes": "磁盘读取量告警",
        "disk_write_bytes": "磁盘写入量告警",
        "load_1m": "1 分钟负载告警",
        "load_5m": "5 分钟负载告警",
        "load_15m": "15 分钟负载告警",
    }
    return labels.get(metric_key, metric_key or "指标告警")


def _resources_for_policy(policy):
    resource_type = policy.resource_type
    ids = policy.resource_ids or []

    if resource_type in (ResourceType.SYNC_PROXY, ResourceType.AGENT_PROXY):
        from nodes.models import ProxyNode

        role = "sync" if resource_type == ResourceType.SYNC_PROXY else "agent"
        qs = ProxyNode.objects.filter(role=role, tenant=policy.tenant)
    elif resource_type == ResourceType.SYSTEM:
        return [
            SimpleNamespace(
                id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                name="Control Plane",
                status="active",
            )
        ]
    elif resource_type == ResourceType.GATEWAY:
        from gateways.models import Gateway

        qs = Gateway.objects.filter(tenant=policy.tenant)
    elif resource_type == ResourceType.BACKUP_REPOSITORY:
        from repository.models import Repository

        qs = Repository.objects.filter(tenant=policy.tenant)
    elif resource_type == ResourceType.SOURCE_RESOURCE:
        from source_resources.models import SourceResource

        qs = SourceResource.objects.filter(tenant=policy.tenant)
    else:
        return []

    if policy.scope == "selected":
        qs = qs.filter(id__in=ids)
    return qs


def _metric_value(resource, resource_type, metric_key, rule, tenant=None):
    if resource_type == ResourceType.SYSTEM:
        return _system_metric_value(metric_key, rule, tenant=tenant)
    if resource_type in (ResourceType.SYNC_PROXY, ResourceType.AGENT_PROXY):
        return _proxy_metric_value(resource, metric_key, rule)
    if resource_type == ResourceType.GATEWAY:
        return _gateway_metric_value(resource, metric_key, rule)
    if resource_type == ResourceType.BACKUP_REPOSITORY:
        return _repository_metric_value(resource, metric_key)
    if resource_type == ResourceType.SOURCE_RESOURCE:
        return _source_resource_metric_value(resource, metric_key)
    return None


def _system_metric_value(metric_key, rule, tenant=None):
    from alerts.models import SystemMetric

    duration = int(rule.get("duration_seconds") or 0)
    queryset = SystemMetric.objects.filter(tenant=tenant)
    if duration > 0:
        since = timezone.now() - timezone.timedelta(seconds=duration)
        queryset = queryset.filter(timestamp__gte=since)
    metrics = list(queryset.order_by("-timestamp")[:300])
    if not metrics:
        return None
    values = [_system_metric_from_sample(metric, metric_key) for metric in metrics]
    values = [value for value in values if value is not None]
    if not values:
        return None
    return sum(values) / len(values) if duration > 0 else values[0]


def _system_metric_from_sample(metric, metric_key):
    cpu = metric.cpu or {}
    memory = metric.memory or {}
    swap = metric.swap or {}
    disks = metric.disks or []
    disk_io = metric.disk_io or []
    networks = metric.networks or []
    load_average = metric.load_average or []

    if metric_key == "cpu_usage":
        return _number_or_none(cpu.get("usage_percent"))
    if metric_key == "memory_usage":
        return _number_or_none(memory.get("percent"))
    if metric_key == "swap_usage":
        return _number_or_none(swap.get("percent"))
    if metric_key == "disk_usage":
        values = [_number_or_none(item.get("percent")) for item in disks if isinstance(item, dict)]
        values = [value for value in values if value is not None]
        return max(values) if values else None
    if metric_key == "disk_read_bytes":
        return sum(_number_or_none(item.get("read_bytes")) or 0 for item in disk_io if isinstance(item, dict))
    if metric_key == "disk_write_bytes":
        return sum(_number_or_none(item.get("write_bytes")) or 0 for item in disk_io if isinstance(item, dict))
    if metric_key == "network_rx":
        return sum(_number_or_none(item.get("bytes_recv")) or 0 for item in networks if isinstance(item, dict))
    if metric_key == "network_tx":
        return sum(_number_or_none(item.get("bytes_sent")) or 0 for item in networks if isinstance(item, dict))
    if metric_key == "load_1m":
        return _number_or_none(load_average[0]) if len(load_average) > 0 else None
    if metric_key == "load_5m":
        return _number_or_none(load_average[1]) if len(load_average) > 1 else None
    if metric_key == "load_15m":
        return _number_or_none(load_average[2]) if len(load_average) > 2 else None
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
