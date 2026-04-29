"""
HyperFileLens Backend - Event Log Models

事件日志模型：记录系统中发生的各种事件，包括系统事件、业务事件、安全事件、告警事件。

与审计日志的区别：
- 审计日志：记录用户的操作行为（谁在什么时候做了什么）
- 事件日志：记录系统中发生的事件（系统、业务、安全、告警等）
"""

import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings


class EventLogManager(models.Manager):
    """事件日志管理器"""
    
    def log_system(self, event_name, message, details=None, severity='info',
                   source='', resource_type='', resource_id='', tenant_id=None):
        """记录系统事件"""
        return self._create_event(
            event_type='system',
            event_name=event_name,
            message=message,
            details=details,
            severity=severity,
            source=source,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id
        )
    
    def log_business(self, event_name, message, details=None, severity='info',
                     source='', resource_type='', resource_id='', tenant_id=None, user=None):
        """记录业务事件"""
        return self._create_event(
            event_type='business',
            event_name=event_name,
            message=message,
            details=details,
            severity=severity,
            source=source,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            user=user
        )
    
    def log_security(self, event_name, message, details=None, severity='warning',
                     source='', resource_type='', resource_id='', tenant_id=None, user=None,
                     ip_address=None):
        """记录安全事件"""
        event = self._create_event(
            event_type='security',
            event_name=event_name,
            message=message,
            details=details,
            severity=severity,
            source=source,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            user=user
        )
        if ip_address:
            event.ip_address = ip_address
            event.save(update_fields=['ip_address'])
        return event
    
    def log_alert(self, event_name, message, details=None, severity='warning',
                  source='', resource_type='', resource_id='', tenant_id=None):
        """记录告警事件"""
        return self._create_event(
            event_type='alert',
            event_name=event_name,
            message=message,
            details=details,
            severity=severity,
            source=source,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id
        )
    
    def log_backup_event(self, event_name, task_id, message, details=None,
                         severity='info', tenant_id=None, user=None):
        """记录备份相关事件"""
        return self._create_event(
            event_type='business',
            event_name=event_name,
            message=message,
            details=details,
            severity=severity,
            source='backup_service',
            resource_type='backup_task',
            resource_id=str(task_id),
            tenant_id=tenant_id,
            user=user
        )
    
    def log_proxy_event(self, event_name, proxy_id, message, details=None,
                        severity='info', tenant_id=None):
        """记录代理相关事件"""
        return self._create_event(
            event_type='system',
            event_name=event_name,
            message=message,
            details=details,
            severity=severity,
            source='proxy_service',
            resource_type='proxy',
            resource_id=str(proxy_id),
            tenant_id=tenant_id
        )
    
    def log_storage_event(self, event_name, repository_id, message, details=None,
                          severity='info', tenant_id=None):
        """记录存储相关事件"""
        return self._create_event(
            event_type='system',
            event_name=event_name,
            message=message,
            details=details,
            severity=severity,
            source='storage_service',
            resource_type='repository',
            resource_id=str(repository_id),
            tenant_id=tenant_id
        )
    
    def _create_event(self, event_type, event_name, message, details=None,
                      severity='info', source='', resource_type='', resource_id='',
                      tenant_id=None, user=None):
        """创建事件日志"""
        user_email = ''
        user_name = ''
        if user:
            user_email = user.email
            user_name = f"{user.first_name} {user.last_name}".strip()
        
        return self.create(
            event_type=event_type,
            event_name=event_name,
            message=message,
            details=details or {},
            severity=severity,
            source=source,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            user=user,
            user_email=user_email,
            user_name=user_name
        )


