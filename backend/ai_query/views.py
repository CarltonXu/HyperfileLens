"""
HyperFileLens Backend - AI Query Views
"""

import asyncio
import json
import queue
import threading
import time
from datetime import timedelta
from django.http import StreamingHttpResponse
from django.db.models import Count, Q, Sum
from django.utils import timezone
import requests
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import AIProvider, AIQuery
from .serializers import AIProviderSerializer, AIQuerySerializer, AIQueryCreateSerializer
from .provider_client import AIProviderClient, sse_comment, sse_event
from .services import (
    build_ai_query_messages,
    dispatch_ai_query,
    local_metadata_answer,
    prepare_query_context,
    run_ai_query_direct,
)


def _chat_completions_url(base_url):
    normalized = str(base_url or '').rstrip('/')
    if normalized.endswith('/chat/completions'):
        return normalized
    if normalized.endswith('/v1'):
        return f'{normalized}/chat/completions'
    return f'{normalized}/v1/chat/completions'


def _sse(data):
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _sse_comment(text=''):
    return f": {text}\n\n"


def _chunk_text(text, size=12):
    for index in range(0, len(text), size):
        yield text[index:index + size]


def _streaming_response(iterator):
    response = StreamingHttpResponse(iterator, content_type='text/event-stream; charset=utf-8')
    response['Cache-Control'] = 'no-cache, no-transform'
    response['X-Accel-Buffering'] = 'no'
    return response


def _format_bytes(value):
    size = float(value or 0)
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{size:.0f} {units[index]}" if index == 0 else f"{size:.1f} {units[index]}"


def _tenant_snapshot_filter(user):
    from backup_tasks.models import BackupSnapshot

    queryset = BackupSnapshot.objects.select_related('task', 'repository', 'task__tenant')
    if user.is_superuser:
        return queryset
    if user.tenant:
        return queryset.filter(task__tenant=user.tenant)
    return queryset.filter(task__user=user)


def _request_scope(request):
    data = getattr(request, 'data', {}) or {}
    scope_type = request.query_params.get('scope_type') or data.get('scope_type') or ''
    scope_id = request.query_params.get('scope_id') or data.get('scope_id') or ''
    scope_type = str(scope_type or '').strip()
    scope_id = str(scope_id or '').strip()

    legacy_snapshot = request.query_params.get('snapshot_id') or data.get('snapshot_id')
    legacy_repository = request.query_params.get('repository_id') or data.get('repository_id')
    legacy_task = request.query_params.get('task_id') or data.get('task_id')

    if not scope_type:
        if legacy_snapshot:
            return 'snapshot', str(legacy_snapshot)
        if legacy_repository:
            return 'repository', str(legacy_repository)
        if legacy_task:
            return 'backup_task', str(legacy_task)
        return 'tenant', ''
    return scope_type, scope_id


def _apply_snapshot_scope(queryset, scope_type, scope_id):
    if scope_type == 'snapshot' and scope_id:
        return queryset.filter(id=scope_id)
    if scope_type == 'repository' and scope_id:
        return queryset.filter(repository_id=scope_id)
    if scope_type in {'backup_task', 'task'} and scope_id:
        return queryset.filter(task_id=scope_id)
    return queryset


def _scope_filter_kwargs(request):
    scope_type, scope_id = _request_scope(request)
    return {
        'scope_type': scope_type,
        'scope_id': scope_id,
        'snapshot_id': scope_id if scope_type == 'snapshot' and scope_id else None,
        'repository_id': scope_id if scope_type == 'repository' and scope_id else None,
        'task_id': scope_id if scope_type in {'backup_task', 'task'} and scope_id else None,
    }


def _indexed_files_queryset(request):
    from insights.models import SnapshotFileIndex

    scope_type, scope_id = _request_scope(request)
    snapshots = _apply_snapshot_scope(_tenant_snapshot_filter(request.user), scope_type, scope_id)
    snapshot_ids = snapshots.values_list('id', flat=True)
    queryset = SnapshotFileIndex.objects.select_related('snapshot', 'snapshot__task', 'snapshot__repository').filter(
        snapshot_id__in=snapshot_ids,
        is_directory=False,
    )
    repository_id = request.query_params.get('repository_id')
    if repository_id:
        queryset = queryset.filter(snapshot__repository_id=repository_id)
    snapshot_id = request.query_params.get('snapshot_id')
    if snapshot_id:
        queryset = queryset.filter(snapshot_id=snapshot_id)
    task_id = request.query_params.get('task_id')
    if task_id:
        queryset = queryset.filter(snapshot__task_id=task_id)
    return queryset


