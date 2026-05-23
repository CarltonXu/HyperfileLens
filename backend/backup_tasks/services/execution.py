"""Backup task execution service shared by API and scheduler."""

import copy

from django.utils import timezone

from nodes.models import ProxyNode, ProxyTask
from nodes.proxy_service import ProxyService
from nodes.repository_locks import RepositoryLockError, create_repository_proxy_task
from repository.models import Repository
from backup_tasks.models import BackupTask, BackupTaskRun


class BackupTaskExecutionError(Exception):
    """Raised when a backup task cannot be dispatched."""


def dispatch_backup_task(task, *, trigger_type=BackupTaskRun.TRIGGER_MANUAL, force=False,
                         task_type=None, repository_password=None, scheduled_for=None):
    """Create a run, select an execution proxy, and dispatch the backup command."""
    if task.status == BackupTask.STATUS_RUNNING and not force:
        raise BackupTaskExecutionError('Task is already running. Use force=true to override.')
    if not task.is_enabled:
        raise BackupTaskExecutionError('Task is disabled. Enable it before execution.')
    if not task.source_resource_id:
        raise BackupTaskExecutionError('Backup task has no source resource')
    if not task.target_repository_id:
        raise BackupTaskExecutionError('Backup task has no target repository')

    if force:
        task.mark_pending()

    execution_node, placement_error = select_execution_node(task)
    if placement_error:
        raise BackupTaskExecutionError(placement_error)

    source_path = resolve_source_path(task)
    if not source_path:
        raise BackupTaskExecutionError('Backup task has no source path to execute')

    repository_password = repository_password or task.target_repository.get_kopia_password()
    if not repository_password:
        raise BackupTaskExecutionError(
            'Repository password is not saved. Please save the Kopia repository password before executing backup tasks.'
        )

    effective_policy = build_effective_policy(task, source_path)
    repository_config = build_repository_config(task.target_repository)

    run = BackupTaskRun.objects.create(
        task=task,
        trigger_type=trigger_type,
        scheduled_for=scheduled_for,
        status=BackupTaskRun.STATUS_PENDING,
        selected_proxy=execution_node,
        repository=task.target_repository,
        source_resource=task.source_resource,
    )

    try:
        proxy_task = create_repository_proxy_task(
            repository_id=task.target_repository_id,
            task_type=ProxyTask.TaskType.BACKUP,
            proxy=execution_node,
            parameters={
                'backup_task_id': str(task.id),
                'backup_run_id': str(run.id),
                'backup_task_name': task.name,
                'source_resource_id': str(task.source_resource_id),
                'repository_id': str(task.target_repository_id),
                'source_path': source_path,
                'backup_paths': task.backup_paths,
                'exclude_patterns': task.exclude_patterns,
                'include_patterns': task.include_patterns,
                'policy_overrides': task.policy_overrides,
                'effective_policy': effective_policy,
                'execution_mode': task.execution_mode,
                'selected_execution_node_id': str(execution_node.id),
                'selected_execution_node_name': execution_node.name,
                'task_type': task_type or task.task_type,
                'priority': task.priority,
                'trigger_type': trigger_type,
            },
            source_resource_id=task.source_resource_id,
            status=ProxyTask.TaskStatus.PENDING,
            timeout_seconds=task.checkpoint_interval_minutes * 60 if task.checkpoint_interval_minutes else 3600,
        )
    except RepositoryLockError as exc:
        run.status = BackupTaskRun.STATUS_FAILED
        run.error_message = str(exc)
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'error_message', 'completed_at'])
        raise BackupTaskExecutionError(str(exc)) from exc
    proxy_task.dispatch()

    payload = {
        'task_id': str(proxy_task.id),
        'backup_task_id': str(task.id),
        'backup_run_id': str(run.id),
        'source_resource_id': str(task.source_resource_id),
        'repository_id': str(task.target_repository_id),
        'source_path': source_path,
        'backup_paths': task.backup_paths,
        'exclude_patterns': task.exclude_patterns,
        'include_patterns': task.include_patterns,
        'policy_overrides': task.policy_overrides,
        'effective_policy': effective_policy,
        'execution_placement': {
            'mode': task.execution_mode,
            'selected_proxy_id': str(execution_node.id),
            'selected_proxy_name': execution_node.name,
            'preferred_proxy_id': str(task.preferred_execution_node_id) if task.preferred_execution_node_id else None,
        },
        'source_resource': build_source_resource_config(task.source_resource),
        'repository': repository_config,
        'password': repository_password,
        'task_type': task_type or task.task_type,
        'priority': task.priority,
        'compression_enabled': task.compression_enabled,
        'compression_type': task.compression_type,
        'compression_level': task.compression_level,
        'verify_checksum': task.verify_checksum,
        'max_concurrent_files': task.max_concurrent_files,
        'bandwidth_limit_kbps': task.bandwidth_limit_kbps,
        'timestamp': timezone.now().isoformat(),
    }

    sent = ProxyService.send_to_proxy(
        str(execution_node.id),
        {
            'type': 'backup',
            'id': str(proxy_task.id),
            'timestamp': timezone.now().isoformat(),
            'payload': payload,
        },
    )
    if not sent:
        proxy_task.fail('Failed to send backup command to proxy')
        run.status = BackupTaskRun.STATUS_FAILED
        run.error_message = 'Failed to send backup command to proxy'
        run.proxy_task = proxy_task
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'error_message', 'proxy_task', 'completed_at'])
        raise BackupTaskExecutionError('Failed to send backup command to proxy')

    run.proxy_task = proxy_task
    run.status = BackupTaskRun.STATUS_DISPATCHED
    run.parameters = payload
    run.dispatched_at = timezone.now()
    run.save(update_fields=['proxy_task', 'status', 'parameters', 'dispatched_at'])

    task.status = BackupTask.STATUS_RUNNING
    task.progress = 0
    task.status_message = 'Backup command dispatched to proxy'
    task.error_message = ''
    task.effective_policy = effective_policy
    task.started_at = timezone.now()
    task.last_run_time = timezone.now()
    task.last_run_status = BackupTaskRun.STATUS_DISPATCHED
    task.save(update_fields=[
        'status', 'progress', 'status_message', 'error_message',
        'effective_policy', 'started_at', 'last_run_time', 'last_run_status', 'updated_at'
    ])

    return run, proxy_task


