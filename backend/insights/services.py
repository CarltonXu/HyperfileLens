from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, Sum
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from backup_tasks.models import BackupSnapshot
from backup_tasks.services.execution import build_repository_config
from gateways.gateway_service import GatewayService
from gateways.models import Gateway
from ai_query.models import AIProvider

from .models import SnapshotAIJob, SnapshotFileIndex, SnapshotIndexJob, SnapshotInsight


DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.md', '.csv'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.tif', '.tiff', '.bmp', '.svg'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'}
ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tgz'}
CODE_EXTENSIONS = {'.py', '.js', '.ts', '.vue', '.go', '.java', '.rb', '.php', '.c', '.cpp', '.h', '.cs', '.json', '.yaml', '.yml', '.xml', '.html', '.css', '.scss', '.sh'}
DATABASE_EXTENSIONS = {'.db', '.sqlite', '.sqlite3', '.sql', '.mdb'}


def categorize_file(name, extension='', is_directory=False):
    if is_directory:
        return SnapshotFileIndex.CATEGORY_DIRECTORY
    ext = (extension or '').lower()
    if not ext and name and '.' in name:
        ext = '.' + name.rsplit('.', 1)[-1].lower()
    if ext in DOCUMENT_EXTENSIONS:
        return SnapshotFileIndex.CATEGORY_DOCUMENT
    if ext in IMAGE_EXTENSIONS:
        return SnapshotFileIndex.CATEGORY_IMAGE
    if ext in VIDEO_EXTENSIONS:
        return SnapshotFileIndex.CATEGORY_VIDEO
    if ext in AUDIO_EXTENSIONS:
        return SnapshotFileIndex.CATEGORY_AUDIO
    if ext in ARCHIVE_EXTENSIONS:
        return SnapshotFileIndex.CATEGORY_ARCHIVE
    if ext in CODE_EXTENSIONS:
        return SnapshotFileIndex.CATEGORY_CODE
    if ext in DATABASE_EXTENSIONS:
        return SnapshotFileIndex.CATEGORY_DATABASE
    return SnapshotFileIndex.CATEGORY_OTHER


def select_gateway(gateway_id=None, tenant=None):
    queryset = Gateway.objects.all()
    if tenant:
        queryset = queryset.filter(tenant=tenant)
    if gateway_id:
        gateway = queryset.get(id=gateway_id)
        if not gateway.is_online():
            raise ValueError('Selected Gateway is offline')
        return gateway

    excluded_statuses = [
        Gateway.GatewayStatus.INACTIVE,
        Gateway.GatewayStatus.ERROR,
        Gateway.GatewayStatus.MAINTENANCE,
    ]
    candidates = queryset.exclude(status__in=excluded_statuses).order_by(
        '-last_heartbeat',
        '-created_at',
    )
    gateway = next((candidate for candidate in candidates if candidate.is_online()), None)
    if gateway is None:
        raise ValueError('No available Gateway found')
    return gateway


def dispatch_snapshot_index(snapshot, user, gateway_id=None, force=False):
    if snapshot.snapshot_status != BackupSnapshot.STATUS_AVAILABLE:
        raise ValueError('Snapshot is not available for indexing')
    repository = snapshot.repository
    password = repository.get_kopia_password()
    if not password:
        raise ValueError('Repository password is not saved')

    gateway = select_gateway(gateway_id, getattr(user, 'tenant', None))
    if force:
        SnapshotFileIndex.objects.filter(snapshot=snapshot).delete()
        SnapshotInsight.objects.filter(snapshot=snapshot).delete()

    object_id = snapshot.kopia_root_object_id or snapshot.manifest_path or ''
    kopia_snapshot_id = snapshot.kopia_snapshot_id or (snapshot.metadata or {}).get('referenced_snapshot_id', '')
    if not kopia_snapshot_id:
        raise ValueError('Snapshot ID is missing. Please resync snapshots before indexing')
    job = SnapshotIndexJob.objects.create(
        snapshot=snapshot,
        gateway=gateway,
        tenant=getattr(user, 'tenant', None),
        user=user,
        status=SnapshotIndexJob.STATUS_PENDING,
    )
    task_id = GatewayService.index_snapshot(
        str(gateway.id),
        job_id=str(job.id),
        snapshot_id=str(snapshot.id),
        kopia_snapshot_id=kopia_snapshot_id,
        object_id=object_id,
        repository_config=build_repository_config(repository),
        password=password,
    )
    job.task_id = task_id
    job.status = SnapshotIndexJob.STATUS_DISPATCHED
    job.save(update_fields=['task_id', 'status', 'updated_at'])
    return job


