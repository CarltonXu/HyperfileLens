"""
HyperFileLens Backend Application

AI-Powered File Intelligence for Backup and Archive Data

Core configuration module for Django settings, Celery, and periodic task registry.
"""

import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load local environment files before reading settings. Docker Compose injects
# real environment variables, and python-dotenv keeps those values by default.
load_dotenv(BASE_DIR.parent / '.env')
load_dotenv(BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production-hyperfilelens-2024')
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', os.environ.get('DEBUG', 'True')).lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# CSRF trusted origins - allow coze.site domain and localhost
_default_csrf_origins = [
    'http://localhost:5000',
    'http://10.147.18.11:5001',
    'http://localhost:8000',
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', ','.join(_default_csrf_origins)).split(',')
    if origin.strip()
]

# Application definition
DJANGO_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',
    'django_celery_results',
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
]

# Third-party apps
THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'django_celery_beat',
    'django_celery_results',
    'drf_spectacular',
    'django_filters',  # Required for DRF filtering
]

# Project apps
PROJECT_APPS = [
    'core',
    'accounts',
    'tenants',       # Multi-tenancy support
    'licenses',      # License management
    'nodes',
    'gateways',      # Gateway nodes for AI Insights
    'source_resources',
    'backup_tasks',
    'recovery_tasks',
    'repository',
    'policies',
    'schedules',     # 定时任务调度
    'alerts',       # 告警管理
    'checkpoints',   # 断点续传检查点
    'ai_query',
    'insights',
    'audit_log',
    'system_settings',  # System settings & SMTP config
]

INSTALLED_APPS = DJANGO_APPS + PROJECT_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'tenants.middleware.TenantMiddleware',  # Multi-tenancy support
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=os.environ.get('DB_SSL_REQUIRE', 'false').lower() in ('true', '1', 'yes'),
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': os.environ.get(
                'DJANGO_DB_ENGINE',
                'django.db.backends.postgresql' if os.environ.get('USE_POSTGRES', 'false').lower() == 'true'
                else 'django.db.backends.sqlite3'
            ),
            'NAME': os.environ.get(
                'DJANGO_DB_NAME',
                BASE_DIR / 'db.sqlite3' if os.environ.get('USE_POSTGRES', 'false').lower() != 'true'
                else 'hyperfilelens'
            ),
            'USER': os.environ.get('DJANGO_DB_USER', 'hyperfilelens'),
            'PASSWORD': os.environ.get('DJANGO_DB_PASSWORD', 'hyperfilelens'),
            'HOST': os.environ.get('DJANGO_DB_HOST', 'postgres'),
            'PORT': os.environ.get('DJANGO_DB_PORT', '5432'),
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = os.environ.get('DJANGO_LANGUAGE_CODE', 'en-us')
TIME_ZONE = os.environ.get('DJANGO_TIME_ZONE', 'UTC')
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = Path(os.environ.get('STATIC_ROOT', BASE_DIR / 'staticfiles'))
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

# Public install distribution.
# This must be the externally reachable Nginx/Ingress/LB URL used by target
# proxy and gateway machines. Do not set this to backend-only addresses such as
# localhost:8000 or control:8000 in production.
PUBLIC_CONTROL_PLANE_URL = os.environ.get(
    'PUBLIC_CONTROL_PLANE_URL',
    os.environ.get('CONTROL_PLANE_PUBLIC_URL', os.environ.get('INSTALL_SERVER_URL', ''))
).rstrip('/')
FRONTEND_BASE_URL = os.environ.get('FRONTEND_BASE_URL', '').rstrip('/')
INSTALL_DOWNLOADS_URL = '/downloads/'
_source_downloads_root = BASE_DIR / 'static' / 'downloads'
if os.environ.get('INSTALL_DOWNLOADS_ROOT'):
    INSTALL_DOWNLOADS_ROOT = Path(os.environ['INSTALL_DOWNLOADS_ROOT'])
elif _source_downloads_root.exists() and not (STATIC_ROOT / 'downloads').exists():
    INSTALL_DOWNLOADS_ROOT = _source_downloads_root
