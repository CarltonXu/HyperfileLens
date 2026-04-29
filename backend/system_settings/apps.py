"""
System Settings Application

This module provides system-wide configuration management,
including SMTP settings, system preferences, and other admin-configurable options.
"""

from django.apps import AppConfig


class SystemSettingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'system_settings'
    verbose_name = 'System Settings'
