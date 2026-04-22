"""
HyperFileLens Backend - Backup Tasks URLs

URL configuration for backup tasks API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BackupTaskViewSet


# Create router and register viewsets
router = DefaultRouter()
router.register(r'tasks', BackupTaskViewSet, basename='backup-task')

urlpatterns = [
    path('', include(router.urls)),
]
