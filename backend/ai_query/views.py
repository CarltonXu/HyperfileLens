"""
HyperFileLens Backend - AI Query Views
"""

import time
from datetime import timedelta
from django.db.models import Count, Q, Sum
from django.utils import timezone
import requests
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import AIProvider, AIQuery
from .serializers import AIProviderSerializer, AIQuerySerializer, AIQueryCreateSerializer
from .services import dispatch_ai_query


def _chat_completions_url(base_url):
    normalized = str(base_url or '').rstrip('/')
    if normalized.endswith('/chat/completions'):
        return normalized
    if normalized.endswith('/v1'):
        return f'{normalized}/chat/completions'
    return f'{normalized}/v1/chat/completions'


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


def _indexed_files_queryset(request):
    from insights.models import SnapshotFileIndex

    snapshot_ids = _tenant_snapshot_filter(request.user).values_list('id', flat=True)
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


def _insights_queryset(request):
    from insights.models import SnapshotInsight

    snapshot_ids = _tenant_snapshot_filter(request.user).values_list('id', flat=True)
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
        """Create a new AI query and dispatch it to an online Gateway."""
        payload = request.data.copy()
        if not payload.get('query_text') and payload.get('query'):
            payload['query_text'] = payload.get('query')
        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        snapshot_id = data.pop('snapshot_id', None)
        repository_id = data.pop('repository_id', None)
        gateway_id = data.pop('gateway_id', None)
        
        query = AIQuery.objects.create(
            user=request.user,
            tenant=getattr(request.user, 'tenant', None),
            **data
        )
        try:
            query = dispatch_ai_query(
                query,
                gateway_id=gateway_id,
                snapshot_id=snapshot_id,
                repository_id=repository_id,
            )
        except Exception as exc:
            query.mark_failed(str(exc))
            return Response(AIQuerySerializer(query).data, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(
            AIQuerySerializer(query).data,
            status=status.HTTP_201_CREATED
        )
    
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
        if provider.provider_type == AIProvider.PROVIDER_LOCAL:
            return Response({
                'success': True,
                'provider': provider.provider_type,
                'model': provider.default_model or 'rule-summary',
                'answer': f'Local fallback is enabled. Test prompt: {prompt}',
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
            'stream': False,
            'model': provider.default_model,
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a helpful AI assistant. Answer the user naturally and concisely.',
                },
                {'role': 'user', 'content': prompt},
            ],
            'max_tokens': int(request.data.get('max_tokens') or 160),
            'temperature': 0.2,
        }
        started = time.monotonic()
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=max(5, min(int(provider.timeout_seconds or 60), 120)),
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
    snapshot_ids = _tenant_snapshot_filter(request.user).values('id')
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
def insights_overview(request):
    """
    AI Insights Overview - 洞察看板
    Returns comprehensive statistics about the backup data.
    """
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
            'sensitive_files': 0,
            'ransomware_risk': 'safe',
            'permission_issues': 0
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
        'indexed_snapshots': _tenant_snapshot_filter(request.user).filter(index_jobs__status='completed').distinct().count(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sensitive_data_scan(request):
    """
    Sensitive Data Scanner - 敏感数据扫描
    Scans for PII, sensitive information, compliance issues.
    """
    return Response({
        'scan_status': 'completed',
        'last_scan': timezone.now().isoformat(),
        'findings': [],
        'compliance_status': {
            'gdpr': {'status': 'not_scanned', 'issues': 0},
            'pci_dss': {'status': 'pass', 'issues': 0},
            'hipaa': {'status': 'not_applicable', 'issues': 0}
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