def _accessible_repository_queryset(user):
    from repository.models import Repository

    queryset = Repository.objects.select_related('tenant')
    if user.is_superuser:
        return queryset
    if user.tenant:
        return queryset.filter(tenant=user.tenant)
    return queryset.filter(user=user)


def _accessible_backup_task_queryset(user):
    from backup_tasks.models import BackupTask

    queryset = BackupTask.objects.select_related('tenant', 'target_repository')
    if user.is_superuser:
        return queryset
    if user.tenant:
        return queryset.filter(tenant=user.tenant)
    return queryset.filter(user=user)


def _insights_queryset(request):
    from insights.models import SnapshotInsight

    scope_type, scope_id = _request_scope(request)
    snapshots = _apply_snapshot_scope(_tenant_snapshot_filter(request.user), scope_type, scope_id)
    snapshot_ids = snapshots.values_list('id', flat=True)
    queryset = SnapshotInsight.objects.select_related('snapshot', 'snapshot__task', 'snapshot__repository').filter(
        snapshot_id__in=snapshot_ids,
    )
    repository_id = request.query_params.get('repository_id')
    if repository_id:
        queryset = queryset.filter(snapshot__repository_id=repository_id)
    snapshot_id = request.query_params.get('snapshot_id')
    if snapshot_id:
        queryset = queryset.filter(snapshot_id=snapshot_id)
    task_id = request.query_params.get('task_id')
    if task_id:
        queryset = queryset.filter(snapshot__task_id=task_id)
    return queryset


class AIQueryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing AI queries."""
    queryset = AIQuery.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AIQueryCreateSerializer
        return AIQuerySerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = AIQuery.objects.select_related('user', 'tenant')
        
        # Superuser can see all AI queries
        if user.is_superuser:
            return queryset
        # Filter by tenant for tenant users
        if user.tenant:
            return queryset.filter(tenant=user.tenant)
        # Users without tenant can only see their own queries
        return queryset.filter(user=user)
    
    def create(self, request, *args, **kwargs):
        """Create a new AI query.

        Prefer Gateway execution when available because it can read backup
        content samples. Fall back to direct control-plane metadata RAG so the
        AI Insights page remains usable without an online Gateway.
        """
        payload = request.data.copy()
        if not payload.get('query_text') and payload.get('query'):
            payload['query_text'] = payload.get('query')
        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        scope = _scope_filter_kwargs(request)
        snapshot_id = data.pop('snapshot_id', None)
        repository_id = data.pop('repository_id', None)
        gateway_id = data.pop('gateway_id', None)
        task_id = scope.get('task_id')
        snapshot_id = snapshot_id or scope.get('snapshot_id')
        repository_id = repository_id or scope.get('repository_id')
        
        query = AIQuery.objects.create(
            user=request.user,
            tenant=getattr(request.user, 'tenant', None),
            **data
        )
        use_gateway = request.data.get('execution') != 'direct' and not task_id
        if use_gateway:
            try:
                query = dispatch_ai_query(
                    query,
                    gateway_id=gateway_id,
                    snapshot_id=snapshot_id,
                    repository_id=repository_id,
                )
            except Exception:
                query = run_ai_query_direct(
                    query,
                    snapshot_id=snapshot_id,
                    repository_id=repository_id,
                    task_id=task_id,
                    language=request.data.get('language') or 'zh-CN',
                )
        else:
            query = run_ai_query_direct(
                query,
                snapshot_id=snapshot_id,
                repository_id=repository_id,
                task_id=task_id,
                language=request.data.get('language') or 'zh-CN',
            )
        
        return Response(
            AIQuerySerializer(query).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'], url_path='stream')
    def stream(self, request):
        """Stream an AI Insights answer from the default provider and persist it."""
        payload = request.data.copy()
        if not payload.get('query_text') and payload.get('query'):
            payload['query_text'] = payload.get('query')
        serializer = AIQueryCreateSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        scope = _scope_filter_kwargs(request)
        snapshot_id = data.pop('snapshot_id', None)
        repository_id = data.pop('repository_id', None)
        data.pop('gateway_id', None)
        task_id = scope.get('task_id')
        snapshot_id = snapshot_id or scope.get('snapshot_id')
        repository_id = repository_id or scope.get('repository_id')
        query = AIQuery.objects.create(
            user=request.user,
            tenant=getattr(request.user, 'tenant', None),
            status=AIQuery.STATUS_PROCESSING,
            **data,
        )

        def iterator():
            answer_parts = []
            result = {}
            model = 'metadata-query'
            try:
                yield sse_comment('stream-start ' + (' ' * 2048))
                context = prepare_query_context(
                    query,
                    snapshot_id=snapshot_id,
                    repository_id=repository_id,
                    task_id=task_id,
                )
                provider = __import__('insights.services', fromlist=['select_ai_provider']).select_ai_provider(
                    getattr(request.user, 'tenant', None)
                )
                client = AIProviderClient(provider)
                yield sse_event({
                    'type': 'query',
                    'query_id': str(query.id),
                    'candidate_count': len(context.get('candidate_files') or []),
                    'scope_type': scope.get('scope_type'),
                    'scope_id': scope.get('scope_id'),
                })
                if client.is_external():
                    messages = build_ai_query_messages(
                        query,
                        context,
                        language=request.data.get('language') or 'zh-CN',
                    )
                    for event in client.stream_chat(messages, temperature=0.1):
                        if event.get('type') == 'delta':
                            answer_parts.append(event.get('content') or '')
                        if event.get('model'):
                            model = event.get('model')
                        yield sse_event(event)
                    answer = ''.join(answer_parts)
                    result = {
                        'answer': answer,
                        'summary': answer,
                        'sources': [
                            {
                                'path': item.get('path'),
                                'snapshot_name': item.get('snapshot_name'),
                                'repository_name': item.get('repository_name'),
                                'reason': 'Candidate context used for AI answer',
                            }
                            for item in (context.get('candidate_files') or [])[:12]
                        ],
                        'candidate_count': len(context.get('candidate_files') or []),
                        'provider': client.provider_type,
                        'model': model,
                        'query_id': str(query.id),
                    }
                else:
                    result = local_metadata_answer(query, context)
                    model = result.get('model') or model
                    answer = result.get('answer') or ''
                    for piece in _chunk_text(answer, size=16):
                        answer_parts.append(piece)
                        yield sse_event({'type': 'delta', 'content': piece})

                query.mark_completed(result=result, model_used=model)
                yield sse_event({'type': 'done', 'query_id': str(query.id), 'answer': result.get('answer') or ''.join(answer_parts)})
            except Exception as exc:
                query.mark_failed(str(exc))
                yield sse_event({'type': 'error', 'query_id': str(query.id), 'error': str(exc)})

        return _streaming_response(iterator())
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed query."""
        query = self.get_object()
        
        if query.status not in ['failed']:
            return Response(
                {'error': 'Only failed queries can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        query.status = 'pending'
        query.error_message = ''
        query.save(update_fields=['status', 'error_message'])
        try:
            dispatch_ai_query(query)
        except Exception as exc:
            query.mark_failed(str(exc))
            return Response(AIQuerySerializer(query).data, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'message': 'Query retry started'})
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get user's query history."""
        queries = self.get_queryset()[:20]
        serializer = AIQuerySerializer(queries, many=True)
        return Response(serializer.data)


class AIProviderViewSet(viewsets.ModelViewSet):
    """ViewSet for platform-side AI provider configuration."""

    serializer_class = AIProviderSerializer
    permission_classes = [IsAuthenticated]
    queryset = AIProvider.objects.all()

    def get_queryset(self):
        user = self.request.user
        queryset = AIProvider.objects.all()
        if user.is_superuser:
            return queryset
        if user.tenant:
            return queryset.filter(tenant=user.tenant)
        return queryset.filter(created_by=user, tenant__isnull=True)

    def perform_create(self, serializer):
        provider = serializer.save(
            tenant=getattr(self.request.user, 'tenant', None),
            created_by=self.request.user,
        )
        if not AIProvider.objects.filter(tenant=provider.tenant, is_default=True).exclude(id=provider.id).exists():
            provider.is_default = True
            provider.save(update_fields=['is_default', 'updated_at'])

    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, pk=None):
        provider = self.get_object()
        provider.is_default = True
        provider.save(update_fields=['is_default', 'updated_at'])
        return Response(AIProviderSerializer(provider).data)

    @action(detail=False, methods=['get'], url_path='default')
    def default(self, request):
        provider = self.get_queryset().filter(is_default=True).first()
        if not provider:
            provider = self.get_queryset().first()
        if not provider:
            return Response({'detail': 'No AI provider configured'}, status=status.HTTP_404_NOT_FOUND)
        return Response(AIProviderSerializer(provider).data)

    @action(detail=True, methods=['post'], url_path='test-chat')
    def test_chat(self, request, pk=None):
        provider = self.get_object()
        prompt = (request.data.get('message') or 'Hello').strip()
        stream = request.data.get('stream') is True
        if provider.provider_type == AIProvider.PROVIDER_LOCAL:
            answer = f'Local fallback is enabled. Test prompt: {prompt}'
            if stream:
                async def local_stream():
                    yield _sse({
                        'type': 'meta',
                        'provider': provider.provider_type,
                        'model': provider.default_model or 'rule-summary',
                        'url': '',
                        'latency_ms': 0,
                    })
                    yield _sse_comment('stream-start ' + (' ' * 2048))
                    for piece in _chunk_text(answer):
                        yield _sse({'type': 'delta', 'content': piece})
                        await asyncio.sleep(0.012)
                    yield _sse({'type': 'done'})

                return _streaming_response(local_stream())
            return Response({
                'success': True,
                'provider': provider.provider_type,
                'model': provider.default_model or 'rule-summary',
                'answer': answer,
                'url': '',
                'latency_ms': 0,
            })

        api_key = provider.get_decrypted_api_key()
        if not api_key:
            return Response({'success': False, 'error': 'API key is required.'}, status=status.HTTP_400_BAD_REQUEST)

        url = _chat_completions_url(provider.base_url)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        }
        extra_headers = (provider.config or {}).get('headers') if isinstance(provider.config, dict) else None
        if isinstance(extra_headers, dict):
            headers.update({str(key): str(value) for key, value in extra_headers.items()})

        payload = {
            'stream': stream,
            'model': provider.default_model,
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a helpful AI assistant. Answer the user naturally and concisely.',
                },
                {'role': 'user', 'content': prompt},
            ],
            'max_tokens': int(request.data.get('max_tokens') or 4096),
            'temperature': 0.2,
        }
        started = time.monotonic()
        timeout = max(5, min(int(provider.timeout_seconds or 60), 120))
        if stream:
            async def provider_stream():
                events = queue.Queue()
                sentinel = object()

                def enqueue(data):
                    events.put(_sse(data))

                def enqueue_comment(text=''):
                    events.put(_sse_comment(text))

                def worker():
                    answer = []
                    model = provider.default_model
                    try:
                        with requests.post(
                            url,
                            headers=headers,
                            json=payload,
                            stream=True,
                            timeout=timeout,
                        ) as response:
                            latency_ms = int((time.monotonic() - started) * 1000)
                            if response.status_code >= 400:
                                enqueue({
                                    'type': 'error',
                                    'error': response.text[:1000],
                                    'url': url,
                                    'status_code': response.status_code,
                                })
                                return

                            enqueue({
                                'type': 'meta',
                                'provider': provider.provider_type,
                                'model': model,
                                'url': url,
                                'latency_ms': latency_ms,
                            })
                            for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                                if not line:
                                    continue
                                if line.startswith('data:'):
                                    line = line[5:].strip()
                                if line == '[DONE]':
                                    break
                                try:
                                    chunk = json.loads(line)
                                except json.JSONDecodeError:
                                    continue
                                model = chunk.get('model') or model
                                choices = chunk.get('choices') or []
                                if not choices:
                                    continue
                                delta = choices[0].get('delta') or {}
                                message = choices[0].get('message') or {}
                                content = delta.get('content') or message.get('content') or choices[0].get('text') or ''
                                if content:
                                    answer.append(content)
                                    if message.get('content') or choices[0].get('text'):
                                        for piece in _chunk_text(content):
                                            enqueue({'type': 'delta', 'content': piece})
                                    else:
                                        enqueue({'type': 'delta', 'content': content})
                            enqueue({
                                'type': 'done',
                                'model': model,
                                'answer': ''.join(answer),
                            })
                    except Exception as exc:
                        enqueue({'type': 'error', 'error': str(exc), 'url': url})
                    finally:
                        events.put(sentinel)

                yield _sse_comment('stream-start ' + (' ' * 2048))
                threading.Thread(target=worker, daemon=True).start()
                while True:
                    event = await asyncio.to_thread(events.get)
                    if event is sentinel:
                        break
                    yield event

            return _streaming_response(provider_stream())

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            latency_ms = int((time.monotonic() - started) * 1000)
            response.raise_for_status()
            data = response.json()
            answer = ''
            choices = data.get('choices') or []
            if choices:
                message = choices[0].get('message') or {}
                answer = message.get('content') or choices[0].get('text') or ''
            return Response({
                'success': True,
                'provider': provider.provider_type,
                'model': data.get('model') or provider.default_model,
                'answer': answer,
                'url': url,
                'latency_ms': latency_ms,
                'usage': data.get('usage') or {},
            })
        except requests.HTTPError as exc:
            body = exc.response.text[:1000] if exc.response is not None else str(exc)
            return Response({
                'success': False,
                'error': body,
                'url': url,
                'status_code': exc.response.status_code if exc.response is not None else None,
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'success': False, 'error': str(exc), 'url': url}, status=status.HTTP_400_BAD_REQUEST)


