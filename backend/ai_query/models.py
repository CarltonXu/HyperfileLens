"""
HyperFileLens Backend - AI Query Models

This module defines models for AI-powered backup data queries.
"""

import uuid
from django.db import models
from django.utils import timezone
from accounts.models import User
from tenants.models import Tenant


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