def select_execution_node(task):
    """Select the proxy that should execute this backup task."""
    source = task.source_resource
    repo = task.target_repository
    mode = task.execution_mode or BackupTask.EXECUTION_MODE_PINNED

    def online_error(proxy):
        if not proxy:
            return 'No execution proxy is configured for this task'
        is_online, error_msg = ProxyService.check_proxy_connectivity(str(proxy.id))
        if not is_online:
            return f"Execution proxy is not reachable: {error_msg}"
        return ''

    def is_network_source():
        return source and source.resource_type in ('nas', 'nfs', 'cifs', 's3')

    def is_network_repository():
        return repo and repo.repo_type in (
            Repository.TYPE_NAS,
            Repository.TYPE_NFS,
            Repository.TYPE_S3,
            Repository.TYPE_AZURE,
            Repository.TYPE_GCS,
        )

    if source.resource_type == 'local':
        proxy = source.bound_node
        error = online_error(proxy)
        return (None, error) if error else (proxy, '')

    if repo.repo_type == Repository.TYPE_LOCAL:
        proxy = repo.bound_node
        error = online_error(proxy)
        return (None, error) if error else (proxy, '')

    if mode == BackupTask.EXECUTION_MODE_PINNED:
        proxy = source.bound_node or repo.bound_node
        error = online_error(proxy)
        return (None, error) if error else (proxy, '')

    if not (is_network_source() and is_network_repository()):
        return None, 'Auto proxy selection requires network-accessible source and repository resources'

    if mode == BackupTask.EXECUTION_MODE_PREFERRED and task.preferred_execution_node_id:
        preferred = task.preferred_execution_node
        if preferred.role == ProxyNode.Role.SYNC and preferred.active_tasks < preferred.max_concurrent_tasks:
            if not online_error(preferred):
                return preferred, ''

    candidates = ProxyNode.objects.filter(
        role=ProxyNode.Role.SYNC,
        status=ProxyNode.NodeStatus.ONLINE,
    )
    if task.tenant_id:
        candidates = candidates.filter(tenant_id=task.tenant_id)
    candidates = candidates.order_by('active_tasks', '-health_score', 'name')
    for proxy in candidates:
        if proxy.active_tasks < proxy.max_concurrent_tasks:
            return proxy, ''

    return None, 'No available Sync Proxy found for automatic execution. Please start a Sync Proxy or reduce running tasks.'


