"""
License quota checking utilities.

Provides decorators and mixins to check license quotas before creating resources.
"""
from functools import wraps
from rest_framework.exceptions import PermissionDenied

from .models import License

SYSTEM_TENANT_NAME = 'administrator'


class LicenseQuotaExceeded(PermissionDenied):
    """Raised when a license quota would be exceeded."""

    default_code = 'license_quota_exceeded'


def get_quota_license(tenant=None):
    """Return the license that should be used for quota checks."""
    if tenant:
        return License.get_active_license(tenant)
    return None


def get_platform_license():
    """Return the system license used for platform-wide quotas."""
    from tenants.models import Tenant

    system_tenant = Tenant.objects.filter(name=SYSTEM_TENANT_NAME).first()
    if not system_tenant:
        return None
    return License.get_active_license(system_tenant)


def get_platform_tenant_count():
    """Count tenant records controlled by the platform tenant quota."""
    from tenants.models import Tenant

    return Tenant.objects.exclude(name=SYSTEM_TENANT_NAME).count()


def get_repository_reserved_storage_gb(tenant):
    """
    Calculate storage quota usage from current repository state.

    Priority per repository:
    - explicit repository quota, when enabled
    - detected storage capacity
    - actual used space
    """
    from repository.models import Repository

    total_bytes = 0
    for repo in Repository.objects.filter(tenant=tenant).only(
        'quota_enabled',
        'quota_bytes',
        'capacity',
        'used_space',
    ):
        if repo.quota_enabled and repo.quota_bytes > 0:
            total_bytes += repo.quota_bytes
        elif repo.capacity > 0:
            total_bytes += repo.capacity
        else:
            total_bytes += repo.used_space

    return total_bytes / (1024 ** 3)


def get_monthly_ai_insights_used(tenant):
    """Count AI query usage for the tenant in the current calendar month."""
    if not tenant:
        return 0

    from django.utils import timezone
    from ai_query.models import AIQuery

    now = timezone.now()
    return AIQuery.objects.filter(
        tenant=tenant,
        created_at__year=now.year,
        created_at__month=now.month,
    ).count()


def get_license_usage_stats(tenant) -> dict:
    """Return real-time license usage statistics for a tenant."""
    if not tenant:
        return {
            'tenants_count': 0,
            'users_count': 0,
            'proxies_count': 0,
            'storage_used_gb': 0,
            'gateways_count': 0,
            'ai_insights_used': 0,
            'backup_tasks_count': 0,
            'recovery_tasks_count': 0,
            'source_resources_count': 0,
            'policies_count': 0,
            'repositories_count': 0,
        }

    from accounts.models import User
    from backup_tasks.models import BackupTask
    from gateways.models import Gateway
    from nodes.models import ProxyNode
    from policies.models import BackupPolicy
    from recovery_tasks.models import RecoveryTask
    from repository.models import Repository
    from source_resources.models import SourceResource

    return {
        'tenants_count': (
            get_platform_tenant_count()
            if tenant.name == SYSTEM_TENANT_NAME
            else 0
        ),
        'users_count': User.objects.filter(tenant=tenant, is_active=True).count(),
        'proxies_count': ProxyNode.objects.filter(tenant=tenant).count(),
        'storage_used_gb': get_repository_reserved_storage_gb(tenant),
        'gateways_count': Gateway.objects.filter(tenant=tenant).count(),
        'ai_insights_used': get_monthly_ai_insights_used(tenant),
        'backup_tasks_count': BackupTask.objects.filter(tenant=tenant).count(),
        'recovery_tasks_count': RecoveryTask.objects.filter(tenant=tenant).count(),
        'source_resources_count': SourceResource.objects.filter(tenant=tenant).count(),
        'policies_count': BackupPolicy.objects.filter(tenant=tenant).count(),
        'repositories_count': Repository.objects.filter(tenant=tenant).count(),
    }


def get_license_quota_warnings(license_obj, usage: dict, threshold_percent=80):
    """Return warning entries for license quotas close to or over their limits."""
    if not license_obj:
        return []

    quota_fields = [
        ('tenants', 'max_tenants', 'tenants_count', 'tenants'),
        ('users', 'max_users', 'users_count', 'users'),
        ('proxies', 'max_proxies', 'proxies_count', 'proxies'),
        ('storage_gb', 'max_storage_gb', 'storage_used_gb', 'GB'),
        ('gateways', 'max_gateways', 'gateways_count', 'gateways'),
        ('ai_insights', 'ai_insights_quota', 'ai_insights_used', 'requests'),
        ('backup_tasks', 'max_backup_tasks', 'backup_tasks_count', 'tasks'),
        ('recovery_tasks', 'max_recovery_tasks', 'recovery_tasks_count', 'tasks'),
        ('source_resources', 'max_source_resources', 'source_resources_count', 'resources'),
        ('policies', 'max_policies', 'policies_count', 'policies'),
        ('repositories', 'max_repositories', 'repositories_count', 'repositories'),
    ]

    warnings = []
    limits = license_obj.get_limits()
    for quota_type, limit_field, usage_field, unit in quota_fields:
        limit = limits.get(limit_field, 0)
        if limit in (-1, 0):
            continue

        current = usage.get(usage_field, 0) or 0
        percent = (current / limit) * 100
        if percent < threshold_percent:
            continue

        warnings.append({
            'quota_type': quota_type,
            'current_usage': current,
            'limit': limit,
            'usage_percent': round(percent, 2),
            'unit': unit,
            'level': 'exceeded' if current >= limit else 'warning',
        })

    return warnings


def enforce_platform_tenant_quota(additional=1):
    """Enforce the platform-wide tenant quota from the system tenant license."""
    license_obj = get_platform_license()
    if not license_obj:
        return None

    limit = license_obj.max_tenants
    if limit == -1:
        return license_obj

    current = get_platform_tenant_count()
    new_total = current + additional
    if new_total > limit:
        raise LicenseQuotaExceeded(
            f"License quota exceeded: Cannot create {additional} tenant(s). "
            f"Current: {current}, Limit: {limit}"
        )

    return license_obj


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
