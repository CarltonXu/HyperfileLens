"""
HyperFileLens Backend - Recovery Tasks URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RecoveryExportViewSet, RecoveryTaskViewSet


router = DefaultRouter()
router.register(r'tasks', RecoveryTaskViewSet, basename='recovery-task')
router.register(r'exports', RecoveryExportViewSet, basename='recovery-export')

urlpatterns = [
    path('', include(router.urls)),
]
