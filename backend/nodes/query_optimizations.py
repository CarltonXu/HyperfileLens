"""
Database query optimizations for HyperFileLens.

This module provides optimized query methods for common operations.
"""

import logging
from typing import List, Dict, Any, Optional
from django.db.models import Count, Sum, Avg, Max, Min, Q, F, Value, Case, When
from django.db.models import Prefetch, Subquery, OuterRef
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache

from .models import ProxyNode, ProxyTask

# Import Alert from alerts module
try:
    from alerts.models import Alert
except ImportError:
    Alert = None

logger = logging.getLogger(__name__)


# Cache configuration
CACHE_PREFIX = "nodes_query:"
CACHE_TIMEOUT = 300  # 5 minutes


def get_online_proxies_with_stats() -> List[Dict[str, Any]]:
    """
    Get online proxies with statistics.

    Optimized query with annotations and caching.
    """
    cache_key = f"{CACHE_PREFIX}online_proxies_with_stats"
    
    # Try cache first
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached

    # Query with annotations
    proxies = ProxyNode.objects.filter(
        status=ProxyNode.NodeStatus.ONLINE
    ).annotate(
        task_count=Count('tasks'),
        running_count=Count('tasks', filter=Q(tasks__status='running')),
        completed_count=Count('tasks', filter=Q(tasks__status='completed')),
        failed_count=Count('tasks', filter=Q(tasks__status='failed')),
        active_alert_count=Count('alerts', filter=Q(alerts__status='active')),
        total_alert_count=Count('alerts'),
    ).select_related(
        'alerts'
    ).order_by('-created_at')

    # Convert to dict
    result = [
        {
            'id': str(proxy.id),
            'name': proxy.name,
            'status': proxy.status,
            'task_count': proxy.task_count,
            'running_count': proxy.running_count,
            'completed_count': proxy.completed_count,
            'failed_count': proxy.failed_count,
            'active_alert_count': proxy.active_alert_count,
            'total_alert_count': proxy.total_alert_count,
            'last_heartbeat': proxy.last_heartbeat.isoformat() if proxy.last_heartbeat else None,
            'uptime_seconds': (timezone.now() - proxy.created_at).total_seconds() if proxy.created_at else 0,
        }
        for proxy in proxies
    ]

    # Cache result
    cache.set(cache_key, result, timeout=CACHE_TIMEOUT)
    
    return result


def get_proxy_summary(proxy_id: str) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive proxy summary.

    Optimized query with all relevant information.
    """
    cache_key = f"{CACHE_PREFIX}proxy_summary:{proxy_id}"
    
    # Try cache first
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        proxy = ProxyNode.objects.annotate(
            task_count=Count('tasks'),
            running_count=Count('tasks', filter=Q(tasks__status='running')),
            completed_count=Count('tasks', filter=Q(tasks__status='completed')),
            failed_count=Count('tasks', filter=Q(tasks__status='failed')),
            active_alert_count=Count('alerts', filter=Q(alerts__status='active')),
            total_alert_count=Count('alerts'),
            total_task_count=Count('tasks'),
        ).select_related().get(id=proxy_id)

        if not proxy:
            return None

        result = {
            'id': str(proxy.id),
            'name': proxy.name,
            'status': proxy.status,
            'task_count': proxy.task_count,
            'running_count': proxy.running_count,
            'completed_count': proxy.completed_count,
            'failed_count': proxy.failed_count,
            'active_alert_count': proxy.active_alert_count,
            'total_alert_count': proxy.total_alert_count,
            'total_task_count': proxy.total_task_count,
            'last_heartbeat': proxy.last_heartbeat.isoformat() if proxy.last_heartbeat else None,
            'uptime_seconds': (timezone.now() - proxy.created_at).total_seconds() if proxy.created_at else 0,
            'cpu_usage': proxy.cpu_usage,
            'memory_usage': proxy.memory_usage,
            'disk_usage': proxy.disk_usage,
            'bandwidth_limit_kbps': proxy.bandwidth_limit_kbps,
        }

        # Cache result
        cache.set(cache_key, result, timeout=CACHE_TIMEOUT)

        return result

    except ProxyNode.DoesNotExist:
        return None


def get_task_list(
    proxy_id: str = None,
    status: str = None,
    task_type: str = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get task list with filters and optimizations.

    Optimized query with select_related and only().
    """
    cache_key = f"{CACHE_PREFIX}task_list:{proxy_id}:{status}:{task_type}:{limit}"
    
    # Try cache first
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Build queryset
    queryset = ProxyTask.objects.select_related('proxy')

    # Apply filters
    if proxy_id:
        queryset = queryset.filter(proxy_id=proxy_id)
    if status:
        queryset = queryset.filter(status=status)
    if task_type:
        queryset = queryset.filter(task_type=task_type)

    # Order and limit
    queryset = queryset.order_by('-created_at')[:limit]

    # Optimize fields
    queryset = queryset.only(
        'id', 'task_type', 'status', 'progress', 'message',
        'created_at', 'started_at', 'completed_at',
        'proxy__name'
    )

    # Convert to dict
    result = [
        {
            'id': str(task.id),
            'task_type': task.task_type,
            'status': task.status,
            'progress': task.progress,
            'message': task.message,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'proxy_name': task.proxy.name if task.proxy else None,
            'duration_seconds': task.get_duration_seconds() if task.completed_at and task.started_at else 0,
        }
        for task in queryset
    ]

    # Cache result
    cache.set(cache_key, result, timeout=CACHE_TIMEOUT)

    return result


