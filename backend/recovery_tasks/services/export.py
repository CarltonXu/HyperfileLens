"""Recovery export dispatch service."""

from django.utils import timezone
from datetime import timedelta

from backup_tasks.models import BackupSnapshot
from backup_tasks.services.execution import build_repository_config
from nodes.models import ProxyTask
from nodes.proxy_service import ProxyService
from nodes.repository_locks import RepositoryLockError, create_repository_proxy_task
from recovery_tasks.models import RecoveryExport


class RecoveryExportExecutionError(Exception):
    """Raised when an export cannot be dispatched."""


def _is_probably_kopia_object_id(value):
    value = (value or '').strip()
    return len(value) >= 16 and '-' not in value and value[0].lower() == 'k'


def dispatch_recovery_export(export):
    """Create a proxy task and dispatch a snapshot export command."""
    if export.status in [RecoveryExport.STATUS_RUNNING, RecoveryExport.STATUS_DISPATCHED]:
        raise RecoveryExportExecutionError('Export is already running')
    if export.snapshot.snapshot_status != BackupSnapshot.STATUS_AVAILABLE:
        raise RecoveryExportExecutionError('Snapshot is not available in Kopia')

    task = export.snapshot.task
    proxy = task.execution_node
    if not proxy:
        raise RecoveryExportExecutionError('Backup task has no execution proxy')

    is_online, error_msg = ProxyService.check_proxy_connectivity(str(proxy.id))
    if not is_online:
        raise RecoveryExportExecutionError(f'Execution proxy is not reachable: {error_msg}')

    repository = export.repository
    repository_password = repository.get_kopia_password()
    if not repository_password:
        raise RecoveryExportExecutionError('Repository password is not saved')

    object_id = export.snapshot.kopia_root_object_id or export.snapshot.manifest_path or ''
    if not _is_probably_kopia_object_id(object_id):
        raise RecoveryExportExecutionError(
            'Snapshot root object ID is missing or invalid. Please resync snapshots before exporting files.'
        )
    snapshot_id = export.snapshot.kopia_snapshot_id or (export.snapshot.metadata or {}).get('referenced_snapshot_id', '')
    if not snapshot_id:
        raise RecoveryExportExecutionError('Snapshot ID is missing. Please resync snapshots before exporting files.')

    try:
        proxy_task = create_repository_proxy_task(
            repository_id=repository.id,
            proxy=proxy,
            task_type=ProxyTask.TaskType.SNAPSHOT_EXPORT,
            parameters={
                'recovery_export_id': str(export.id),
                'snapshot_record_id': str(export.snapshot_id),
                'snapshot_id': snapshot_id,
                'object_id': object_id,
                'selected_paths': export.selected_paths,
                'package_format': export.package_format,
                'repository_id': str(repository.id),
            },
            source_resource_id=task.source_resource_id,
            status=ProxyTask.TaskStatus.PENDING,
            timeout_seconds=24 * 60 * 60,
        )
    except RepositoryLockError as exc:
        raise RecoveryExportExecutionError(str(exc)) from exc
    proxy_task.dispatch()

    export.proxy_task = proxy_task
    export.executor_node = proxy
    export.status = RecoveryExport.STATUS_DISPATCHED
    export.status_message = 'Export dispatched'
    export.started_at = timezone.now()
    if not export.expires_at:
        export.expires_at = timezone.now() + timedelta(hours=24)
    export.save(update_fields=[
        'proxy_task', 'executor_node', 'status', 'status_message',
        'started_at', 'expires_at', 'updated_at',
    ])

    payload = {
        'task_id': str(proxy_task.id),
        'recovery_export_id': str(export.id),
        'snapshot_record_id': str(export.snapshot_id),
        'snapshot_id': snapshot_id,
        'object_id': object_id,
        'selected_paths': export.selected_paths,
        'package_format': export.package_format,
        'repository': build_repository_config(repository),
        'password': repository_password,
        'upload_url': f'/api/v1/recovery-tasks/exports/{export.id}/upload/',
        'server_url': '',
        'timestamp': timezone.now().isoformat(),
    }
    sent = ProxyService.send_to_proxy(
        str(proxy.id),
        {
            'type': 'snapshot_export',
            'id': str(proxy_task.id),
            'timestamp': timezone.now().isoformat(),
            'payload': payload,
        },
    )
    if not sent:
        proxy_task.fail('Failed to send export command to proxy')
        export.status = RecoveryExport.STATUS_FAILED
        export.error_message = 'Failed to send export command to proxy'
        export.completed_at = timezone.now()
        export.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
        raise RecoveryExportExecutionError('Failed to send export command to proxy')

    return proxy_task
