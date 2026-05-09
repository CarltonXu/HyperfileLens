# This is the updated update_proxy_heartbeat method

def update_proxy_heartbeat(self, metrics):
    """Update proxy heartbeat and store detailed metrics."""
    from .models import ProxyNode, ProxyHeartbeat
    
    try:
        proxy = ProxyNode.objects.get(id=self.proxy_id)
        proxy.last_heartbeat = timezone.now()

        if metrics:
            proxy.cpu_usage = metrics.get('cpu_usage')
            proxy.memory_usage = metrics.get('memory_usage')
            proxy.disk_usage = metrics.get('disk_usage')
            proxy.active_tasks = metrics.get('active_tasks', 0)

        proxy.save()

        # Create heartbeat record (for backward compatibility)
        ProxyHeartbeat.objects.create(
            proxy=proxy,
            cpu_usage=metrics.get('cpu_usage'),
            memory_usage=metrics.get('memory_usage'),
            disk_usage=metrics.get('disk_usage'),
            network_in=metrics.get('network_in'),
            network_out=metrics.get('network_out'),
            active_tasks=metrics.get('active_tasks', 0),
            completed_tasks=metrics.get('completed_tasks', 0),
            failed_tasks=metrics.get('failed_tasks', 0),
            metadata=metrics.get('metadata', {})
        )

        # Store detailed metrics for historical analysis
        # Map heartbeat metrics to ProxyMetrics format
        detailed_metrics = {
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
            'network_bytes_sent': metrics.get('network_out', 0) if metrics.get('network_out') else 0,
            'network_bytes_recv': metrics.get('network_in', 0) if metrics.get('network_in') else 0,
            'uptime': metrics.get('uptime', 0),
            'goroutines': metrics.get('goroutines', 0),
            'load_average': metrics.get('load_average'),
            'extra_metrics': metrics.get('metadata', {}),
        }

        # Only store if we have meaningful metrics
        if any(detailed_metrics.get(k) for k in ['cpu_usage', 'memory_usage', 'disk_usage']):
            try:
                metrics_service.store_metrics(proxy, detailed_metrics)
            except Exception as e:
                # Don't fail heartbeat if metrics storage fails
                logger.error(f"Failed to store metrics: {e}")

    except ProxyNode.DoesNotExist:
        pass
