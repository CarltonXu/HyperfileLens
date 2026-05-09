"""
Django middleware for HyperFileLens.

This module provides custom middleware for request processing,
logging, and other cross-cutting concerns.
"""

import uuid
import time
import logging
from django.utils import timezone

from .logging_config import RequestContext, get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware:
    """
    Middleware that logs all requests with structured context.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.request_id = request_id

        # Add request ID to response headers
        response = self.get_response(request)
        response['X-Request-ID'] = request_id

        return response


class RequestContextMiddleware:
    """
    Middleware that adds request context to all log records.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Build request context
        context_kwargs = {
            'request_id': getattr(request, 'request_id', str(uuid.uuid4())),
            'path': request.path,
            'method': request.method,
        }

        # Add user context if authenticated
        if hasattr(request, 'user') and request.user.is_authenticated:
            context_kwargs['user_id'] = str(request.user.id)
            context_kwargs['username'] = request.user.username

            # Add tenant context if available
            if hasattr(request.user, 'tenant_id'):
                context_kwargs['tenant_id'] = str(request.user.tenant_id)

        # Add proxy context if available
        if hasattr(request, 'proxy_id'):
            context_kwargs['proxy_id'] = str(request.proxy_id)

        # Use context manager for request
        with RequestContext(**context_kwargs):
            start_time = time.time()
            response = self.get_response(request)

            # Log request completion
            duration = time.time() - start_time
            log_data = {
                'status_code': response.status_code,
                'duration_ms': int(duration * 1000),
                'path': request.path,
                'method': request.method,
            }

            if response.status_code >= 400:
                log_data['level'] = 'WARNING'
                logger.warning(f"{request.method} {request.path} completed", extra=log_data)
            else:
                logger.info(f"{request.method} {request.path} completed", extra=log_data)

            return response


class RequestTimingMiddleware:
    """
    Middleware that tracks request timing for performance monitoring.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        request.start_time = start_time

        response = self.get_response(request)

        duration = time.time() - start_time
        response['X-Response-Time'] = f'{int(duration * 1000)}ms'

        # Log slow requests
        if duration > 1.0:  # Log requests taking more than 1 second
            logger.warning(
                f"Slow request detected",
                extra={
                    'path': request.path,
                    'method': request.method,
                    'duration_ms': int(duration * 1000),
                    'status_code': response.status_code,
                }
            )

        return response


class SecurityHeadersMiddleware:
    """
    Middleware that adds security headers to all responses.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # HSTS (only in production with HTTPS)
        if not DEBUG and request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response


class TenantContextMiddleware:
    """
    Middleware that adds tenant context to requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Try to get tenant from various sources
        tenant_id = None

        # From authenticated user
        if hasattr(request, 'user') and request.user.is_authenticated:
            tenant_id = getattr(request.user, 'tenant_id', None)

        # From request headers (for API requests)
        if not tenant_id:
            tenant_id = request.META.get('HTTP_X_TENANT_ID')

        # From query parameter (for testing)
        if not tenant_id:
            tenant_id = request.GET.get('tenant_id')

        # Store tenant in request
        if tenant_id:
            request.tenant_id = tenant_id

        response = self.get_response(request)
        return response
