"""Repository-level dispatch guard for proxy tasks."""

from __future__ import annotations

from django.db import IntegrityError, transaction

from nodes.models import ProxyTask


ACTIVE_REPOSITORY_TASK_STATUSES = (
    ProxyTask.TaskStatus.PENDING,
    ProxyTask.TaskStatus.DISPATCHED,
    ProxyTask.TaskStatus.ACCEPTED,
    ProxyTask.TaskStatus.RUNNING,
)

EXCLUSIVE_REPOSITORY_TASK_TYPES = (
    ProxyTask.TaskType.SNAPSHOT_DELETE,
    ProxyTask.TaskType.KOPIA_MAINTENANCE,
    ProxyTask.TaskType.INIT_REPOSITORY,
)

SOURCE_SERIAL_REPOSITORY_TASK_TYPES = (
    ProxyTask.TaskType.BACKUP,
)

REPOSITORY_ACCESS_TASK_TYPES = (
    *EXCLUSIVE_REPOSITORY_TASK_TYPES,
    *SOURCE_SERIAL_REPOSITORY_TASK_TYPES,
    ProxyTask.TaskType.RESTORE,
    ProxyTask.TaskType.POLICY_SHOW,
    ProxyTask.TaskType.SNAPSHOT_EXPORT,
    'list_snapshot_files',
)

DATABASE_GUARDED_TASK_TYPES = (
    *EXCLUSIVE_REPOSITORY_TASK_TYPES,
    *SOURCE_SERIAL_REPOSITORY_TASK_TYPES,
)


class RepositoryLockError(Exception):
    """Raised when a repository already has a conflicting proxy task."""


def get_active_repository_task(repository_id, *, task_types=None, source_resource_id=None, exclude_task_id=None):
    """Return the currently active repository task matching the requested scope."""
    if not repository_id:
        return None

    queryset = ProxyTask.objects.filter(
        repository_id=repository_id,
        status__in=ACTIVE_REPOSITORY_TASK_STATUSES,
        task_type__in=task_types or REPOSITORY_ACCESS_TASK_TYPES,
    ).order_by('created_at')
    if source_resource_id:
        queryset = queryset.filter(source_resource_id=source_resource_id)
    if exclude_task_id:
        queryset = queryset.exclude(id=exclude_task_id)
    return queryset.first()


def assert_repository_available(repository_id, task_type, source_resource_id=None, exclude_task_id=None):
    """Fail fast with a readable error before the database uniqueness guard."""
    if not repository_id or task_type not in REPOSITORY_ACCESS_TASK_TYPES:
        return

    if task_type in EXCLUSIVE_REPOSITORY_TASK_TYPES:
        active = get_active_repository_task(repository_id, exclude_task_id=exclude_task_id)
        if active:
            raise RepositoryLockError(
                f'Repository is busy with {active.task_type} task {active.id} ({active.status})'
            )
        return

    active_exclusive = get_active_repository_task(
        repository_id,
        task_types=EXCLUSIVE_REPOSITORY_TASK_TYPES,
        exclude_task_id=exclude_task_id,
    )
    if active_exclusive:
        raise RepositoryLockError(
            f'Repository is busy with {active_exclusive.task_type} task '
            f'{active_exclusive.id} ({active_exclusive.status})'
        )

    if task_type in SOURCE_SERIAL_REPOSITORY_TASK_TYPES and source_resource_id:
        active_source = get_active_repository_task(
            repository_id,
            task_types=SOURCE_SERIAL_REPOSITORY_TASK_TYPES,
            source_resource_id=source_resource_id,
            exclude_task_id=exclude_task_id,
        )
        if active_source:
            raise RepositoryLockError(
                f'Repository source is busy with {active_source.task_type} task '
                f'{active_source.id} ({active_source.status})'
            )


def _lock_repository_row(repository_id):
    """Serialize repository lock decisions on databases that support row locks."""
    if not repository_id:
        return
    from repository.models import Repository

    Repository.objects.select_for_update().filter(id=repository_id).first()


def create_repository_proxy_task(*, repository_id, task_type, **fields):
    """Create a repository task while enforcing repository/source serialization."""
    source_resource_id = fields.get('source_resource_id')
    try:
        with transaction.atomic():
            _lock_repository_row(repository_id)
            assert_repository_available(
                repository_id,
                task_type,
                source_resource_id=source_resource_id,
            )
            return ProxyTask.objects.create(
                repository_id=repository_id,
                task_type=task_type,
                **fields,
            )
    except IntegrityError as exc:
        if task_type in EXCLUSIVE_REPOSITORY_TASK_TYPES:
            active = get_active_repository_task(repository_id)
        elif task_type in SOURCE_SERIAL_REPOSITORY_TASK_TYPES and source_resource_id:
            active = get_active_repository_task(
                repository_id,
                task_types=SOURCE_SERIAL_REPOSITORY_TASK_TYPES,
                source_resource_id=source_resource_id,
            )
        else:
            active = get_active_repository_task(
                repository_id,
                task_types=EXCLUSIVE_REPOSITORY_TASK_TYPES,
            )
        if active:
            raise RepositoryLockError(
                f'Repository is busy with {active.task_type} task {active.id} ({active.status})'
            ) from exc
        raise
