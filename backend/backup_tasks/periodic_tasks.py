"""
HyperFileLens Backend - Backup Tasks Periodic Tasks

This module defines periodic tasks for backup scheduling.
"""

import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task
def schedule_backup_tasks():
    """
    Schedule due backup tasks.

    Celery Beat only wakes this task up. HyperFileLens owns the business
    scheduling decision so task runs remain auditable, cancellable and visible.
    """
    from backup_tasks.models import BackupTask, BackupTaskRun
    from backup_tasks.services.execution import dispatch_backup_task, BackupTaskExecutionError

    now = timezone.now()
    checked_count = 0
    triggered_count = 0
    skipped_count = 0

    due_ids = list(
        BackupTask.objects.filter(
            is_enabled=True,
            next_run_time__isnull=False,
            next_run_time__lte=now,
        )
        .exclude(status=BackupTask.STATUS_RUNNING)
        .order_by('next_run_time')
        .values_list('id', flat=True)[:100]
    )

    for task_id in due_ids:
        try:
            with transaction.atomic():
                task = BackupTask.objects.select_for_update().select_related(
                    'source_resource', 'target_repository',
                    'source_resource__bound_node', 'target_repository__bound_node',
                    'preferred_execution_node', 'schedule', 'tenant', 'user',
                ).get(id=task_id)

                checked_count += 1
                if not task.next_run_time or task.next_run_time > now or not task.is_enabled:
                    skipped_count += 1
                    continue

                has_active_run = BackupTaskRun.objects.filter(
                    task=task,
                    status__in=[
                        BackupTaskRun.STATUS_PENDING,
                        BackupTaskRun.STATUS_DISPATCHED,
                        BackupTaskRun.STATUS_RUNNING,
                    ],
                ).exists()
                if has_active_run:
                    skipped_count += 1
                    continue

                scheduled_for = task.next_run_time
                run, _ = dispatch_backup_task(
                    task,
                    trigger_type=BackupTaskRun.TRIGGER_SCHEDULED,
                    scheduled_for=scheduled_for,
                )
                task.next_run_time = task.calculate_next_run_time(base_time=now)
                task.save(update_fields=['next_run_time', 'updated_at'])
                triggered_count += 1
                logger.info("Triggered scheduled backup task %s run %s", task.id, run.id)
        except BackupTask.DoesNotExist:
            continue
        except BackupTaskExecutionError as exc:
            BackupTask.objects.filter(id=task_id).update(
                last_run_status=BackupTaskRun.STATUS_FAILED,
                status_message=str(exc),
                next_run_time=now + timedelta(minutes=5),
                updated_at=timezone.now(),
            )
            skipped_count += 1
            logger.warning("Skipped scheduled backup task %s: %s", task_id, exc)
        except Exception as exc:
            skipped_count += 1
            logger.exception("Failed to schedule backup task %s: %s", task_id, exc)

    return {
        'tasks_checked': checked_count,
        'tasks_triggered': triggered_count,
        'tasks_skipped': skipped_count,
    }
