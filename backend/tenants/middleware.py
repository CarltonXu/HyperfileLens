"""
Middleware for Multi-Tenancy Support

This middleware provides automatic tenant isolation for API requests.
"""

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware that sets the tenant context for each request.

    This middleware:
    1. Attaches the user's tenant to the request object
    2. Provides tenant isolation for database queries
    """

    def process_request(self, request):
        """
        Process incoming request and attach tenant context.

        Args:
            request: Django HTTP request object
        """
        # Skip tenant context for unauthenticated requests
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            request.tenant = None
            return None

        # Super admins can work across tenants
        if request.user.is_superuser:
            # Check for tenant_id in headers or query params
            tenant_id = (
                request.headers.get('X-Tenant-ID') or
                request.GET.get('tenant_id')
            )
            if tenant_id:
                from tenants.models import Tenant
                try:
                    request.tenant = Tenant.objects.get(id=tenant_id)
                except Tenant.DoesNotExist:
                    request.tenant = None
            else:
                request.tenant = None
        else:
            # Regular users are bound to their tenant
            request.tenant = request.user.tenant

        return None

    def process_response(self, request, response):
        """
        Process response and add tenant headers if applicable.

        Args:
            request: Django HTTP request object
            response: Django HTTP response object
        """
        # Add tenant ID to response headers for debugging
        if hasattr(request, 'tenant') and request.tenant:
            response['X-Tenant-ID'] = str(request.tenant.id)

        return response


class TenantQuerySetMixin:
    """
    Mixin for ViewSets that automatically filters querysets by tenant.

    Usage:
        class MyViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
            queryset = MyModel.objects.all()
            serializer_class = MySerializer
    """

    def get_queryset(self):
        """
        Get the queryset filtered by the current user's tenant.

        Returns:
            Filtered queryset
        """
        queryset = super().get_queryset()

        # Skip filtering for super admins unless they specify a tenant
        if self.request.user.is_superuser:
            tenant_id = (
                self.request.headers.get('X-Tenant-ID') or
                self.request.GET.get('tenant_id')
            )
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            return queryset

        # Filter by user's tenant
        if hasattr(self.request.user, 'tenant') and self.request.user.tenant:
            queryset = queryset.filter(tenant=self.request.user.tenant)
        else:
            # User has no tenant, return empty queryset
            queryset = queryset.none()

        return queryset


class TenantAccessMixin:
    """
    Mixin for checking tenant-level permissions.
    """

    def check_tenant_access(self, obj):
        """
        Check if the current user has access to the given object.

        Args:
            obj: Object to check access for

        Returns:
            bool: True if user has access
        """
        if self.request.user.is_superuser:
            return True

        user_tenant = getattr(self.request.user, 'tenant', None)
        obj_tenant = getattr(obj, 'tenant', None)

        return user_tenant and user_tenant == obj_tenant
