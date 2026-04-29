from django.contrib import admin
from .models import Tenant, TenantInvitation


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'plan', 'status', 'max_proxies', 'max_users', 'created_at']
    list_filter = ['plan', 'status', 'created_at']
    search_fields = ['name', 'slug', 'contact_email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'slug', 'plan', 'status')
        }),
        ('Quotas', {
            'fields': ('max_proxies', 'max_repositories', 'max_storage_gb', 'max_users', 'max_backup_tasks')
        }),
        ('Contact', {
            'fields': ('contact_email', 'contact_phone', 'logo_url')
        }),
        ('Settings', {
            'fields': ('settings',)
        }),
        ('Subscription', {
            'fields': ('trial_ends_at', 'subscription_ends_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(TenantInvitation)
class TenantInvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'tenant', 'role', 'status', 'created_at', 'expires_at']
    list_filter = ['status', 'role', 'created_at']
    search_fields = ['email', 'tenant__name']
    readonly_fields = ['id', 'token', 'created_at', 'accepted_at']
