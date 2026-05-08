"""
HyperFileLens Backend - Audit Log Models

审计日志模型：记录用户操作行为，用于合规审计、安全分析、问题追溯。

设计原则：
1. 完整性：记录所有用户操作
2. 不可篡改：日志一旦创建不可修改
3. 可追溯：支持按用户、时间、操作类型等多维度查询
4. 详细性：记录操作前后的数据变化
"""

import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings


class AuditLogManager(models.Manager):
    """审计日志管理器"""
    
    def log_create(self, request, resource_type, resource_id, resource_name='',
                   details='', before_data=None, after_data=None, result='success',
                   error_message=''):
        """
        记录创建操作
        
        Args:
            request: HTTP请求对象
            resource_type: 资源类型（如 'user', 'tenant', 'proxy'）
            resource_id: 资源ID
            resource_name: 资源名称（用于显示）
            details: 操作详情
            after_data: 创建后的数据
            result: 操作结果 ('success', 'failure')
            error_message: 错误信息
        """
        return self._create_log(
            request=request,
            action='create',
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else '',
            resource_name=resource_name,
            details=details,
            before_data=None,
            after_data=after_data,
            result=result,
            error_message=error_message
        )
    
    def log_update(self, request, resource_type, resource_id, resource_name='',
                   details='', before_data=None, after_data=None, changed_fields=None,
                   result='success', error_message=''):
        """
        记录更新操作
        
        Args:
            request: HTTP请求对象
            resource_type: 资源类型
            resource_id: 资源ID
            resource_name: 资源名称
            details: 操作详情
            before_data: 更新前的数据
            after_data: 更新后的数据
            changed_fields: 变更的字段列表
            result: 操作结果
            error_message: 错误信息
        """
        return self._create_log(
            request=request,
            action='update',
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else '',
            resource_name=resource_name,
            details=details,
            before_data=before_data,
            after_data=after_data,
            changed_fields=changed_fields,
            result=result,
            error_message=error_message
        )
    
    def log_delete(self, request, resource_type, resource_id, resource_name='',
                   details='', before_data=None, result='success', error_message=''):
        """
        记录删除操作
        
        Args:
            request: HTTP请求对象
            resource_type: 资源类型
            resource_id: 资源ID
            resource_name: 资源名称
            details: 操作详情
            before_data: 删除前的数据（用于恢复）
            result: 操作结果
            error_message: 错误信息
        """
        return self._create_log(
            request=request,
            action='delete',
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else '',
            resource_name=resource_name,
            details=details,
            before_data=before_data,
            after_data=None,
            result=result,
            error_message=error_message
        )
    
    def log_login(self, request, user, result='success', error_message='', details=''):
        """记录登录操作"""
        return self._create_log(
            request=request,
            action='login',
            resource_type='session',
            resource_id=str(user.id) if user else '',
            resource_name=user.email if user else '',
            details=details or f"User login: {user.email if user else 'Unknown'}",
            result=result,
            error_message=error_message
        )
    
    def log_logout(self, request, user):
        """记录登出操作"""
        return self._create_log(
            request=request,
            action='logout',
            resource_type='session',
            resource_id=str(user.id) if user else '',
            resource_name=user.email if user else '',
            details=f"User logout: {user.email if user else 'Unknown'}"
        )
    
    def log_access(self, request, resource_type, resource_id='', resource_name='',
                   details='', result='success', error_message=''):
        """记录访问操作"""
        return self._create_log(
            request=request,
            action='access',
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else '',
            resource_name=resource_name,
            details=details,
            result=result,
            error_message=error_message
        )
    
    def log_execute(self, request, resource_type, resource_id, resource_name='',
                    details='', before_data=None, after_data=None, result='success',
                    error_message=''):
        """记录执行操作（如备份、恢复、挂载等）"""
        return self._create_log(
            request=request,
            action='execute',
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else '',
            resource_name=resource_name,
            details=details,
            before_data=before_data,
            after_data=after_data,
            result=result,
            error_message=error_message
        )
    
    def log_export(self, request, resource_type, resource_id='', resource_name='',
                   details='', result='success', error_message=''):
        """记录导出操作"""
        return self._create_log(
            request=request,
            action='export',
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else '',
            resource_name=resource_name,
            details=details,
            result=result,
            error_message=error_message
        )
    
    def log_import(self, request, resource_type, resource_id='', resource_name='',
                   details='', before_data=None, after_data=None, result='success',
                   error_message=''):
        """记录导入操作"""
        return self._create_log(
            request=request,
            action='import',
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else '',
            resource_name=resource_name,
            details=details,
            before_data=before_data,
            after_data=after_data,
            result=result,
            error_message=error_message
        )
    
    def _create_log(self, request, action, resource_type, resource_id, resource_name,
                    details, before_data=None, after_data=None, changed_fields=None,
                    result='success', error_message=''):
        """创建审计日志记录"""
        user = None
        ip_address = None
        user_agent = ''
        request_method = ''
        request_path = ''
        request_query = {}
        request_body = {}
        tenant_id = None
        
        if request:
            user = getattr(request, 'user', None)
            if user and not user.is_authenticated:
                user = None
            
            # 获取真实IP（支持代理）
            ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '')
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            request_method = request.method
            request_path = request.path[:1000]
            
            # 记录租户ID
            if user and hasattr(user, 'tenant_id') and user.tenant_id:
                tenant_id = str(user.tenant_id)
            
            # 记录查询参数
            try:
                request_query = dict(request.GET) if hasattr(request, 'GET') else {}
            except Exception:
                request_query = {}
            
            # 记录请求体
            try:
                if hasattr(request, 'data'):
                    request_body = self._sanitize_request_body(request.data)
                elif hasattr(request, 'body') and request.body:
                    import json
                    try:
                        request_body = self._sanitize_request_body(json.loads(request.body.decode('utf-8')))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        request_body = {'raw': '[无法解析]'}
                else:
                    request_body = {}
            except Exception:
                request_body = {}
        
        # 构建变更字段信息
        changes = {}
        if changed_fields:
            changes['changed_fields'] = changed_fields
        if before_data:
            changes['before'] = before_data
        if after_data:
            changes['after'] = after_data
        
        return self.create(
            tenant_id=tenant_id,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            changes=changes,
            details=details,
            result=result,
            error_message=error_message,
            request_method=request_method,
            request_path=request_path,
            request_query=request_query,
            request_body=request_body
        )
    
    def _sanitize_request_body(self, data):
        """脱敏请求体中的敏感字段"""
        if not isinstance(data, dict):
            return data
        
        sensitive_fields = ['password', 'password_confirm', 'new_password', 'old_password',
                           'token', 'access_token', 'refresh_token', 'api_key', 'secret',
                           'authorization', 'credential']
        
        sanitized = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                sanitized[key] = '******'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_request_body(value)
            else:
                sanitized[key] = value
        return sanitized


