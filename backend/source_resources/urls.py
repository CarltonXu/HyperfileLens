"""
HyperFileLens Backend - Source Resource URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SourceResourceViewSet

router = DefaultRouter()
router.register(r'', SourceResourceViewSet, basename='source-resource')

urlpatterns = [
    path('', include(router.urls)),
]
