"""
HyperFileLens Backend - Audit Log Views

审计日志和事件日志的视图集。
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from django.utils import timezone

from .models import AuditLog
from .event_models import EventLog
from .serializers import (
    AuditLogSerializer,
    AuditLogListSerializer,
    AuditLogDetailSerializer,
    EventLogSerializer,
    EventLogListSerializer,
    EventLogHandleSerializer,
)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    审计日志视图集
    
    提供审计日志的查询功能，所有日志只读不可修改。
    
    权限说明：
    - 平台管理员：可查看所有审计日志
    - 租户管理员：可查看自己租户的审计日志
    """
    
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['action', 'resource_type', 'result']
    ordering_fields = ['timestamp', 'action', 'resource_type']
    ordering = ['-timestamp']
    search_fields = ['user_email', 'user_name', 'resource_name', 'resource_id', 'details']
    
    def list(self, request, *args, **kwargs):
        """重写 list 方法以支持自定义 page_size"""
        # get_queryset 已经应用了所有过滤和权限控制
        queryset = self.get_queryset()
        
        # 应用排序（从 filter_queryset 中获取排序功能）
        ordering = request.query_params.get('ordering', '-timestamp')
        queryset = queryset.order_by(ordering)
        
        # 获取分页参数
        page_size = request.query_params.get('page_size', 10)
        
        # 创建分页器并配置
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = int(page_size)
        paginator.page_size_query_param = 'page_size'
        paginator.max_page_size = 100
        
        # 应用分页
        page_obj = paginator.paginate_queryset(queryset, request, view=self)
        
        # 序列化数据
        serializer = self.get_serializer(page_obj, many=True)
        
        return paginator.get_paginated_response(serializer.data)
    
    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'list':
            return AuditLogListSerializer
        if self.action == 'retrieve':
            return AuditLogDetailSerializer
        return AuditLogSerializer
    
    def get_queryset(self):
        """根据用户权限过滤日志"""
        user = self.request.user
        queryset = AuditLog.objects.all()
        
        # 平台管理员可查看所有日志
        if user.is_superuser:
            pass
        # 租户管理员只能查看自己租户的日志
        elif user.tenant_role == 'admin':
            queryset = queryset.filter(tenant_id=user.tenant_id)
        # 普通用户无权查看审计日志
        else:
            return AuditLog.objects.none()
        
        # 应用额外过滤
        queryset = self._apply_filters(queryset)
        
        return queryset
    
    def _apply_filters(self, queryset):
        """应用额外过滤条件"""
        params = self.request.query_params
        
        # 时间范围过滤（使用 __date 进行日期比较）
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)
        
        # 用户过滤
        user_id = params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # 租户过滤（仅平台管理员）
        tenant_id = params.get('tenant_id')
        if tenant_id and self.request.user.is_superuser:
            queryset = queryset.filter(tenant_id=tenant_id)
        
        # IP地址过滤
        ip_address = params.get('ip_address')
        if ip_address:
            queryset = queryset.filter(ip_address=ip_address)
        
        # 资源ID过滤
        resource_id = params.get('resource_id')
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        获取审计日志统计信息
        
        返回：
        - 总日志数
        - 今日日志数
        - 按操作类型统计
        - 按资源类型统计
        - 按结果统计
        """
        user = request.user
        queryset = self.get_queryset()
        
        # 基础统计
        total_count = queryset.count()
        
        # 今日统计
        today = timezone.now().date()
        today_count = queryset.filter(timestamp__date=today).count()
        
        # 按操作类型统计
        action_stats = {}
        for action, _ in AuditLog.ACTION_CHOICES:
            action_stats[action] = queryset.filter(action=action).count()
        
        # 按资源类型统计
        resource_stats = {}
        for resource_type, _ in AuditLog.RESOURCE_CHOICES:
            resource_stats[resource_type] = queryset.filter(resource_type=resource_type).count()
        
        # 按结果统计
        result_stats = {
            'success': queryset.filter(result='success').count(),
            'failure': queryset.filter(result='failure').count(),
            'partial': queryset.filter(result='partial').count(),
        }
        
        return Response({
            'total_count': total_count,
            'today_count': today_count,
            'action_stats': action_stats,
            'resource_stats': resource_stats,
            'result_stats': result_stats,
        })
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        导出审计日志
        
        支持 CSV 和 JSON 格式导出
        """
        from django.http import HttpResponse
        import json
        import csv
        
        queryset = self.get_queryset()
        
        # 限制导出数量
        queryset = queryset[:10000]
        
        format_type = request.query_params.get('format', 'json')
        
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'ID', '时间', '用户', 'IP地址', '操作', '资源类型',
                '资源ID', '资源名称', '结果', '错误信息', '请求路径'
            ])
            
            for log in queryset:
                writer.writerow([
                    str(log.id),
                    log.timestamp.isoformat(),
                    log.user_email or 'System',
                    log.ip_address or '',
                    log.get_action_display(),
                    log.get_resource_type_display(),
                    log.resource_id,
                    log.resource_name,
                    log.get_result_display(),
                    log.error_message,
                    log.request_path,
                ])
            
            return response
        
        else:
            serializer = AuditLogListSerializer(queryset, many=True)
            response = HttpResponse(
                json.dumps(serializer.data, ensure_ascii=False, indent=2),
                content_type='application/json'
            )
            response['Content-Disposition'] = 'attachment; filename="audit_logs.json"'
            return response


class EventLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    事件日志视图集
    
    提供事件日志的查询和处理功能。
    
    权限说明：
    - 平台管理员：可查看和处理所有事件日志
    - 租户管理员：可查看和处理自己租户的事件日志
    """
    
    queryset = EventLog.objects.all()
    serializer_class = EventLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['event_type', 'severity', 'is_handled', 'source']
    ordering_fields = ['timestamp', 'severity', 'event_type']
    ordering = ['-timestamp']
    search_fields = ['message', 'event_name', 'user_email', 'resource_id']
    
    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'list':
            return EventLogListSerializer
        return EventLogSerializer
    
    def get_queryset(self):
        """根据用户权限过滤日志"""
        user = self.request.user
        queryset = EventLog.objects.all()
        
        # 平台管理员可查看所有日志
        if user.is_superuser:
            pass
        # 租户管理员只能查看自己租户的日志
        elif user.tenant_role == 'admin':
            queryset = queryset.filter(tenant_id=user.tenant_id)
        # 普通用户无权查看事件日志
        else:
            return EventLog.objects.none()
        
        # 应用额外过滤
        queryset = self._apply_filters(queryset)
        
        return queryset
    
    def _apply_filters(self, queryset):
        """应用额外过滤条件"""
        params = self.request.query_params
        
        # 时间范围过滤
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        # 用户过滤
        user_id = params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # 租户过滤（仅平台管理员）
        tenant_id = params.get('tenant_id')
        if tenant_id and self.request.user.is_superuser:
            queryset = queryset.filter(tenant_id=tenant_id)
        
        # 事件名称过滤
        event_name = params.get('event_name')
        if event_name:
            queryset = queryset.filter(event_name=event_name)
        
        # 资源类型过滤
        resource_type = params.get('resource_type')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def handle(self, request, pk=None):
        """
        处理事件
        
        将事件标记为已处理状态
        """
        event = self.get_object()
        
        # 检查是否已处理
        if event.is_handled:
            return Response(
                {'error': 'Event already handled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = EventLogHandleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        note = serializer.validated_data.get('note', '')
        event.mark_handled(request.user, note)
        
        return Response({
            'id': str(event.id),
            'is_handled': event.is_handled,
            'handled_by': event.handled_by.email if event.handled_by else None,
            'handled_at': event.handled_at,
            'handle_note': event.handle_note,
        })
    
    @action(detail=True, methods=['post'])
    def unhandle(self, request, pk=None):
        """
        取消处理事件
        
        将事件重新标记为未处理状态
        """
        event = self.get_object()
        
        if not event.is_handled:
            return Response(
                {'error': 'Event is not handled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        event.is_handled = False
        event.handled_by = None
        event.handled_at = None
        event.handle_note = ''
        event.save()
        
        return Response({
            'id': str(event.id),
            'is_handled': False,
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        获取事件日志统计信息
        """
        queryset = self.get_queryset()
        
        # 基础统计
        total_count = queryset.count()
        
        # 今日统计
        today = timezone.now().date()
        today_count = queryset.filter(timestamp__date=today).count()
        
        # 未处理统计
        unhandled_count = queryset.filter(is_handled=False).count()
        
        # 按事件类型统计
        type_stats = {}
        for event_type, _ in EventLog.TYPE_CHOICES:
            type_stats[event_type] = queryset.filter(event_type=event_type).count()
        
        # 按严重级别统计
        severity_stats = {}
        for severity, _ in EventLog.SEVERITY_CHOICES:
            severity_stats[severity] = queryset.filter(severity=severity).count()
        
        # 按来源统计
        source_stats = {}
        sources = queryset.values_list('source', flat=True).distinct()
        for source in sources:
            if source:
                source_stats[source] = queryset.filter(source=source).count()
        
        return Response({
            'total_count': total_count,
            'today_count': today_count,
            'unhandled_count': unhandled_count,
            'type_stats': type_stats,
            'severity_stats': severity_stats,
            'source_stats': source_stats,
        })
    
    @action(detail=False, methods=['get'])
    def alerts(self, request):
        """
        获取未处理的告警和严重事件
        """
        queryset = self.get_queryset().filter(
            is_handled=False,
            severity__in=['warning', 'error', 'critical']
        ).order_by('-timestamp')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
