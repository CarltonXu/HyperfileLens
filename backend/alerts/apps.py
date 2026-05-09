"""
Django app configuration for alerts module.
"""

from django.apps import AppConfig


class AlertsConfig(AppConfig):
    """Configuration for the alerts application."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'alerts'
    verbose_name = 'Alerts'
    verbose_name_plural = 'Alerts'