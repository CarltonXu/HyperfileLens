"""
URL Configuration for Accounts Application

Defines URL patterns for user authentication, registration,
profile management, and session management endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RoleViewSet,
    UserRegistrationView,
    UserProfileView,
    PasswordChangeView,
    LoginView,
    LogoutView,
    CSRFTokenView,
    APITokenViewSet,
    UserSessionViewSet,
)


# Create router for viewsets
router = DefaultRouter()
router.register(r'tokens', APITokenViewSet, basename='api-token')
router.register(r'sessions', UserSessionViewSet, basename='user-session')
router.register(r'roles', RoleViewSet, basename='role')

urlpatterns = [
    # Registration
    path('register/', UserRegistrationView.as_view(), name='register'),

    # Profile
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('password/', PasswordChangeView.as_view(), name='password-change'),

    # Authentication
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('csrf/', CSRFTokenView.as_view(), name='csrf-token'),

    # Router URLs
    path('', include(router.urls)),
]