def build_source_resource_config(source):
    if not source:
        return {}
    config = source.config or {}
    credentials = source.credentials or {}
    payload = {
        'id': str(source.id),
        'name': source.name,
        'type': source.resource_type,
        'resource_type': source.resource_type,
        'mount_point': source.mount_point or source.get_effective_mount_point(),
        'config': config,
        'credentials': credentials,
    }
    if source.resource_type in ('nas', 'nfs', 'cifs'):
        payload.update({
            'server': config.get('server', ''),
            'export_path': config.get('export_path') or config.get('share') or '',
            'share': config.get('share') or config.get('export_path') or '',
            'mount_type': config.get('mount_type') or config.get('protocol') or ('cifs' if source.resource_type == 'cifs' else 'nfs'),
            'mount_options': config.get('mount_options', ''),
            'username': credentials.get('username') or config.get('username', ''),
            'password': credentials.get('password') or config.get('password', ''),
        })
    elif source.resource_type == 's3':
        payload.update({
            'endpoint': config.get('endpoint', ''),
            'bucket': config.get('bucket', ''),
            'region': config.get('region', 'us-east-1'),
            'prefix': config.get('prefix', ''),
            'access_key': credentials.get('access_key') or config.get('access_key', ''),
            'secret_key': credentials.get('secret_key') or config.get('secret_key', ''),
            'use_tls': config.get('use_tls', True),
            'url_style': config.get('url_style', 'virtual'),
        })
    elif source.resource_type == 'local':
        payload['path'] = config.get('root_path') or config.get('path') or ''
    return payload


def resolve_source_path(task):
    kopia_source_path = resolve_kopia_source_path(task)
    if kopia_source_path:
        return kopia_source_path
    if task.backup_paths:
        return task.backup_paths[0]
    return ''


def resolve_kopia_source_path(task):
    """Return the path Kopia records as source.path on the execution proxy."""
    if task.backup_paths:
        source = task.source_resource
        if source and source.resource_type in ('local', 's3'):
            return task.backup_paths[0]
    source = task.source_resource
    if not source:
        return ''
    config = source.config or {}
    if source.resource_type == 'local':
        return config.get('root_path') or config.get('path') or '/'
    if source.resource_type == 's3':
        return config.get('prefix') or '/'
    if source.mount_point:
        return source.mount_point
    return f"/mnt/hyperfilelens/source-{_safe_source_id_prefix(source.id)}"


def _safe_source_id_prefix(source_id):
    value = str(source_id or '').strip()
    token = ''.join(
        char if char.isalnum() or char in {'-', '_', '.'} else '-'
        for char in value
    ).strip('-.')
    return (token or 'unknown')[:8]


