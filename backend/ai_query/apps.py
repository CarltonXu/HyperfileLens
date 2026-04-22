"""
HyperFileLens Backend - AI Query Module

This module provides AI-powered query capabilities for backup data analysis.
"""

from django.apps import AppConfig


class AIQueryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_query'
    verbose_name = 'AI Query'
