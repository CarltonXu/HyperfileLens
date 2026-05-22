"""System monitoring for the Gateway agent."""

import os
import platform
from datetime import datetime

try:
    import psutil
except ImportError:  # pragma: no cover - installer should provide psutil
    psutil = None


class SystemMonitor:
    """System monitoring utilities."""
    
    @staticmethod
    def get_cpu_usage() -> float:
        """Get CPU usage percentage."""
        if psutil:
            return psutil.cpu_percent(interval=1)
        return 0.0
    
    @staticmethod
    def get_memory_usage() -> float:
        """Get memory usage percentage."""
        if psutil:
            return psutil.virtual_memory().percent
        return 0.0
    
    @staticmethod
    def get_disk_usage(path: str = '/') -> float:
        """Get disk usage percentage."""
        if psutil:
            return psutil.disk_usage(path).percent
        return 0.0
    
    @staticmethod
    def get_system_info() -> dict:
        """Get system information."""
        info = {
            'hostname': platform.node(),
            'os': platform.system(),
            'os_version': platform.version(),
            'python_version': platform.python_version(),
            'cpu_cores': os.cpu_count() or 1,
            'architecture': platform.machine(),
        }
        
        if psutil:
            mem = psutil.virtual_memory()
            info['memory_total_gb'] = round(mem.total / (1024**3), 2)
            info['memory_available_gb'] = round(mem.available / (1024**3), 2)
            
            disk = psutil.disk_usage('/')
            info['disk_total_gb'] = round(disk.total / (1024**3), 2)
            info['disk_free_gb'] = round(disk.free / (1024**3), 2)
        
        return info
    
    @staticmethod
    def get_metrics() -> dict:
        """Get current system metrics."""
        metrics = {
            'cpu_usage': SystemMonitor.get_cpu_usage(),
            'memory_usage': SystemMonitor.get_memory_usage(),
            'disk_usage': SystemMonitor.get_disk_usage(),
            'timestamp': datetime.now().isoformat()
        }
        if psutil:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net = psutil.net_io_counters()
            metrics.update({
                'cpu_cores': os.cpu_count() or 1,
                'memory_total': mem.total,
                'memory_used': mem.used,
                'memory_free': mem.available,
                'disk_total': disk.total,
                'disk_used': disk.used,
                'disk_free': disk.free,
                'network_bytes_sent': net.bytes_sent,
                'network_bytes_recv': net.bytes_recv,
                'load_average': list(os.getloadavg()) if hasattr(os, 'getloadavg') else None,
                'process_count': len(psutil.pids()),
            })
        return metrics
