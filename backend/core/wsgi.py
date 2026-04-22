"""
WSGI config for HyperFileLens project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Initialize WSGI application
application = get_wsgi_application()

# Add logging middleware if in debug mode
if os.environ.get('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes'):
    # Enable verbose logging in development
    import logging
    logging.basicConfig(level=logging.DEBUG)