class EventLog(models.Model):
    """
    事件日志模型
    
    记录系统中发生的各种事件，包括系统事件、业务事件、安全事件、告警事件。
    """
    
    # ==================== 事件类型 ====================
    TYPE_SYSTEM = 'system'
    TYPE_BUSINESS = 'business'
    TYPE_SECURITY = 'security'
    TYPE_ALERT = 'alert'
    
    TYPE_CHOICES = [
        (TYPE_SYSTEM, '系统事件'),
        (TYPE_BUSINESS, '业务事件'),
        (TYPE_SECURITY, '安全事件'),
        (TYPE_ALERT, '告警事件'),
    ]
    
    # ==================== 事件级别 ====================
    SEVERITY_DEBUG = 'debug'
    SEVERITY_INFO = 'info'
    SEVERITY_NOTICE = 'notice'
    SEVERITY_WARNING = 'warning'
    SEVERITY_ERROR = 'error'
    SEVERITY_CRITICAL = 'critical'
    
    SEVERITY_CHOICES = [
        (SEVERITY_DEBUG, '调试'),
        (SEVERITY_INFO, '信息'),
        (SEVERITY_NOTICE, '通知'),
        (SEVERITY_WARNING, '警告'),
        (SEVERITY_ERROR, '错误'),
        (SEVERITY_CRITICAL, '严重'),
    ]
    
    # ==================== 常用事件名称 ====================
    # 系统事件
    EVENT_SYSTEM_START = 'system.start'
    EVENT_SYSTEM_STOP = 'system.stop'
    EVENT_SYSTEM_CONFIG_CHANGE = 'system.config_change'
    EVENT_SYSTEM_ERROR = 'system.error'
    
    # 代理事件
    EVENT_PROXY_REGISTERED = 'proxy.registered'
    EVENT_PROXY_ONLINE = 'proxy.online'
    EVENT_PROXY_OFFLINE = 'proxy.offline'
    EVENT_PROXY_HEARTBEAT_MISSED = 'proxy.heartbeat_missed'
    EVENT_PROXY_ERROR = 'proxy.error'
    
    # 备份事件
    EVENT_BACKUP_STARTED = 'backup.started'
    EVENT_BACKUP_COMPLETED = 'backup.completed'
    EVENT_BACKUP_FAILED = 'backup.failed'
    EVENT_BACKUP_CANCELLED = 'backup.cancelled'
    EVENT_BACKUP_WARNING = 'backup.warning'
    
    # 恢复事件
    EVENT_RECOVERY_STARTED = 'recovery.started'
    EVENT_RECOVERY_COMPLETED = 'recovery.completed'
    EVENT_RECOVERY_FAILED = 'recovery.failed'
    
    # 存储事件
    EVENT_STORAGE_LOW = 'storage.low'
    EVENT_STORAGE_CRITICAL = 'storage.critical'
    EVENT_REPOSITORY_CREATED = 'repository.created'
    EVENT_REPOSITORY_DELETED = 'repository.deleted'
    EVENT_REPOSITORY_ERROR = 'repository.error'
    
    # 安全事件
    EVENT_SECURITY_LOGIN_FAILED = 'security.login_failed'
    EVENT_SECURITY_LOGIN_SUCCESS = 'security.login_success'
    EVENT_SECURITY_LOGOUT = 'security.logout'
    EVENT_SECURITY_PASSWORD_CHANGE = 'security.password_change'
    EVENT_SECURITY_PERMISSION_CHANGE = 'security.permission_change'
    EVENT_SECURITY_API_KEY_EXPOSED = 'security.api_key_exposed'
    EVENT_SECURITY_SUSPICIOUS_ACTIVITY = 'security.suspicious_activity'
    EVENT_SECURITY_BRUTE_FORCE = 'security.brute_force'
    
    # 许可证事件
    EVENT_LICENSE_EXPIRED = 'license.expired'
    EVENT_LICENSE_EXPIRING = 'license.expiring'
    EVENT_LICENSE_ACTIVATED = 'license.activated'
    EVENT_LICENSE_INVALID = 'license.invalid'
    
    # 用户事件
    EVENT_USER_CREATED = 'user.created'
    EVENT_USER_DELETED = 'user.deleted'
    EVENT_USER_ENABLED = 'user.enabled'
    EVENT_USER_DISABLED = 'user.disabled'
    EVENT_USER_ROLE_CHANGED = 'user.role_changed'
    
    # 租户事件
    EVENT_TENANT_CREATED = 'tenant.created'
    EVENT_TENANT_DELETED = 'tenant.deleted'
    EVENT_TENANT_ENABLED = 'tenant.enabled'
    EVENT_TENANT_DISABLED = 'tenant.disabled'
    
    # 网关事件
    EVENT_GATEWAY_CONNECTED = 'gateway.connected'
    EVENT_GATEWAY_DISCONNECTED = 'gateway.disconnected'
    EVENT_GATEWAY_ERROR = 'gateway.error'
    
    # ==================== 字段定义 ====================
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='事件ID'
    )
    
    # 时间戳
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name='事件时间'
    )
    
    # 租户信息
    tenant_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='租户ID'
    )
    
    # 事件类型和名称
    event_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True,
        verbose_name='事件类型'
    )
    event_name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='事件名称'
    )
    
    # 事件详情
    message = models.TextField(
        verbose_name='事件消息'
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='事件详情'
    )
    
    # 事件级别
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_INFO,
        db_index=True,
        verbose_name='事件级别'
    )
    
    # 事件来源
    source = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='事件来源',
        help_text='事件产生的来源，如服务名、模块名'
    )
    
    # 关联资源
    resource_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='资源类型'
    )
    resource_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='资源ID'
    )
    
    # 关联用户
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='event_logs',
        verbose_name='关联用户'
    )
    user_email = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='用户邮箱'
    )
    user_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='用户姓名'
    )
    
    # IP地址
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP地址'
    )
    
    # 请求追踪
    request_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='请求ID'
    )
    
    # 是否已处理（用于告警事件）
    is_handled = models.BooleanField(
        default=False,
        verbose_name='是否已处理'
    )
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_events',
        verbose_name='处理人'
    )
    handled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='处理时间'
    )
    handle_note = models.TextField(
        blank=True,
        verbose_name='处理备注'
    )
    
    # 额外元数据
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='元数据'
    )
    
    objects = EventLogManager()
    
    class Meta:
        db_table = 'event_logs'
        ordering = ['-timestamp']
        verbose_name = '事件日志'
        verbose_name_plural = '事件日志'
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['tenant_id', '-timestamp']),
            models.Index(fields=['event_type']),
            models.Index(fields=['event_name']),
            models.Index(fields=['severity']),
            models.Index(fields=['is_handled']),
        ]
    
    def __str__(self):
        return f"[{self.timestamp}] {self.get_event_type_display()}: {self.event_name} - {self.message[:50]}"
    
    @property
    def is_critical(self):
        return self.severity == self.SEVERITY_CRITICAL
    
    @property
    def is_error(self):
        return self.severity == self.SEVERITY_ERROR
    
    @property
    def is_warning(self):
        return self.severity == self.SEVERITY_WARNING
    
    def mark_handled(self, user, note=''):
        """标记事件为已处理"""
        self.is_handled = True
        self.handled_by = user
        self.handled_at = timezone.now()
        self.handle_note = note
        self.save(update_fields=['is_handled', 'handled_by', 'handled_at', 'handle_note'])


# ==================== 便捷函数 ====================

def event_log(event_type, event_name, message, details=None, severity='info',
              source='', resource_type='', resource_id='', tenant_id=None, user=None):
    """
    便捷的事件日志记录函数
    
    使用示例:
        from audit_log.models import event_log
        
        # 记录系统事件
        event_log(
            event_type='system',
            event_name='proxy.online',
            message='Proxy proxy-001 is now online',
            source='proxy_service',
            resource_type='proxy',
            resource_id='proxy-001'
        )
        
        # 记录安全事件
        event_log(
            event_type='security',
            event_name='security.login_failed',
            message='Login failed for user admin@test.com',
            severity='warning',
            details={'reason': 'Invalid password', 'attempts': 3}
        )
    """
    user_email = ''
    user_name = ''
    if user:
        user_email = user.email
        user_name = f"{user.first_name} {user.last_name}".strip()
    
    return EventLog.objects.create(
        event_type=event_type,
        event_name=event_name,
        message=message,
        details=details or {},
        severity=severity,
        source=source,
        resource_type=resource_type,
        resource_id=resource_id,
        tenant_id=tenant_id,
        user=user,
        user_email=user_email,
        user_name=user_name
    )
