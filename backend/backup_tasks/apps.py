"""
HyperFileLens Backend - Backup Tasks Module

This module handles all backup task operations including:
- Creating backup tasks
- Managing task schedules
- Executing backup operations
- Tracking task status and progress
"""

from django.apps import AppConfig


class BackupTasksConfig(AppConfig):
    """
    Configuration for the backup_tasks application.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backup_tasks'
    verbose_name = 'Backup Tasks'

    def ready(self):
        """
        Import signals and register periodic tasks when the app is ready.
        """
        # Import signals if any
        pass
