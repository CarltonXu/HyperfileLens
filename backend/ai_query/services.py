from django.db.models import Q
from django.utils import timezone

from backup_tasks.models import BackupSnapshot
from backup_tasks.services.execution import build_repository_config
from gateways.gateway_service import GatewayService
from insights.models import SnapshotFileIndex
from insights.services import select_ai_provider, select_gateway

from .models import AIQuery


def _tenant_snapshots(user):
    queryset = BackupSnapshot.objects.select_related('task', 'repository', 'task__tenant')
    if user.is_superuser:
        return queryset
    if getattr(user, 'tenant', None):
        return queryset.filter(task__tenant=user.tenant)
    return queryset.filter(task__user=user)


def _query_terms(text):
    return [term.strip() for term in (text or '').replace('\n', ' ').split(' ') if term.strip()]


def _candidate_files(query, snapshot_id=None, repository_id=None, limit=80):
    snapshots = _tenant_snapshots(query.user)
    if snapshot_id:
        snapshots = snapshots.filter(id=snapshot_id)
    if repository_id:
        snapshots = snapshots.filter(repository_id=repository_id)

    files = SnapshotFileIndex.objects.select_related(
        'snapshot',
        'snapshot__task',
        'snapshot__repository',
    ).filter(snapshot_id__in=snapshots.values('id'), is_directory=False)

    if query.target_paths:
        path_filter = Q()
        for path in query.target_paths:
            path_filter |= Q(path__icontains=str(path).strip('/'))
        files = files.filter(path_filter)

    if query.file_types:
        extensions = []
        categories = []
        for value in query.file_types:
            normalized = str(value).lower().strip()
            if not normalized:
                continue
            if normalized.startswith('.'):
                extensions.append(normalized)
            else:
                categories.append(normalized)
        type_filter = Q()
        if extensions:
            type_filter |= Q(extension__in=extensions)
        if categories:
            type_filter |= Q(category__in=categories)
        if type_filter:
            files = files.filter(type_filter)

    terms = _query_terms(query.query_text)
    if terms:
        text_filter = Q()
        for term in terms[:8]:
            text_filter |= Q(path__icontains=term) | Q(name__icontains=term) | Q(extension__icontains=term)
        files = files.filter(text_filter)

    return list(files.order_by('-size', 'path')[:limit])


def _serialize_file_index(item):
    snapshot = item.snapshot
    return {
        'path': item.path,
        'name': item.name,
        'extension': item.extension,
        'category': item.category,
        'size': item.size,
        'modified_time': item.modified_time.isoformat() if item.modified_time else None,
        'snapshot_id': str(snapshot.id),
        'snapshot_name': snapshot.name,
        'kopia_snapshot_id': snapshot.kopia_snapshot_id,
        'object_id': snapshot.kopia_root_object_id or snapshot.manifest_path or '',
        'repository_id': str(snapshot.repository_id),
        'repository_name': snapshot.repository.name if snapshot.repository_id else '',
        'backup_task_id': str(snapshot.task_id),
        'backup_task_name': snapshot.task.name if snapshot.task_id else '',
    }


def _query_context(query, candidates, snapshot=None, repository_id=None):
    return {
        'query': {
            'id': str(query.id),
            'text': query.query_text,
            'type': query.query_type,
            'target_paths': query.target_paths,
            'file_types': query.file_types,
        },
        'scope': {
            'snapshot_id': str(snapshot.id) if snapshot else None,
            'snapshot_name': snapshot.name if snapshot else '',
            'repository_id': str(repository_id or (snapshot.repository_id if snapshot else '') or ''),
        },
        'candidate_files': [_serialize_file_index(item) for item in candidates],
        'candidate_count': len(candidates),
    }


def dispatch_ai_query(query, gateway_id=None, snapshot_id=None, repository_id=None):
    snapshot = None
    repository_config = None
    repository_password = ''

    if snapshot_id:
        snapshot = _tenant_snapshots(query.user).get(id=snapshot_id)
        repository_id = snapshot.repository_id
        repository_config = build_repository_config(snapshot.repository)
        repository_password = snapshot.repository.get_kopia_password()

    candidates = _candidate_files(query, snapshot_id=snapshot_id, repository_id=repository_id)
    gateway = select_gateway(gateway_id, getattr(query.user, 'tenant', None))
    provider = select_ai_provider(getattr(query.user, 'tenant', None))
    context = _query_context(query, candidates, snapshot=snapshot, repository_id=repository_id)

    task_id = GatewayService.ai_query(
        str(gateway.id),
        query=query.query_text,
        query_id=str(query.id),
        context=context,
        repository_ids=[str(repository_id)] if repository_id else [],
        repository_config=repository_config,
        repository_password=repository_password,
        ai_provider_config=provider.to_gateway_config() if provider else None,
    )

    result = dict(query.result or {})
    result['dispatch'] = {
        'task_id': task_id,
        'gateway_id': str(gateway.id),
        'gateway_name': gateway.name,
        'provider': provider.provider_type if provider else 'local',
        'model': provider.default_model if provider else 'rule-query',
        'candidate_count': len(candidates),
        'snapshot_id': str(snapshot.id) if snapshot else None,
        'repository_id': str(repository_id or ''),
    }
    query.status = AIQuery.STATUS_PROCESSING
    query.result = result
    query.model_used = provider.default_model if provider else 'rule-query'
    query.save(update_fields=['status', 'result', 'model_used'])
    return query


def complete_ai_query(query_id, success, result=None, error=''):
    query = AIQuery.objects.get(id=query_id)
    if success:
        payload = result or {}
        query.mark_completed(
            result=payload,
            model_used=payload.get('model') or query.model_used,
            tokens_used=int(payload.get('tokens_used') or 0),
        )
    else:
        query.status = AIQuery.STATUS_FAILED
        query.error_message = error or 'AI query failed'
        query.completed_at = timezone.now()
        query.save(update_fields=['status', 'error_message', 'completed_at'])
    return query
