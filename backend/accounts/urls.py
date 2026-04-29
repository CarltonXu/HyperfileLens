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
    UserViewSet,
    # New views
    CaptchaView,
    CaptchaValidateView,
    RegisterView,
    ForgotPasswordView,
    VerifyResetCodeView,
    ResetPasswordView,
    MFASetupView,
    MFAVerifyView,
)


# Create router for viewsets
router = DefaultRouter()
router.register(r'tokens', APITokenViewSet, basename='api-token')
router.register(r'sessions', UserSessionViewSet, basename='user-session')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # Registration
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('register-v2/', RegisterView.as_view(), name='register-v2'),

    # Profile
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('password/', PasswordChangeView.as_view(), name='password-change'),

    # Authentication
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('csrf/', CSRFTokenView.as_view(), name='csrf-token'),

    # Captcha
    path('captcha/', CaptchaView.as_view(), name='captcha'),
    path('captcha/validate/', CaptchaValidateView.as_view(), name='captcha-validate'),

    # Password Reset
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('verify-reset-code/', VerifyResetCodeView.as_view(), name='verify-reset-code'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),

    # MFA
    path('mfa/', MFASetupView.as_view(), name='mfa-setup'),
    path('mfa/verify/', MFAVerifyView.as_view(), name='mfa-verify'),

    # Router URLs
    path('', include(router.urls)),
]
