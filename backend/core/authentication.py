"""
Custom Authentication Backends for HyperFileLens

This module provides custom authentication mechanisms including
token-based authentication for API access.
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from accounts.models import User, APIToken


class TokenAuthentication(BaseAuthentication):
    """
    Custom token authentication for API access.

    This authentication backend validates API tokens passed in the
    Authorization header with the format: 'Token <token_value>'
    """

    keyword = 'Token'

    def authenticate(self, request):
        """
        Authenticate the request and return a tuple of (user, token).

        Args:
            request: The incoming HTTP request

        Returns:
            Tuple of (user, token) if authentication succeeds, None otherwise

        Raises:
            AuthenticationFailed: If authentication fails
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header:
            return None

        try:
            auth_type, token_value = auth_header.split(' ', 1)
        except ValueError:
            return None

        if auth_type.lower() != self.keyword.lower():
            return None

        return self.authenticate_token(token_value)

    def authenticate_token(self, token_value: str):
        """
        Validate the API token.

        Args:
            token_value: The token string to validate

        Returns:
            Tuple of (user, token) if valid

        Raises:
            AuthenticationFailed: If token is invalid or expired
        """
        try:
            token = APIToken.objects.select_related('user').get(
                key=token_value,
                is_active=True,
            )
        except APIToken.DoesNotExist:
            raise AuthenticationFailed('Invalid API token.')

        # Check if token has expired
        if token.expires_at and token.expires_at < timezone.now():
            raise AuthenticationFailed('API token has expired.')

        # Check if user is active
        if not token.user.is_active:
            raise AuthenticationFailed('User account is disabled.')

        return (token.user, token)

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the WWW-Authenticate
        header in a 401 Unauthenticated response.
        """
        return self.keyword