else:
    INSTALL_DOWNLOADS_ROOT = STATIC_ROOT / 'downloads'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', BASE_DIR / 'media'))

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# CORS settings - Allow all origins for development
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://10.147.18.11:5001,http://localhost:5173,http://localhost:8000,http://127.0.0.1:5000'
).split(',')
CORS_ALLOW_ALL_ORIGINS = os.environ.get('CORS_ALLOW_ALL_ORIGINS', 'true').lower() == 'true'
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type', 'dnt',
    'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
]

# Authentication backends - support both username and email login
AUTHENTICATION_BACKENDS = [
    'core.authentication.EmailAuthBackend',
]

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'core.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%SZ',
    'DATE_FORMAT': '%Y-%m-%d',
}

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'default'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_RESULT_EXTENDED = True
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Redis Configuration
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')

# Cookie and HTTPS related settings.
SESSION_COOKIE_AGE = int(os.environ.get('SESSION_COOKIE_AGE', '86400'))
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() in ('true', '1', 'yes')
SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'true').lower() in ('true', '1', 'yes')
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'false').lower() in ('true', '1', 'yes')
CSRF_COOKIE_HTTPONLY = os.environ.get('CSRF_COOKIE_HTTPONLY', 'false').lower() in ('true', '1', 'yes')
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'false').lower() in ('true', '1', 'yes')

# Logging Configuration
_configured_log_file = Path(os.environ.get('LOG_FILE', BASE_DIR / 'logs' / 'app.log'))
if _configured_log_file.is_absolute() and not _configured_log_file.parent.exists():
    _configured_log_file = BASE_DIR / 'logs' / _configured_log_file.name
_configured_log_file.parent.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': _configured_log_file,
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.getenv('DJ_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'hyperfilelens': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Spectacular (API Documentation) Settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'HyperFileLens API',
    'DESCRIPTION': 'AI-Powered File Intelligence for Backup and Archive Data',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'TAGS': [
        {'name': 'Nodes', 'description': 'Node management endpoints'},
        {'name': 'Backup Tasks', 'description': 'Backup task management'},
        {'name': 'Recovery Tasks', 'description': 'Recovery task management'},
        {'name': 'Repository', 'description': 'Backup repository management'},
        {'name': 'Policies', 'description': 'Backup policy management'},
        {'name': 'AI Query', 'description': 'AI-powered file analysis'},
        {'name': 'Audit', 'description': 'Audit logging'},
    ],
}

# Kopia Configuration
KOPIA_PATH = os.environ.get('KOPIA_PATH', '/usr/local/bin/kopia')
KOPIA_REPOSITORY_PATH = os.environ.get('KOPIA_REPOSITORY_PATH', '/data/repository')

# AI Configuration
AI_PROVIDER = os.environ.get('AI_PROVIDER', 'openai')
AI_API_KEY = os.environ.get('AI_API_KEY', '')
AI_BASE_URL = os.environ.get('AI_BASE_URL', 'https://api.openai.com/v1')
AI_MODEL = os.environ.get('AI_MODEL', 'gpt-4-turbo-preview')
AI_EMBEDDING_MODEL = os.environ.get('AI_EMBEDDING_MODEL', 'text-embedding-3-small')

# WebSocket Configuration
WEBSOCKET_PING_INTERVAL = int(os.environ.get('WEBSOCKET_PING_INTERVAL', '30'))
WEBSOCKET_PING_TIMEOUT = int(os.environ.get('WEBSOCKET_PING_TIMEOUT', '10'))

# File Analysis Configuration
MAX_FILE_SIZE_FOR_AI = int(os.environ.get('MAX_FILE_SIZE_FOR_AI', str(10 * 1024 * 1024)))  # 10MB
SUPPORTED_FILE_TYPES = [
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.txt', '.md', '.json', '.xml', '.csv',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
]

# Retention Policy Defaults
DEFAULT_RETENTION_DAYS = int(os.environ.get('DEFAULT_RETENTION_DAYS', '30'))
DEFAULT_BACKUP_SCHEDULE = os.environ.get('DEFAULT_BACKUP_SCHEDULE', '0 2 * * *')  # Daily at 2 AM

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

# Channel Layers Configuration for WebSocket
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [REDIS_URL],
        },
    },
}
