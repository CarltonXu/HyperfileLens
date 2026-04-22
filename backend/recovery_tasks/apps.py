"""
HyperFileLens Backend - Recovery Tasks Module
"""

from django.apps import AppConfig


class RecoveryTasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recovery_tasks'
    verbose_name = 'Recovery Tasks'
