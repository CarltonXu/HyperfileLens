"""
HyperFileLens Backend - Audit Log Models

This module defines the audit log model for tracking system activities.
"""

import uuid
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """
    Stores audit logs for all system activities.
    """
    
    # Action type choices
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_ACCESS = 'access'
    ACTION_EXECUTE = 'execute'
    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'
    ACTION_ERROR = 'error'
    
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Create'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
        (ACTION_ACCESS, 'Access'),
        (ACTION_EXECUTE, 'Execute'),
        (ACTION_LOGIN, 'Login'),
        (ACTION_LOGOUT, 'Logout'),
        (ACTION_ERROR, 'Error'),
    ]
    
    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the action occurred"
    )
    
    # Actor information
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="User who performed the action"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the actor"
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        help_text="User agent string"
    )
    
    # Action details
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text="Type of action"
    )
    resource_type = models.CharField(
        max_length=100,
        help_text="Type of resource affected"
    )
    resource_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="ID of the affected resource"
    )
    
    # Change details
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Changes made (for updates)"
    )
    details = models.TextField(
        blank=True,
        help_text="Additional details"
    )
    
    # Result
    result = models.CharField(
        max_length=20,
        default='success',
        help_text="Result of the action"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if failed"
    )
    
    # Request information
    request_method = models.CharField(
        max_length=10,
        blank=True,
        help_text="HTTP method"
    )
    request_path = models.CharField(
        max_length=1000,
        blank=True,
        help_text="Request path"
    )
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
    
    def __str__(self):
        user_str = self.user.email if self.user else 'System'
        return f"{user_str} - {self.action} - {self.resource_type} at {self.timestamp}"


def log_action(
    user,
    action,
    resource_type,
    resource_id=None,
    details=None,
    changes=None,
    request=None,
    result='success',
    error_message=None
):
    """
    Helper function to create audit log entries.
    
    Args:
        user: User who performed the action (can be None for system actions)
        action: Action type (see ACTION_CHOICES)
        resource_type: Type of resource affected
        resource_id: ID of the affected resource
        details: Additional details
        changes: Changes made
        request: HTTP request object (optional)
        result: Result of the action
        error_message: Error message if failed
    
    Returns:
        Created AuditLog instance
    """
    ip_address = None
    user_agent = None
    request_method = None
    request_path = None
    
    if request:
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        request_method = request.method
        request_path = request.path[:1000]
    
    return AuditLog.objects.create(
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else '',
        changes=changes or {},
        details=details or '',
        result=result,
        error_message=error_message or '',
        request_method=request_method,
        request_path=request_path
    )
