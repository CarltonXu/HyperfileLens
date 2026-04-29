from django.contrib import admin
from .models import License, LicenseAuditLog


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ['license_key', 'licensee_name', 'edition', 'status', 'expires_at', 'is_valid']
    list_filter = ['edition', 'status', 'created_at']
    search_fields = ['license_key', 'licensee_name', 'licensee_email']
    readonly_fields = ['id', 'issued_at', 'created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('id', 'license_key', 'status')
        }),
        ('Licensee', {
            'fields': ('licensee_name', 'licensee_email', 'licensee_company')
        }),
        ('Product', {
            'fields': ('product', 'edition', 'version')
        }),
        ('Validity', {
            'fields': ('issued_at', 'starts_at', 'expires_at')
        }),
        ('Limits', {
            'fields': ('max_tenants', 'max_users_per_tenant', 'max_proxies_per_tenant',
                      'max_repositories_per_tenant', 'max_storage_gb')
        }),
        ('Features', {
            'fields': ('features', 'modules')
        }),
        ('Security', {
            'fields': ('signature', 'fingerprint')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def is_valid(self, obj):
        return obj.is_valid
    is_valid.boolean = True
    is_valid.short_description = 'Valid'


@admin.register(LicenseAuditLog)
class LicenseAuditLogAdmin(admin.ModelAdmin):
    list_display = ['license', 'event_type', 'message', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['license__license_key', 'message']
    readonly_fields = ['id', 'created_at']
