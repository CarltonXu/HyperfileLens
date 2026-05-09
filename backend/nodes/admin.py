"""
Admin configuration for nodes module.

This module provides Django admin interface for managing
proxy nodes, tasks, and connections.
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.db.models import Count, Q
from .models import (
    ProxyNode,
    ProxyHeartbeat,
    ProxyTask,
    NodeConnection,
)


@admin.register(ProxyNode)
class ProxyNodeAdmin(admin.ModelAdmin):
    """Admin interface for ProxyNode."""

    list_display = [
        'name',
        'role',
        'status',
        'hostname',
        'cpu_usage',
        'memory_usage',
        'disk_usage',
        'last_heartbeat',
        'active_tasks_count',
        'health_score',
    ]
    list_filter = ['role', 'status', 'operating_system', 'health_status']
    search_fields = ['name', 'hostname', 'internal_ip']
    readonly_fields = [
        'id',
        'api_token',
        'created_at',
        'registered_at',
        'installed_at',
        'last_heartbeat',
        'uptime_display',
        'total_tasks_completed',
        'total_tasks_failed',
        'total_data_backed_up',
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'role', 'hostname', 'internal_ip', 'api_token')
        }),
        ('System Information', {
            'fields': ('operating_system', 'os_version', 'version', 'kopia_version')
        }),
        ('Hardware', {
            'fields': ('cpu_cores', 'memory_total', 'disk_total')
        }),
        ('Status & Health', {
            'fields': ('status', 'health_score', 'health_status', 'last_heartbeat',
                      'cpu_usage', 'memory_usage', 'disk_usage', 'active_tasks')
        }),
        ('Performance', {
            'fields': ('max_concurrent_tasks', 'bandwidth_limit_kbps')
        }),
        ('Statistics', {
            'fields': ('uptime_display', 'total_tasks_completed', 'total_tasks_failed',
                      'total_data_backed_up')
        }),
        ('Installation', {
            'fields': ('install_token', 'install_token_used', 'target_os',
                      'install_command', 'installed_at', 'installed_by')
        }),
        ('Capabilities & Tags', {
            'fields': ('capabilities', 'mount_types', 'tags', 'labels', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at', 'registered_at')
        }),
        ('Ownership', {
            'fields': ('owner', 'tenant')
        }),
    )

    def active_tasks_count(self, obj):
        """Count active tasks for this proxy."""
        return obj.tasks.filter(status__in=['pending', 'dispatched', 'accepted', 'running']).count()
    active_tasks_count.short_description = 'Active Tasks'

    def uptime_display(self, obj):
        """Display uptime in human readable format."""
        if obj.uptime_seconds:
            hours = obj.uptime_seconds // 3600
            minutes = (obj.uptime_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        return '-'
    uptime_display.short_description = 'Uptime'

    def get_queryset(self, request):
        """Optimize queryset."""
        qs = super().get_queryset(request)
        return qs.annotate(
            active_tasks_count=Count('tasks', filter=models.Q(
                tasks__status__in=['pending', 'dispatched', 'accepted', 'running']
            ))
        )


@admin.register(ProxyHeartbeat)
class ProxyHeartbeatAdmin(admin.ModelAdmin):
    """Admin interface for ProxyHeartbeat."""

    list_display = ['proxy', 'timestamp', 'cpu_usage', 'memory_usage', 'disk_usage',
                   'active_tasks', 'completed_tasks', 'failed_tasks']
    list_filter = ['proxy', 'timestamp']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']
    raw_id_fields = ['proxy']


@admin.register(ProxyTask)
class ProxyTaskAdmin(admin.ModelAdmin):
    """Admin interface for ProxyTask."""

    list_display = ['id', 'proxy', 'task_type', 'status', 'progress',
                   'started_at', 'completed_at']
    list_filter = ['task_type', 'status', 'proxy']
    search_fields = ['id', 'proxy__name']
    readonly_fields = [
        'id',
        'created_at',
        'dispatched_at',
        'started_at',
        'completed_at',
        'progress_details',
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'proxy', 'task_type', 'status')
        }),
        ('Task Parameters', {
            'fields': ('parameters',)
        }),
        ('Timing', {
            'fields': ('created_at', 'dispatched_at', 'started_at', 'completed_at',
                      'timeout_seconds')
        }),
        ('Progress', {
            'fields': ('progress', 'progress_message', 'progress_details')
        }),
        ('Result', {
            'fields': ('result', 'error_message')
        }),
        ('Related Objects', {
            'fields': ('repository_id', 'source_resource_id')
        }),
    )

    def progress_details(self, obj):
        """Display detailed progress information."""
        if obj.current_file or obj.total_files > 0:
            return format_html(
                '<div>File: {}<br>'
                'Files: {} / {}<br>'
                'Bytes: {} / {}<br>'
                'Speed: {:.2f} MB/s<br>'
                'ETA: {}</div>',
                obj.current_file or '-',
                obj.processed_files,
                obj.total_files,
                self._format_bytes(obj.processed_bytes),
                self._format_bytes(obj.total_bytes),
                obj.speed_mbps,
                obj.eta or '-'
            )
        return '-'
    progress_details.short_description = 'Progress Details'

    def _format_bytes(self, bytes_val):
        """Format bytes to human readable."""
        if not bytes_val:
            return '0 B'
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024:
                return f'{bytes_val:.1f} {unit}'
            bytes_val /= 1024
        return f'{bytes_val:.1f} PB'


@admin.register(NodeConnection)
class NodeConnectionAdmin(admin.ModelAdmin):
    """Admin interface for NodeConnection."""

    list_display = ['proxy', 'connection_id', 'status', 'remote_address',
                   'connected_at', 'disconnected_at', 'message_count']
    list_filter = ['status', 'proxy']
    search_fields = ['connection_id', 'remote_address', 'proxy__name']
    readonly_fields = ['connection_id', 'connected_at', 'disconnected_at',
                      'last_message_at', 'message_count']