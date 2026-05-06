"""
Gateway Admin Configuration
"""

from django.contrib import admin
from .models import Gateway


@admin.register(Gateway)
class GatewayAdmin(admin.ModelAdmin):
    """Admin interface for Gateway model."""
    
    list_display = ['name', 'status', 'hostname', 'internal_ip', 'is_online', 'active_mounts', 'created_at']
    list_filter = ['status', 'ai_enabled']
    search_fields = ['name', 'hostname', 'internal_ip']
    readonly_fields = ['id', 'api_token', 'install_token', 'created_at', 'updated_at', 'registered_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'status')
        }),
        ('Connection', {
            'fields': ('hostname', 'internal_ip', 'ssh_port')
        }),
        ('System Information', {
            'fields': ('os_version', 'version', 'kopia_version', 'cpu_cores', 'memory_total', 'disk_total')
        }),
        ('Metrics', {
            'fields': ('cpu_usage', 'memory_usage', 'disk_usage', 'active_mounts')
        }),
        ('Mount Configuration', {
            'fields': ('mount_base_path', 'max_concurrent_mounts')
        }),
        ('AI Insights', {
            'fields': ('ai_enabled', 'indexer_status', 'last_index_time')
        }),
        ('Authentication', {
            'fields': ('api_token', 'install_token', 'install_token_used')
        }),
        ('Ownership', {
            'fields': ('owner', 'tenant')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'registered_at', 'installed_at', 'last_heartbeat')
        }),
    )
