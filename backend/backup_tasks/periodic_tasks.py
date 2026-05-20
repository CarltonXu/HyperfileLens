"""
HyperFileLens Backend - Backup Tasks Periodic Tasks

This module defines periodic tasks for backup scheduling.
"""

import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.db.utils import OperationalError

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
    from nodes.models import ProxyTask

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
            scheduled_for = None
            with transaction.atomic():
                task = BackupTask.objects.select_for_update().select_related('schedule').get(id=task_id)
                checked_count += 1
                scheduled_for = _claim_due_backup_task(task, BackupTaskRun, ProxyTask, now)
                if not scheduled_for:
                    skipped_count += 1
                    continue

            task = BackupTask.objects.select_related(
                'source_resource', 'target_repository',
                'source_resource__bound_node', 'target_repository__bound_node',
                'preferred_execution_node', 'schedule', 'tenant', 'user',
            ).get(id=task_id)
            run, _ = dispatch_backup_task(
                task,
                trigger_type=BackupTaskRun.TRIGGER_SCHEDULED,
                scheduled_for=scheduled_for,
            )
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
        except OperationalError as exc:
            if scheduled_for:
                BackupTask.objects.filter(id=task_id).update(
                    next_run_time=scheduled_for,
                    updated_at=timezone.now(),
                )
            skipped_count += 1
            logger.warning(
                "Database was busy while scheduling backup task %s; will retry on next scan: %s",
                task_id,
                exc,
            )
        except Exception as exc:
            skipped_count += 1
            logger.exception("Failed to schedule backup task %s: %s", task_id, exc)

    return {
        'tasks_checked': checked_count,
        'tasks_triggered': triggered_count,
        'tasks_skipped': skipped_count,
    }


def _claim_due_backup_task(task, BackupTaskRun, ProxyTask, now):
    """Validate a due task and advance its next run before dispatching outside the DB lock."""
    if not task.next_run_time or task.next_run_time > now or not task.is_enabled:
        return None

    reconciled_runs = _reconcile_terminal_proxy_runs(task, BackupTaskRun, ProxyTask, now)
    if reconciled_runs:
        logger.info(
            "Reconciled %s stale active backup run(s) before scheduling task %s",
            reconciled_runs,
            task.id,
        )

    has_active_run = BackupTaskRun.objects.filter(
        task=task,
        status__in=[
            BackupTaskRun.STATUS_PENDING,
            BackupTaskRun.STATUS_DISPATCHED,
            BackupTaskRun.STATUS_RUNNING,
        ],
    ).exists()
    if has_active_run:
        return None

    scheduled_for = task.next_run_time
    task.next_run_time = task.calculate_next_run_time(base_time=now)
    task.save(update_fields=['next_run_time', 'updated_at'])
    return scheduled_for


def _reconcile_terminal_proxy_runs(task, BackupTaskRun, ProxyTask, now):
    """Close active backup runs whose underlying proxy task already reached a terminal state."""
    terminal_status_map = {
        ProxyTask.TaskStatus.COMPLETED: BackupTaskRun.STATUS_COMPLETED,
        ProxyTask.TaskStatus.FAILED: BackupTaskRun.STATUS_FAILED,
        ProxyTask.TaskStatus.TIMEOUT: BackupTaskRun.STATUS_TIMEOUT,
        ProxyTask.TaskStatus.CANCELLED: BackupTaskRun.STATUS_CANCELLED,
    }
    active_statuses = [
        BackupTaskRun.STATUS_PENDING,
        BackupTaskRun.STATUS_DISPATCHED,
        BackupTaskRun.STATUS_RUNNING,
    ]
    runs = BackupTaskRun.objects.select_related('proxy_task').filter(
        task=task,
        status__in=active_statuses,
        proxy_task__status__in=list(terminal_status_map.keys()),
    )

    reconciled = 0
    for run in runs:
        proxy_task = run.proxy_task
        run_status = terminal_status_map.get(proxy_task.status)
        if not run_status:
            continue

        update_fields = ['status', 'completed_at']
        run.status = run_status
        run.completed_at = proxy_task.completed_at or now
        if proxy_task.error_message and not run.error_message:
            run.error_message = proxy_task.error_message
            update_fields.append('error_message')
        if proxy_task.result and not run.result:
            run.result = proxy_task.result
            update_fields.append('result')
        run.save(update_fields=update_fields)
        reconciled += 1

    return reconciled
