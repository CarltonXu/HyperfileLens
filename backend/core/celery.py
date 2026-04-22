"""
Celery Configuration for HyperFileLens

This module configures Celery to work with Django and enables
automatic task discovery from all installed apps.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Create the Celery application
app = Celery('hyperfilelens')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
# This discovers tasks.py files in every app listed in INSTALLED_APPS.
app.autodiscover_tasks()

# Configure periodic tasks (Celery Beat)
# These tasks will be registered with django_celery_beat
# via the register_periodic_tasks management command.
app.conf.beat_schedule = {
    'check-node-health': {
        'task': 'nodes.tasks.check_all_nodes_health',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'cleanup-old-backups': {
        'task': 'backup_tasks.tasks.cleanup_old_backups',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    'sync-repository-stats': {
        'task': 'repository.tasks.sync_repository_stats',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
    'generate-usage-reports': {
        'task': 'audit_log.tasks.generate_daily_report',
        'schedule': crontab(hour=0, minute=30),  # Daily at 00:30
    },
}

# Task routing
app.conf.task_routes = {
    'nodes.tasks.*': {'queue': 'nodes'},
    'backup_tasks.tasks.*': {'queue': 'backup'},
    'recovery_tasks.tasks.*': {'queue': 'recovery'},
    'ai_query.tasks.*': {'queue': 'ai'},
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Debug task for testing Celery configuration.

    This task can be triggered manually to verify that
    Celery is properly configured and can execute tasks.
    """
    print(f'Request: {self.request!r}')
