"""
Views for Accounts Application

This module provides API views for user authentication,
registration, profile management, and session management.
"""

import uuid
from django.core.cache import cache

from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from accounts.models import APIToken
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import User, Role, APIToken, UserSession
from audit_log.services import AuditService
from .serializers import (
    UserCreateSerializer,
    UserRegistrationSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    PasswordChangeSerializer,
    RoleSerializer,
    APITokenSerializer,
    APITokenCreateResponseSerializer,
    UserSessionSerializer,
)
from audit_log.services import AuditService
from tenants.models import Tenant


class IsTenantAdmin(permissions.BasePermission):
    """
    Permission class for tenant admin or super admin.
    """

    def has_permission(self, request, view):
        if not request.user:
            return False
        if request.user.is_superuser:
            return True
        return request.user.tenant_role in ['owner', 'admin']

class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing roles.

    Provides list and retrieve actions for roles.
    Users can view available roles to understand their permissions.
    """

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        """
        Return all roles ordered by name.
        """
        return Role.objects.all().order_by('name')


class UserRegistrationView(generics.CreateAPIView):
    """
    View for user registration.

    Allows new users to create an account.
    """

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Register a new user account',
        description='Create a new user account with email and password.',
        responses={
            201: UserProfileSerializer,
            400: OpenApiResponse(description='Validation error'),
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Register a new user.

        Creates a new user account and returns the user profile.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Create token for automatic login after registration
        import secrets
        token_key = secrets.token_urlsafe(32)
        api_token = APIToken.objects.create(
            user=user,
            name='Registration API Token',
            key=token_key,
            prefix=token_key[:8]
        )

        response_serializer = UserProfileSerializer(user)
        response_data = response_serializer.data
        response_data['token'] = api_token.key

        return Response(response_data, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    View for user profile management.

    Allows users to view and update their own profile.
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Return the current authenticated user.
        """
        return self.request.user

    @extend_schema(
        summary='Get current user profile',
        description='Retrieve the profile of the currently authenticated user.'
    )
    def get(self, request, *args, **kwargs):
        """Get user profile."""
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='Update current user profile',
        description='Update the profile of the currently authenticated user.'
    )
    def patch(self, request, *args, **kwargs):
        """Update user profile."""
        serializer = UserUpdateSerializer(
            self.get_object(),
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserProfileSerializer(self.get_object()).data)


