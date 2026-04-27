"""
URL Configuration for HyperFileLens

Main URL routing for the API endpoints.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),

    # API v1 endpoints
    path('api/v1/proxies/', include('nodes.urls')),
    path('api/v1/source-resources/', include('source_resources.urls')),
    path('api/v1/backup-tasks/', include('backup_tasks.urls')),
    path('api/v1/recovery-tasks/', include('recovery_tasks.urls')),
    path('api/v1/repository/', include('repository.urls')),
    path('api/v1/policies/', include('policies.urls')),
    path('api/v1/ai-query/', include('ai_query.urls')),
    path('api/v1/audit/', include('audit_log.urls')),
    path('api/v1/accounts/', include('accounts.urls')),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
