"""API views for the global alert center."""

import os
import platform
import shutil
import uuid

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .choices import (
    AVAILABILITY_CHECK_TYPES,
    EVENT_CATEGORIES,
    EVENT_TYPES,
    JOB_EVENT_TYPES,
    JOB_TYPES,
    METRICS_BY_RESOURCE_TYPE,
    SYSTEM_CHECK_TYPES,
    AlertSeverity,
    AlertStatus,
    AlertType,
    NotificationChannelType,
    NotificationStatus,
    ResourceType,
)
from .models import AlertPolicy, AlertRecord, NotificationChannel, NotificationLog, SystemMetric
from .serializers import (
    AlertPolicySerializer,
    AlertRecordActionSerializer,
    AlertRecordSerializer,
    NotificationChannelSerializer,
    NotificationLogSerializer,
)
from .services.evaluator import resolve_alert
from .services.notifier import test_channel
from licenses.quota import SYSTEM_TENANT_NAME


PLATFORM_RESOURCE_TYPES = {
    ResourceType.SYSTEM,
    ResourceType.SYSTEM_SERVICE,
    ResourceType.LICENSE,
}


def _is_system_admin(user):
    return bool(user and user.is_authenticated and user.is_superuser)


def _tenant_filtered_queryset(request, queryset):
    user = request.user
    if user.is_superuser:
        tenant_id = request.headers.get("X-Tenant-ID") or request.query_params.get("tenant_id")
        return queryset.filter(tenant_id=tenant_id) if tenant_id else queryset
    if getattr(user, "tenant_id", None):
        return queryset.filter(tenant_id=user.tenant_id)
    return queryset.none()


def _request_tenant(request):
    user = request.user
    if user.is_superuser:
        tenant_id = request.headers.get("X-Tenant-ID") or request.query_params.get("tenant_id")
        if tenant_id:
            from tenants.models import Tenant

            return Tenant.objects.filter(id=tenant_id).first()
    return getattr(user, "tenant", None)


class AlertPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 300

    def get_page_size(self, request):
        if request.query_params.get("limit") and not request.query_params.get("page_size"):
            try:
                return min(int(request.query_params["limit"]), self.max_page_size)
            except (TypeError, ValueError):
                return self.page_size
        return super().get_page_size(request)


class AlertPolicyViewSet(viewsets.ModelViewSet):
    queryset = AlertPolicy.objects.all()
    serializer_class = AlertPolicySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AlertPagination

    def get_queryset(self):
        queryset = _tenant_filtered_queryset(self.request, AlertPolicy.objects.all())
        search = self.request.query_params.get("search")
        alert_type = self.request.query_params.get("type")
        severity = self.request.query_params.get("severity")
        resource_type = self.request.query_params.get("resource_type")
        enabled = self.request.query_params.get("enabled")

        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if alert_type:
            queryset = queryset.filter(type=alert_type)
        if severity:
            queryset = queryset.filter(severity=severity)
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        if enabled in {"true", "false"}:
            queryset = queryset.filter(enabled=enabled == "true")
        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        tenant = _request_tenant(self.request)
        alert_type = self.request.data.get("type")
        resource_type = self.request.data.get("resource_type")
        if (alert_type == AlertType.SYSTEM or resource_type in PLATFORM_RESOURCE_TYPES) and (
            not tenant or tenant.name != SYSTEM_TENANT_NAME
        ):
            raise ValidationError({
                "tenant": "System alert policies must belong to the administrator tenant."
            })
        serializer.save(
            tenant=tenant,
            created_by=self.request.user.id
            if self.request.user and self.request.user.is_authenticated
            else None
        )

    @action(detail=True, methods=["post"])
    def enable(self, request, pk=None):
        policy = self.get_object()
        policy.enabled = True
        policy.save(update_fields=["enabled", "updated_at"])
        return Response(self.get_serializer(policy).data)

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        policy = self.get_object()
        policy.enabled = False
        policy.save(update_fields=["enabled", "updated_at"])
        return Response(self.get_serializer(policy).data)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        policy = self.get_object()
        tenant = _request_tenant(request) or policy.tenant
        policy.pk = None
        policy.id = uuid.uuid4()
        policy.name = f"{policy.name} Copy"
        policy.created_by = request.user.id if request.user and request.user.is_authenticated else None
        policy.tenant = tenant
        policy.save()
        return Response(self.get_serializer(policy).data, status=status.HTTP_201_CREATED)


class AlertRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AlertRecord.objects.all()
    serializer_class = AlertRecordSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AlertPagination

    def get_queryset(self):
        queryset = _tenant_filtered_queryset(self.request, AlertRecord.objects.all())
        params = self.request.query_params

        for field in ["status", "type", "severity", "resource_type", "resource_id"]:
            value = params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(message__icontains=search) | Q(resource_name__icontains=search)
            )

        start_time = _parse_datetime(params.get("start_time") or params.get("start_at"))
        end_time = _parse_datetime(params.get("end_time") or params.get("end_at"))
        if start_time:
            queryset = queryset.filter(created_at__gte=start_time)
        if end_time:
            queryset = queryset.filter(created_at__lte=end_time)

        return queryset.order_by("-last_triggered_at", "-created_at")

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        serializer = AlertRecordActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = timezone.now()
        alert.acknowledged_by = request.user.id
        metadata = dict(alert.metadata or {})
        if serializer.validated_data.get("note"):
            metadata["acknowledge_note"] = serializer.validated_data["note"]
        alert.metadata = metadata
        alert.save(update_fields=["status", "acknowledged_at", "acknowledged_by", "metadata", "updated_at"])
        return Response(self.get_serializer(alert).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        serializer = AlertRecordActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("note"):
            metadata = dict(alert.metadata or {})
            metadata["resolve_note"] = serializer.validated_data["note"]
            alert.metadata = metadata
            alert.save(update_fields=["metadata", "updated_at"])
        alert = resolve_alert(alert)
        return Response(self.get_serializer(alert).data)


class NotificationChannelViewSet(viewsets.ModelViewSet):
    queryset = NotificationChannel.objects.all()
    serializer_class = NotificationChannelSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AlertPagination

    def get_queryset(self):
        queryset = _tenant_filtered_queryset(self.request, NotificationChannel.objects.all())
        params = self.request.query_params
        search = params.get("search")
        channel_type = params.get("type")
        enabled = params.get("enabled")

        if search:
            queryset = queryset.filter(name__icontains=search)
        if channel_type:
            queryset = queryset.filter(type=channel_type)
        if enabled in {"true", "false"}:
            queryset = queryset.filter(enabled=enabled == "true")
        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(tenant=_request_tenant(self.request))

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        channel = self.get_object()
        try:
            return Response(test_channel(channel))
        except Exception as exc:
            return Response({"status": "failed", "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def details(self, request, pk=None):
        """Get channel details including associated alerts."""
        channel = self.get_object()

        # Get associated alert policies
        from alerts.models import AlertPolicy, AlertRecord

        # Filter policies in Python since SQLite doesn't support JSONField contains
        channel_id_str = str(channel.id)
        all_policies = _tenant_filtered_queryset(request, AlertPolicy.objects.all()).order_by('-created_at')
        alert_policies = [
            p for p in all_policies
            if channel_id_str in (p.notification_channel_ids or [])
        ]

        # Get notification logs for this channel
        from alerts.models import NotificationLog

        # Get all logs for stats (without slicing)
        all_notification_logs = _tenant_filtered_queryset(request, NotificationLog.objects.all()).filter(
            channel_id=str(channel.id)
        ).order_by('-sent_at')

        # Get recent logs for display (with slicing)
        notification_logs = all_notification_logs[:20]

        all_alert_record_ids = list(all_notification_logs.values_list('alert_record_id', flat=True).distinct())
        alert_record_ids = [log.alert_record_id for log in notification_logs]
        recent_records_qs = _tenant_filtered_queryset(request, AlertRecord.objects.all()).filter(id__in=alert_record_ids)
        alert_record_map = {record.id: record for record in recent_records_qs}
        policy_ids = [record.policy_id for record in recent_records_qs if record.policy_id]
        policy_map = {
            policy.id: policy
            for policy in _tenant_filtered_queryset(request, AlertPolicy.objects.all()).filter(id__in=policy_ids)
        }
        recent_records = sorted(
            recent_records_qs,
            key=lambda record: record.created_at,
            reverse=True,
        )[:10]
        success_count = all_notification_logs.filter(status='success').count()
        failed_count = all_notification_logs.filter(status='failed').count()
        logs_count = all_notification_logs.count()
        last_success = all_notification_logs.filter(status='success').first()
        last_failed = all_notification_logs.filter(status='failed').first()

        return Response({
            'channel': {
                'id': str(channel.id),
                'name': channel.name,
                'type': channel.type,
                'enabled': channel.enabled,
                'config': channel.config or {},
                'created_at': channel.created_at.isoformat(),
                'updated_at': channel.updated_at.isoformat(),
            },
            'associated_policies': [
                {
                    'id': str(policy.id),
                    'name': policy.name,
                    'description': policy.description,
                    'enabled': policy.enabled,
                    'created_at': policy.created_at.isoformat(),
                }
                for policy in alert_policies
            ],
            'recent_alerts': [
                {
                    'id': str(record.id),
                    'title': record.title,
                    'message': record.message,
                    'severity': record.severity,
                    'status': record.status,
                    'created_at': record.created_at.isoformat(),
                }
                for record in recent_records
            ],
            'notification_logs': [
                _notification_log_detail(log, alert_record_map.get(log.alert_record_id), policy_map)
                for log in notification_logs
            ],
            'stats': {
                'policies_count': len(alert_policies),
                'alerts_count': _tenant_filtered_queryset(request, AlertRecord.objects.all()).filter(id__in=all_alert_record_ids).count(),
                'logs_count': logs_count,
                'logs_success': success_count,
                'logs_failed': failed_count,
                'success_rate': round((success_count / logs_count) * 100, 2) if logs_count else 0,
                'last_success_at': last_success.sent_at.isoformat() if last_success else None,
                'last_failed_at': last_failed.sent_at.isoformat() if last_failed else None,
            }
        })


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AlertPagination

    def get_queryset(self):
        queryset = _tenant_filtered_queryset(self.request, NotificationLog.objects.all()).order_by("-sent_at")
        params = self.request.query_params

        channel_id = params.get("channel_id")
        status_value = params.get("status")
        notification_type = params.get("notification_type")
        search = params.get("search")
        alert_type = params.get("type")
        severity = params.get("severity")
        policy_id = params.get("policy_id")
        start_time = _parse_datetime(params.get("start_time") or params.get("start_at"))
        end_time = _parse_datetime(params.get("end_time") or params.get("end_at"))

        if channel_id:
            queryset = queryset.filter(channel_id=channel_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        if start_time:
            queryset = queryset.filter(sent_at__gte=start_time)
        if end_time:
            queryset = queryset.filter(sent_at__lte=end_time)

        alert_filters = Q()
        if search:
            alert_filters &= (
                Q(title__icontains=search)
                | Q(message__icontains=search)
                | Q(resource_name__icontains=search)
            )
        if alert_type:
            alert_filters &= Q(type=alert_type)
        if severity:
            alert_filters &= Q(severity=severity)
        if policy_id:
            alert_filters &= Q(policy_id=policy_id)
        if alert_filters:
            alert_ids = _tenant_filtered_queryset(
                self.request, AlertRecord.objects.all()
            ).filter(alert_filters).values_list("id", flat=True)
            queryset = queryset.filter(alert_record_id__in=list(alert_ids))

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        logs = list(page if page is not None else queryset)
        data = _notification_log_details(logs)
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        log = self.get_object()
        return Response(_notification_log_details([log])[0])

    @action(detail=False, methods=["get"])
    def stats(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        total = queryset.count()
        success = queryset.filter(status=NotificationStatus.SUCCESS).count()
        failed = queryset.filter(status=NotificationStatus.FAILED).count()
        recent_failed = queryset.filter(status=NotificationStatus.FAILED).order_by("-sent_at")[:5]
        channel_ids = list(queryset.values_list("channel_id", flat=True).distinct())
        channels = _tenant_filtered_queryset(request, NotificationChannel.objects.all()).filter(id__in=channel_ids)
        return Response({
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": round((success / total) * 100, 2) if total else 0,
            "channels": channels.count(),
            "recent_failed": _notification_log_details(list(recent_failed)),
        })


class MetadataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, kind):
        if kind == "alert-types":
            return Response(_choices(AlertType, include_platform=_is_system_admin(request.user)))
        if kind == "resource-types":
            return Response(_choices(ResourceType, include_platform=_is_system_admin(request.user)))
        if kind == "metrics":
            resource_type = request.query_params.get("resource_type")
            if resource_type in PLATFORM_RESOURCE_TYPES and not _is_system_admin(request.user):
                return Response([])
            return Response(METRICS_BY_RESOURCE_TYPE.get(resource_type, []))
        if kind == "resources":
            resource_type = request.query_params.get("resource_type")
            return Response(_resource_options(request, resource_type))
        if kind == "job-types":
            return Response(JOB_TYPES)
        if kind == "event-types":
            return Response({"categories": EVENT_CATEGORIES, "types": EVENT_TYPES, "job_event_types": JOB_EVENT_TYPES})
        if kind == "system-check-types":
            if not _is_system_admin(request.user):
                return Response([])
            return Response(SYSTEM_CHECK_TYPES)
        if kind == "availability-check-types":
            return Response(AVAILABILITY_CHECK_TYPES)
        if kind == "severities":
            return Response(_choices(AlertSeverity))
        if kind == "statuses":
            return Response(_choices(AlertStatus))
        if kind == "notification-channel-types":
            return Response(_choices(NotificationChannelType))
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)


class MetadataResourcesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        resource_type = request.query_params.get("resource_type")
        return Response(_resource_options(request, resource_type))


class SystemMonitorView(APIView):
    """Control-plane host monitoring data."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_system_admin(request.user):
            return Response({"detail": "System monitor is only available to system administrators."}, status=status.HTTP_403_FORBIDDEN)

        since, until, error = self._resolve_time_range(request)
        if error:
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        sample = collect_system_sample()
        system_tenant = _system_tenant()
        new_metric = SystemMetric.objects.create(tenant=system_tenant, **sample)
        metrics = list(
            SystemMetric.objects.filter(
                tenant=system_tenant,
                timestamp__gte=since,
                timestamp__lte=until,
            ).order_by("timestamp")[:2000]
        )
        if since <= new_metric.timestamp <= until and all(metric.id != new_metric.id for metric in metrics):
            metrics.append(new_metric)
            metrics.sort(key=lambda metric: metric.timestamp)

        return Response(
            {
                "host": {
                    "hostname": platform.node(),
                    "platform": platform.platform(),
                    "python": platform.python_version(),
                },
                "range": {
                    "start_at": since.isoformat(),
                    "end_at": until.isoformat(),
                    "count": len(metrics),
                },
                "current": self._metric_to_dict(metrics[-1]) if metrics else {},
                "series": [self._metric_to_dict(metric) for metric in metrics],
            }
        )

    def _resolve_time_range(self, request):
        start_at_param = request.query_params.get("start_at")
        end_at_param = request.query_params.get("end_at")
        if start_at_param or end_at_param:
            if not start_at_param or not end_at_param:
                return None, None, {"error": "invalid_time_range", "message": "start_at and end_at must be provided together."}
            since = _parse_datetime(start_at_param)
            until = _parse_datetime(end_at_param)
            if not since or not until:
                return None, None, {"error": "invalid_time_range", "message": "start_at and end_at must be valid ISO datetime values."}
            if since > until:
                return None, None, {"error": "invalid_time_range", "message": "start_at must be earlier than end_at."}
            return since, until, None

        try:
            hours = min(float(request.query_params.get("hours", 24)), 720)
        except (TypeError, ValueError):
            hours = 24
        hours = max(1 / 60, hours)
        until = timezone.now()
        since = until - timezone.timedelta(hours=hours)
        return since, until, None

    def _metric_to_dict(self, metric):
        return {
            "timestamp": metric.timestamp.isoformat(),
            "cpu": metric.cpu,
            "memory": metric.memory,
            "swap": metric.swap,
            "disks": metric.disks,
            "disk_io": metric.disk_io,
            "networks": metric.networks,
            "load_average": metric.load_average,
            "metadata": metric.metadata,
        }


def _choices(choice_cls, include_platform=True):
    choices = choice_cls.choices
    if not include_platform:
        if choice_cls == AlertType:
            choices = [(value, label) for value, label in choices if value != AlertType.SYSTEM]
        if choice_cls == ResourceType:
            choices = [(value, label) for value, label in choices if value not in PLATFORM_RESOURCE_TYPES]
    return [{"value": value, "label": label} for value, label in choices]


def _resource_options(request, resource_type):
    if resource_type in PLATFORM_RESOURCE_TYPES and not _is_system_admin(request.user):
        return []

    tenant = _request_tenant(request)

    if resource_type == ResourceType.SYSTEM:
        return [
            {
                "id": "00000000-0000-0000-0000-000000000000",
                "name": "Control Plane",
                "status": "active",
            }
        ]
    if resource_type == ResourceType.SYNC_PROXY:
        from nodes.models import ProxyNode

        queryset = ProxyNode.objects.filter(role=ProxyNode.Role.SYNC)
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        return [
            _resource_option(item, item.name, item.status)
            for item in queryset.order_by("name")[:300]
        ]
    if resource_type == ResourceType.AGENT_PROXY:
        from nodes.models import ProxyNode

        queryset = ProxyNode.objects.filter(role=ProxyNode.Role.AGENT)
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        return [
            _resource_option(item, item.name, item.status)
            for item in queryset.order_by("name")[:300]
        ]
    if resource_type == ResourceType.GATEWAY:
        from gateways.models import Gateway

        queryset = Gateway.objects.all()
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        return [_resource_option(item, item.name, item.status) for item in queryset.order_by("name")[:300]]
    if resource_type == ResourceType.BACKUP_REPOSITORY or resource_type == ResourceType.TARGET_STORAGE:
        from repository.models import Repository

        queryset = Repository.objects.all()
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        return [_resource_option(item, item.name, item.status) for item in queryset.order_by("name")[:300]]
    if resource_type == ResourceType.SOURCE_RESOURCE:
        from source_resources.models import SourceResource

        queryset = SourceResource.objects.all()
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        return [_resource_option(item, item.name, item.status) for item in queryset.order_by("name")[:300]]
    if resource_type == ResourceType.JOB:
        from nodes.models import ProxyTask

        queryset = ProxyTask.objects.all()
        if tenant:
            queryset = queryset.filter(proxy__tenant=tenant)
        return [
            _resource_option(item, f"{item.task_type} / {item.id}", item.status)
            for item in queryset.order_by("-created_at")[:300]
        ]
    if resource_type == ResourceType.USER:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        queryset = User.objects.all()
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        return [
            _resource_option(item, getattr(item, "email", str(item.id)), "active" if item.is_active else "inactive")
            for item in queryset.order_by("email")[:300]
        ]
    return []


def _system_tenant():
    from tenants.models import Tenant
    from licenses.quota import SYSTEM_TENANT_NAME

    return Tenant.objects.filter(name=SYSTEM_TENANT_NAME).first()


def _notification_log_details(logs):
    alert_ids = [log.alert_record_id for log in logs if log.alert_record_id]
    channel_ids = [log.channel_id for log in logs if log.channel_id]
    alert_records = AlertRecord.objects.filter(id__in=alert_ids)
    alert_record_map = {record.id: record for record in alert_records}
    policy_ids = [record.policy_id for record in alert_records if record.policy_id]
    policy_map = {policy.id: policy for policy in AlertPolicy.objects.filter(id__in=policy_ids)}
    channel_map = {channel.id: channel for channel in NotificationChannel.objects.filter(id__in=channel_ids)}
    return [
        _notification_log_detail(
            log,
            alert_record_map.get(log.alert_record_id),
            policy_map,
            channel_map.get(log.channel_id),
        )
        for log in logs
    ]


def _notification_log_detail(log, alert_record, policy_map, channel=None):
    policy = policy_map.get(alert_record.policy_id) if alert_record and alert_record.policy_id else None
    return {
        'id': str(log.id),
        'channel_id': str(log.channel_id) if log.channel_id else None,
        'alert_record_id': str(log.alert_record_id) if log.alert_record_id else None,
        'notification_type': log.notification_type,
        'status': log.status,
        'error_message': log.error_message,
        'created_at': log.sent_at.isoformat(),
        'sent_at': log.sent_at.isoformat(),
        'channel': {
            'id': str(channel.id),
            'name': channel.name,
            'type': channel.type,
            'enabled': channel.enabled,
        } if channel else None,
        'alert': {
            'id': str(alert_record.id),
            'title': alert_record.title,
            'message': alert_record.message,
            'type': alert_record.type,
            'severity': alert_record.severity,
            'status': alert_record.status,
            'resource_type': alert_record.resource_type,
            'resource_id': str(alert_record.resource_id) if alert_record.resource_id else None,
            'resource_name': alert_record.resource_name,
            'current_value': str(alert_record.current_value) if alert_record.current_value is not None else None,
            'threshold_value': str(alert_record.threshold_value) if alert_record.threshold_value is not None else None,
            'unit': alert_record.unit,
            'first_triggered_at': alert_record.first_triggered_at.isoformat() if alert_record.first_triggered_at else None,
            'last_triggered_at': alert_record.last_triggered_at.isoformat() if alert_record.last_triggered_at else None,
        } if alert_record else None,
        'policy': {
            'id': str(policy.id),
            'name': policy.name,
            'type': policy.type,
            'severity': policy.severity,
            'enabled': policy.enabled,
        } if policy else None,
    }


def _resource_option(item, name, status=None):
    return {
        "id": str(item.id),
        "name": name,
        "status": status,
    }


def _parse_datetime(value):
    if not value:
        return None
    parsed = parse_datetime(value)
    if not parsed:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def collect_system_sample():
    try:
        import psutil
    except ImportError:
        return _collect_fallback()

    cpu_freq = psutil.cpu_freq()
    virtual_memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    disks = []
    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except (PermissionError, FileNotFoundError, OSError):
            continue
        disks.append(
            {
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            }
        )

    disk_io = []
    for name, item in psutil.disk_io_counters(perdisk=True).items():
        disk_io.append(
            {
                "name": name,
                "read_bytes": item.read_bytes,
                "write_bytes": item.write_bytes,
                "read_count": item.read_count,
                "write_count": item.write_count,
                "read_time": item.read_time,
                "write_time": item.write_time,
            }
        )

    networks = []
    addresses = psutil.net_if_addrs()
    for name, item in psutil.net_io_counters(pernic=True).items():
        networks.append(
            {
                "name": name,
                "bytes_sent": item.bytes_sent,
                "bytes_recv": item.bytes_recv,
                "packets_sent": item.packets_sent,
                "packets_recv": item.packets_recv,
                "errin": item.errin,
                "errout": item.errout,
                "dropin": item.dropin,
                "dropout": item.dropout,
                "addresses": [addr.address for addr in addresses.get(name, [])],
            }
        )

    load_average = list(os.getloadavg()) if hasattr(os, "getloadavg") else []
    return {
        "cpu": {
            "usage_percent": psutil.cpu_percent(interval=0.1),
            "per_cpu_percent": psutil.cpu_percent(interval=None, percpu=True),
            "logical_cores": psutil.cpu_count(),
            "physical_cores": psutil.cpu_count(logical=False),
            "frequency_mhz": round(cpu_freq.current, 2) if cpu_freq else None,
        },
        "memory": {
            "total": virtual_memory.total,
            "used": virtual_memory.used,
            "available": virtual_memory.available,
            "percent": virtual_memory.percent,
        },
        "swap": {"total": swap.total, "used": swap.used, "free": swap.free, "percent": swap.percent},
        "disks": disks,
        "disk_io": disk_io,
        "networks": networks,
        "load_average": load_average,
        "metadata": {"collector": "psutil"},
    }


def _collect_fallback():
    usage = shutil.disk_usage(settings.BASE_DIR)
    load_average = list(os.getloadavg()) if hasattr(os, "getloadavg") else []
    return {
        "cpu": {
            "usage_percent": 0,
            "per_cpu_percent": [],
            "logical_cores": os.cpu_count(),
            "physical_cores": None,
            "frequency_mhz": None,
        },
        "memory": {"total": 0, "used": 0, "available": 0, "percent": 0},
        "swap": {"total": 0, "used": 0, "free": 0, "percent": 0},
        "disks": [
            {
                "device": "default",
                "mountpoint": str(settings.BASE_DIR),
                "fstype": "",
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": round((usage.used / usage.total) * 100, 2) if usage.total else 0,
            }
        ],
        "disk_io": [],
        "networks": [],
        "load_average": load_average,
        "metadata": {"collector": "fallback"},
    }
