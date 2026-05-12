"""URL configuration for global task management."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TaskManagementViewSet


router = DefaultRouter()
router.register(r'', TaskManagementViewSet, basename='task-management')

urlpatterns = [
    path('', include(router.urls)),
]