def build_effective_policy(task, source_path):
    policy = task.schedule
    overrides = task.policy_overrides or {}

    if policy:
        effective = {
            'source': 'policy',
            'policy_id': str(policy.id),
            'policy_name': policy.name,
            'policy_scope': policy.policy_scope,
            'policy_target': copy.deepcopy(policy.policy_target or {}),
            'snapshot_schedule': copy.deepcopy(policy.snapshot_schedule or {}),
            'apply_kopia_schedule': False,
            'retention_policy': copy.deepcopy(policy.retention_policy or {}),
            'file_policy': {
                'ignore_patterns': [],
                'dot_ignore_files': ['.kopiaignore'],
                'one_file_system': False,
                'ignore_file_errors': False,
                'ignore_dir_errors': False,
            },
            'compression_policy': {
                'compression': task.compression_type if task.compression_enabled else 'none',
                'metadata_compression': task.compression_enabled,
                'max_parallel_file_reads': task.max_concurrent_files,
                'ignore_identical_snapshots': True,
            },
            'advanced_policy': copy.deepcopy(policy.advanced_policy or {}),
        }
    else:
        effective = {
            'source': 'task',
            'policy_id': None,
            'policy_name': '',
            'policy_scope': 'path',
            'policy_target': {},
            'snapshot_schedule': {'mode': 'manual', 'interval': '', 'time_of_day': '', 'cron': '', 'run_missed': True},
            'apply_kopia_schedule': False,
            'retention_policy': {
                'keep_latest': task.max_snapshots,
                'keep_hourly': 0,
                'keep_daily': task.retention_days,
                'keep_weekly': 0,
                'keep_monthly': 0,
                'keep_annual': 0,
            },
            'file_policy': {
                'ignore_patterns': [],
                'dot_ignore_files': ['.kopiaignore'],
                'one_file_system': False,
                'ignore_file_errors': False,
                'ignore_dir_errors': False,
            },
            'compression_policy': {
                'compression': task.compression_type if task.compression_enabled else 'none',
                'metadata_compression': task.compression_enabled,
                'max_parallel_file_reads': task.max_concurrent_files,
                'ignore_identical_snapshots': True,
            },
            'advanced_policy': {},
        }

    effective['policy_target'] = copy.deepcopy(effective.get('policy_target') or {})
    if not effective['policy_target'].get('kopia_target'):
        effective['policy_target']['kopia_target'] = source_path

    effective['snapshot_schedule'] = merge_policy_section(effective.get('snapshot_schedule'), overrides, 'snapshot_schedule')
    effective['retention_policy'] = merge_policy_section(effective.get('retention_policy'), overrides, 'retention_policy')
    effective['compression_policy'] = merge_policy_section(effective.get('compression_policy'), overrides, 'compression_policy')

    file_policy = copy.deepcopy(effective.get('file_policy') or {})
    file_override = copy.deepcopy(overrides.get('file_policy') or {})
    if file_override.get('override') is True:
        file_override.pop('override', None)
        file_policy.update({k: v for k, v in file_override.items() if v is not None})

    merged_ignores = []
    merged_ignores.extend(file_policy.get('ignore_patterns') or [])
    merged_ignores.extend(task.exclude_patterns or [])
    merged_ignores.extend(file_override.get('additional_ignore_patterns') or [])
    file_policy['ignore_patterns'] = dedupe_list(merged_ignores)
    file_policy['include_patterns'] = dedupe_list(task.include_patterns or [])
    effective['file_policy'] = file_policy
    effective['task_overrides'] = overrides
    return effective


def build_repository_config(repo):
    config = repo.config or {}
    credentials = repo.get_decrypted_credentials() if hasattr(repo, 'get_decrypted_credentials') else (repo.credentials or {})
    repository_config = {
        'id': str(repo.id),
        'type': repo.repo_type,
    }

    if repo.repo_type == Repository.TYPE_LOCAL:
        repository_config['path'] = config.get('path') or repo.path or ''
    elif repo.repo_type in (Repository.TYPE_NAS, Repository.TYPE_NFS):
        server = config.get('server') or config.get('nas_server') or ''
        export_path = config.get('export_path') or config.get('path') or config.get('nas_path') or repo.path or ''
        share = config.get('share') or export_path
        mount_type = config.get('mount_type') or config.get('nas_type') or 'nfs'
        mount_path = config.get('mount_path') or ''
        repository_config.update({
            'path': mount_path or export_path,
            'server': server,
            'share': share,
            'export_path': export_path,
            'nas_server': server,
            'nas_path': export_path,
            'mount_type': mount_type,
            'mount_path': mount_path,
            'mount_options': config.get('mount_options', ''),
            'username': credentials.get('username', ''),
            'password': credentials.get('password', ''),
        })
    elif repo.repo_type == Repository.TYPE_S3:
        bucket = config.get('bucket') or repo.path or ''
        prefix = (config.get('prefix') or '').strip('/')
        repository_url = config.get('url') or config.get('repository_url') or (
            f"s3://{bucket}/{prefix}" if prefix else f"s3://{bucket}"
        )
        repository_config.update({
            'path': repository_url,
            'url': repository_url,
            'endpoint': config.get('endpoint', ''),
            'bucket': bucket,
            'region': config.get('region', 'us-east-1'),
            'access_key': credentials.get('access_key', config.get('access_key', '')),
            'secret_key': credentials.get('secret_key', config.get('secret_key', '')),
            'prefix': prefix,
            'use_tls': config.get('use_tls', True),
            'url_style': config.get('url_style', 'virtual'),
        })
    else:
        repository_config['path'] = config.get('path') or repo.path or ''

    return repository_config


def merge_policy_section(base, overrides, override_key):
    base_section = copy.deepcopy(base or {})
    override_section = copy.deepcopy((overrides or {}).get(override_key) or {})
    if override_section.get('override') is True:
        override_section.pop('override', None)
        base_section.update({k: v for k, v in override_section.items() if v is not None})
    return base_section


def dedupe_list(values):
    result = []
    seen = set()
    for value in values or []:
        if value is None:
            continue
        item = str(value).strip()
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result
