"""
License Admin Configuration
"""

from django.contrib import admin
from .models import License, LicenseAuditLog, QuotaUsage


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    """Admin interface for License management."""
    
    list_display = [
        'license_key', 'licensee_name', 'edition', 
        'status', 'expires_at', 'is_valid'
    ]
    list_filter = ['status', 'edition']
    search_fields = ['license_key', 'licensee_name', 'licensee_email']
    readonly_fields = [
        'id', 'license_key', 'checksum', 'signature',
        'issued_at', 'verify_integrity', 'days_until_expiry'
    ]
    
    fieldsets = (
        ('License Information', {
            'fields': (
                'id', 'license_key', 'licensee_name', 
                'licensee_email', 'licensee_company'
            )
        }),
        ('Product', {
            'fields': ('product', 'edition', 'version')
        }),
        ('Validity', {
            'fields': ('issued_at', 'starts_at', 'expires_at', 'status')
        }),
        ('Resource Limits', {
            'fields': (
                'max_tenants', 'max_users_per_tenant', 
                'max_proxies_per_tenant', 'max_repositories_per_tenant',
                'max_storage_gb'
            )
        }),
        ('Security', {
            'fields': ('signature', 'checksum', 'machine_fingerprint', 'tamper_detected'),
            'classes': ('collapse',)
        }),
        ('Features', {
            'fields': ('features',),
            'classes': ('collapse',)
        }),
    )
    
    def is_valid(self, obj):
        return obj.is_valid
    is_valid.boolean = True
    is_valid.short_description = 'Valid'


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
    
    list_display = ['license', 'tenants_count', 'total_users', 'total_proxies', 'last_synced']
    readonly_fields = ['license', 'tenants_count', 'total_users', 'total_proxies', 
                       'total_repositories', 'storage_used_gb', 'last_synced']
    
    def has_add_permission(self, request):
        return False
