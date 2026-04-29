"""
HyperFileLens Backend - Audit Log URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuditLogViewSet, EventLogViewSet


router = DefaultRouter()
router.register(r'audit', AuditLogViewSet, basename='audit')
router.register(r'events', EventLogViewSet, basename='events')

urlpatterns = [
    path('', include(router.urls)),
]
