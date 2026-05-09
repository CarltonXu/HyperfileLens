"""
Proxy metrics models for storing heartbeat data.

This module contains models for storing detailed proxy metrics
for historical analysis and trend monitoring.
"""

from django.db import models
from django.utils import timezone
import uuid


class ProxyMetrics(models.Model):
    """
    Detailed proxy metrics for historical analysis.

    Stores comprehensive metrics from proxy heartbeats for
    trend analysis, performance monitoring, and capacity planning.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Reference to proxy node
    proxy = models.ForeignKey(
        'ProxyNode',
        on_delete=models.CASCADE,
        related_name='metrics',
        db_index=True
    )

    # Timestamp
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text='When these metrics were recorded'
    )

    # CPU metrics
    cpu_usage = models.FloatField(
        help_text='CPU usage percentage (0-100)'
    )
    cpu_cores = models.IntegerField(
        help_text='Number of CPU cores (logical)'
    )
    cpu_physical = models.IntegerField(
        null=True,
        blank=True,
        help_text='Number of physical CPU cores'
    )

    # Memory metrics
    memory_usage = models.FloatField(
        help_text='Memory usage percentage (0-100)'
    )
    memory_total = models.BigIntegerField(
        help_text='Total memory in bytes'
    )
    memory_used = models.BigIntegerField(
        help_text='Used memory in bytes'
    )
    memory_free = models.BigIntegerField(
        help_text='Free memory in bytes'
    )

    # Disk metrics (root partition)
    disk_usage = models.FloatField(
        help_text='Disk usage percentage (0-100)'
    )
    disk_total = models.BigIntegerField(
        help_text='Total disk space in bytes'
    )
    disk_used = models.BigIntegerField(
        help_text='Used disk space in bytes'
    )
    disk_free = models.BigIntegerField(
        help_text='Free disk space in bytes'
    )

    # Network metrics
    network_bytes_sent = models.BigIntegerField(
        default=0,
        help_text='Total bytes sent'
    )
    network_bytes_recv = models.BigIntegerField(
        default=0,
        help_text='Total bytes received'
    )
    network_packets_sent = models.IntegerField(
        default=0,
        help_text='Total packets sent'
    )
    network_packets_recv = models.IntegerField(
        default=0,
        help_text='Total packets received'
    )

    # System metrics
    uptime = models.BigIntegerField(
        help_text='System uptime in seconds'
    )
    goroutines = models.IntegerField(
        default=0,
        help_text='Number of goroutines (for Go proxies)'
    )
    load_average = models.FloatField(
        null=True,
        blank=True,
        help_text='System load average (1-minute)'
    )

    # Additional metrics (JSON format for flexibility)
    extra_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional custom metrics'
    )

    class Meta:
        db_table = 'nodes_proxy_metrics'
        verbose_name = 'Proxy Metrics'
        verbose_name_plural = 'Proxy Metrics'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['proxy', '-timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['proxy', 'timestamp'], name='nodes_proxy_m_proxy_time_idx'),
        ]

    def __str__(self):
        return f'{self.proxy.name} metrics at {self.timestamp}'

    def get_cpu_trend(self, hours: int = 1):
        """Get CPU usage trend for the last N hours."""
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=hours)
        recent_metrics = ProxyMetrics.objects.filter(
            proxy=self.proxy,
            timestamp__gte=cutoff
        ).order_by('timestamp')
        
        values = [m.cpu_usage for m in recent_metrics]
        if len(values) < 2:
            return 'stable'
        
        recent_avg = sum(values[-len(values)//4:]) / max(1, len(values)//4)
        old_avg = sum(values[:-len(values)//4]) / max(1, len(values)//4)
        
        change = (recent_avg - old_avg) / max(old_avg, 1) * 100
        
        if change > 20:
            return 'increasing'
        elif change < -20:
            return 'decreasing'
        else:
            return 'stable'

    @classmethod
    def get_latest(cls, proxy):
        """Get the latest metrics for a proxy."""
        return cls.objects.filter(proxy=proxy).order_by('-timestamp').first()

    @classmethod
    def get_average(cls, proxy, field, minutes: int = 60):
        """Get average value of a field over the last N minutes."""
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(minutes=minutes)
        queryset = cls.objects.filter(
            proxy=proxy,
            timestamp__gte=cutoff
        )
        
        values = [getattr(m, field, 0) for m in queryset if hasattr(m, field)]
        return sum(values) / len(values) if values else 0

    @classmethod
    def cleanup_old_metrics(cls, days: int = 30):
        """Delete metrics older than N days."""
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=days)
        return cls.objects.filter(timestamp__lt=cutoff).delete()


class MetricsAggregation(models.Model):
    """
    Aggregated metrics for improved query performance.

    Stores aggregated metrics (hourly/daily) for quick retrieval
    without needing to scan raw metrics data.
    """

    AGGREGATION_PERIODS = (
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    proxy = models.ForeignKey(
        'ProxyNode',
        on_delete=models.CASCADE,
        related_name='aggregated_metrics',
        db_index=True
    )

    period = models.CharField(
        max_length=20,
        choices=AGGREGATION_PERIODS,
        db_index=True
    )

    period_start = models.DateTimeField(
        db_index=True,
        help_text='Start of aggregation period'
    )

    period_end = models.DateTimeField(
        help_text='End of aggregation period'
    )

    # Aggregated CPU metrics
    cpu_usage_avg = models.FloatField()
    cpu_usage_min = models.FloatField()
    cpu_usage_max = models.FloatField()
    cpu_usage_p50 = models.FloatField(null=True, blank=True)
    cpu_usage_p95 = models.FloatField(null=True, blank=True)

    # Aggregated memory metrics
    memory_usage_avg = models.FloatField()
    memory_usage_min = models.FloatField()
    memory_usage_max = models.FloatField()

    # Aggregated disk metrics
    disk_usage_avg = models.FloatField()
    disk_usage_min = models.FloatField()
    disk_usage_max = models.FloatField()

    # Count of raw metrics in this aggregation
    sample_count = models.IntegerField()

    # Additional aggregated data
    extra_aggregations = models.JSONField(
        default=dict,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nodes_metrics_aggregation'
        verbose_name = 'Metrics Aggregation'
        verbose_name_plural = 'Metrics Aggregations'
        ordering = ['-period_start']
        unique_together = ['proxy', 'period', 'period_start']
        indexes = [
            models.Index(fields=['proxy', 'period', '-period_start']),
            models.Index(fields=['period_start']),
        ]

    def __str__(self):
        return f'{self.proxy.name} {self.period} {self.period_start}'

    @classmethod
    def aggregate_metrics(cls, period: str, proxy=None):
        """
        Aggregate raw metrics for the specified period.

        Args:
            period: 'hourly' or 'daily'
            proxy: Optional proxy to aggregate, if None aggregates all proxies
        """
        from datetime import datetime, timedelta
        import statistics

        # Determine aggregation window
        if period == 'hourly':
            window = timedelta(hours=1)
        else:  # daily
            window = timedelta(days=1)

        # Get raw metrics
        queryset = ProxyMetrics.objects.all()
        if proxy:
            queryset = queryset.filter(proxy=proxy)

        # Group by time window and proxy
        grouped = {}
        for metric in queryset:
            # Calculate period start
            period_start = metric.timestamp.replace(
                minute=0, second=0, microsecond=0
            )
            if period == 'daily':
                period_start = period_start.replace(hour=0)

            key = (metric.proxy.id, period_start)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(metric)

        # Create aggregations
        aggregations = []
        for (proxy_id, period_start), metrics in grouped.items():
            # Calculate aggregates
            cpu_values = [m.cpu_usage for m in metrics]
            memory_values = [m.memory_usage for m in metrics]
            disk_values = [m.disk_usage for m in metrics]

            agg = cls(
                proxy_id=proxy_id,
                period=period,
                period_start=period_start,
                period_end=period_start + window,
                
                cpu_usage_avg=statistics.mean(cpu_values),
                cpu_usage_min=min(cpu_values),
                cpu_usage_max=max(cpu_values),
                
                memory_usage_avg=statistics.mean(memory_values),
                memory_usage_min=min(memory_values),
                memory_usage_max=max(memory_values),
                
                disk_usage_avg=statistics.mean(disk_values),
                disk_usage_min=min(disk_values),
                disk_usage_max=max(disk_values),
                
                sample_count=len(metrics)
            )

            # Calculate percentiles if enough samples
            if len(cpu_values) >= 10:
                cpu_values.sort()
                agg.cpu_usage_p50 = statistics.median(cpu_values)
                p95_index = int(len(cpu_values) * 0.95)
                agg.cpu_usage_p95 = cpu_values[p95_index]

            aggregations.append(agg)

        # Bulk create
        cls.objects.bulk_create(aggregations, ignore_conflicts=True)
        
        return len(aggregations)
