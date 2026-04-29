"""
License Admin for HyperFileLens
"""

from django.contrib import admin
from .models import License, LicenseHistory, MachineCode, QuotaUsage


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    """Admin for License model."""
    
    list_display = [
        'license_key_short', 'tenant_name', 'version', 'change_type',
        'status', 'is_valid', 'expires_at', 'activated_at'
    ]
    list_filter = ['status', 'change_type']
    search_fields = ['license_key', 'machine_code', 'tenant__name']
    readonly_fields = [
        'id', 'license_key', 'version', 'change_type', 'change_reason',
        'machine_code', 'signature', 'issued_at', 'activated_at', 'updated_at'
    ]
    
    fieldsets = (
        ('License Info', {
            'fields': ('id', 'license_key', 'version', 'change_type', 'change_reason')
        }),
        ('Binding', {
            'fields': ('machine_code', 'tenant', 'activated_by')
        }),
        ('Limits', {
            'fields': (
                'max_tenants', 'max_users', 'max_proxies', 'max_storage_gb',
                'max_gateways', 'ai_insights_quota',
                'max_backup_tasks', 'max_recovery_tasks', 'max_source_resources',
                'max_policies', 'max_repositories'
            )
        }),
        ('Time', {
            'fields': ('issued_at', 'expires_at', 'activated_at', 'updated_at')
        }),
        ('Status', {
            'fields': ('status', 'signature')
        }),
    )
    
    def license_key_short(self, obj):
        return f"{obj.license_key[:20]}..."
    license_key_short.short_description = 'License Key'
    
    def tenant_name(self, obj):
        return obj.tenant.name if obj.tenant else '-'
    tenant_name.short_description = 'Tenant'
    
    def is_valid(self, obj):
        return obj.is_valid
    is_valid.boolean = True
    is_valid.short_description = 'Valid'


@admin.register(LicenseHistory)
class LicenseHistoryAdmin(admin.ModelAdmin):
    """Admin for License history (audit)."""
    
    list_display = [
        'license_key_short', 'tenant_name', 'version', 'change_type',
        'archived_at', 'expires_at'
    ]
    list_filter = ['change_type', 'status']
    search_fields = ['license_key', 'machine_code', 'tenant__name']
    readonly_fields = [
        'id', 'license_key', 'version', 'machine_code',
        'tenant', 'activated_by',
        'max_tenants', 'max_users', 'max_proxies', 'max_storage_gb',
        'max_gateways', 'ai_insights_quota',
        'max_backup_tasks', 'max_recovery_tasks', 'max_source_resources',
        'max_policies', 'max_repositories',
        'issued_at', 'expires_at', 'activated_at', 'archived_at',
        'status', 'signature', 'change_type', 'change_reason'
    ]
    
    def license_key_short(self, obj):
        return f"{obj.license_key[:20]}..."
    license_key_short.short_description = 'License Key'
    
    def tenant_name(self, obj):
        return obj.tenant.name if obj.tenant else '(deleted)'
    tenant_name.short_description = 'Tenant'


@admin.register(MachineCode)
class MachineCodeAdmin(admin.ModelAdmin):
    """Admin for MachineCode model."""
    
    list_display = ['code_short', 'tenant_name', 'user_name', 'hostname', 'created_at']
    search_fields = ['code', 'tenant__name', 'user__username', 'hostname']
    readonly_fields = ['id', 'code', 'tenant', 'user', 'mac_address', 'cpu_id', 'hostname', 'created_at']
    
    def code_short(self, obj):
        return obj.code
    code_short.short_description = 'Machine Code'
    
    def tenant_name(self, obj):
        return obj.tenant.name if obj.tenant else '-'
    tenant_name.short_description = 'Tenant'
    
    def user_name(self, obj):
        return obj.user.username if obj.user else '-'
    user_name.short_description = 'User'


@admin.register(QuotaUsage)
class QuotaUsageAdmin(admin.ModelAdmin):
    """Admin for QuotaUsage model."""
    
    list_display = [
        'license_key_short', 'users_count', 'proxies_count',
        'storage_used_gb', 'ai_insights_used', 'last_updated'
    ]
    readonly_fields = [
        'license', 'users_count', 'proxies_count', 'gateways_count',
        'backup_tasks_count', 'recovery_tasks_count',
        'source_resources_count', 'policies_count', 'repositories_count',
        'storage_used_gb', 'ai_insights_used', 'ai_reset_date', 'last_updated'
    ]
    
    def license_key_short(self, obj):
        return f"{obj.license.license_key[:20]}..."
    license_key_short.short_description = 'License'