def build_snapshot_ai_context(snapshot):
    insights = []
    for insight in SnapshotInsight.objects.filter(snapshot=snapshot).exclude(insight_type=SnapshotInsight.TYPE_AI_SUMMARY):
        insights.append({
            'type': insight.insight_type,
            'severity': insight.severity,
            'title': insight.title,
            'summary': insight.summary,
            'evidence': insight.evidence,
            'related_paths': insight.related_paths,
        })
    candidate_files = []
    text_extensions = {'.txt', '.md', '.csv', '.json', '.yaml', '.yml', '.xml', '.html', '.css', '.js', '.ts', '.py', '.go', '.sh', '.log'}
    object_id = snapshot.kopia_root_object_id or snapshot.manifest_path or ''
    for item in SnapshotFileIndex.objects.filter(snapshot=snapshot, is_directory=False).filter(
        extension__in=text_extensions,
    ).order_by('-size')[:20]:
        candidate_files.append({
            'path': item.path,
            'name': item.name,
            'extension': item.extension,
            'category': item.category,
            'size': item.size,
            'modified_time': item.modified_time.isoformat() if item.modified_time else None,
            'snapshot_id': str(snapshot.id),
            'snapshot_name': snapshot.name,
            'object_id': object_id,
            'repository_id': str(snapshot.repository_id),
            'repository_name': snapshot.repository.name if snapshot.repository_id else '',
        })
    return {
        'snapshot': {
            'id': str(snapshot.id),
            'name': snapshot.name,
            'storage_path': snapshot.storage_path,
            'manifest_path': snapshot.manifest_path,
            'created_at': snapshot.created_at.isoformat() if snapshot.created_at else None,
            'total_size': snapshot.total_size,
            'file_count': snapshot.file_count,
            'task_name': snapshot.task.name if snapshot.task_id else '',
            'repository_name': snapshot.repository.name if snapshot.repository_id else '',
        },
        'insights': insights,
        'candidate_files': candidate_files,
        'candidate_count': len(candidate_files),
    }


def dispatch_snapshot_ai_summary(snapshot, user, gateway_id=None, language='zh-CN'):
    if not SnapshotInsight.objects.filter(snapshot=snapshot).exclude(insight_type=SnapshotInsight.TYPE_AI_SUMMARY).exists():
        if SnapshotFileIndex.objects.filter(snapshot=snapshot).exists():
            generate_snapshot_insights(snapshot)
        else:
            raise ValueError('Snapshot must be indexed before AI summary')

    gateway = select_gateway(gateway_id, getattr(user, 'tenant', None))
    job = SnapshotAIJob.objects.create(
        snapshot=snapshot,
        gateway=gateway,
        tenant=getattr(user, 'tenant', None),
        user=user,
        job_type=SnapshotAIJob.TYPE_SUMMARIZE,
        status=SnapshotAIJob.STATUS_PENDING,
        language=language or 'zh-CN',
    )
    provider = select_ai_provider(getattr(user, 'tenant', None))
    task_id = GatewayService.ai_summarize_snapshot(
        str(gateway.id),
        job_id=str(job.id),
        snapshot_id=str(snapshot.id),
        snapshot_context=build_snapshot_ai_context(snapshot),
        language=job.language,
        ai_provider_config=provider.to_gateway_config() if provider else None,
        repository_config=build_repository_config(snapshot.repository),
        repository_password=snapshot.repository.get_kopia_password(),
    )
    if provider:
        job.provider = provider.provider_type
        job.model = provider.default_model
    job.task_id = task_id
    job.status = SnapshotAIJob.STATUS_DISPATCHED
    job.save(update_fields=['task_id', 'status', 'provider', 'model', 'updated_at'])
    return job


def select_ai_provider(tenant=None):
    queryset = AIProvider.objects.filter(is_enabled=True)
    if tenant:
        queryset = queryset.filter(tenant=tenant)
    else:
        queryset = queryset.filter(tenant__isnull=True)
    provider = queryset.filter(is_default=True).first()
    if provider:
        return provider
    return queryset.first()


def update_ai_job_progress(job_id, payload):
    job = SnapshotAIJob.objects.get(id=job_id)
    job.status = payload.get('status') or SnapshotAIJob.STATUS_RUNNING
    job.progress = int(payload.get('progress') or job.progress or 0)
    if job.status == SnapshotAIJob.STATUS_RUNNING and not job.started_at:
        job.started_at = timezone.now()
    job.save(update_fields=['status', 'progress', 'started_at', 'updated_at'])
    return job


