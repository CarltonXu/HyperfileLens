"""
HyperFileLens Backend - AI Query Models

This module defines models for AI-powered backup data queries.
"""

import uuid
from django.db import models
from django.utils import timezone
from accounts.models import User
from tenants.models import Tenant
from common.encryption import decrypt_value, encrypt_value, is_encrypted, mask_access_key


class AIQuery(models.Model):
    """
    Represents an AI query request for analyzing backup data.
    """
    
    # Status choices
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]
    
    # Query type choices
    TYPE_SEARCH = 'search'
    TYPE_ANALYSIS = 'analysis'
    TYPE_SUMMARY = 'summary'
    TYPE_COMPARISON = 'comparison'
    
    TYPE_CHOICES = [
        (TYPE_SEARCH, 'Search'),
        (TYPE_ANALYSIS, 'Analysis'),
        (TYPE_SUMMARY, 'Summary'),
        (TYPE_COMPARISON, 'Comparison'),
    ]
    
    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query_text = models.TextField(help_text="User's query text")
    
    # Query configuration
    query_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_SEARCH,
        help_text="Type of query"
    )
    target_paths = models.JSONField(
        default=list,
        blank=True,
        help_text="Paths to search/analyze"
    )
    file_types = models.JSONField(
        default=list,
        blank=True,
        help_text="File types to focus on"
    )
    
    # Results
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text="Query status"
    )
    result = models.JSONField(
        default=dict,
        blank=True,
        help_text="Query results"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if failed"
    )
    
    # AI model information
    model_used = models.CharField(
        max_length=100,
        blank=True,
        help_text="AI model used for query"
    )
    tokens_used = models.IntegerField(
        default=0,
        help_text="Number of tokens used"
    )
    
    # Metadata
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='ai_queries',
        null=True,
        blank=True,
        help_text="Tenant who owns this query"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_queries',
        help_text="User who made the query"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When query completed"
    )
    
    class Meta:
        db_table = 'ai_queries'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.query_text[:50]}... ({self.get_status_display()})"
    
    @property
    def duration(self):
        """Calculate query duration in seconds."""
        if self.created_at and self.completed_at:
            return (self.completed_at - self.created_at).total_seconds()
        return None
    
    def mark_processing(self):
        """Mark query as processing."""
        self.status = self.STATUS_PROCESSING
        self.save(update_fields=['status'])
    
    def mark_completed(self, result, model_used=None, tokens_used=0):
        """Mark query as completed with results."""
        self.status = self.STATUS_COMPLETED
        self.result = result
        self.completed_at = timezone.now()
        self.model_used = model_used or ''
        self.tokens_used = tokens_used
        self.save(update_fields=['status', 'result', 'completed_at', 'model_used', 'tokens_used'])
    
    def mark_failed(self, error_message):
        """Mark query as failed."""
        self.status = self.STATUS_FAILED
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])


class AIFeature(models.Model):
    """
    Stores AI feature configuration and capabilities.
    """
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Feature name"
    )
    description = models.TextField(
        blank=True,
        help_text="Feature description"
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="Whether feature is enabled"
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Feature configuration"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ai_features'
    
    def __str__(self):
        return self.name


class AIProvider(models.Model):
    """Platform-side AI provider configuration used by Gateway AI tasks."""

    PROVIDER_OPENAI_COMPATIBLE = 'openai_compatible'
    PROVIDER_OPENAI = 'openai'
    PROVIDER_LOCAL = 'local'

    PROVIDER_CHOICES = [
        (PROVIDER_OPENAI_COMPATIBLE, 'OpenAI Compatible'),
        (PROVIDER_OPENAI, 'OpenAI'),
        (PROVIDER_LOCAL, 'Local Fallback'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='ai_providers',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    provider_type = models.CharField(
        max_length=32,
        choices=PROVIDER_CHOICES,
        default=PROVIDER_OPENAI_COMPATIBLE,
    )
    base_url = models.URLField(blank=True, default='https://api.openai.com/v1')
    api_key = models.TextField(blank=True)
    default_model = models.CharField(max_length=128, blank=True, default='gpt-4.1-mini')
    timeout_seconds = models.PositiveIntegerField(default=60)
    is_enabled = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    config = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_ai_providers',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_providers'
        ordering = ['-is_default', 'name']
        indexes = [
            models.Index(fields=['tenant', 'is_enabled']),
            models.Index(fields=['tenant', 'is_default']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='uniq_tenant_ai_provider_name'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.api_key and not is_encrypted(self.api_key):
            self.api_key = encrypt_value(self.api_key)
        super().save(*args, **kwargs)
        if self.is_default:
            AIProvider.objects.filter(tenant=self.tenant, is_default=True).exclude(id=self.id).update(is_default=False)

    def get_decrypted_api_key(self):
        if not self.api_key:
            return ''
        try:
            return decrypt_value(self.api_key)
        except Exception:
            return self.api_key

    def get_masked_api_key(self):
        return mask_access_key(self.get_decrypted_api_key())

    def to_gateway_config(self):
        return {
            'enabled': self.is_enabled,
            'provider': self.provider_type,
            'base_url': self.base_url,
            'api_key': self.get_decrypted_api_key(),
            'model': self.default_model,
            'timeout': self.timeout_seconds,
            'config': self.config or {},
        }
