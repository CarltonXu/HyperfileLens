"""
HyperFileLens Backend - Policies URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BackupPolicyViewSet


router = DefaultRouter()
router.register(r'policies', BackupPolicyViewSet, basename='policy')

urlpatterns = [
    path('', include(router.urls)),
]
