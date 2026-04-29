"""
HyperFileLens Backend - Audit Log Module

审计日志模块，提供审计日志和事件日志功能。
"""


def get_audit_log():
    """延迟导入 AuditLog"""
    from .models import AuditLog
    return AuditLog


def get_audit_log_func():
    """延迟导入 audit_log 函数"""
    from .models import audit_log
    return audit_log


def get_event_log():
    """延迟导入 EventLog"""
    from .event_models import EventLog
    return EventLog


def get_event_log_func():
    """延迟导入 event_log 函数"""
    from .event_models import event_log
    return event_log


# 导出延迟加载函数
__all__ = [
    'get_audit_log',
    'get_audit_log_func',
    'get_event_log',
    'get_event_log_func',
]
