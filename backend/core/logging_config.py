"""
Structured logging configuration for HyperFileLens.

This module provides a centralized logging configuration with support for
both text and JSON formats, making logs easier to parse and analyze.
"""

import json
import logging
import logging.config
import os
import sys
from datetime import datetime
from pathlib import Path

# Project root
BASE_DIR = Path(__file__).resolve().parent.parent


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs in JSON format for easier parsing and analysis by log aggregation tools.
    """

    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread,
        }

        # Add request_id if available (from middleware)
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id

        # Add user_id if available (from middleware)
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id

        # Add tenant_id if available (from middleware)
        if hasattr(record, 'tenant_id'):
            log_entry['tenant_id'] = record.tenant_id

        # Add task_id if available (from async tasks)
        if hasattr(record, 'task_id'):
            log_entry['task_id'] = record.task_id

        # Add proxy_id if available (from WebSocket consumers)
        if hasattr(record, 'proxy_id'):
            log_entry['proxy_id'] = record.proxy_id

        # Add extra fields if provided
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for better readability in development.
    """

    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        reset = self.RESET
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


def get_logging_config(debug=False, log_level=None, log_format='text'):
    """
    Get logging configuration.

    Args:
        debug: Whether debug mode is enabled
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR)
        log_format: Log format ('text' or 'json')

    Returns:
        Logging configuration dictionary
    """
    if not log_level:
        log_level = 'DEBUG' if debug else 'INFO'

    # Create logs directory if it doesn't exist
    logs_dir = BASE_DIR / 'logs'
    logs_dir.mkdir(exist_ok=True)

    # Formatters
    formatters = {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    }

    # Add JSON formatter if JSON format is requested
    if log_format == 'json':
        formatters['json'] = {
            '()': 'core.logging_config.JSONFormatter',
        }

    # Add colored formatter for console in debug mode
    if debug and log_format == 'text':
        formatters['colored'] = {
            '()': 'core.logging_config.ColoredFormatter',
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        }

    # Handlers
    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'colored' if debug and log_format == 'text' else 'simple',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': logs_dir / 'app.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'json' if log_format == 'json' else 'verbose',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': logs_dir / 'error.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'json' if log_format == 'json' else 'verbose',
            'level': 'ERROR',
        },
    }

    # Loggers
    loggers = {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': log_level,
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': log_level,
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file', 'error_file'],
            'level': log_level,
            'propagate': False,
        },
        'channels': {
            'handlers': ['console', 'file', 'error_file'],
            'level': log_level,
            'propagate': False,
        },
        'hyperfilelens': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG' if debug else 'INFO',
            'propagate': False,
        },
        'alerts': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG' if debug else 'INFO',
            'propagate': False,
        },
        'nodes': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG' if debug else 'INFO',
            'propagate': False,
        },
    }

    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': formatters,
        'handlers': handlers,
        'root': {
            'handlers': ['console', 'file', 'error_file'],
            'level': log_level,
        },
        'loggers': loggers,
    }

    return config


def setup_logging(debug=False, log_level=None, log_format=None):
    """
    Setup logging configuration.

    Args:
        debug: Whether debug mode is enabled
        log_level: Override log level
        log_format: Log format ('text' or 'json', defaults to 'json' in production)
    """
    # Determine log format
    if log_format is None:
        log_format = 'json' if not debug else 'text'

    # Get configuration
    config = get_logging_config(
        debug=debug,
        log_level=log_level,
        log_format=log_format
    )

    # Apply configuration
    logging.config.dictConfig(config)

    # Log startup message
    logger = logging.getLogger('hyperfilelens')
    logger.info(f"Logging configured: format={log_format}, level={config['root']['level']}")


class RequestContext:
    """
    Request context for structured logging.

    This class provides a context manager for adding request-specific
    information to log records.
    """

    _contexts = {}

    def __init__(self, request_id=None, user_id=None, tenant_id=None, **kwargs):
        self.request_id = request_id
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.extra = kwargs
        self.old_factory = None

    def __enter__(self):
        # Store current context
        self._contexts[thread_id()] = {
            'request_id': self.request_id,
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
            'extra': self.extra,
        }
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Remove context
        self._contexts.pop(thread_id(), None)

    @classmethod
    def get_current(cls):
        """Get current request context."""
        import threading
        return cls._contexts.get(threading.get_ident(), {})


class RequestContextFilter(logging.Filter):
    """
    Logging filter that adds request context to log records.
    """

    def filter(self, record):
        context = RequestContext.get_current()
        if context:
            for key, value in context.items():
                if key != 'extra':
                    setattr(record, key, value)
            if 'extra' in context:
                record.extra = context['extra']
        return True


def get_logger(name):
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    return logger


def bind_logger(logger, **kwargs):
    """
    Bind additional context to a logger.

    This is a convenience function for adding context to log records.

    Args:
        logger: Logger instance
        **kwargs: Context key-value pairs

    Returns:
        LoggerAdapter with bound context
    """
    class ContextAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            kwargs.setdefault('extra', {})
            kwargs['extra'].update(self.extra)
            return msg, kwargs

    return ContextAdapter(logger, extra=kwargs)


def thread_id():
    """Get current thread ID."""
    import threading
    return threading.get_ident()