class AuditLog(models.Model):
    """
    审计日志模型
    
    记录系统中所有用户操作行为，用于安全审计、合规检查、问题追溯。
    """
    
    # ==================== 操作类型 ====================
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_ACCESS = 'access'
    ACTION_EXECUTE = 'execute'
    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'
    ACTION_EXPORT = 'export'
    ACTION_IMPORT = 'import'
    ACTION_ENABLE = 'enable'
    ACTION_DISABLE = 'disable'
    
    ACTION_CHOICES = [
        (ACTION_CREATE, '创建'),
        (ACTION_UPDATE, '更新'),
        (ACTION_DELETE, '删除'),
        (ACTION_ACCESS, '访问'),
        (ACTION_EXECUTE, '执行'),
        (ACTION_LOGIN, '登录'),
        (ACTION_LOGOUT, '登出'),
        (ACTION_EXPORT, '导出'),
        (ACTION_IMPORT, '导入'),
        (ACTION_ENABLE, '启用'),
        (ACTION_DISABLE, '禁用'),
    ]
    
    # ==================== 资源类型 ====================
    RESOURCE_USER = 'user'
    RESOURCE_TENANT = 'tenant'
    RESOURCE_LICENSE = 'license'
    RESOURCE_PROXY = 'proxy'
    RESOURCE_REPOSITORY = 'repository'
    RESOURCE_BACKUP_TASK = 'backup_task'
    RESOURCE_RECOVERY_TASK = 'recovery_task'
    RESOURCE_POLICY = 'policy'
    RESOURCE_SOURCE_RESOURCE = 'source_resource'
    RESOURCE_GATEWAY = 'gateway'
    RESOURCE_SESSION = 'session'
    RESOURCE_SYSTEM = 'system'
    RESOURCE_AUDIT_LOG = 'audit_log'
    
    RESOURCE_CHOICES = [
        (RESOURCE_USER, '用户'),
        (RESOURCE_TENANT, '租户'),
        (RESOURCE_LICENSE, '许可证'),
        (RESOURCE_PROXY, '代理'),
        (RESOURCE_REPOSITORY, '存储库'),
        (RESOURCE_BACKUP_TASK, '备份任务'),
        (RESOURCE_RECOVERY_TASK, '恢复任务'),
        (RESOURCE_POLICY, '备份策略'),
        (RESOURCE_SOURCE_RESOURCE, '备份源'),
        (RESOURCE_GATEWAY, '网关'),
        (RESOURCE_SESSION, '会话'),
        (RESOURCE_SYSTEM, '系统'),
        (RESOURCE_AUDIT_LOG, '审计日志'),
    ]
    
    # ==================== 操作结果 ====================
    RESULT_SUCCESS = 'success'
    RESULT_FAILURE = 'failure'
    RESULT_PARTIAL = 'partial'
    
    RESULT_CHOICES = [
        (RESULT_SUCCESS, '成功'),
        (RESULT_FAILURE, '失败'),
        (RESULT_PARTIAL, '部分成功'),
    ]
    
    # ==================== 字段定义 ====================
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='日志ID'
    )
    
    # 时间戳
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name='操作时间'
    )
    
    # 租户信息（用于多租户隔离）
    tenant_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='租户ID'
    )
    
    # 操作者信息
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='操作用户'
    )
    user_email = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='用户邮箱',
        help_text='冗余存储，避免用户删除后无法追溯'
    )
    user_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='用户姓名',
        help_text='冗余存储，避免用户删除后无法追溯'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP地址'
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='用户代理'
    )
    
    # 操作详情
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        db_index=True,
        verbose_name='操作类型'
    )
    resource_type = models.CharField(
        max_length=50,
        choices=RESOURCE_CHOICES,
        db_index=True,
        verbose_name='资源类型'
    )
    resource_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name='资源ID'
    )
    resource_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='资源名称',
        help_text='资源显示名称，便于日志阅读'
    )
    
    # 变更详情
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='变更详情',
        help_text='包含 before、after、changed_fields 等信息'
    )
    details = models.TextField(
        blank=True,
        verbose_name='操作描述',
        help_text='人类可读的操作描述'
    )
    
    # 操作结果
    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        default=RESULT_SUCCESS,
        verbose_name='操作结果'
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='错误信息'
    )
    error_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='错误代码'
    )
    
    # 请求信息
    request_method = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='请求方法'
    )
    request_path = models.CharField(
        max_length=1000,
        blank=True,
        verbose_name='请求路径'
    )
    request_query = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='查询参数',
        help_text='URL查询参数'
    )
    request_body = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='请求体',
        help_text='请求体数据（敏感字段已脱敏）'
    )
    request_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='请求ID',
        help_text='用于追踪请求链路'
    )
    
    # 会话信息
    session_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='会话ID'
    )
    
    # 地理位置（可选，需要 IP 解析服务）
    location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='地理位置'
    )
    
    # 额外元数据
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='元数据'
    )
    
    objects = AuditLogManager()
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志'
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['tenant_id', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['result']),
        ]
    
    def __str__(self):
        user_str = self.user_email or 'System'
        return f"[{self.timestamp}] {user_str} - {self.get_action_display()} - {self.resource_type}:{self.resource_name}"
    
    def save(self, *args, **kwargs):
        # 冗余存储用户信息
        if self.user and not self.user_email:
            self.user_email = self.user.email
            self.user_name = f"{self.user.first_name} {self.user.last_name}".strip()
        super().save(*args, **kwargs)
    
    @property
    def is_success(self):
        return self.result == self.RESULT_SUCCESS
    
    @property
    def is_failure(self):
        return self.result == self.RESULT_FAILURE
    
    @property
    def changed_fields_display(self):
        """返回变更字段的友好显示"""
        if not self.changes:
            return []
        return self.changes.get('changed_fields', [])
    
    @property
    def before_data(self):
        """返回操作前的数据"""
        if not self.changes:
            return None
        return self.changes.get('before')
    
    @property
    def after_data(self):
        """返回操作后的数据"""
        if not self.changes:
            return None
        return self.changes.get('after')


