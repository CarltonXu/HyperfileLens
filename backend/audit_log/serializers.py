"""
HyperFileLens Backend - Audit Log Serializers
"""

from rest_framework import serializers
from .models import AuditLog
from .event_models import EventLog


class AuditLogSerializer(serializers.ModelSerializer):
    """审计日志序列化器"""
    
    action_display = serializers.CharField(
        source='get_action_display',
        read_only=True
    )
    resource_type_display = serializers.CharField(
        source='get_resource_type_display',
        read_only=True
    )
    result_display = serializers.CharField(
        source='get_result_display',
        read_only=True
    )
    user_display = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'timestamp',
            # 租户信息
            'tenant_id', 'tenant_name',
            # 操作者信息
            'user', 'user_display', 'user_email', 'user_name', 'ip_address', 'user_agent',
            # 操作详情
            'action', 'action_display', 'resource_type', 'resource_type_display',
            'resource_id', 'resource_name',
            # 变更详情
            'changes', 'details',
            # 操作结果
            'result', 'result_display', 'error_message', 'error_code',
            # 请求信息
            'request_method', 'request_path', 'request_query', 'request_body', 'request_id', 'session_id',
            # 其他
            'location', 'metadata',
        ]
        read_only_fields = fields
    
    def get_user_display(self, obj):
        """获取用户显示名称"""
        if obj.user_name:
            return obj.user_name
        if obj.user_email:
            return obj.user_email
        if obj.user:
            return obj.user.email
        return 'System'
    
    def get_tenant_name(self, obj):
        """获取租户名称"""
        if not obj.tenant_id:
            return None
        from tenants.models import Tenant
        try:
            tenant = Tenant.objects.get(id=obj.tenant_id)
            return tenant.name
        except Tenant.DoesNotExist:
            return None


class AuditLogListSerializer(serializers.ModelSerializer):
    """审计日志列表序列化器（简化版）"""
    
    action_display = serializers.CharField(
        source='get_action_display',
        read_only=True
    )
    resource_type_display = serializers.CharField(
        source='get_resource_type_display',
        read_only=True
    )
    result_display = serializers.CharField(
        source='get_result_display',
        read_only=True
    )
    user_display = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'timestamp', 'tenant_id',
            'user_display', 'user_email', 'ip_address',
            'action', 'action_display',
            'resource_type', 'resource_type_display', 'resource_id', 'resource_name',
            'result', 'result_display', 'error_message',
            'request_method', 'request_path'
        ]
    
    def get_user_display(self, obj):
        if obj.user_name:
            return obj.user_name
        if obj.user_email:
            return obj.user_email
        return 'System'


class AuditLogDetailSerializer(AuditLogSerializer):
    """审计日志详情序列化器（包含完整变更信息）"""
    pass


class EventLogSerializer(serializers.ModelSerializer):
    """事件日志序列化器"""
    
    event_type_display = serializers.CharField(
        source='get_event_type_display',
        read_only=True
    )
    severity_display = serializers.CharField(
        source='get_severity_display',
        read_only=True
    )
    user_display = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()
    handled_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = EventLog
        fields = [
            'id', 'timestamp',
            # 租户信息
            'tenant_id', 'tenant_name',
            # 事件类型和名称
            'event_type', 'event_type_display', 'event_name',
            # 事件详情
            'message', 'details', 'severity', 'severity_display',
            # 事件来源
            'source',
            # 关联资源
            'resource_type', 'resource_id',
            # 关联用户
            'user', 'user_display', 'user_email', 'user_name',
            'ip_address', 'request_id',
            # 处理状态
            'is_handled', 'handled_by', 'handled_by_name', 'handled_at', 'handle_note',
            # 其他
            'metadata',
        ]
        read_only_fields = fields
    
    def get_user_display(self, obj):
        if obj.user_name:
            return obj.user_name
        if obj.user_email:
            return obj.user_email
        if obj.user:
            return obj.user.email
        return None
    
    def get_tenant_name(self, obj):
        if not obj.tenant_id:
            return None
        from tenants.models import Tenant
        try:
            tenant = Tenant.objects.get(id=obj.tenant_id)
            return tenant.name
        except Tenant.DoesNotExist:
            return None
    
    def get_handled_by_name(self, obj):
        if obj.handled_by:
            return f"{obj.handled_by.first_name} {obj.handled_by.last_name}".strip() or obj.handled_by.email
        return None


class EventLogListSerializer(serializers.ModelSerializer):
    """事件日志列表序列化器（简化版）"""
    
    event_type_display = serializers.CharField(
        source='get_event_type_display',
        read_only=True
    )
    severity_display = serializers.CharField(
        source='get_severity_display',
        read_only=True
    )
    user_display = serializers.SerializerMethodField()
    
    class Meta:
        model = EventLog
        fields = [
            'id', 'timestamp', 'tenant_id',
            'event_type', 'event_type_display', 'event_name',
            'message', 'severity', 'severity_display',
            'source', 'resource_type', 'resource_id',
            'user_display', 'ip_address',
            'is_handled'
        ]
    
    def get_user_display(self, obj):
        if obj.user_name:
            return obj.user_name
        if obj.user_email:
            return obj.user_email
        return None


class EventLogHandleSerializer(serializers.Serializer):
    """事件处理序列化器"""
    
    note = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        help_text='处理备注'
    )