# ============== Gateway Proxy Views ==============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gateway_mount_status(request):
    """Return Gateway availability for the AI Insights page."""
    from insights.services import select_gateway
    try:
        gateway = select_gateway(tenant=getattr(request.user, 'tenant', None))
        return Response({'mounted': False, 'gateway_id': str(gateway.id), 'gateway_name': gateway.name, 'online': True})
    except Exception as exc:
        return Response({'error': str(exc), 'mounted': False, 'online': False}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gateway_index_status(request):
    """Return indexed snapshot/file counts."""
    from insights.models import SnapshotFileIndex, SnapshotIndexJob
    scope = _scope_filter_kwargs(request)
    scoped_snapshots = _apply_snapshot_scope(
        _tenant_snapshot_filter(request.user),
        scope.get('scope_type'),
        scope.get('scope_id'),
    )
    snapshot_ids = scoped_snapshots.values('id')

    return Response({
        'indexed_files': SnapshotFileIndex.objects.filter(snapshot_id__in=snapshot_ids).count(),
        'running_jobs': SnapshotIndexJob.objects.filter(snapshot_id__in=snapshot_ids, status__in=['pending', 'dispatched', 'running']).count(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def gateway_ai_query(request):
    """Compatibility endpoint that now uses the WebSocket Gateway task model."""
    payload = {
        'query_text': request.data.get('query') or request.data.get('query_text') or '',
        'query_type': request.data.get('query_type') or AIQuery.TYPE_SEARCH,
        'target_paths': request.data.get('target_paths') or [],
        'file_types': request.data.get('file_types') or [],
        'repository_id': request.data.get('repository_id'),
        'snapshot_id': request.data.get('snapshot_id'),
        'gateway_id': request.data.get('gateway_id'),
    }
    serializer = AIQueryCreateSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)
    snapshot_id = data.pop('snapshot_id', None)
    repository_id = data.pop('repository_id', None)
    gateway_id = data.pop('gateway_id', None)
    query = AIQuery.objects.create(user=request.user, tenant=getattr(request.user, 'tenant', None), **data)
    try:
        query = dispatch_ai_query(query, gateway_id=gateway_id, snapshot_id=snapshot_id, repository_id=repository_id)
    except Exception as exc:
        query.mark_failed(str(exc))
        return Response(AIQuerySerializer(query).data, status=status.HTTP_400_BAD_REQUEST)
    return Response(AIQuerySerializer(query).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def gateway_rebuild_index(request):
    return Response({'error': 'Use snapshot index endpoint for rebuild operations.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gateway_list_files(request):
    """List indexed files from the platform index."""
    limit = min(int(request.query_params.get('limit', 200)), 1000)
    path = (request.query_params.get('path') or '').strip('/')
    queryset = _indexed_files_queryset(request)
    if path:
        queryset = queryset.filter(path__startswith=path)
    data = [
        {
            'id': str(item.id),
            'path': item.path,
            'name': item.name,
            'size': item.size,
            'category': item.category,
            'extension': item.extension,
            'snapshot_id': str(item.snapshot_id),
            'snapshot_name': item.snapshot.name,
            'repository_id': str(item.snapshot.repository_id),
            'repository_name': item.snapshot.repository.name if item.snapshot.repository_id else '',
        }
        for item in queryset.order_by('path')[:limit]
    ]
    return Response({'results': data, 'count': len(data)})


# ============== AI Insights Feature APIs ==============

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scope_options(request):
    """Return tenant-safe AI Insights analysis scopes."""
    from insights.models import SnapshotFileIndex

    scope_type = (request.query_params.get('scope_type') or 'repository').strip()
    search = (request.query_params.get('search') or '').strip()
    try:
        limit = int(request.query_params.get('limit') or 100)
    except (TypeError, ValueError):
        limit = 100
    limit = min(max(limit, 1), 200)

    accessible_snapshots = _tenant_snapshot_filter(request.user)
    repository_id = (request.query_params.get('repository_id') or '').strip()
    task_id = (request.query_params.get('task_id') or '').strip()
    if repository_id:
        accessible_snapshots = accessible_snapshots.filter(repository_id=repository_id)
    if task_id:
        accessible_snapshots = accessible_snapshots.filter(task_id=task_id)

    files = SnapshotFileIndex.objects.filter(
        snapshot_id__in=accessible_snapshots.values('id'),
        is_directory=False,
    )

    def grouped_stats(group_field):
        return {
            str(row[group_field]): {
                'indexed_files': row['indexed_files'] or 0,
                'indexed_snapshots': row['indexed_snapshots'] or 0,
                'total_size': row['total_size'] or 0,
            }
            for row in files.values(group_field).annotate(
                indexed_files=Count('id'),
                indexed_snapshots=Count('snapshot_id', distinct=True),
                total_size=Sum('size'),
            )
            if row[group_field]
        }

    if scope_type == 'tenant':
        stats = files.aggregate(
            indexed_files=Count('id'),
            indexed_snapshots=Count('snapshot_id', distinct=True),
            total_size=Sum('size'),
        )
        return Response({
            'scope_type': 'tenant',
            'results': [{
                'id': '',
                'name': getattr(getattr(request.user, 'tenant', None), 'name', '') or 'Current tenant',
                'description': 'All indexed snapshots available to the current user.',
                'indexed_files': stats['indexed_files'] or 0,
                'indexed_snapshots': stats['indexed_snapshots'] or 0,
                'total_size': stats['total_size'] or 0,
            }],
        })

    if scope_type == 'repository':
        queryset = _accessible_repository_queryset(request.user)
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        stats_by_id = grouped_stats('snapshot__repository_id')
        results = []
        for repository in queryset.order_by('-updated_at')[:limit]:
            stats = stats_by_id.get(str(repository.id), {})
            results.append({
                'id': str(repository.id),
                'name': repository.name,
                'description': repository.description,
                'status': repository.status,
                'type': repository.repo_type,
                'indexed_files': stats.get('indexed_files', 0),
                'indexed_snapshots': stats.get('indexed_snapshots', 0),
                'total_size': stats.get('total_size', 0),
            })
        return Response({'scope_type': scope_type, 'results': results})

    if scope_type in {'backup_task', 'task'}:
        queryset = _accessible_backup_task_queryset(request.user)
        if repository_id:
            queryset = queryset.filter(target_repository_id=repository_id)
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        stats_by_id = grouped_stats('snapshot__task_id')
        results = []
        for task in queryset.order_by('-updated_at')[:limit]:
            stats = stats_by_id.get(str(task.id), {})
            results.append({
                'id': str(task.id),
                'name': task.name,
                'description': task.description,
                'status': task.status,
                'repository_id': str(task.target_repository_id),
                'repository_name': task.target_repository.name if task.target_repository_id else '',
                'indexed_files': stats.get('indexed_files', 0),
                'indexed_snapshots': stats.get('indexed_snapshots', 0),
                'total_size': stats.get('total_size', 0),
            })
        return Response({'scope_type': 'backup_task', 'results': results})

    if scope_type == 'snapshot':
        queryset = accessible_snapshots.select_related('task', 'repository')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(task__name__icontains=search)
                | Q(repository__name__icontains=search)
            )
        stats_by_id = grouped_stats('snapshot_id')
        results = []
        for snapshot in queryset.order_by('-created_at')[:limit]:
            stats = stats_by_id.get(str(snapshot.id), {})
            results.append({
                'id': str(snapshot.id),
                'name': snapshot.name,
                'description': snapshot.description,
                'status': snapshot.snapshot_status,
                'repository_id': str(snapshot.repository_id),
                'repository_name': snapshot.repository.name if snapshot.repository_id else '',
                'task_id': str(snapshot.task_id),
                'task_name': snapshot.task.name if snapshot.task_id else '',
                'created_at': snapshot.created_at.isoformat() if snapshot.created_at else None,
                'indexed_files': stats.get('indexed_files', 0),
                'indexed_snapshots': 1 if stats.get('indexed_files', 0) else 0,
                'total_size': stats.get('total_size', 0),
            })
        return Response({'scope_type': scope_type, 'results': results})

    return Response({'error': 'Invalid scope_type'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def insights_overview(request):
    """
    AI Insights Overview - 洞察看板
    Returns comprehensive statistics about the backup data.
    """
    scope = _scope_filter_kwargs(request)
    files = _indexed_files_queryset(request)
    total_files = files.count()
    total_size_bytes = files.aggregate(total=Sum('size'))['total'] or 0
    category_rows = list(
        files.values('category')
        .annotate(count=Count('id'), size=Sum('size'))
        .order_by('-size')
    )
    category_names = {
        'document': ('Documents', '文档'),
        'image': ('Images', '图片'),
        'video': ('Videos', '视频'),
        'audio': ('Audio', '音频'),
        'archive': ('Archives', '压缩包'),
        'code': ('Code', '代码'),
        'database': ('Databases', '数据库'),
        'other': ('Others', '其他'),
    }
    file_categories = []
    for row in category_rows:
        name, name_zh = category_names.get(row['category'], (row['category'].title(), row['category']))
        size = row['size'] or 0
        file_categories.append({
            'name': name,
            'name_zh': name_zh,
            'percentage': round((size / total_size_bytes) * 100, 1) if total_size_bytes else 0,
            'size': _format_bytes(size),
            'size_bytes': size,
            'count': row['count'],
        })

    insights = _insights_queryset(request)
    from insights.services import build_sensitive_findings
    sensitive_findings = build_sensitive_findings(files)
    sensitive_files = len({
        file_item.get('path')
        for finding in sensitive_findings
        for file_item in finding.get('files', [])
        if file_item.get('path')
    })
    high_risk_count = sum(finding['count'] for finding in sensitive_findings if finding.get('severity') == 'high')
    duplicate_groups = 0
    duplicate_size = 0
    for insight in insights.filter(insight_type='duplicates'):
        for group in (insight.evidence or {}).get('groups', []):
            duplicate_groups += 1
            duplicate_size += int(group.get('size') or 0) * max(int(group.get('count') or 0) - 1, 0)
    cold_size = 0
    cold_count = 0
    for insight in insights.filter(insight_type='cold_data'):
        evidence = insight.evidence or {}
        cold_size += int(evidence.get('size') or 0)
        cold_count += int(evidence.get('count') or 0)
    growth = insights.filter(insight_type='growth').order_by('-updated_at').first()
    growth_evidence = growth.evidence if growth else {}

    return Response({
        'total_files': total_files,
        'total_size': _format_bytes(total_size_bytes),
        'total_size_bytes': total_size_bytes,
        'last_sync': timezone.now().isoformat(),
        'file_categories': file_categories,
        'risk_summary': {
            'sensitive_files': sensitive_files,
            'ransomware_risk': 'review_required' if high_risk_count else 'safe',
            'permission_issues': high_risk_count,
            'findings': sensitive_findings[:5],
        },
        'optimization_suggestions': {
            'duplicate_files': {'size': _format_bytes(duplicate_size), 'size_bytes': duplicate_size, 'count': duplicate_groups},
            'cold_data': {'size': _format_bytes(cold_size), 'size_bytes': cold_size, 'count': cold_count},
            'fastest_growing': {
                'path': growth_evidence.get('previous_snapshot_id') or '-',
                'growth_rate': growth_evidence.get('size_delta', 0),
                'period': 'snapshot'
            }
        },
        'indexed_snapshots': scoped_snapshots.filter(index_jobs__status='completed').distinct().count(),
        'scope': {
            'type': scope.get('scope_type') or 'tenant',
            'id': scope.get('scope_id') or '',
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sensitive_data_scan(request):
    """
    Sensitive Data Scanner - 敏感数据扫描
    Scans for PII, sensitive information, compliance issues.
    """
    from insights.services import build_sensitive_findings
    files = _indexed_files_queryset(request)
    findings = build_sensitive_findings(files)
    high = sum(item['count'] for item in findings if item['severity'] == 'high')
    medium = sum(item['count'] for item in findings if item['severity'] == 'medium')
    return Response({
        'scan_status': 'completed',
        'last_scan': timezone.now().isoformat(),
        'findings': findings,
        'summary': {
            'high': high,
            'medium': medium,
            'low': sum(item['count'] for item in findings if item['severity'] == 'low'),
            'total_findings': sum(item['count'] for item in findings),
        },
        'compliance_status': {
            'gdpr': {'status': 'review_required' if high or medium else 'pass', 'issues': high + medium},
            'pci_dss': {'status': 'review_required' if high else 'pass', 'issues': high},
            'hipaa': {'status': 'not_applicable', 'issues': 0},
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def content_profile(request):
    """
    Content Profiling - 内容分类画像
    Auto-categorization and tagging of files.
    """
    files = _indexed_files_queryset(request)
    labels = {
        'document': ('Documents', '文档'),
        'image': ('Images', '图片'),
        'video': ('Videos', '视频'),
        'audio': ('Audio', '音频'),
        'archive': ('Archives', '压缩包'),
        'code': ('Code', '代码'),
        'database': ('Databases', '数据库'),
        'other': ('Others', '其他'),
    }
    categories = []
    for row in files.values('category').annotate(count=Count('id'), size=Sum('size')).order_by('-size'):
        examples = list(
            files.filter(category=row['category'])
            .order_by('-size')
            .values_list('name', flat=True)[:2]
        )
        name, name_zh = labels.get(row['category'], (row['category'].title(), row['category']))
        categories.append({
            'name': name,
            'name_zh': name_zh,
            'count': row['count'],
            'size': _format_bytes(row['size'] or 0),
            'size_bytes': row['size'] or 0,
            'tags': [row['category']],
            'examples': examples,
        })
    auto_tags = [
        {'tag': row['extension'] or 'no-extension', 'tag_zh': row['extension'] or '无扩展名', 'count': row['count']}
        for row in files.values('extension').annotate(count=Count('id')).order_by('-count')[:20]
    ]
    return Response({
        'categories': categories,
        'auto_tags': auto_tags,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def data_heatmap(request):
    """
    Data Heatmap - 冷热数据分析
    Identifies hot/warm/cold data based on access patterns.
    """
    days = int(request.query_params.get('days', 90))
    files = _indexed_files_queryset(request)
    now = timezone.now()
    hot_cutoff = now - timedelta(days=30)
    warm_cutoff = now - timedelta(days=days)
    hot = files.filter(modified_time__gte=hot_cutoff)
    warm = files.filter(modified_time__lt=hot_cutoff, modified_time__gte=warm_cutoff)
    cold = files.filter(Q(modified_time__lt=warm_cutoff) | Q(modified_time__isnull=True))
    total_size = files.aggregate(total=Sum('size'))['total'] or 0

    def heat_row(queryset, category, category_zh, description):
        size = queryset.aggregate(total=Sum('size'))['total'] or 0
        return {
            'category': category,
            'category_zh': category_zh,
            'description': description,
            'size': _format_bytes(size),
            'size_bytes': size,
            'percentage': round((size / total_size) * 100, 1) if total_size else 0,
            'file_count': queryset.count(),
        }

    cold_size = cold.aggregate(total=Sum('size'))['total'] or 0
    cold_count = cold.count()
    return Response({
        'period_days': days,
        'heatmap': [
            heat_row(hot, 'hot', '热数据', 'Modified in the last 30 days'),
            heat_row(warm, 'warm', '温数据', f'Modified in the last {days} days'),
            heat_row(cold, 'cold', '冷数据', f'Not modified for more than {days} days or missing mtime'),
        ],
        'zombie_data': {
            'description': f'超过{days}天未修改的数据',
            'size': _format_bytes(cold_size),
            'size_bytes': cold_size,
            'file_count': cold_count,
            'potential_savings': '建议评估是否归档到低成本存储'
        },
        'trend': {
            'hot_growth': None,
            'cold_growth': None,
            'recommendation': '基于已索引快照的修改时间统计'
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def redundancy_analysis(request):
    """
    Redundancy Analysis - 冗余内容识别
    Identifies duplicate and similar files.
    """
    duplicate_groups = []
    total_duplicates = 0
    duplicate_size = 0
    for insight in _insights_queryset(request).filter(insight_type='duplicates').order_by('-updated_at'):
        for group in (insight.evidence or {}).get('groups', []):
            paths = group.get('paths') or []
            count = int(group.get('count') or len(paths))
            size = int(group.get('size') or 0)
            total_duplicates += max(count - 1, 0)
            duplicate_size += size * max(count - 1, 0)
            duplicate_groups.append({
                'file_name': paths[0].rsplit('/', 1)[-1] if paths else 'duplicate candidate',
                'count': count,
                'size': _format_bytes(size),
                'size_bytes': size,
                'locations': paths,
            })
    duplicate_groups = sorted(
        duplicate_groups,
        key=lambda item: item.get('size_bytes', 0) * item.get('count', 0),
        reverse=True,
    )[:100]
    return Response({
        'total_duplicates': total_duplicates,
        'duplicate_size': _format_bytes(duplicate_size),
        'duplicate_size_bytes': duplicate_size,
        'potential_savings': _format_bytes(duplicate_size),
        'duplicate_groups': duplicate_groups,
        'similar_files': {
            'count': 0,
            'potential_savings': '0 B',
            'description': '内容相似识别将在内容抽取和向量索引阶段启用'
        },
        'recommendation': '当前重复候选基于文件名和大小识别，后续可升级为哈希级去重。'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def smart_search(request):
    """Global indexed file search backed by SnapshotFileIndex."""
    query = (request.query_params.get('query') or request.query_params.get('q') or '').strip()
    if not query:
        return Response({'results': [], 'count': 0, 'query': query})
    limit = min(int(request.query_params.get('limit', 100)), 500)
    files = _indexed_files_queryset(request).filter(
        Q(path__icontains=query) |
        Q(name__icontains=query) |
        Q(extension__icontains=query) |
        Q(category__icontains=query)
    ).order_by('-size')[:limit]
    results = [
        {
            'id': str(item.id),
            'path': item.path,
            'name': item.name,
            'size': item.size,
            'category': item.category,
            'extension': item.extension,
            'modified_time': item.modified_time.isoformat() if item.modified_time else None,
            'snapshot_id': str(item.snapshot_id),
            'snapshot_name': item.snapshot.name,
            'backup_task_id': str(item.snapshot.task_id),
            'backup_task_name': item.snapshot.task.name if item.snapshot.task_id else '',
            'repository_id': str(item.snapshot.repository_id) if item.snapshot.repository_id else '',
            'repository_name': item.snapshot.repository.name if item.snapshot.repository_id else '',
            'relevance': 'metadata',
        }
        for item in files
    ]
    return Response({'results': results, 'count': len(results), 'query': query, 'mode': 'indexed_metadata'})
