"""
Views for Accounts Application

This module provides API views for user authentication,
registration, profile management, and session management.
"""

from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import User, Role, APIToken, UserSession
from .serializers import (
    UserRegistrationSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    PasswordChangeSerializer,
    RoleSerializer,
    APITokenSerializer,
    APITokenCreateResponseSerializer,
    UserSessionSerializer,
)


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

        # Generate token for automatic login after registration
        token, _ = Token.objects.get_or_create(user=user)

        response_serializer = UserProfileSerializer(user)
        response_data = response_serializer.data
        response_data['token'] = token.key

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
            return Response({
                'error': 'Invalid credentials.'
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({
                'error': 'User account is disabled.'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Update last login time
        user.last_login_at = timezone.now()
        user.save(update_fields=['last_login_at'])

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

        # Create session
        login(request, user)

        serializer = UserProfileSerializer(user)
        response_data = serializer.data
        response_data['token'] = api_token.key

        return Response(response_data)


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
        try:
            # Delete API token
            APIToken.objects.filter(user=request.user).delete()
        except Exception:
            pass

        # Logout from session
        logout(request)

        return Response({
            'message': 'Logged out successfully.'
        })


class CSRFTokenView(APIView):
    """
    View for retrieving CSRF token.

    Required for session-based authentication.
    """

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

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

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

    def perform_create(self, serializer):
        """Create a user within the same tenant."""
        user = self.request.user
        if not user.tenant:
            raise ValueError("User must belong to a tenant to create users")
        serializer.save(tenant=user.tenant)

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
                'role': {'type': 'string', 'enum': ['owner', 'admin', 'member', 'viewer']},
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

        if new_role not in ['owner', 'admin', 'member', 'viewer']:
            return Response(
                {'error': 'Invalid role'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cannot change your own role
        if user == request.user:
            return Response(
                {'error': 'Cannot change your own role'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Only owner can change to/from owner role
        if new_role == 'owner' or user.tenant_role == 'owner':
            if request.user.tenant_role != 'owner':
                return Response(
                    {'error': 'Only tenant owner can assign or remove owner role'},
                    status=status.HTTP_403_FORBIDDEN
                )

        user.tenant_role = new_role
        user.save()
        return Response({'status': 'role_changed', 'role': new_role})
