"""Admin configuration for the global alert center."""

from django.contrib import admin

from .models import AlertPolicy, AlertRecord, NotificationChannel, NotificationLog


@admin.register(AlertPolicy)
class AlertPolicyAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "severity", "resource_type", "enabled", "created_at"]
    list_filter = ["type", "severity", "resource_type", "enabled"]
    search_fields = ["name", "description"]
    readonly_fields = ["id", "created_by", "created_at", "updated_at"]


@admin.register(AlertRecord)
class AlertRecordAdmin(admin.ModelAdmin):
    list_display = ["title", "type", "severity", "status", "resource_name", "first_triggered_at", "resolved_at"]
    list_filter = ["type", "severity", "status", "resource_type"]
    search_fields = ["title", "message", "resource_name", "fingerprint"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "enabled", "created_at"]
    list_filter = ["type", "enabled"]
    search_fields = ["name"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ["alert_record_id", "channel_id", "status", "sent_at"]
    list_filter = ["status"]
    search_fields = ["alert_record_id", "channel_id", "error_message"]
    readonly_fields = ["id", "sent_at"]
