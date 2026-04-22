"""
HyperFileLens Backend - Recovery Tasks URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RecoveryTaskViewSet


router = DefaultRouter()
router.register(r'tasks', RecoveryTaskViewSet, basename='recovery-task')

urlpatterns = [
    path('', include(router.urls)),
]
