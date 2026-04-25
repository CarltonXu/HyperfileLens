"""
HyperFileLens Backend - Source Resources App Configuration
"""

from django.apps import AppConfig


class SourceResourcesConfig(AppConfig):
    """App configuration for source resources management."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'source_resources'
    verbose_name = 'Source Resources'
    verbose_name_plural = 'Source Resources'
    
    def ready(self):
        """Import signal handlers when app is ready."""
        try:
            import source_resources.signals  # noqa
        except ImportError:
            pass
