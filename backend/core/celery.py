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

# Celery autodiscovery only imports each app's tasks.py. Backup scheduling lives
# in periodic_tasks.py so it must be imported explicitly for workers to register
# the task name emitted by django-celery-beat.
app.conf.imports = tuple(app.conf.imports or ()) + (
    'backup_tasks.periodic_tasks',
)

# Configure periodic tasks (Celery Beat)
# These tasks will be registered with django_celery_beat
# via the register_periodic_tasks management command.
app.conf.beat_schedule = {
    'collect-system-metrics': {
        'task': 'alerts.tasks.collect_system_metrics',
        'schedule': 60.0,  # Every 60 seconds
    },
    'cleanup-old-metrics': {
        'task': 'alerts.tasks.cleanup_old_metrics',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'evaluate-alert-policies': {
        'task': 'alerts.tasks.evaluate_alert_policies',
        'schedule': 60.0,  # Every 60 seconds
    },
    'schedule-backup-tasks': {
        'task': 'backup_tasks.periodic_tasks.schedule_backup_tasks',
        'schedule': 60.0,  # Every 60 seconds
    },
    'reconcile-backup-snapshots': {
        'task': 'backup_tasks.tasks.reconcile_backup_snapshots',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'evaluate-backup-retention': {
        'task': 'backup_tasks.tasks.evaluate_backup_retention',
        'schedule': crontab(hour=4, minute=0),  # Daily at 4 AM
    },
    'check-node-health': {
        'task': 'nodes.tasks.check_all_nodes_health',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
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