def complete_ai_summary_job(job_id, payload):
    job = SnapshotAIJob.objects.select_related('snapshot').get(id=job_id)
    result = payload.get('result') or {}
    job.status = SnapshotAIJob.STATUS_COMPLETED
    job.progress = 100
    job.provider = result.get('provider') or payload.get('provider') or job.provider
    job.model = result.get('model') or payload.get('model') or job.model
    job.result = result
    job.completed_at = timezone.now()
    job.save()

    severity = result.get('risk_level') or result.get('severity') or SnapshotInsight.SEVERITY_INFO
    if severity not in {SnapshotInsight.SEVERITY_INFO, SnapshotInsight.SEVERITY_WARNING, SnapshotInsight.SEVERITY_CRITICAL}:
        severity = SnapshotInsight.SEVERITY_WARNING if severity in {'medium', 'high'} else SnapshotInsight.SEVERITY_INFO
    SnapshotInsight.objects.update_or_create(
        snapshot=job.snapshot,
        insight_type=SnapshotInsight.TYPE_AI_SUMMARY,
        defaults={
            'title': result.get('title') or 'AI summary',
            'summary': result.get('summary') or '',
            'severity': severity,
            'evidence': result,
            'related_paths': result.get('related_paths') or [],
            'recommended_actions': result.get('recommended_actions') or [],
            'generated_by': 'gateway_ai',
        },
    )
    return job


def fail_ai_job(job_id, error):
    job = SnapshotAIJob.objects.get(id=job_id)
    job.status = SnapshotAIJob.STATUS_FAILED
    job.error_message = str(error or 'AI job failed')
    job.completed_at = timezone.now()
    job.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
    return job


def update_index_progress(job_id, payload):
    job = SnapshotIndexJob.objects.get(id=job_id)
    status = payload.get('status') or SnapshotIndexJob.STATUS_RUNNING
    job.status = status
    job.progress = int(payload.get('progress') or job.progress or 0)
    job.total_files = int(payload.get('total_files') or job.total_files or 0)
    job.indexed_files = int(payload.get('indexed_files') or payload.get('processed_files') or job.indexed_files or 0)
    job.total_bytes = int(payload.get('total_bytes') or job.total_bytes or 0)
    job.indexed_bytes = int(payload.get('indexed_bytes') or payload.get('processed_bytes') or job.indexed_bytes or 0)
    job.current_path = payload.get('current_path') or payload.get('current_file') or job.current_path
    if status == SnapshotIndexJob.STATUS_RUNNING and not job.started_at:
        job.started_at = timezone.now()
    job.save()
    return job


def save_index_batch(job_id, files):
    job = SnapshotIndexJob.objects.select_related('snapshot').get(id=job_id)
    records = []
    now = timezone.now()
    for item in files or []:
        path = item.get('path') or ''
        if not path:
            continue
        name = item.get('name') or path.rstrip('/').rsplit('/', 1)[-1]
        extension = (item.get('extension') or '').lower()
        is_directory = bool(item.get('is_directory'))
        category = item.get('category') or categorize_file(name, extension, is_directory)
        modified_time = item.get('modified_time') or None
        if isinstance(modified_time, str):
            modified_time = parse_datetime(modified_time)
        records.append(SnapshotFileIndex(
            snapshot=job.snapshot,
            job=job,
            path=path,
            name=name[:1024],
            extension=extension[:64],
            category=category,
            size=int(item.get('size') or 0),
            modified_time=modified_time,
            is_directory=is_directory,
            depth=int(item.get('depth') or path.strip('/').count('/')),
            content_hash=item.get('content_hash') or '',
            metadata=item.get('metadata') or {},
            indexed_at=now,
        ))
    if records:
        SnapshotFileIndex.objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=['snapshot', 'path'],
            update_fields=[
                'job', 'name', 'extension', 'category', 'size', 'modified_time',
                'is_directory', 'depth', 'content_hash', 'metadata', 'indexed_at',
            ],
        )
    return len(records)


def complete_index_job(job_id, payload=None):
    payload = payload or {}
    job = SnapshotIndexJob.objects.select_related('snapshot').get(id=job_id)
    job.status = SnapshotIndexJob.STATUS_COMPLETED
    job.progress = 100
    job.indexed_files = int(payload.get('indexed_files') or SnapshotFileIndex.objects.filter(snapshot=job.snapshot).count())
    job.indexed_bytes = int(payload.get('indexed_bytes') or SnapshotFileIndex.objects.filter(snapshot=job.snapshot, is_directory=False).aggregate(total=Sum('size'))['total'] or 0)
    job.total_files = int(payload.get('total_files') or job.indexed_files)
    job.total_bytes = int(payload.get('total_bytes') or job.indexed_bytes)
    job.completed_at = timezone.now()
    job.save()
    generate_snapshot_insights(job.snapshot)
    return job


