"""
HyperFileLens Backend - Backup Tasks Periodic Tasks

This module defines periodic tasks for backup scheduling.
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def schedule_backup_tasks():
    """
    Schedule backup tasks based on active policies.
    
    This periodic task runs every minute to check if any
    backup policies should trigger and create backup tasks.
    """
    from policies.models import BackupPolicy
    from backup_tasks.models import BackupTask
    from backup_tasks.tasks import execute_backup_task
    from licenses.quota import enforce_license_quota, LicenseQuotaExceeded
    
    now = timezone.now()
    
    # Find active policies that should run now
    policies = BackupPolicy.objects.filter(is_active=True)
    
    triggered_count = 0
    
    for policy in policies:
        next_run = policy.get_next_run_time()
        
        if next_run and next_run <= now:
            # Policy should trigger
            
            # Check if there's already a pending/running task for this policy
            existing_task = BackupTask.objects.filter(
                schedule=policy,
                status__in=['pending', 'running']
            ).exists()
            
            if not existing_task:
                # Create backup task
                try:
                    enforce_license_quota(policy.tenant, 'backup_tasks')
                    task = BackupTask.objects.create(
                        name=f"{policy.name} - {now.strftime('%Y-%m-%d %H:%M')}",
                        description=f"Scheduled backup from policy: {policy.name}",
                        source_node=policy.source_node,
                        target_repository=policy.target_repository,
                        task_type=policy.backup_type,
                        paths=policy.paths or [],
                        exclude_patterns=policy.exclude_patterns or [],
                        compression_enabled=policy.compression_enabled,
                        encryption_enabled=policy.encryption_enabled,
                        retention_days=policy.retention_days,
                        max_snapshots=policy.retention_snapshots,
                        schedule=policy,
                        user=policy.user,
                        tenant=policy.tenant
                    )
                    
                    # Execute the task
                    execute_backup_task.delay(str(task.id))
                    triggered_count += 1
                    
                    logger.info(f"Triggered backup task for policy: {policy.name}")
                    
                except Exception as e:
                    if isinstance(e, LicenseQuotaExceeded):
                        logger.warning(f"Skipped backup task for policy {policy.name}: {e}")
                        continue
                    logger.error(f"Failed to create backup task for policy {policy.name}: {e}")
    
    return {'policies_checked': policies.count(), 'tasks_triggered': triggered_count}
