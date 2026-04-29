"""
License quota checking utilities.

Provides decorators and mixins to check license quotas before creating resources.
"""
from functools import wraps
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.response import Response

from .models import License


def check_quota(resource_type: str):
    """
    Decorator to check license quota before creating a resource.
    
    Usage:
        @check_quota('proxies')
        def perform_create(self, serializer):
            ...
    
    Args:
        resource_type: Type of resource to check (e.g., 'users', 'proxies', 'repositories')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, serializer, *args, **kwargs):
            # Get the tenant from the request user
            user = self.request.user
            tenant = getattr(user, 'tenant', None)
            
            if not tenant:
                # No tenant, allow creation (or handle differently)
                return func(self, serializer, *args, **kwargs)
            
            # Get the active license
            license = License.get_active_license(tenant)
            
            if not license:
                raise PermissionDenied("No active license found for this tenant.")
            
            # Check quota
            is_allowed, message = license.check_quota(resource_type)
            
            if not is_allowed:
                raise PermissionDenied(f"License quota exceeded: {message}")
            
            # Execute the original function
            return func(self, serializer, *args, **kwargs)
        
        return wrapper
    return decorator


class QuotaCheckMixin:
    """
    Mixin to add quota checking to ViewSets.
    
    Usage:
        class ProxyNodeViewSet(QuotaCheckMixin, viewsets.ModelViewSet):
            quota_resource_type = 'proxies'
            
            def perform_create(self, serializer):
                self.check_quota_before_create()
                serializer.save(user=self.request.user, tenant=self.request.user.tenant)
    """
    quota_resource_type = None
    
    def check_quota_before_create(self, additional: int = 1):
        """Check if the quota allows creating additional resources."""
        if not self.quota_resource_type:
            return
        
        user = self.request.user
        tenant = getattr(user, 'tenant', None)
        
        if not tenant:
            return
        
        license = License.get_active_license(tenant)
        
        if not license:
            raise PermissionDenied("No active license found for this tenant.")
        
        is_allowed, message = license.check_quota(self.quota_resource_type, additional)
        
        if not is_allowed:
            raise PermissionDenied(f"License quota exceeded: {message}")
    
    def perform_create(self, serializer):
        """Override to add quota check before creation."""
        self.check_quota_before_create()
        serializer.save(user=self.request.user, tenant=self.request.user.tenant)