def get_alert_list(
    proxy_id: str = None,
    severity: str = None,
    status: str = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get alert list with filters and optimizations.

    Optimized query with select_related.
    """
    if Alert is None:
        logger.warning("Alert model not available")
        return []

    cache_key = f"{CACHE_PREFIX}alert_list:{proxy_id}:{severity}:{status}:{limit}"

    # Try cache first
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Build queryset
    queryset = Alert.objects.select_related('proxy', 'task', 'repository')

    # Apply filters
    if proxy_id:
        queryset = queryset.filter(proxy_id=proxy_id)
    if severity:
        queryset = queryset.filter(severity=severity)
    if status:
        queryset = queryset.filter(status=status)

    # Order and limit
    queryset = queryset.order_by('-triggered_at')[:limit]

    # Optimize fields
    queryset = queryset.only(
        'id', 'alert_type', 'severity', 'status',
        'triggered_at', 'acknowledged_at', 'resolved_at',
        'title', 'message',
        'proxy__name', 'task__id', 'task__task_type',
        'repository__name',
        'occurrence_count'
    )

    # Convert to dict
    result = [
        {
            'id': str(alert.id),
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'status': alert.status,
            'title': alert.title,
            'message': alert.message,
            'triggered_at': alert.triggered_at.isoformat() if alert.triggered_at else None,
            'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
            'proxy_name': alert.proxy.name if alert.proxy else None,
            'task_id': str(alert.task.id) if alert.task else None,
            'task_type': alert.task.task_type if alert.task else None,
            'repository_name': alert.repository.name if alert.repository else None,
            'occurrence_count': alert.occurrence_count,
        }
        for alert in queryset
    ]

    # Cache result
    cache.set(cache_key, result, timeout=CACHE_TIMEOUT)

    return result


def get_proxy_statistics(hours: int = 24) -> Dict[str, Any]:
    """
    Get statistics for all proxies.

    Optimized query with aggregations.
    """
    cache_key = f"{CACHE_PREFIX}proxy_stats:{hours}"
    
    # Try cache first
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    from datetime import timedelta
    cutoff = timezone.now() - timedelta(hours=hours)

    # Get statistics
    proxies = ProxyNode.objects.annotate(
        total_tasks=Count('tasks'),
        running_tasks=Count('tasks', filter=Q(tasks__status='running')),
        completed_tasks=Count('tasks', filter=Q(tasks__status='completed')),
        failed_tasks=Count('tasks', filter=Q(tasks__status='failed')),
        active_alerts=Count('alerts', filter=Q(alerts__status='active')),
        completed_alerts=Count('alerts', filter=Q(alerts__status='resolved')),
    ).filter(
        created_at__gte=cutoff
    ).values('id', 'name', 'status', *[
        'total_tasks', 'running_tasks', 'completed_tasks', 
        'failed_tasks', 'active_alerts', 'completed_alerts'
    ])

    # Calculate aggregates
    total = proxies.count()
    online = proxies.filter(status='online').count()
    offline = proxies.filter(status='offline').count()

    result = {
        'total_proxies': total,
        'online_proxies': online,
        'offline_proxies': offline,
        'time_range_hours': hours,
        'proxies': list(proxies),
        'aggregates': {
            'total_tasks': sum(p['total_tasks'] for p in proxies),
            'running_tasks': sum(p['running_tasks'] for p in proxies),
            'completed_tasks': sum(p['completed_tasks'] for p in proxies),
            'failed_tasks': sum(p['failed_tasks'] for p in proxies),
            'active_alerts': sum(p['active_alerts'] for p in proxies),
            'completed_alerts': sum(p['completed_alerts'] for p in proxies),
        }
    }

    # Cache result
    cache.set(cache_key, result, timeout=CACHE_TIMEOUT)

    return result


def get_task_statistics(hours: int = 24) -> Dict[str, Any]:
    """
    Get task statistics.

    Optimized query with aggregations.
    """
    cache_key = f"{CACHE_PREFIX}task_stats:{hours}"
    
    # Try cache first
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    from datetime import timedelta
    cutoff = timezone.now() - timedelta(hours=hours)

    # Get task statistics
    tasks = ProxyTask.objects.filter(
        created_at__gte=cutoff
    )

    result = tasks.aggregate(
        total=Count('id'),
        by_type=Count('task_type'),
        by_status=Count('status'),
        avg_duration=Avg('completed_at') - Avg('started_at'),
        success_rate=Count('id', filter=Q(status='completed')) / Count('id') * 100,
    )

    # Get proxy distribution
    proxy_stats = tasks.values('proxy__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    result['time_range_hours'] = hours
    result['proxies'] = list(proxy_stats)

    # Cache result
    cache.set(cache_key, result, timeout=CACHE_TIMEOUT)

    return result


def invalidate_cache(proxy_id: str = None):
    """
    Invalidate cache for specific proxy or all caches.

    Args:
        proxy_id: Proxy ID to invalidate, or None for all
    """
    if proxy_id:
        keys_to_delete = cache.keys(f"{CACHE_PREFIX}*:{proxy_id}*")
    else:
        keys_to_delete = cache.keys(f"{CACHE_PREFIX}*")

    for key in keys_to_delete:
        cache.delete(key)

    logger.info(
        f"Cache invalidated",
        extra={'proxy_id': proxy_id, 'keys_count': len(keys_to_delete)}
    )


def clear_old_cache(minutes: int = 30):
    """
    Clear cache entries older than specified minutes.

    Args:
        minutes: Minutes threshold
    """
    # Cache automatically expires, but we can manually clear
    pass
