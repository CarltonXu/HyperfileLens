"""
Admin configuration for alerts module.

This module provides Django admin interface for managing
alerts and alert rules.
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import Alert, AlertRule


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    """Admin interface for Alert."""

    list_display = [
        'id',
        'alert_type',
        'severity',
        'status',
        'title',
        'entity_name',
        'triggered_at',
        'occurrence_count',
        'duration',
        'source',
    ]
    list_filter = [
        'alert_type',
        'severity',
        'status',
        'triggered_at',
        'source',
    ]
    search_fields = [
        'title',
        'message',
        'entity_name',
        'entity_id',
    ]
    readonly_fields = [
        'id',
        'triggered_at',
        'acknowledged_at',
        'resolved_at',
        'first_occurrence_at',
        'last_occurrence_at',
        'duration_display',
    ]
    date_hierarchy = 'triggered_at'
    actions = ['acknowledge_alerts', 'resolve_alerts']

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'alert_type', 'severity', 'status', 'title')
        }),
        ('Related Entity', {
            'fields': ('entity_type', 'entity_id', 'entity_name', 'source')
        }),
        ('Specific Relations', {
            'fields': ('proxy', 'task', 'backup_task', 'repository')
        }),
        ('Content', {
            'fields': ('message', 'details', 'metric_value', 'threshold_value')
        }),
        ('Timestamps', {
            'fields': ('triggered_at', 'acknowledged_at', 'resolved_at',
                      'duration_display')
        }),
        ('Repetition', {
            'fields': ('occurrence_count', 'first_occurrence_at', 'last_occurrence_at')
        }),
        ('Acknowledgment', {
            'fields': ('acknowledged_by', 'acknowledgment_note')
        }),
        ('Resolution', {
            'fields': ('resolved_by', 'resolution_note')
        }),
        ('Notification', {
            'fields': ('notification_sent', 'notification_channels')
        }),
        ('Silencing', {
            'fields': ('silenced_until', 'silenced_by')
        }),
        ('Metadata', {
            'fields': ('metadata',)
        }),
    )

    def duration(self, obj):
        """Display alert duration."""
        return obj.get_duration()
    duration.short_description = 'Duration (s)'

    def duration_display(self, obj):
        """Display alert duration in human readable format."""
        duration = obj.get_duration()
        if duration:
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            return f"{hours}h {minutes}m {seconds}s"
        return '-'
    duration_display.short_description = 'Duration'

    def acknowledge_alerts(self, request, queryset):
        """Acknowledge selected alerts."""
        count = queryset.update(
            status=Alert.AlertStatus.ACKNOWLEDGED,
            acknowledged_at=timezone.now(),
            acknowledged_by=request.user
        )
        self.message_user(request, f'{count} alerts acknowledged.')
    acknowledge_alerts.short_description = 'Acknowledge selected alerts'

    def resolve_alerts(self, request, queryset):
        """Resolve selected alerts."""
        count = queryset.update(
            status=Alert.AlertStatus.RESOLVED,
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f'{count} alerts resolved.')
    resolve_alerts.short_description = 'Resolve selected alerts'


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    """Admin interface for AlertRule."""

    list_display = [
        'name',
        'alert_type',
        'severity',
        'enabled',
        'applies_to_all_entities',
        'entity_type',
        'evaluation_interval',
        'cooldown_period',
        'last_triggered_at',
        'source',
    ]
    list_filter = [
        'alert_type',
        'severity',
        'enabled',
        'applies_to_all_entities',
        'entity_type',
        'source',
    ]
    search_fields = [
        'name',
        'description',
        'alert_type',
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'alert_type', 'severity', 'enabled', 'source')
        }),
        ('Condition', {
            'fields': ('condition', 'threshold_value', 'threshold_operator')
        }),
        ('Target Scope', {
            'fields': ('applies_to_all_entities', 'entity_type', 'target_ids')
        }),
        ('Timing', {
            'fields': ('evaluation_interval', 'cooldown_period')
        }),
        ('Notification', {
            'fields': ('notification_enabled', 'notification_channels')
        }),
        ('Status', {
            'fields': ('last_triggered_at', 'created_at', 'updated_at')
        }),
    )

    readonly_fields = ['last_triggered_at', 'created_at', 'updated_at']