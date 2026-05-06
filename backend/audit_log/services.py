"""
HyperFileLens Backend - Audit Log Service

审计日志服务层，提供统一的审计日志记录接口。

使用方法：
1. 在 ViewSet 中使用 @audit_action 装饰器
2. 在业务逻辑中调用 AuditService 方法
3. 使用 audit_context 上下文管理器
"""

import functools
import json
from typing import Dict, Any, Optional, List, Callable
from django.http import HttpRequest
from rest_framework.request import Request

from .models import AuditLog, audit_log
from .event_models import EventLog, event_log


class AuditService:
    """
    审计日志服务
    
    提供统一的审计日志记录接口，封装常用操作。
    """
    
    # ==================== 用户相关 ====================
    
    @staticmethod
    def log_user_create(request, user, result='success', error_message=''):
        """记录用户创建"""
        return audit_log(
            request=request,
            action='create',
            resource_type='user',
            resource_id=str(user.id) if user else '',
            resource_name=user.email if user else '',
            details=f'创建用户: {user.email if user else "Unknown"}',
            changes={'after': {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'tenant_id': str(user.tenant_id) if user.tenant_id else None,
                'tenant_role': user.tenant_role,
                'is_superuser': user.is_superuser,
            }} if user else {},
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_user_update(request, user, changed_fields=None, before_data=None, after_data=None,
                        result='success', error_message=''):
        """记录用户更新"""
        details = f'更新用户: {user.email if user else "Unknown"}'
        if changed_fields:
            details += f' (变更字段: {", ".join(changed_fields)})'
        
        return audit_log(
            request=request,
            action='update',
            resource_type='user',
            resource_id=str(user.id) if user else '',
            resource_name=user.email if user else '',
            details=details,
            changes={
                'changed_fields': changed_fields or [],
                'before': before_data or {},
                'after': after_data or {},
            },
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_user_delete(request, user, result='success', error_message=''):
        """记录用户删除"""
        return audit_log(
            request=request,
            action='delete',
            resource_type='user',
            resource_id=str(user.id) if user else '',
            resource_name=user.email if user else '',
            details=f'删除用户: {user.email if user else "Unknown"}',
            changes={'before': {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }} if user else {},
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_user_login(request, user, result='success', error_message=''):
        """记录用户登录"""
        return audit_log(
            request=request,
            action='login',
            resource_type='session',
            resource_id=str(user.id) if user else '',
            resource_name=user.email if user else '',
            details=f'用户登录: {user.email if user else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_user_logout(request, user):
        """记录用户登出"""
        return audit_log(
            request=request,
            action='logout',
            resource_type='session',
            resource_id=str(user.id) if user else '',
            resource_name=user.email if user else '',
            details=f'用户登出: {user.email if user else "Unknown"}'
        )
    
    @staticmethod
    def log_password_reset(request, user, result='success', error_message=''):
        """记录密码重置"""
        return audit_log(
            request=request,
            action='update',
            resource_type='user',
            resource_id=str(user.id) if user else '',
            resource_name=user.email if user else '',
            details=f'重置密码: {user.email if user else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_role_change(request, user, old_role, new_role, result='success', error_message=''):
        """记录角色变更"""
        return audit_log(
            request=request,
            action='update',
            resource_type='user',
            resource_id=str(user.id) if user else '',
            resource_name=user.email if user else '',
            details=f'角色变更: {user.email if user else "Unknown"} ({old_role} -> {new_role})',
            changes={
                'changed_fields': ['tenant_role', 'is_superuser'],
                'before': {'role': old_role},
                'after': {'role': new_role},
            },
            result=result,
            error_message=error_message
        )
    
    # ==================== 租户相关 ====================
    
    @staticmethod
    def log_tenant_create(request, tenant, result='success', error_message=''):
        """记录租户创建"""
        return audit_log(
            request=request,
            action='create',
            resource_type='tenant',
            resource_id=str(tenant.id) if tenant else '',
            resource_name=tenant.name if tenant else '',
            details=f'创建租户: {tenant.name if tenant else "Unknown"}',
            changes={'after': {
                'name': tenant.name,
                'slug': tenant.slug,
                'plan': tenant.plan,
            }} if tenant else {},
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_tenant_update(request, tenant, changed_fields=None, before_data=None, after_data=None,
                         result='success', error_message=''):
        """记录租户更新"""
        return audit_log(
            request=request,
            action='update',
            resource_type='tenant',
            resource_id=str(tenant.id) if tenant else '',
            resource_name=tenant.name if tenant else '',
            details=f'更新租户: {tenant.name if tenant else "Unknown"}',
            changes={
                'changed_fields': changed_fields or [],
                'before': before_data or {},
                'after': after_data or {},
            },
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_tenant_delete(request, tenant, result='success', error_message=''):
        """记录租户删除"""
        return audit_log(
            request=request,
            action='delete',
            resource_type='tenant',
            resource_id=str(tenant.id) if tenant else '',
            resource_name=tenant.name if tenant else '',
            details=f'删除租户: {tenant.name if tenant else "Unknown"}',
            changes={'before': {
                'name': tenant.name,
                'slug': tenant.slug,
            }} if tenant else {},
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_tenant_activate(request, tenant, result='success', error_message=''):
        """记录租户激活"""
        return audit_log(
            request=request,
            action='enable',
            resource_type='tenant',
            resource_id=str(tenant.id) if tenant else '',
            resource_name=tenant.name if tenant else '',
            details=f'激活租户: {tenant.name if tenant else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_tenant_deactivate(request, tenant, result='success', error_message=''):
        """记录租户停用"""
        return audit_log(
            request=request,
            action='disable',
            resource_type='tenant',
            resource_id=str(tenant.id) if tenant else '',
            resource_name=tenant.name if tenant else '',
            details=f'停用租户: {tenant.name if tenant else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_tenant_add_user(request, tenant, user, result='success', error_message=''):
        """记录租户添加用户"""
        return audit_log(
            request=request,
            action='update',
            resource_type='tenant',
            resource_id=str(tenant.id) if tenant else '',
            resource_name=tenant.name if tenant else '',
            details=f'添加用户到租户: {user.email if user else "Unknown"} -> {tenant.name if tenant else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_tenant_remove_user(request, tenant, user, result='success', error_message=''):
        """记录租户移除用户"""
        return audit_log(
            request=request,
            action='update',
            resource_type='tenant',
            resource_id=str(tenant.id) if tenant else '',
            resource_name=tenant.name if tenant else '',
            details=f'从租户移除用户: {user.email if user else "Unknown"} <- {tenant.name if tenant else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    # ==================== 代理相关 ====================
    
    @staticmethod
    def log_proxy_create(request, proxy, result='success', error_message=''):
        """记录代理创建"""
        return audit_log(
            request=request,
            action='create',
            resource_type='proxy',
            resource_id=str(proxy.id) if proxy else '',
            resource_name=proxy.name if proxy else '',
            details=f'创建代理: {proxy.name if proxy else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_proxy_delete(request, proxy, result='success', error_message=''):
        """记录代理删除"""
        return audit_log(
            request=request,
            action='delete',
            resource_type='proxy',
            resource_id=str(proxy.id) if proxy else '',
            resource_name=proxy.name if proxy else '',
            details=f'删除代理: {proxy.name if proxy else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_proxy_update(request, proxy, changed_fields=None, before_data=None, after_data=None,
                         result='success', error_message=''):
        """记录代理更新"""
        details = f'更新代理: {proxy.name if proxy else "Unknown"}'
        if changed_fields:
            details += f' (变更字段: {", ".join(changed_fields)})'
        return audit_log(
            request=request,
            action='update',
            resource_type='proxy',
            resource_id=str(proxy.id) if proxy else '',
            resource_name=proxy.name if proxy else '',
            details=details,
            changes={
                'changed_fields': changed_fields or [],
                'before': before_data or {},
                'after': after_data or {},
            },
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_proxy_token_regenerate(request, proxy, result='success', error_message=''):
        """记录代理令牌重新生成"""
        return audit_log(
            request=request,
            action='execute',
            resource_type='proxy',
            resource_id=str(proxy.id) if proxy else '',
            resource_name=proxy.name if proxy else '',
            details=f'重新生成代理令牌: {proxy.name if proxy else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_proxy_activate(request, proxy, result='success', error_message=''):
        """记录代理激活"""
        return audit_log(
            request=request,
            action='execute',
            resource_type='proxy',
            resource_id=str(proxy.id) if proxy else '',
            resource_name=proxy.name if proxy else '',
            details=f'激活代理: {proxy.name if proxy else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_proxy_deactivate(request, proxy, result='success', error_message=''):
        """记录代理停用"""
        return audit_log(
            request=request,
            action='execute',
            resource_type='proxy',
            resource_id=str(proxy.id) if proxy else '',
            resource_name=proxy.name if proxy else '',
            details=f'停用代理: {proxy.name if proxy else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    # ==================== 网关相关 ====================
    
    @staticmethod
    def log_gateway_create(request, gateway, result='success', error_message=''):
        """记录网关创建"""
        return audit_log(
            request=request,
            action='create',
            resource_type='gateway',
            resource_id=str(gateway.id) if gateway else '',
            resource_name=gateway.name if gateway else '',
            details=f'创建网关: {gateway.name if gateway else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_gateway_delete(request, gateway, result='success', error_message=''):
        """记录网关删除"""
        return audit_log(
            request=request,
            action='delete',
            resource_type='gateway',
            resource_id=str(gateway.id) if gateway else '',
            resource_name=gateway.name if gateway else '',
            details=f'删除网关: {gateway.name if gateway else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_gateway_update(request, gateway, changed_fields=None, before_data=None, after_data=None,
                           result='success', error_message=''):
        """记录网关更新"""
        details = f'更新网关: {gateway.name if gateway else "Unknown"}'
        if changed_fields:
            details += f' (变更字段: {", ".join(changed_fields)})'
        return audit_log(
            request=request,
            action='update',
            resource_type='gateway',
            resource_id=str(gateway.id) if gateway else '',
            resource_name=gateway.name if gateway else '',
            details=details,
            changes={
                'changed_fields': changed_fields or [],
                'before': before_data or {},
                'after': after_data or {},
            },
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_gateway_token_regenerate(request, gateway, result='success', error_message=''):
        """记录网关令牌重新生成"""
        return audit_log(
            request=request,
            action='execute',
            resource_type='gateway',
            resource_id=str(gateway.id) if gateway else '',
            resource_name=gateway.name if gateway else '',
            details=f'重新生成网关令牌: {gateway.name if gateway else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_gateway_activate(request, gateway, result='success', error_message=''):
        """记录网关激活"""
        return audit_log(
            request=request,
            action='execute',
            resource_type='gateway',
            resource_id=str(gateway.id) if gateway else '',
            resource_name=gateway.name if gateway else '',
            details=f'激活网关: {gateway.name if gateway else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_gateway_deactivate(request, gateway, result='success', error_message=''):
        """记录网关停用"""
        return audit_log(
            request=request,
            action='execute',
            resource_type='gateway',
            resource_id=str(gateway.id) if gateway else '',
            resource_name=gateway.name if gateway else '',
            details=f'停用网关: {gateway.name if gateway else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    # ==================== 许可证相关 ====================
    
    @staticmethod
    def log_license_activate(request, license_obj, result='success', error_message=''):
        """记录许可证激活"""
        return audit_log(
            request=request,
            action='execute',
            resource_type='license',
            resource_id=str(license_obj.id) if license_obj else '',
            resource_name=license_obj.license_key[:20] + '...' if license_obj else '',
            details=f'激活许可证',
            result=result,
            error_message=error_message
        )
    
    # ==================== 仓库相关 ====================
    
    @staticmethod
    def log_repository_create(request, repository, result='success', error_message=''):
        """记录仓库创建"""
        return audit_log(
            request=request,
            action='create',
            resource_type='repository',
            resource_id=str(repository.id) if repository else '',
            resource_name=repository.name if repository else '',
            details=f'创建仓库: {repository.name if repository else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_repository_update(request, repository, changed_fields=None, result='success', error_message=''):
        """记录仓库更新"""
        details = f'更新仓库: {repository.name if repository else "Unknown"}'
        if changed_fields:
            details += f' (变更字段: {", ".join(changed_fields)})'
        return audit_log(
            request=request,
            action='update',
            resource_type='repository',
            resource_id=str(repository.id) if repository else '',
            resource_name=repository.name if repository else '',
            details=details,
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_repository_delete(request, repository, result='success', error_message=''):
        """记录仓库删除"""
        return audit_log(
            request=request,
            action='delete',
            resource_type='repository',
            resource_id=str(repository.id) if repository else '',
            resource_name=repository.name if repository else '',
            details=f'删除仓库: {repository.name if repository else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_repository_connect(request, repository, result='success', error_message=''):
        """记录仓库连接"""
        return audit_log(
            request=request,
            action='access',
            resource_type='repository',
            resource_id=str(repository.id) if repository else '',
            resource_name=repository.name if repository else '',
            details=f'连接仓库: {repository.name if repository else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    # ==================== 策略相关 ====================
    
    @staticmethod
    def log_policy_create(request, policy, result='success', error_message=''):
        """记录策略创建"""
        return audit_log(
            request=request,
            action='create',
            resource_type='policy',
            resource_id=str(policy.id) if policy else '',
            resource_name=policy.name if policy else '',
            details=f'创建策略: {policy.name if policy else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_policy_update(request, policy, changed_fields=None, result='success', error_message=''):
        """记录策略更新"""
        details = f'更新策略: {policy.name if policy else "Unknown"}'
        if changed_fields:
            details += f' (变更字段: {", ".join(changed_fields)})'
        return audit_log(
            request=request,
            action='update',
            resource_type='policy',
            resource_id=str(policy.id) if policy else '',
            resource_name=policy.name if policy else '',
            details=details,
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_policy_delete(request, policy, result='success', error_message=''):
        """记录策略删除"""
        return audit_log(
            request=request,
            action='delete',
            resource_type='policy',
            resource_id=str(policy.id) if policy else '',
            resource_name=policy.name if policy else '',
            details=f'删除策略: {policy.name if policy else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    # ==================== 备份任务相关 ====================
    
    @staticmethod
    def log_backup_task_create(request, task, result='success', error_message=''):
        """记录备份任务创建"""
        return audit_log(
            request=request,
            action='create',
            resource_type='backup_task',
            resource_id=str(task.id) if task else '',
            resource_name=task.name if task else '',
            details=f'创建备份任务: {task.name if task else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_backup_task_update(request, task, changed_fields=None, result='success', error_message=''):
        """记录备份任务更新"""
        details = f'更新备份任务: {task.name if task else "Unknown"}'
        if changed_fields:
            details += f' (变更字段: {", ".join(changed_fields)})'
        return audit_log(
            request=request,
            action='update',
            resource_type='backup_task',
            resource_id=str(task.id) if task else '',
            resource_name=task.name if task else '',
            details=details,
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_backup_task_delete(request, task, result='success', error_message=''):
        """记录备份任务删除"""
        return audit_log(
            request=request,
            action='delete',
            resource_type='backup_task',
            resource_id=str(task.id) if task else '',
            resource_name=task.name if task else '',
            details=f'删除备份任务: {task.name if task else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_backup_task_execute(request, task, result='success', error_message=''):
        """记录备份任务执行"""
        return audit_log(
            request=request,
            action='execute',
            resource_type='backup_task',
            resource_id=str(task.id) if task else '',
            resource_name=task.name if task else '',
            details=f'执行备份任务: {task.name if task else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    # ==================== 源资源相关 ====================
    
    @staticmethod
    def log_source_resource_create(request, resource, result='success', error_message=''):
        """记录源资源创建"""
        return audit_log(
            request=request,
            action='create',
            resource_type='source_resource',
            resource_id=str(resource.id) if resource else '',
            resource_name=resource.name if resource else '',
            details=f'创建源资源: {resource.name if resource else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_source_resource_update(request, resource, changed_fields=None, result='success', error_message=''):
        """记录源资源更新"""
        details = f'更新源资源: {resource.name if resource else "Unknown"}'
        if changed_fields:
            details += f' (变更字段: {", ".join(changed_fields)})'
        return audit_log(
            request=request,
            action='update',
            resource_type='source_resource',
            resource_id=str(resource.id) if resource else '',
            resource_name=resource.name if resource else '',
            details=details,
            result=result,
            error_message=error_message
        )
    
    @staticmethod
    def log_source_resource_delete(request, resource, result='success', error_message=''):
        """记录源资源删除"""
        return audit_log(
            request=request,
            action='delete',
            resource_type='source_resource',
            resource_id=str(resource.id) if resource else '',
            resource_name=resource.name if resource else '',
            details=f'删除源资源: {resource.name if resource else "Unknown"}',
            result=result,
            error_message=error_message
        )
    
    # ==================== 通用方法 ====================
    
    @staticmethod
    def log_custom(request, action, resource_type, resource_id='', resource_name='',
                   details='', changes=None, result='success', error_message=''):
        """记录自定义审计日志"""
        return audit_log(
            request=request,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details,
            changes=changes,
            result=result,
            error_message=error_message
        )


class EventService:
    """
    事件日志服务
    
    提供统一的事件日志记录接口。
    """
    
    # ==================== 系统事件 ====================
    
    @staticmethod
    def log_system_start(details=None):
        """记录系统启动"""
        return event_log(
            event_type='system',
            event_name='system.start',
            message='System started',
            details=details
        )
    
    @staticmethod
    def log_system_stop(details=None):
        """记录系统停止"""
        return event_log(
            event_type='system',
            event_name='system.stop',
            message='System stopped',
            details=details
        )
    
    # ==================== 代理事件 ====================
    
    @staticmethod
    def log_proxy_online(proxy_id, proxy_name, tenant_id=None, details=None):
        """记录代理上线"""
        return event_log(
            event_type='system',
            event_name='proxy.online',
            message=f'Proxy {proxy_name} is now online',
            severity='info',
            source='proxy_service',
            resource_type='proxy',
            resource_id=str(proxy_id),
            tenant_id=tenant_id,
            details=details
        )
    
    @staticmethod
    def log_proxy_offline(proxy_id, proxy_name, tenant_id=None, details=None):
        """记录代理下线"""
        return event_log(
            event_type='system',
            event_name='proxy.offline',
            message=f'Proxy {proxy_name} is now offline',
            severity='warning',
            source='proxy_service',
            resource_type='proxy',
            resource_id=str(proxy_id),
            tenant_id=tenant_id,
            details=details
        )
    
    @staticmethod
    def log_proxy_error(proxy_id, proxy_name, error_message, tenant_id=None, details=None):
        """记录代理错误"""
        return event_log(
            event_type='alert',
            event_name='proxy.error',
            message=f'Proxy {proxy_name} error: {error_message}',
            severity='error',
            source='proxy_service',
            resource_type='proxy',
            resource_id=str(proxy_id),
            tenant_id=tenant_id,
            details=details
        )
    
    # ==================== 备份事件 ====================
    
    @staticmethod
    def log_backup_started(task_id, task_name, tenant_id=None, user=None, details=None):
        """记录备份开始"""
        return event_log(
            event_type='business',
            event_name='backup.started',
            message=f'Backup task started: {task_name}',
            severity='info',
            source='backup_service',
            resource_type='backup_task',
            resource_id=str(task_id),
            tenant_id=tenant_id,
            user=user,
            details=details
        )
    
    @staticmethod
    def log_backup_completed(task_id, task_name, tenant_id=None, user=None, details=None):
        """记录备份完成"""
        return event_log(
            event_type='business',
            event_name='backup.completed',
            message=f'Backup task completed: {task_name}',
            severity='info',
            source='backup_service',
            resource_type='backup_task',
            resource_id=str(task_id),
            tenant_id=tenant_id,
            user=user,
            details=details
        )
    
    @staticmethod
    def log_backup_failed(task_id, task_name, error_message, tenant_id=None, user=None, details=None):
        """记录备份失败"""
        return event_log(
            event_type='alert',
            event_name='backup.failed',
            message=f'Backup task failed: {task_name} - {error_message}',
            severity='error',
            source='backup_service',
            resource_type='backup_task',
            resource_id=str(task_id),
            tenant_id=tenant_id,
            user=user,
            details=details
        )
    
    # ==================== 安全事件 ====================
    
    @staticmethod
    def log_login_failed(email, ip_address, reason='', details=None):
        """记录登录失败"""
        return event_log(
            event_type='security',
            event_name='security.login_failed',
            message=f'Login failed for {email} from {ip_address}',
            severity='warning',
            source='auth_service',
            resource_type='session',
            details={'email': email, 'ip_address': ip_address, 'reason': reason, **(details or {})}
        )
    
    @staticmethod
    def log_brute_force_detected(ip_address, attempt_count, details=None):
        """记录暴力破解检测"""
        return event_log(
            event_type='security',
            event_name='security.brute_force',
            message=f'Brute force attack detected from {ip_address} ({attempt_count} attempts)',
            severity='critical',
            source='auth_service',
            details={'ip_address': ip_address, 'attempt_count': attempt_count, **(details or {})}
        )
    
    @staticmethod
    def log_suspicious_activity(user, activity, details=None):
        """记录可疑活动"""
        return event_log(
            event_type='security',
            event_name='security.suspicious_activity',
            message=f'Suspicious activity detected: {activity}',
            severity='warning',
            source='security_service',
            resource_type='user',
            resource_id=str(user.id) if user else '',
            user=user,
            details=details
        )
    
    # ==================== 存储事件 ====================
    
    @staticmethod
    def log_storage_low(repository_id, repository_name, usage_percent, tenant_id=None, details=None):
        """记录存储空间不足"""
        return event_log(
            event_type='alert',
            event_name='storage.low',
            message=f'Storage space low for {repository_name}: {usage_percent}% used',
            severity='warning',
            source='storage_service',
            resource_type='repository',
            resource_id=str(repository_id),
            tenant_id=tenant_id,
            details={'usage_percent': usage_percent, **(details or {})}
        )
    
    @staticmethod
    def log_storage_critical(repository_id, repository_name, usage_percent, tenant_id=None, details=None):
        """记录存储空间严重不足"""
        return event_log(
            event_type='alert',
            event_name='storage.critical',
            message=f'Storage space critical for {repository_name}: {usage_percent}% used',
            severity='critical',
            source='storage_service',
            resource_type='repository',
            resource_id=str(repository_id),
            tenant_id=tenant_id,
            details={'usage_percent': usage_percent, **(details or {})}
        )
    
    # ==================== 许可证事件 ====================
    
    @staticmethod
    def log_license_expiring(license_id, days_left, tenant_id=None, details=None):
        """记录许可证即将过期"""
        return event_log(
            event_type='alert',
            event_name='license.expiring',
            message=f'License will expire in {days_left} days',
            severity='warning',
            source='license_service',
            resource_type='license',
            resource_id=str(license_id),
            tenant_id=tenant_id,
            details={'days_left': days_left, **(details or {})}
        )
    
    @staticmethod
    def log_license_expired(license_id, tenant_id=None, details=None):
        """记录许可证已过期"""
        return event_log(
            event_type='alert',
            event_name='license.expired',
            message='License has expired',
            severity='critical',
            source='license_service',
            resource_type='license',
            resource_id=str(license_id),
            tenant_id=tenant_id,
            details=details
        )
    
    # ==================== 通用方法 ====================
    
    @staticmethod
    def log_custom(event_type, event_name, message, severity='info', source='',
                   resource_type='', resource_id='', tenant_id=None, user=None, details=None):
        """记录自定义事件"""
        return event_log(
            event_type=event_type,
            event_name=event_name,
            message=message,
            severity=severity,
            source=source,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            user=user,
            details=details
        )


# ==================== 装饰器 ====================

def audit_action(action, resource_type, get_resource_id=None, get_resource_name=None):
    """
    审计日志装饰器
    
    用于自动记录 ViewSet 方法的审计日志。
    
    使用示例:
        @audit_action('create', 'user')
        def create(self, request, *args, **kwargs):
            response = super().create(request, *args, **kwargs)
            return response
    
    Args:
        action: 操作类型 ('create', 'update', 'delete', etc.)
        resource_type: 资源类型 ('user', 'tenant', etc.)
        get_resource_id: 获取资源ID的函数，签名: (response, view, request) -> str
        get_resource_name: 获取资源名称的函数，签名: (response, view, request) -> str
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, request, *args, **kwargs):
            result = 'success'
            error_message = ''
            response = None
            resource_id = ''
            resource_name = ''
            
            try:
                response = func(self, request, *args, **kwargs)
                
                # 尝试获取资源信息
                if get_resource_id:
                    try:
                        resource_id = get_resource_id(response, self, request)
                    except Exception:
                        pass
                
                if get_resource_name:
                    try:
                        resource_name = get_resource_name(response, self, request)
                    except Exception:
                        pass
                
                # 从响应数据中获取资源信息
                if not resource_id and response and hasattr(response, 'data'):
                    data = response.data if isinstance(response.data, dict) else {}
                    resource_id = str(data.get('id', ''))
                    resource_name = data.get('name', '') or data.get('email', '')
                
            except Exception as e:
                result = 'failure'
                error_message = str(e)
                raise
            
            finally:
                # 记录审计日志
                try:
                    audit_log(
                        request=request,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        resource_name=resource_name,
                        details=f'{action} {resource_type}',
                        result=result,
                        error_message=error_message
                    )
                except Exception:
                    pass  # 日志记录失败不影响业务
            
            return response
        
        return wrapper
    return decorator


class audit_context:
    """
    审计日志上下文管理器
    
    用于在代码块中自动记录审计日志。
    
    使用示例:
        with audit_context(request, 'create', 'user') as ctx:
            user = User.objects.create(email='test@test.com')
            ctx.resource_id = str(user.id)
            ctx.resource_name = user.email
            ctx.details = f'创建用户: {user.email}'
    """
    
    def __init__(self, request, action, resource_type, resource_id='', resource_name='',
                 details='', result='success'):
        self.request = request
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.resource_name = resource_name
        self.details = details
        self.result = result
        self.error_message = ''
        self._exception = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.result = 'failure'
            self.error_message = str(exc_val)
        
        try:
            audit_log(
                request=self.request,
                action=self.action,
                resource_type=self.resource_type,
                resource_id=self.resource_id,
                resource_name=self.resource_name,
                details=self.details,
                result=self.result,
                error_message=self.error_message
            )
        except Exception:
            pass
        
        return False  # 不抑制异常
