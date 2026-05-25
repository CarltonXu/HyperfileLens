from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backup_tasks.models import BackupSnapshot

from .models import SnapshotAIJob, SnapshotFileIndex, SnapshotIndexJob, SnapshotInsight
from .serializers import (
    SnapshotAIJobSerializer,
    SnapshotFileIndexSerializer,
    SnapshotIndexJobSerializer,
    SnapshotInsightSerializer,
)
from .services import (
    dispatch_snapshot_index,
    dispatch_snapshot_ai_summary,
    generate_snapshot_insights,
    reconcile_stale_index_job,
)


class SnapshotInsightsViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def _snapshot_queryset(self, request):
        queryset = BackupSnapshot.objects.select_related('task', 'repository', 'task__tenant')
        user = request.user
        if user.is_superuser:
            return queryset
        if user.tenant:
            return queryset.filter(task__tenant=user.tenant)
        return queryset.filter(task__user=user)

    def _get_snapshot(self, request, snapshot_id):
        return get_object_or_404(self._snapshot_queryset(request), id=snapshot_id)

    @action(detail=False, methods=['post'], url_path=r'snapshots/(?P<snapshot_id>[^/.]+)/index')
    def index_snapshot(self, request, snapshot_id=None):
        snapshot = self._get_snapshot(request, snapshot_id)
        try:
            job = dispatch_snapshot_index(
                snapshot,
                request.user,
                gateway_id=request.data.get('gateway_id'),
                force=bool(request.data.get('force', False)),
            )
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SnapshotIndexJobSerializer(job).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path=r'snapshots/(?P<snapshot_id>[^/.]+)/index/status')
    def index_status(self, request, snapshot_id=None):
        snapshot = self._get_snapshot(request, snapshot_id)
        job = SnapshotIndexJob.objects.filter(snapshot=snapshot).order_by('-created_at').first()
        if not job:
            return Response({'status': 'not_indexed'})
        job = reconcile_stale_index_job(job)
        return Response(SnapshotIndexJobSerializer(job).data)

    @action(detail=False, methods=['get'], url_path=r'snapshots/(?P<snapshot_id>[^/.]+)/files')
    def files(self, request, snapshot_id=None):
        snapshot = self._get_snapshot(request, snapshot_id)
        queryset = SnapshotFileIndex.objects.filter(snapshot=snapshot)
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        extension = request.query_params.get('extension')
        if extension:
            queryset = queryset.filter(extension=extension.lower())
        query = request.query_params.get('q')
        if query:
            queryset = queryset.filter(Q(path__icontains=query) | Q(name__icontains=query))
        ordering = request.query_params.get('ordering') or 'path'
        allowed = {'path', '-path', 'name', '-name', 'size', '-size', 'modified_time', '-modified_time', 'category', '-category'}
        queryset = queryset.order_by(ordering if ordering in allowed else 'path')
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(SnapshotFileIndexSerializer(page, many=True).data)
        return Response(SnapshotFileIndexSerializer(queryset[:200], many=True).data)

    @action(detail=False, methods=['get'], url_path=r'snapshots/(?P<snapshot_id>[^/.]+)/search')
    def search(self, request, snapshot_id=None):
        snapshot = self._get_snapshot(request, snapshot_id)
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'results': [], 'count': 0})
        limit = min(int(request.query_params.get('limit', 50)), 200)
        queryset = SnapshotFileIndex.objects.filter(snapshot=snapshot).filter(
            Q(path__icontains=query) | Q(name__icontains=query) | Q(extension__icontains=query)
        ).order_by('-size')[:limit]
        data = SnapshotFileIndexSerializer(queryset, many=True).data
        return Response({'results': data, 'count': len(data), 'query': query})

    @action(detail=False, methods=['get'], url_path=r'snapshots/(?P<snapshot_id>[^/.]+)/insights')
    def insights(self, request, snapshot_id=None):
        snapshot = self._get_snapshot(request, snapshot_id)
        queryset = SnapshotInsight.objects.filter(snapshot=snapshot)
        return Response(SnapshotInsightSerializer(queryset, many=True).data)

    @action(detail=False, methods=['post'], url_path=r'snapshots/(?P<snapshot_id>[^/.]+)/analyze')
    def analyze(self, request, snapshot_id=None):
        snapshot = self._get_snapshot(request, snapshot_id)
        if not SnapshotFileIndex.objects.filter(snapshot=snapshot).exists():
            return Response({'error': 'Snapshot is not indexed'}, status=status.HTTP_400_BAD_REQUEST)
        generate_snapshot_insights(snapshot)
        queryset = SnapshotInsight.objects.filter(snapshot=snapshot)
        return Response(SnapshotInsightSerializer(queryset, many=True).data)

    @action(detail=False, methods=['post'], url_path=r'snapshots/(?P<snapshot_id>[^/.]+)/ai-summary')
    def ai_summary(self, request, snapshot_id=None):
        snapshot = self._get_snapshot(request, snapshot_id)
        try:
            job = dispatch_snapshot_ai_summary(
                snapshot,
                request.user,
                gateway_id=request.data.get('gateway_id'),
                language=request.data.get('language') or 'zh-CN',
            )
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SnapshotAIJobSerializer(job).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path=r'snapshots/(?P<snapshot_id>[^/.]+)/ai-jobs')
    def ai_jobs(self, request, snapshot_id=None):
        snapshot = self._get_snapshot(request, snapshot_id)
        queryset = SnapshotAIJob.objects.filter(snapshot=snapshot).order_by('-created_at')
        return Response(SnapshotAIJobSerializer(queryset[:20], many=True).data)