# ==================== 便捷函数 ====================

def audit_log(request=None, action='', resource_type='', resource_id='',
              resource_name='', details='', changes=None, result='success',
              error_message='', user=None):
    """
    便捷的审计日志记录函数

    使用示例:
        from audit_log.models import audit_log

        # 记录创建操作
        audit_log(
            request=request,
            action='create',
            resource_type='user',
            resource_id=user.id,
            resource_name=user.email,
            details=f'创建用户: {user.email}'
        )

        # 记录更新操作
        audit_log(
            request=request,
            action='update',
            resource_type='user',
            resource_id=user.id,
            resource_name=user.email,
            changes={'changed_fields': ['email', 'name'], 'before': {...}, 'after': {...}},
            details='更新用户信息'
        )
    """
    ip_address = None
    user_agent = ''
    request_method = ''
    request_path = ''
    request_query = {}
    request_body = {}
    tenant_id = None
    session_id = ''

    if request:
        if user is None:
            user = getattr(request, 'user', None)
            if user and not user.is_authenticated:
                user = None

        # 获取真实IP
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        request_method = request.method
        request_path = request.path[:1000]

        # 获取查询参数
        try:
            if hasattr(request, 'GET'):
                request_query = dict(request.GET)
        except Exception:
            request_query = {}

        # 获取请求体（排除敏感字段）
        try:
            if hasattr(request, 'data') and request.data:
                request_body = _sanitize_request_body(request.data)
            elif hasattr(request, 'body') and request.body:
                import json
                try:
                    request_body = _sanitize_request_body(json.loads(request.body.decode('utf-8')))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    request_body = {'raw': '[无法解析]'}
        except Exception:
            request_body = {}

        if user and hasattr(user, 'tenant_id') and user.tenant_id:
            tenant_id = str(user.tenant_id)

        session_id = request.session.session_key or ''

    user_email = ''
    user_name = ''
    if user:
        user_email = user.email
        user_name = f"{user.first_name} {user.last_name}".strip()

    return AuditLog.objects.create(
        tenant_id=tenant_id,
        user=user,
        user_email=user_email,
        user_name=user_name,
        ip_address=ip_address,
        user_agent=user_agent,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else '',
        resource_name=resource_name,
        changes=changes or {},
        details=details,
        result=result,
        error_message=error_message,
        request_method=request_method,
        request_path=request_path,
        request_query=request_query,
        request_body=request_body,
        session_id=session_id
    )


def _sanitize_request_body(data):
    """
    清理请求体，移除敏感字段。

    Args:
        data: 原始请求数据

    Returns:
        清理后的数据
    """
    # 敏感字段列表
    sensitive_fields = {'password', 'token', 'secret', 'key', 'api_key', 'access_token',
                      'refresh_token', 'authorization', 'api_secret', 'private_key',
                      'pass', 'pwd', 'credential', 'captcha_code', 'captcha_key'}

    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                sanitized[key] = '[已隐藏]'
            elif isinstance(value, (dict, list)):
                sanitized[key] = _sanitize_request_body(value)
            else:
                sanitized[key] = value
        return sanitized
    elif isinstance(data, list):
        return [_sanitize_request_body(item) if isinstance(item, (dict, list)) else item for item in data]
    else:
        return data