def fail_index_job(job_id, error):
    job = SnapshotIndexJob.objects.get(id=job_id)
    job.status = SnapshotIndexJob.STATUS_FAILED
    job.error_message = str(error or 'Index failed')
    job.completed_at = timezone.now()
    job.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])
    return job


def generate_snapshot_insights(snapshot):
    files = SnapshotFileIndex.objects.filter(snapshot=snapshot, is_directory=False)
    total_files = files.count()
    total_size = files.aggregate(total=Sum('size'))['total'] or 0

    category_rows = list(
        files.values('category')
        .annotate(count=Count('id'), size=Sum('size'))
        .order_by('-size')
    )
    upsert_insight(
        snapshot,
        SnapshotInsight.TYPE_FILE_CATEGORIES,
        'File category profile',
        f'{total_files} files indexed across {len(category_rows)} categories.',
        {'total_files': total_files, 'total_size': total_size, 'categories': category_rows},
    )

    large_files = list(files.order_by('-size').values('path', 'name', 'size', 'category')[:20])
    upsert_insight(
        snapshot,
        SnapshotInsight.TYPE_LARGE_FILES,
        'Large files',
        f'Top {len(large_files)} large files in this snapshot.',
        {'files': large_files},
        related_paths=[item['path'] for item in large_files[:10]],
    )

    duplicate_candidates = []
    grouped = defaultdict(list)
    for row in files.exclude(size=0).values('path', 'name', 'size')[:50000]:
        grouped[(row['name'], row['size'])].append(row)
    for (_name, size), rows in grouped.items():
        if len(rows) > 1:
            duplicate_candidates.append({
                'size': size,
                'count': len(rows),
                'paths': [row['path'] for row in rows[:20]],
            })
    duplicate_candidates.sort(key=lambda item: item['size'] * item['count'], reverse=True)
    upsert_insight(
        snapshot,
        SnapshotInsight.TYPE_DUPLICATES,
        'Duplicate candidates',
        f'{len(duplicate_candidates)} duplicate candidate groups found by name and size.',
        {'groups': duplicate_candidates[:50]},
        severity=SnapshotInsight.SEVERITY_WARNING if duplicate_candidates else SnapshotInsight.SEVERITY_INFO,
        related_paths=[path for group in duplicate_candidates[:5] for path in group['paths'][:3]],
    )

    cold_cutoff = timezone.now() - timedelta(days=90)
    cold = files.filter(modified_time__lt=cold_cutoff)
    cold_count = cold.count()
    cold_size = cold.aggregate(total=Sum('size'))['total'] or 0
    upsert_insight(
        snapshot,
        SnapshotInsight.TYPE_COLD_DATA,
        'Cold data',
        f'{cold_count} files have not changed for more than 90 days.',
        {'days': 90, 'count': cold_count, 'size': cold_size},
        severity=SnapshotInsight.SEVERITY_WARNING if cold_size and total_size and cold_size / total_size > 0.5 else SnapshotInsight.SEVERITY_INFO,
    )

    previous = BackupSnapshot.objects.filter(
        task=snapshot.task,
        created_at__lt=snapshot.created_at,
    ).order_by('-created_at').first()
    growth = {'previous_snapshot_id': str(previous.id) if previous else None}
    if previous:
        prev_files = SnapshotFileIndex.objects.filter(snapshot=previous, is_directory=False)
        prev_size = prev_files.aggregate(total=Sum('size'))['total'] or 0
        prev_count = prev_files.count()
        growth.update({
            'current_files': total_files,
            'previous_files': prev_count,
            'file_delta': total_files - prev_count,
            'current_size': total_size,
            'previous_size': prev_size,
            'size_delta': total_size - prev_size,
        })
    upsert_insight(
        snapshot,
        SnapshotInsight.TYPE_GROWTH,
        'Growth trend',
        'Growth trend compared with the previous indexed snapshot.' if previous else 'No previous snapshot is available for comparison.',
        growth,
    )


def upsert_insight(snapshot, insight_type, title, summary, evidence, severity=SnapshotInsight.SEVERITY_INFO, related_paths=None):
    SnapshotInsight.objects.update_or_create(
        snapshot=snapshot,
        insight_type=insight_type,
        defaults={
            'title': title,
            'summary': summary,
            'severity': severity,
            'evidence': evidence,
            'related_paths': related_paths or [],
            'recommended_actions': [],
            'generated_by': 'rule',
        },
    )
