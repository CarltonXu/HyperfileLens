"""
License Admin Configuration
"""

from django.contrib import admin
from .models import License, MachineCode, QuotaUsage, LicenseAuditLog


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    """Admin interface for License management."""
    
    list_display = [
        'license_key', 'tenant', 'status', 
        'max_users', 'max_proxies', 'expires_at', 'is_valid'
    ]
    list_filter = ['status']
    search_fields = ['license_key', 'tenant__name', 'machine_code']
    readonly_fields = [
        'id', 'license_key', 'machine_code', 'tenant', 'activated_by',
        'issued_at', 'activated_at', 'signature'
    ]
    
    fieldsets = (
        ('License Information', {
            'fields': (
                'id', 'license_key', 'machine_code', 'status'
            )
        }),
        ('Binding', {
            'fields': ('tenant', 'activated_by', 'activated_at')
        }),
        ('Validity', {
            'fields': ('issued_at', 'expires_at')
        }),
        ('Quantity Limits', {
            'fields': (
                'max_tenants', 'max_users', 'max_proxies', 
                'max_storage_gb', 'max_gateways',
                'ai_insights_quota', 'max_backup_tasks',
                'max_recovery_tasks', 'max_source_resources',
                'max_policies', 'max_repositories'
            )
        }),
        ('Security', {
            'fields': ('signature',),
            'classes': ('collapse',)
        }),
    )
    
    def is_valid(self, obj):
        return obj.is_valid
    is_valid.boolean = True
    is_valid.short_description = 'Valid'


@admin.register(MachineCode)
class MachineCodeAdmin(admin.ModelAdmin):
    """Admin interface for Machine Code management."""
    
    list_display = ['code', 'tenant', 'user', 'created_at', 'used_at']
    list_filter = ['created_at']
    search_fields = ['code', 'tenant__name', 'user__username', 'mac_address']
    readonly_fields = ['id', 'code', 'tenant', 'user', 'mac_address', 'cpu_id', 'hostname', 'created_at', 'used_at']
    
    def has_add_permission(self, request):
        return False


@admin.register(LicenseAuditLog)
class LicenseAuditLogAdmin(admin.ModelAdmin):
    """Admin interface for License audit logs."""
    
    list_display = ['id', 'license', 'action', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['license__license_key']
    readonly_fields = ['id', 'license', 'action', 'details', 'ip_address', 'user_agent', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(QuotaUsage)
class QuotaUsageAdmin(admin.ModelAdmin):
    """Admin interface for quota usage tracking."""
    
    list_display = ['license', 'users_count', 'proxies_count', 'storage_used_gb', 'updated_at']
    readonly_fields = ['license', 'users_count', 'proxies_count', 'storage_used_gb', 
                       'gateways_count', 'backup_tasks_count', 'recovery_tasks_count',
                       'source_resources_count', 'policies_count', 'repositories_count',
                       'ai_insights_used', 'ai_insights_period', 'ai_insights_reset_at',
                       'updated_at']
    
    def has_add_permission(self, request):
        return False
