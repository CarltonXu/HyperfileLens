"""
Accounts Application Configuration

This module configures the accounts Django application,
including user model customization and app-specific settings.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """
    Configuration class for the accounts application.

    This class configures the app name, default auto field,
    and any app-specific initialization logic.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'User Accounts'
    description = 'User authentication, authorization, and profile management'

    def ready(self):
        """
        Called when Django starts up.

        Import signals to ensure they are registered.
        """
        # Import signals to register them
        pass