class PasswordChangeView(APIView):
    """
    View for changing user password.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Change user password',
        description='Change the password of the currently authenticated user.',
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(description='Password changed successfully'),
            400: OpenApiResponse(description='Validation error'),
        }
    )
    def post(self, request):
        """
        Change user password.

        Validates old password and updates to new password.
        """
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Password changed successfully.'
        }, status=status.HTTP_200_OK)


class LoginView(APIView):
    """
    View for user login.

    Authenticates user and returns session/token.
    """

    # Only use SessionAuthentication, not TokenAuthentication
    # This prevents issues with invalid tokens in localStorage
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary='User login',
        description='Authenticate user with email and password.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'email': {'type': 'string', 'format': 'email'},
                    'password': {'type': 'string'},
                },
                'required': ['email', 'password'],
            }
        },
        responses={
            200: UserProfileSerializer,
            401: OpenApiResponse(description='Invalid credentials'),
        }
    )
    def post(self, request):
        """
        Login user.

        Authenticates user credentials and returns user profile with token.
        """
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({
                'error': 'Email and password are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Use custom email authentication
        from core.authentication import EmailAuthBackend
        backend = EmailAuthBackend()
        user = backend.authenticate(request, email=email, password=password)

        if user is None:
            # Log failed login attempt
            AuditService.log_user_login_failure(
                request,
                email=email,
                error_message='Invalid credentials'
            )
            return Response({
                'error': 'Invalid credentials.'
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            # Log failed login attempt - account disabled
            AuditService.log_user_login_failure(
                request,
                email=email,
                error_message='User account is disabled'
            )
            return Response({
                'error': 'User account is disabled.'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Update last login time - use update() to avoid model save issues with UUID
        from django.utils import timezone
        from accounts.models import User
        User.objects.filter(pk=user.pk).update(last_login_at=timezone.now())

        # Get or create API token - ensure user is a proper User instance
        from accounts.models import User
        if not isinstance(user, User):
            return Response({
                'error': 'Authentication error.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Create token with unique key
        import secrets
        token_key = secrets.token_urlsafe(32)
        api_token = APIToken.objects.create(
            user=user,
            name='Default API Token',
            key=token_key,
            prefix=token_key[:8]
        )

        # Log successful login
        AuditService.log_user_login_success(request, user)

        # Create session
        login(request, user)

        serializer = UserProfileSerializer(user)
        response_data = serializer.data
        response_data['token'] = api_token.key

        return Response(response_data)

    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class LogoutView(APIView):
    """
    View for user logout.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='User logout',
        description='Logout the currently authenticated user.',
        responses={
            200: OpenApiResponse(description='Logged out successfully'),
        }
    )
    def post(self, request):
        """
        Logout user.

        Removes user session and deletes token.
        """
        user = request.user

        try:
            # Delete API token
            APIToken.objects.filter(user=user).delete()
        except Exception:
            pass

        # Logout from session
        logout(request)

        # Log logout
        AuditService.log_user_logout(user=user, request=request)

        return Response({
            'message': 'Logged out successfully.'
        })

    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class CSRFTokenView(APIView):
    """
    View for retrieving CSRF token.

    Required for session-based authentication.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Get CSRF token',
        description='Retrieve CSRF token for session-based authentication.',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'csrfToken': {'type': 'string'},
                },
            }
        }
    )
    def get(self, request):
        """
        Get CSRF token.

        Returns the CSRF token for the current session.
        """
        return Response({
            'csrfToken': get_token(request)
        })


class APITokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for API token management.

    Allows users to create, list, view, and revoke API tokens.
    """

    serializer_class = APITokenSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        """
        Return tokens for the current user only.
        """
        return APIToken.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'create':
            return APITokenSerializer
        return APITokenSerializer

    @extend_schema(
        summary='Create API token',
        description='Create a new API token for programmatic access.',
        responses={
            201: APITokenCreateResponseSerializer,
        }
    )
    def create(self, request, *args, **kwargs):
        """
        Create a new API token.

        Returns the full token key which is only shown once.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.save()

        # Return full token in response (only time it's shown)
        return Response({
            'id': token.id,
            'name': token.name,
            'key': token.key,
            'prefix': token.prefix,
            'scopes': token.scopes,
            'rate_limit': token.rate_limit,
            'created_at': token.created_at,
            'expires_at': token.expires_at,
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary='Revoke API token',
        description='Deactivate an API token.',
        responses={
            200: OpenApiResponse(description='Token revoked successfully'),
        }
    )
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """
        Revoke an API token.

        Deactivates the token without deleting it.
        """
        token = self.get_object()
        token.is_active = False
        token.save()
        return Response({
            'message': 'Token revoked successfully.'
        })

    @extend_schema(
        summary='Refresh API token',
        description='Refresh an API token by generating a new key.',
        responses={
            200: APITokenCreateResponseSerializer,
        }
    )
    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """
        Refresh an API token.

        Generates a new key for the token.
        """
        token = self.get_object()
        token.key = secrets.token_hex(32)
        token.prefix = token.key[:8]
        token.save()

        return Response({
            'id': token.id,
            'name': token.name,
            'key': token.key,
            'prefix': token.prefix,
            'scopes': token.scopes,
            'rate_limit': token.rate_limit,
            'created_at': token.created_at,
            'expires_at': token.expires_at,
        })


class UserSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user session management.

    Allows users to view and manage their active sessions.
    """

    serializer_class = UserSessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        """
        Return sessions for the current user only.
        """
        return UserSession.objects.filter(user=self.request.user)

    @extend_schema(
        summary='List user sessions',
        description='List all active sessions for the current user.',
    )
    def list(self, request, *args, **kwargs):
        """List user sessions."""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Get session details',
        description='Get details of a specific session.',
    )
    def retrieve(self, request, *args, **kwargs):
        """Get session details."""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary='Terminate session',
        description='Terminate a specific session.',
        responses={
            200: OpenApiResponse(description='Session terminated successfully'),
        }
    )
    @action(detail=True, methods=['post'])
    def terminate(self, request, pk=None):
        """
        Terminate a session.

        Marks the session as inactive.
        """
        session = self.get_object()
        session.is_active = False
        session.save()
        return Response({
            'message': 'Session terminated successfully.'
        })

    @extend_schema(
        summary='Terminate all other sessions',
        description='Terminate all sessions except the current one.',
        responses={
            200: OpenApiResponse(description='Sessions terminated successfully'),
        }
    )
    @action(detail=False, methods=['post'])
    def terminate_others(self, request):
        """
        Terminate all other sessions.

        Keeps only the current session active.
        """
        current_session_key = request.session.session_key
        UserSession.objects.filter(
            user=request.user
        ).exclude(
            session_key=current_session_key
        ).update(is_active=False)

        return Response({
            'message': 'Other sessions terminated successfully.'
        })


