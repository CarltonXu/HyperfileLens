"""
HyperFileLens Backend - Policies Models

This module defines backup policy models for scheduling and retention rules.
"""

import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta
from accounts.models import User


class BackupPolicy(models.Model):
    """
    Represents a backup policy that defines scheduling and retention rules.
    """
    
    # Frequency choices
    FREQUENCY_MANUAL = 'manual'
    FREQUENCY_HOURLY = 'hourly'
    FREQUENCY_DAILY = 'daily'
    FREQUENCY_WEEKLY = 'weekly'
    FREQUENCY_MONTHLY = 'monthly'
    
    FREQUENCY_CHOICES = [
        (FREQUENCY_MANUAL, 'Manual'),
        (FREQUENCY_HOURLY, 'Hourly'),
        (FREQUENCY_DAILY, 'Daily'),
        (FREQUENCY_WEEKLY, 'Weekly'),
        (FREQUENCY_MONTHLY, 'Monthly'),
    ]
    
    # Backup type choices
    TYPE_FULL = 'full'
    TYPE_INCREMENTAL = 'incremental'
    TYPE_DIFFERENTIAL = 'differential'
    
    TYPE_CHOICES = [
        (TYPE_FULL, 'Full Backup'),
        (TYPE_INCREMENTAL, 'Incremental Backup'),
        (TYPE_DIFFERENTIAL, 'Differential Backup'),
    ]
    
    # Day choices for weekly/monthly
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Policy name")
    description = models.TextField(blank=True, help_text="Policy description")
    
    # Schedule configuration
    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default=FREQUENCY_DAILY,
        help_text="Backup frequency"
    )
    backup_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_FULL,
        help_text="Type of backup to perform"
    )
    
    # Time configuration (for scheduled backups)
    schedule_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time of day to run backup"
    )
    schedule_day = models.IntegerField(
        null=True,
        blank=True,
        help_text="Day of week/month for backup"
    )
    
    # Retention settings
    retention_days = models.IntegerField(
        default=30,
        help_text="Number of days to retain backups"
    )
    retention_snapshots = models.IntegerField(
        default=10,
        help_text="Maximum number of snapshots to keep"
    )
    retention_before_backup = models.BooleanField(
        default=True,
        help_text="Keep snapshots before running new backup"
    )
    
    # Options
    compression_enabled = models.BooleanField(
        default=True,
        help_text="Enable compression"
    )
    encryption_enabled = models.BooleanField(
        default=False,
        help_text="Enable encryption"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this policy is active"
    )
    
    # Metadata
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='backup_policies',
        help_text="Policy owner"
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='policies',
        help_text='Tenant this policy belongs to'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'backup_policies'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
    
    def get_next_run_time(self):
        """Calculate the next scheduled run time."""
        if self.frequency == self.FREQUENCY_MANUAL:
            return None
        
        now = timezone.now()
        
        if self.schedule_time:
            # Calculate next run based on schedule time
            naive_time = self.schedule_time
            next_run = now.replace(
                hour=naive_time.hour,
                minute=naive_time.minute,
                second=0,
                microsecond=0
            )
            
            if self.frequency == self.FREQUENCY_HOURLY:
                # Next hour at the scheduled minute
                if next_run <= now:
                    next_run += timedelta(hours=1)
            elif self.frequency == self.FREQUENCY_DAILY:
                if next_run <= now:
                    next_run += timedelta(days=1)
            elif self.frequency == self.FREQUENCY_WEEKLY:
                current_day = now.weekday()
                target_day = self.schedule_day or 0
                days_ahead = target_day - current_day
                if days_ahead <= 0:
                    days_ahead += 7
                next_run += timedelta(days=days_ahead)
            elif self.frequency == self.FREQUENCY_MONTHLY:
                # First day of next month
                if next_run.day != (self.schedule_day or 1):
                    next_run = next_run.replace(day=self.schedule_day or 1)
                if next_run <= now:
                    if next_run.month == 12:
                        next_run = next_run.replace(year=next_run.year + 1, month=1)
                    else:
                        next_run = next_run.replace(month=next_run.month + 1)
            
            return next_run
        
        return None
