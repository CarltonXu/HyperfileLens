"""Recovery task execution service."""

from django.utils import timezone

from backup_tasks.models import BackupSnapshot
from backup_tasks.services.execution import build_repository_config
from nodes.models import ProxyTask
from nodes.proxy_service import ProxyService
from nodes.repository_locks import RepositoryLockError, create_repository_proxy_task
from recovery_tasks.models import RecoveryRun


class RecoveryTaskExecutionError(Exception):
    """Raised when a recovery task cannot be dispatched."""


def dispatch_recovery_task(task, *, trigger_type=RecoveryRun.TRIGGER_MANUAL):
    """Create a proxy restore task and dispatch it to the target proxy."""
    if task.status == task.STATUS_RUNNING:
        raise RecoveryTaskExecutionError('Recovery task is already running')
    if task.snapshot.snapshot_status != BackupSnapshot.STATUS_AVAILABLE:
        raise RecoveryTaskExecutionError('Snapshot is not available in Kopia')
    if not task.target_node_id:
        raise RecoveryTaskExecutionError('Recovery task has no target node')

    is_online, error_msg = ProxyService.check_proxy_connectivity(str(task.target_node_id))
    if not is_online:
        raise RecoveryTaskExecutionError(f'Target proxy is not reachable: {error_msg}')

    repository = task.snapshot.repository
    repository_password = repository.get_kopia_password()
    if not repository_password:
        raise RecoveryTaskExecutionError(
            'Repository password is not saved. Please save the Kopia repository password before recovery.'
        )

    snapshot_id = task.snapshot.kopia_snapshot_id or (task.snapshot.metadata or {}).get('referenced_snapshot_id', '')
    if not snapshot_id:
        raise RecoveryTaskExecutionError('Snapshot ID is missing')
    object_id = (
        task.snapshot.kopia_root_object_id
        or task.snapshot.manifest_path
        or ''
    )
    if task.restore_scope == task.SCOPE_SELECTED_PATHS and not object_id:
        raise RecoveryTaskExecutionError(
            'Snapshot root object ID is missing. Please resync snapshots before granular recovery.'
        )

    target_path = build_target_path(task)
    if not target_path:
        raise RecoveryTaskExecutionError('Target path is required for recovery')

    restore_paths = task.selected_paths if task.restore_scope == task.SCOPE_SELECTED_PATHS else []
    run = RecoveryRun.objects.create(
        task=task,
        snapshot=task.snapshot,
        target_node=task.target_node,
        trigger_type=trigger_type,
        status=RecoveryRun.STATUS_PENDING,
        parameters={
            'snapshot_id': snapshot_id,
            'target_path': target_path,
            'recovery_type': task.recovery_type,
            'restore_scope': task.restore_scope,
            'selected_paths': restore_paths,
            'conflict_policy': task.conflict_policy,
            'priority': task.priority,
        },
    )
    try:
        proxy_task = create_repository_proxy_task(
            repository_id=repository.id,
            proxy=task.target_node,
            task_type=ProxyTask.TaskType.RESTORE,
            parameters={
                'recovery_task_id': str(task.id),
                'recovery_run_id': str(run.id),
                'recovery_task_name': task.name,
                'snapshot_record_id': str(task.snapshot_id),
                'snapshot_id': snapshot_id,
                'object_id': object_id,
                'repository_id': str(repository.id),
                'target_path': target_path,
                'recovery_type': task.recovery_type,
                'restore_scope': task.restore_scope,
                'selected_paths': restore_paths,
                'conflict_policy': task.conflict_policy,
                'priority': task.priority,
            },
            status=ProxyTask.TaskStatus.PENDING,
            timeout_seconds=task.options.get('timeout_seconds') or 24 * 60 * 60,
        )
    except RepositoryLockError as exc:
        run.status = RecoveryRun.STATUS_FAILED
        run.error_message = str(exc)
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'error_message', 'completed_at'])
        raise RecoveryTaskExecutionError(str(exc)) from exc
    proxy_task.dispatch()
    run.proxy_task = proxy_task
    run.status = RecoveryRun.STATUS_DISPATCHED
    run.dispatched_at = timezone.now()
    run.save(update_fields=['proxy_task', 'status', 'dispatched_at'])

    payload = {
        'task_id': str(proxy_task.id),
        'recovery_task_id': str(task.id),
        'recovery_run_id': str(run.id),
        'snapshot_record_id': str(task.snapshot_id),
        'snapshot_id': snapshot_id,
        'object_id': object_id,
        'target_path': target_path,
        'repository': build_repository_config(repository),
        'password': repository_password,
        'overwrite': task.conflict_policy == task.CONFLICT_OVERWRITE,
        'conflict_policy': task.conflict_policy,
        'restore_scope': task.restore_scope,
        'restore_paths': restore_paths,
        'file_patterns': task.file_patterns or [],
        'exclude_patterns': task.exclude_patterns or [],
        'priority': task.priority,
        'timestamp': timezone.now().isoformat(),
    }

    sent = ProxyService.send_to_proxy(
        str(task.target_node_id),
        {
            'type': 'restore',
            'id': str(proxy_task.id),
            'timestamp': timezone.now().isoformat(),
            'payload': payload,
        },
    )
    if not sent:
        proxy_task.fail('Failed to send recovery command to proxy')
        run.status = RecoveryRun.STATUS_FAILED
        run.error_message = 'Failed to send recovery command to proxy'
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'error_message', 'completed_at'])
        task.proxy_task = proxy_task
        task.mark_failed('Failed to send recovery command to proxy')
        task.save(update_fields=['proxy_task'])
        raise RecoveryTaskExecutionError('Failed to send recovery command to proxy')

    task.proxy_task = proxy_task
    task.mark_running()
    task.save(update_fields=['proxy_task'])
    return run, proxy_task


def build_target_path(task):
    """Resolve the restore destination path."""
    if task.recovery_type == task.TYPE_NEW_LOCATION:
        return task.target_path
    if task.target_path:
        return task.target_path
    source_path = (task.snapshot.metadata or {}).get('source_path') or ''
    return source_path or '/'