# Import timezone for last_login_at update
from django.utils import timezone
import secrets


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user management within a tenant.

    Tenant admins can manage users within their own tenant.
    Super admins can manage all users.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        if self.action == 'create':
            return UserCreateSerializer
        return UserProfileSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.all()
        if user.tenant and user.tenant_role in ['owner', 'admin']:
            return User.objects.filter(tenant=user.tenant)
        # Regular users can only see themselves
        return User.objects.filter(pk=user.pk)

    def get_permissions(self):
        """Only tenant admins can create/update/delete users."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsTenantAdmin()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """Create a user with validation."""
        email = request.data.get('email', '').strip().lower()
        
        # Check if email already exists
        if email and User.objects.filter(email=email).exists():
            return Response(
                {'error': 'A user with this email already exists', 'field': 'email'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Create a user within a tenant."""
        user = self.request.user
        
        # Platform admins can specify which tenant to create user in
        if user.is_superuser:
            tenant_id = self.request.data.get('tenant_id')
            if tenant_id:
                from tenants.models import Tenant
                try:
                    tenant = Tenant.objects.get(id=tenant_id)
                    new_user = serializer.save(tenant=tenant)
                    AuditService.log_user_create(self.request, new_user)
                    return
                except Tenant.DoesNotExist:
                    pass
            # Default to administrator tenant if not specified
            new_user = serializer.save(tenant=user.tenant)
        else:
            # Regular tenant admins can only create users in their own tenant
            if not user.tenant:
                raise ValueError("User must belong to a tenant to create users")
            new_user = serializer.save(tenant=user.tenant)
        
        AuditService.log_user_create(self.request, new_user)

    @extend_schema(
        summary='Disable user',
        description='Disable a user account (tenant admin only).',
        responses={200: OpenApiResponse(description='User disabled')}
    )
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable a user account."""
        user = self.get_object()
        # Cannot disable yourself
        if user == request.user:
            return Response(
                {'error': 'Cannot disable your own account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.is_active = False
        user.save()
        return Response({'status': 'disabled'})

    @extend_schema(
        summary='Enable user',
        description='Enable a user account (tenant admin only).',
        responses={200: OpenApiResponse(description='User enabled')}
    )
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable a user account."""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'status': 'enabled'})

    @extend_schema(
        summary='Change user role',
        description='Change a user\'s role within the tenant.',
        request={
            'type': 'object',
            'properties': {
                'role': {'type': 'string', 'enum': ['admin', 'member']},
            },
            'required': ['role'],
        },
        responses={200: OpenApiResponse(description='Role changed')}
    )
    @action(detail=True, methods=['post'])
    def change_role(self, request, pk=None):
        """Change a user's role within the tenant."""
        user = self.get_object()
        new_role = request.data.get('role')

        if new_role not in ['admin', 'member']:
            return Response(
                {'error': 'Invalid role. Must be admin or member.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cannot change your own role
        if user == request.user:
            return Response(
                {'error': 'Cannot change your own role'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.tenant_role = new_role
        user.save()
        return Response({'status': 'role_changed', 'role': new_role})

    @extend_schema(
        summary='Set superuser status',
        description='Set or remove platform admin privileges. Only platform admins can do this.',
        request={
            'type': 'object',
            'properties': {
                'is_superuser': {'type': 'boolean'},
            },
            'required': ['is_superuser'],
        },
        responses={200: OpenApiResponse(description='Superuser status updated')}
    )
    @action(detail=True, methods=['post'])
    def set_superuser(self, request, pk=None):
        """Set or remove platform admin privileges. Only platform admins can do this."""
        # Only platform admins can set superuser status
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only platform admins can set superuser status'},
                status=status.HTTP_403_FORBIDDEN
            )

        user = self.get_object()
        is_superuser = request.data.get('is_superuser')

        if is_superuser is None:
            return Response(
                {'error': 'is_superuser is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cannot change your own superuser status
        if user == request.user:
            return Response(
                {'error': 'Cannot change your own superuser status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_superuser = is_superuser
        if is_superuser:
            user.tenant_role = 'admin'
        user.save()
        return Response({
            'status': 'superuser_updated',
            'is_superuser': user.is_superuser
        })

    @extend_schema(
        summary='Reset user password',
        description='Reset a user\'s password. Only tenant admins and platform admins can do this.',
        request={
            'type': 'object',
            'properties': {
                'new_password': {'type': 'string'},
            },
            'required': ['new_password'],
        },
        responses={200: OpenApiResponse(description='Password reset successfully')}
    )
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Reset a user's password."""
        user = self.get_object()
        new_password = request.data.get('new_password')

        if not new_password:
            return Response(
                {'error': 'new_password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 6:
            return Response(
                {'error': 'Password must be at least 6 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()
        AuditService.log_password_reset(request, user)
        return Response({'status': 'password_reset', 'message': 'Password reset successfully'})

    def destroy(self, request, *args, **kwargs):
        """Delete a user with validation."""
        user = self.get_object()

        # Cannot delete yourself
        if user == request.user:
            error_msg = 'Cannot delete your own account'
            AuditService.log_user_delete(request, user, result='failure', error_message=error_msg)
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cannot delete platform admin (only platform admin can delete platform admin)
        if user.is_superuser and not request.user.is_superuser:
            error_msg = 'Cannot delete platform admin'
            AuditService.log_user_delete(request, user, result='failure', error_message=error_msg)
            return Response(
                {'error': error_msg},
                status=status.HTTP_403_FORBIDDEN
            )

        # Platform admin cannot delete themselves
        if user.is_superuser and user == request.user:
            error_msg = 'Cannot delete your own platform admin account'
            AuditService.log_user_delete(request, user, result='failure', error_message=error_msg)
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user has associated resources
        from nodes.models import ProxyNode
        from repository.models import Repository
        from source_resources.models import SourceResource
        from policies.models import BackupPolicy
        from backup_tasks.models import BackupTask
        from recovery_tasks.models import RecoveryTask
        from gateways.models import Gateway

        resource_counts = {}
        
        # Count resources created by this user
        proxy_count = ProxyNode.objects.filter(created_by=user).count()
        if proxy_count > 0:
            resource_counts['proxies'] = proxy_count
            
        repo_count = Repository.objects.filter(created_by=user).count()
        if repo_count > 0:
            resource_counts['repositories'] = repo_count
            
        source_count = SourceResource.objects.filter(created_by=user).count()
        if source_count > 0:
            resource_counts['source_resources'] = source_count
            
        policy_count = BackupPolicy.objects.filter(created_by=user).count()
        if policy_count > 0:
            resource_counts['policies'] = policy_count
            
        backup_count = BackupTask.objects.filter(created_by=user).count()
        if backup_count > 0:
            resource_counts['backup_tasks'] = backup_count
            
        recovery_count = RecoveryTask.objects.filter(created_by=user).count()
        if recovery_count > 0:
            resource_counts['recovery_tasks'] = recovery_count
            
        gateway_count = Gateway.objects.filter(created_by=user).count()
        if gateway_count > 0:
            resource_counts['gateways'] = gateway_count

        if resource_counts:
            error_msg = f'Cannot delete user with associated resources. Please transfer or delete the following resources first: {", ".join(f"{v} {k}" for k, v in resource_counts.items())}'
            AuditService.log_user_delete(request, user, result='failure', error_message=error_msg)
            return Response(
                {
                    'error': 'Cannot delete user with associated resources',
                    'detail': f'User has associated resources that must be transferred or deleted first.',
                    'resources': resource_counts
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Record audit log before deletion
        AuditService.log_user_delete(request, user, result='success')
        
        user.delete()
        return Response({'status': 'deleted', 'message': 'User deleted successfully'})


# ============================================================================
# Captcha API
# ============================================================================

class CaptchaView(APIView):
    """
    API endpoint for captcha generation.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary='Generate captcha image',
        description='Generate a new captcha image and return the image key.',
        responses={
            200: OpenApiResponse(
                description='Captcha image',
                response={
                    'type': 'object',
                    'properties': {
                        'key': {'type': 'string'},
                    }
                }
            )
        }
    )
    def get(self, request):
        """Generate and return a captcha image."""
        from .services import CaptchaService
        
        captcha_key, image_bytes = CaptchaService.generate()
        
        if not image_bytes:
            # Fallback if PIL not available
            return Response({
                'key': captcha_key,
                'code': 'dummy'  # For testing only
            })
        
        # Return as base64 encoded image
        import base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        return Response({
            'key': captcha_key,
            'image': f'data:image/png;base64,{image_base64}'
        })


class CaptchaValidateView(APIView):
    """
    API endpoint for captcha validation.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary='Validate captcha code',
        description='Validate a captcha code.',
        request={
            'type': 'object',
            'properties': {
                'key': {'type': 'string'},
                'code': {'type': 'string'}
            },
            'required': ['key', 'code']
        },
        responses={
            200: OpenApiResponse(
                description='Validation result',
                response={
                    'type': 'object',
                    'properties': {
                        'valid': {'type': 'boolean'}
                    }
                }
            )
        }
    )
    def post(self, request):
        """Validate a captcha code."""
        from .services import CaptchaService
        
        captcha_key = request.data.get('key')
        captcha_code = request.data.get('code')
        
        if not captcha_key or not captcha_code:
            return Response(
                {'error': 'Missing key or code'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid = CaptchaService.validate(captcha_key, captcha_code)
        
        return Response({'valid': valid})


# ============================================================================
# Registration API
# ============================================================================

class RegisterView(APIView):
    """
    API endpoint for user registration.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary='Register a new user',
        description='Create a new user account with email and password.',
        request={
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email'},
                'password': {'type': 'string', 'minLength': 6},
                'first_name': {'type': 'string'},
                'last_name': {'type': 'string'},
                'captcha_key': {'type': 'string'},
                'captcha_code': {'type': 'string'}
            },
            'required': ['email', 'password']
        },
        responses={
            201: UserProfileSerializer,
            400: OpenApiResponse(description='Validation error')
        }
    )
    def post(self, request):
        """Register a new user."""
        from .services import CaptchaService
        from django.db import transaction
        
        # Validate captcha if provided
        captcha_key = request.data.get('captcha_key')
        captcha_code = request.data.get('captcha_code')
        
        if captcha_key and captcha_code:
            if not CaptchaService.validate(captcha_key, captcha_code):
                return Response(
                    {'error': 'Invalid captcha code'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        if not email or not password:
            return Response(
                {'error': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(password) < 6:
            AuditService.log_user_register(
                request, 
                type('User', (), {'id': '', 'email': email})(),
                result='failure',
                error_message='Password must be at least 6 characters'
            )
            return Response(
                {'error': 'Password must be at least 6 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(email=email).exists():
            AuditService.log_user_register(
                request,
                type('User', (), {'id': '', 'email': email})(),
                result='failure',
                error_message='Email already registered'
            )
            return Response(
                {'error': 'Email already registered'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Create tenant for new user
            tenant_name = email.split('@')[0]
            tenant_slug = f"{tenant_name}-{uuid.uuid4().hex[:8]}"
            
            tenant = Tenant.objects.create(
                name=tenant_name,
                slug=tenant_slug,
                plan='free',
                status='active',
                contact_email=email
            )
            
            # Create user
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                tenant=tenant,
                tenant_role='admin',
                is_active=True
            )
            
            # Create default license for new tenant
            from licenses.models import License, generate_machine_code
            from django.utils import timezone
            import secrets

            # Generate machine code for the tenant/user
            machine_code, _ = generate_machine_code(str(tenant.id), str(user.id))

            License.objects.create(
                tenant=tenant,
                license_key=f"FREE-{secrets.token_hex(8).upper()}",
                status='active',
                activated_by=user,
                machine_code=machine_code,
                max_tenants=1,
                max_users=5,
                max_proxies=5,
                max_storage_gb=100,
                issued_at=timezone.now(),
                expires_at=None,
                signature=f"FREE-LICENSE-{secrets.token_hex(16).upper()}"
            )
            
            # Generate token
            import secrets
            token_key = secrets.token_urlsafe(32)
            api_token = APIToken.objects.create(
                user=user,
                name='Registration API Token',
                key=token_key,
                prefix=token_key[:8]
            )

            # Record audit log - user registration
            AuditService.log_user_register(request, user)

        response_data = UserProfileSerializer(user).data
        response_data['token'] = api_token.key
        
        return Response(response_data, status=status.HTTP_201_CREATED)


# ============================================================================
# Password Reset API
# ============================================================================

class ForgotPasswordView(APIView):
    """
    API endpoint for requesting password reset.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary='Request password reset',
        description='Send a password reset email with verification code.',
        request={
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email'},
                'captcha_key': {'type': 'string'},
                'captcha_code': {'type': 'string'}
            },
            'required': ['email']
        },
        responses={
            200: OpenApiResponse(description='Reset email sent'),
            404: OpenApiResponse(description='User not found')
        }
    )
    def post(self, request):
        """Request password reset."""
        from .services import CaptchaService, PasswordResetService, EmailService
        
        # Validate captcha if provided
        captcha_key = request.data.get('captcha_key')
        captcha_code = request.data.get('captcha_code')
        
        if captcha_key and captcha_code:
            if not CaptchaService.validate(captcha_key, captcha_code):
                return Response(
                    {'error': 'Invalid captcha code'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if user exists or not
            return Response({
                'message': 'If the email exists, a reset code has been sent.'
            })
        
        # Generate verification code
        code = PasswordResetService.generate_verification_code(email)
        
        # Send email
        EmailService.send_verification_code(email, code, 'password_reset')
        
        return Response({
            'message': 'If the email exists, a reset code has been sent.'
        })


class VerifyResetCodeView(APIView):
    """
    API endpoint for verifying password reset code.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary='Verify password reset code',
        description='Verify the reset code sent to email.',
        request={
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email'},
                'code': {'type': 'string'}
            },
            'required': ['email', 'code']
        },
        responses={
            200: OpenApiResponse(
                description='Verification result',
                response={
                    'type': 'object',
                    'properties': {
                        'valid': {'type': 'boolean'},
                        'token': {'type': 'string'}
                    }
                }
            )
        }
    )
    def post(self, request):
        """Verify reset code."""
        from .services import PasswordResetService
        
        email = request.data.get('email')
        code = request.data.get('code')
        
        if not email or not code:
            return Response(
                {'error': 'Email and code are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid = PasswordResetService.verify_code(email, code)
        
        if valid:
            # Generate a reset token for the actual password reset
            token = PasswordResetService.generate_reset_token(email)
            return Response({
                'valid': True,
                'token': token
            })
        
        return Response({
            'valid': False,
            'error': 'Invalid or expired code'
        })


class ResetPasswordView(APIView):
    """
    API endpoint for resetting password.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary='Reset password',
        description='Reset password using the token from verification.',
        request={
            'type': 'object',
            'properties': {
                'token': {'type': 'string'},
                'new_password': {'type': 'string', 'minLength': 6}
            },
            'required': ['token', 'new_password']
        },
        responses={
            200: OpenApiResponse(description='Password reset successful'),
            400: OpenApiResponse(description='Invalid token or password')
        }
    )
    def post(self, request):
        """Reset password."""
        from .services import PasswordResetService
        
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        
        if not token or not new_password:
            return Response(
                {'error': 'Token and new password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 6:
            return Response(
                {'error': 'Password must be at least 6 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate token
        email = PasswordResetService.validate_reset_token(token)
        
        if not email:
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get user and update password
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            
            # Invalidate tokens
            PasswordResetService.invalidate_reset_token(token)
            PasswordResetService.invalidate_code(email)
            
            # Invalidate all auth tokens (force re-login)
            APIToken.objects.filter(user=user).delete()
            
            return Response({
                'message': 'Password reset successfully'
            })
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ============================================================================
# MFA API
# ============================================================================

class MFASetupView(APIView):
    """
    API endpoint for MFA setup.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary='Get MFA setup info',
        description='Get MFA setup information including QR code URI.',
        responses={
            200: OpenApiResponse(
                description='MFA setup info',
                response={
                    'type': 'object',
                    'properties': {
                        'enabled': {'type': 'boolean'},
                        'method': {'type': 'string'},
                        'qr_uri': {'type': 'string'},
                        'secret': {'type': 'string'}
                    }
                }
            )
        }
    )
    def get(self, request):
        """Get MFA setup info."""
        user = request.user
        
        if user.mfa_enabled:
            return Response({
                'enabled': True,
                'method': user.mfa_method
            })
        
        # Generate new secret for setup
        from .services import MFAService
        
        secret = MFAService.generate_secret()
        MFAService.store_secret(str(user.id), secret)
        
        qr_uri = MFAService.generate_totp_uri(user.email, secret)
        
        return Response({
            'enabled': False,
            'secret': secret,
            'qr_uri': qr_uri
        })
    
    @extend_schema(
        summary='Enable MFA',
        description='Enable MFA with verification code.',
        request={
            'type': 'object',
            'properties': {
                'method': {'type': 'string', 'enum': ['email', 'totp']},
                'code': {'type': 'string'}
            },
            'required': ['method', 'code']
        },
        responses={
            200: OpenApiResponse(description='MFA enabled')
        }
    )
    def post(self, request):
        """Enable MFA."""
        from .services import MFAService
        
        user = request.user
        method = request.data.get('method', 'email')
        code = request.data.get('code')
        
        if method == 'totp':
            # Verify TOTP code
            secret = MFAService.get_secret(str(user.id))
            if not secret:
                return Response(
                    {'error': 'MFA setup not initialized'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # For now, just accept any 6-digit code (simplified)
            if not code or len(code) != 6:
                return Response(
                    {'error': 'Invalid code'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.mfa_enabled = True
            user.mfa_method = 'totp'
            user.mfa_secret = secret
            user.save()
            
            MFAService.clear_secret(str(user.id))
        
        elif method == 'email':
            # Email MFA - just enable it
            user.mfa_enabled = True
            user.mfa_method = 'email'
            user.save()
        
        else:
            return Response(
                {'error': 'Invalid MFA method'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'message': 'MFA enabled successfully',
            'enabled': True,
            'method': user.mfa_method
        })
    
    @extend_schema(
        summary='Disable MFA',
        description='Disable MFA for the current user.',
        responses={
            200: OpenApiResponse(description='MFA disabled')
        }
    )
    def delete(self, request):
        """Disable MFA."""
        user = request.user
        user.mfa_enabled = False
        user.mfa_method = ''
        user.mfa_secret = ''
        user.save()
        
        return Response({
            'message': 'MFA disabled successfully'
        })


class MFAVerifyView(APIView):
    """
    API endpoint for MFA verification during login.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary='Request MFA code',
        description='Request an MFA verification code for email.',
        request={
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email'},
                'login_token': {'type': 'string'}
            },
            'required': ['email', 'login_token']
        },
        responses={
            200: OpenApiResponse(description='MFA code sent')
        }
    )
    def post(self, request):
        """Request MFA code."""
        from .services import MFAService, EmailService
        
        email = request.data.get('email')
        login_token = request.data.get('login_token')
        
        # Validate login token from session
        # This should be set during the initial login step
        cached_email = cache.get(f'mfa_login:{login_token}')
        if not cached_email or cached_email != email:
            return Response(
                {'error': 'Invalid login session'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not user.mfa_enabled:
            return Response(
                {'error': 'MFA not enabled for this user'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate and send code
        if user.mfa_method == 'email':
            code = MFAService.generate_code(email)
            EmailService.send_verification_code(email, code, 'mfa')
        
        return Response({
            'message': 'MFA code sent',
            'method': user.mfa_method
        })
    
    @extend_schema(
        summary='Verify MFA code',
        description='Verify MFA code and complete login.',
        request={
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'format': 'email'},
                'login_token': {'type': 'string'},
                'code': {'type': 'string'}
            },
            'required': ['email', 'login_token', 'code']
        },
        responses={
            200: UserProfileSerializer
        }
    )
    def put(self, request):
        """Verify MFA code and complete login."""
        from .services import MFAService
        from django.core.cache import cache
        
        email = request.data.get('email')
        login_token = request.data.get('login_token')
        code = request.data.get('code')
        
        # Validate login token
        cached_email = cache.get(f'mfa_login:{login_token}')
        if not cached_email or cached_email != email:
            return Response(
                {'error': 'Invalid login session'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify code
        if user.mfa_method == 'email':
            if not MFAService.verify_code(email, code):
                return Response(
                    {'error': 'Invalid MFA code'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # TOTP verification would go here
            if not code or len(code) != 6:
                return Response(
                    {'error': 'Invalid MFA code'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Clear MFA login token
        cache.delete(f'mfa_login:{login_token}')
        
        # Generate auth token
        import secrets
        token_key = secrets.token_urlsafe(32)
        api_token = APIToken.objects.create(
            user=user,
            name='MFA Login Token',
            key=token_key,
            prefix=token_key[:8]
        )
        
        response_data = UserProfileSerializer(user).data
        response_data['token'] = token.key
        
        return Response(response_data)
