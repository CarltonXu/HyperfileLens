"""
License quota checking utilities.

Provides decorators and mixins to check license quotas before creating resources.
"""
from functools import wraps
from rest_framework.exceptions import PermissionDenied

from .models import License


class LicenseQuotaExceeded(PermissionDenied):
    """Raised when a license quota would be exceeded."""

    default_code = 'license_quota_exceeded'


def get_quota_license(tenant=None):
    """Return the license that should be used for quota checks."""
    if tenant:
        return License.get_active_license(tenant)
    return (
        License.objects
        .filter(status=License.LicenseStatus.ACTIVE)
        .select_related('tenant')
        .order_by('-activated_at')
        .first()
    )


def enforce_license_quota(tenant, resource_type: str, additional=1):
    """Enforce license quota and raise a DRF exception when the quota is exceeded."""
    license_obj = get_quota_license(tenant)
    if not license_obj:
        raise PermissionDenied("No active license found. Please activate a license before creating resources.")

    is_allowed, message = license_obj.check_quota(resource_type, additional)
    if not is_allowed:
        raise LicenseQuotaExceeded(f"License quota exceeded: {message}")

    return license_obj


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
            
            enforce_license_quota(tenant, resource_type)
            
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
        
        enforce_license_quota(tenant, self.quota_resource_type, additional)
    
    def perform_create(self, serializer):
        """Override to add quota check before creation."""
        self.check_quota_before_create()
        serializer.save(user=self.request.user, tenant=self.request.user.tenant)
