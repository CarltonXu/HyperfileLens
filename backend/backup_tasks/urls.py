"""
HyperFileLens Backend - Backup Tasks URLs

URL configuration for backup tasks API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BackupTaskViewSet, BackupSnapshotViewSet


# Create router and register viewsets
router = DefaultRouter()
router.register(r'tasks', BackupTaskViewSet, basename='backup-task')
router.register(r'snapshots', BackupSnapshotViewSet, basename='backup-snapshot')

urlpatterns = [
    path('', include(router.urls)),
]
