"""System monitoring for the Gateway agent."""

import os
import platform
import socket
from datetime import datetime

try:
    import psutil
except ImportError:  # pragma: no cover - installer should provide psutil
    psutil = None


class SystemMonitor:
    """System monitoring utilities."""

    def __init__(self):
        self.start_time = datetime.now()

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
    def get_network_interfaces() -> list[dict]:
        if not psutil:
            return []
        counters = psutil.net_io_counters(pernic=True)
        addresses = psutil.net_if_addrs()
        result = []
        for name, addrs in addresses.items():
            ips = []
            mac = ''
            for addr in addrs:
                if getattr(addr, 'family', None) == 2:
                    ips.append(addr.address)
                elif getattr(addr, 'family', None) in (
                    getattr(socket, 'AF_PACKET', object()),
                    getattr(psutil, 'AF_LINK', object()),
                ):
                    mac = addr.address
            io = counters.get(name)
            result.append({
                'name': name,
                'ip_addresses': ips,
                'ip_address': ips[0] if ips else '',
                'mac_address': mac,
                'bytes_in': getattr(io, 'bytes_recv', 0),
                'bytes_out': getattr(io, 'bytes_sent', 0),
                'packets_in': getattr(io, 'packets_recv', 0),
                'packets_out': getattr(io, 'packets_sent', 0),
                'drop_in': getattr(io, 'dropin', 0),
                'drop_out': getattr(io, 'dropout', 0),
                'errs_in': getattr(io, 'errin', 0),
                'errs_out': getattr(io, 'errout', 0),
            })
        return result

    @staticmethod
    def get_disk_io_stats() -> list[dict]:
        if not psutil:
            return []
        result = []
        for name, stat in psutil.disk_io_counters(perdisk=True).items():
            result.append({
                'name': name,
                'read_bytes': getattr(stat, 'read_bytes', 0),
                'write_bytes': getattr(stat, 'write_bytes', 0),
                'read_count': getattr(stat, 'read_count', 0),
                'write_count': getattr(stat, 'write_count', 0),
                'read_time_ms': getattr(stat, 'read_time', 0),
                'write_time_ms': getattr(stat, 'write_time', 0),
                'io_time_ms': getattr(stat, 'busy_time', 0),
            })
        return result
    
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
            net_interfaces = SystemMonitor.get_network_interfaces()
            metrics.update({
                'cpu_cores': os.cpu_count() or 1,
                'cpu_physical': psutil.cpu_count(logical=False) or 0,
                'memory_total': mem.total,
                'memory_used': mem.used,
                'memory_free': mem.available,
                'disk_total': disk.total,
                'disk_used': disk.used,
                'disk_free': disk.free,
                'network_bytes_sent': net.bytes_sent,
                'network_bytes_recv': net.bytes_recv,
                'network_packets_sent': net.packets_sent,
                'network_packets_recv': net.packets_recv,
                'uptime': int(datetime.now().timestamp() - psutil.boot_time()),
                'load_average': list(os.getloadavg()) if hasattr(os, 'getloadavg') else None,
                'process_count': len(psutil.pids()),
                'network_interfaces': {
                    'interfaces': net_interfaces,
                    'total_bytes_in': net.bytes_recv,
                    'total_bytes_out': net.bytes_sent,
                },
                'disk_io': SystemMonitor.get_disk_io_stats(),
            })
        return metrics
