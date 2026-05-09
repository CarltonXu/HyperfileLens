"""
Metrics service for storing and querying proxy metrics.

This module provides functionality for storing heartbeat metrics,
querying historical data, and performing aggregations.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
import logging

from .models_metrics import ProxyMetrics, MetricsAggregation

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for managing proxy metrics."""

    # Cache configuration
    _CACHE_PREFIX = "proxy_metrics:"
    _CACHE_TIMEOUT = 300  # 5 minutes

    @classmethod
    def store_metrics(cls, proxy, metrics: Dict[str, Any]) -> ProxyMetrics:
        """
        Store proxy metrics from heartbeat.

        Args:
            proxy: ProxyNode instance
            metrics: Dictionary of metrics data

        Returns:
            Created ProxyMetrics instance
        """
        # Extract metric values with defaults
        metric_data = {
            'proxy': proxy,
            'cpu_usage': metrics.get('cpu_usage', 0),
            'cpu_cores': metrics.get('cpu_cores', 0),
            'cpu_physical': metrics.get('cpu_physical'),
            'memory_usage': metrics.get('memory_usage', 0),
            'memory_total': metrics.get('memory_total', 0),
            'memory_used': metrics.get('memory_used', 0),
            'memory_free': metrics.get('memory_free', 0),
            'disk_usage': metrics.get('disk_usage', 0),
            'disk_total': metrics.get('disk_total', 0),
            'disk_used': metrics.get('disk_used', 0),
            'disk_free': metrics.get('disk_free', 0),
            'network_bytes_sent': metrics.get('network_bytes_sent', 0),
            'network_bytes_recv': metrics.get('network_bytes_recv', 0),
            'network_packets_sent': metrics.get('network_packets_sent', 0),
            'network_packets_recv': metrics.get('network_packets_recv', 0),
            'uptime': metrics.get('uptime', 0),
            'goroutines': metrics.get('goroutines', 0),
            'load_average': metrics.get('load_average'),
            'extra_metrics': metrics.get('extra_metrics', {}),
        }

        # Create metrics record
        proxy_metrics = ProxyMetrics.objects.create(**metric_data)

        # Invalidate cache
        cache_key = f"{cls._CACHE_PREFIX}latest:{proxy.id}"
        cache.delete(cache_key)

        logger.info(
            f"Stored metrics for proxy {proxy.name}",
            extra={
                'proxy_id': str(proxy.id),
                'cpu_usage': metric_data['cpu_usage'],
                'memory_usage': metric_data['memory_usage'],
            }
        )

        return proxy_metrics

    @classmethod
    def get_latest_metrics(cls, proxy) -> Optional[ProxyMetrics]:
        """
        Get the latest metrics for a proxy.

        Args:
            proxy: ProxyNode instance

        Returns:
            Latest ProxyMetrics instance or None
        """
        # Try cache first
        cache_key = f"{cls._CACHE_PREFIX}latest:{proxy.id}"
        cached = cache.get(cache_key)
        if cached:
            try:
                return ProxyMetrics.objects.get(id=cached)
            except ProxyMetrics.DoesNotExist:
                cache.delete(cache_key)

        # Get from database
        latest = ProxyMetrics.objects.filter(proxy=proxy).first()

        # Cache the result
        if latest:
            cache.set(cache_key, latest.id, cls._CACHE_TIMEOUT)

        return latest

    @classmethod
    def get_metrics_history(
        cls,
        proxy,
        minutes: int = 60,
        limit: int = 100
    ) -> List[ProxyMetrics]:
        """
        Get metrics history for a proxy.

        Args:
            proxy: ProxyNode instance
            minutes: Time range in minutes
            limit: Maximum number of records

        Returns:
            List of ProxyMetrics instances
        """
        cutoff = timezone.now() - timedelta(minutes=minutes)
        return list(ProxyMetrics.objects.filter(
            proxy=proxy,
            timestamp__gte=cutoff
        ).order_by('-timestamp')[:limit])

    @classmethod
    def get_average_metrics(
        cls,
        proxy,
        field: str,
        minutes: int = 60
    ) -> float:
        """
        Get average value of a metric field.

        Args:
            proxy: ProxyNode instance
            field: Metric field name
            minutes: Time range in minutes

        Returns:
            Average value
        """
        cutoff = timezone.now() - timedelta(minutes=minutes)
        queryset = ProxyMetrics.objects.filter(
            proxy=proxy,
            timestamp__gte=cutoff
        )

        values = []
        for metric in queryset:
            if hasattr(metric, field):
                values.append(getattr(metric, field))

        return sum(values) / len(values) if values else 0

    @classmethod
    def get_metric_statistics(
        cls,
        proxy,
        field: str,
        minutes: int = 60
    ) -> Dict[str, float]:
        """
        Get statistical data for a metric field.

        Args:
            proxy: ProxyNode instance
            field: Metric field name
            minutes: Time range in minutes

        Returns:
            Dictionary with min, max, avg, median
        """
        from statistics import mean, median

        cutoff = timezone.now() - timedelta(minutes=minutes)
        queryset = ProxyMetrics.objects.filter(
            proxy=proxy,
            timestamp__gte=cutoff
        )

        values = []
        for metric in queryset:
            if hasattr(metric, field):
                value = getattr(metric, field)
                if isinstance(value, (int, float)):
                    values.append(value)

        if not values:
            return {'min': 0, 'max': 0, 'avg': 0, 'median': 0}

        return {
            'min': min(values),
            'max': max(values),
            'avg': mean(values),
            'median': median(values),
            'count': len(values),
        }

    @classmethod
    def get_trend(
        cls,
        proxy,
        field: str,
        hours: int = 1
    ) -> str:
        """
        Get trend direction for a metric.

        Args:
            proxy: ProxyNode instance
            field: Metric field name
            hours: Time range in hours

        Returns:
            Trend direction: 'increasing', 'decreasing', or 'stable'
        """
        cutoff = timezone.now() - timedelta(hours=hours)
        metrics = list(ProxyMetrics.objects.filter(
            proxy=proxy,
            timestamp__gte=cutoff
        ).order_by('timestamp'))

        if len(metrics) < 2:
            return 'stable'

        values = []
        for metric in metrics:
            if hasattr(metric, field):
                value = getattr(metric, field)
                if isinstance(value, (int, float)):
                    values.append(value)

        if len(values) < 2:
            return 'stable'

        # Split values into recent and old
        split_point = len(values) // 4
        recent_values = values[-split_point:] if split_point > 0 else values[-1:]
        old_values = values[:-split_point] if split_point > 0 else values[:1]

        recent_avg = mean(recent_values)
        old_avg = mean(old_values)

        # Calculate percentage change
        if old_avg > 0:
            change = (recent_avg - old_avg) / old_avg * 100
        else:
            change = 0

        if change > 20:
            return 'increasing'
        elif change < -20:
            return 'decreasing'
        else:
            return 'stable'

    @classmethod
    def get_resource_summary(
        cls,
        proxy,
        minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Get comprehensive resource summary for a proxy.

        Args:
            proxy: ProxyNode instance
            minutes: Time range in minutes

        Returns:
            Dictionary with resource statistics
        """
        return {
            'cpu': cls.get_metric_statistics(proxy, 'cpu_usage', minutes),
            'memory': cls.get_metric_statistics(proxy, 'memory_usage', minutes),
            'disk': cls.get_metric_statistics(proxy, 'disk_usage', minutes),
            'trends': {
                'cpu': cls.get_trend(proxy, 'cpu_usage', hours=1),
                'memory': cls.get_trend(proxy, 'memory_usage', hours=1),
                'disk': cls.get_trend(proxy, 'disk_usage', hours=1),
            },
            'latest': cls.get_latest_metrics(proxy),
            'time_range_minutes': minutes,
        }

    @classmethod
    def cleanup_old_metrics(cls, days: int = 30) -> int:
        """
        Delete metrics older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of deleted records
        """
        return ProxyMetrics.cleanup_old_metrics(days)

    @classmethod
    def aggregate_metrics(cls, period: str = 'hourly', proxy=None) -> int:
        """
        Aggregate raw metrics for analysis.

        Args:
            period: 'hourly' or 'daily'
            proxy: Optional proxy to aggregate

        Returns:
            Number of aggregations created
        """
        return MetricsAggregation.aggregate_metrics(period, proxy)

    @classmethod
    def get_aggregated_metrics(
        cls,
        proxy,
        period: str,
        hours: int = 24
    ) -> List[MetricsAggregation]:
        """
        Get aggregated metrics for a proxy.

        Args:
            proxy: ProxyNode instance
            period: 'hourly' or 'daily'
            hours: Time range in hours

        Returns:
            List of MetricsAggregation instances
        """
        cutoff = timezone.now() - timedelta(hours=hours)
        return list(MetricsAggregation.objects.filter(
            proxy=proxy,
            period=period,
            period_start__gte=cutoff
        ).order_by('-period_start'))

    @classmethod
    def batch_store_metrics(cls, metrics_data: List[Dict[str, Any]]) -> int:
        """
        Batch store multiple metrics records.

        Args:
            metrics_data: List of dictionaries with proxy_id and metrics

        Returns:
            Number of records stored
        """
        from .models import ProxyNode

        records_to_create = []

        for data in metrics_data:
            proxy_id = data.get('proxy_id')
            metrics = data.get('metrics', {})

            if not proxy_id or not metrics:
                continue

            try:
                proxy = ProxyNode.objects.get(id=proxy_id)
            except ProxyNode.DoesNotExist:
                logger.warning(f"Proxy {proxy_id} not found, skipping metrics")
                continue

            metric_data = {
                'proxy': proxy,
                'cpu_usage': metrics.get('cpu_usage', 0),
                'cpu_cores': metrics.get('cpu_cores', 0),
                'cpu_physical': metrics.get('cpu_physical'),
                'memory_usage': metrics.get('memory_usage', 0),
                'memory_total': metrics.get('memory_total', 0),
                'memory_used': metrics.get('memory_used', 0),
                'memory_free': metrics.get('memory_free', 0),
                'disk_usage': metrics.get('disk_usage', 0),
                'disk_total': metrics.get('disk_total', 0),
                'disk_used': metrics.get('disk_used', 0),
                'disk_free': metrics.get('disk_free', 0),
                'network_bytes_sent': metrics.get('network_bytes_sent', 0),
                'network_bytes_recv': metrics.get('network_bytes_recv', 0),
                'network_packets_sent': metrics.get('network_packets_sent', 0),
                'network_packets_recv': metrics.get('network_packets_recv', 0),
                'uptime': metrics.get('uptime', 0),
                'goroutines': metrics.get('goroutines', 0),
                'load_average': metrics.get('load_average'),
                'extra_metrics': metrics.get('extra_metrics', {}),
            }

            records_to_create.append(ProxyMetrics(**metric_data))

        if records_to_create:
            ProxyMetrics.objects.bulk_create(records_to_create)

        return len(records_to_create)


# Global service instance
metrics_service = MetricsService()
