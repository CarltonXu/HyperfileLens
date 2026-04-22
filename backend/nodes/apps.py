"""
Nodes Application Configuration

This module configures the nodes Django application.
"""

from django.apps import AppConfig


class NodesConfig(AppConfig):
    """
    Configuration class for the nodes application.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nodes'
    verbose_name = 'Node Management'
    description = 'Source proxy and target gateway node management'

    def ready(self):
        """
        Called when Django starts up.

        Import signals to ensure they are registered.
        """
        pass
