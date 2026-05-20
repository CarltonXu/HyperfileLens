from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SnapshotInsightsViewSet

router = DefaultRouter()
router.register(r'', SnapshotInsightsViewSet, basename='snapshot-insights')

urlpatterns = [
    path('', include(router.urls)),
]
