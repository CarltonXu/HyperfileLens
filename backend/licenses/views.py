"""
License Views for HyperFileLens

Provides API endpoints for:
- Machine code generation (auto-generated on first access)
- License activation (initial/renewal/upgrade)
- License status checking with usage statistics
- License history for audit
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import datetime
import json

from .models import License, LicenseHistory, MachineCode, QuotaUsage, generate_machine_code
from .serializers import LicenseSerializer, LicenseHistorySerializer, MachineCodeSerializer
from .crypto import LicenseCrypto


class LicenseViewSet(viewsets.ModelViewSet):
    """
    API endpoints for license management.
    
    Endpoints:
    - GET /api/v1/licenses/current/ - Get current active license with usage stats
    - GET/POST /api/v1/licenses/machine_code/ - Generate machine code
    - POST /api/v1/licenses/activate/ - Activate/Renew/Upgrade license
    - GET /api/v1/licenses/history/ - View license history
    """
    
    serializer_class = LicenseSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter licenses by user's tenant."""
        return License.objects.filter(tenant=self.request.user.tenant)
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR', '')
    
    def _get_or_create_machine_code(self, request):
        """Get existing machine code or create a new one (auto-generated)."""
        tenant = request.user.tenant
        
        # Check if machine code already exists
        existing = MachineCode.objects.filter(tenant=tenant).first()
        if existing:
            return existing.code
        
        # Auto-generate new machine code
        machine_code, components = generate_machine_code(
            tenant_id=str(tenant.id),
            user_id=str(request.user.id)
        )
        
        # Store new machine code
        MachineCode.objects.create(
            code=machine_code,
            tenant=tenant,
            user=request.user,
            mac_address=components.get('mac', ''),
            cpu_id=components.get('cpu_id', ''),
            hostname=components.get('hostname', ''),
        )
        
        return machine_code
    
    def _get_usage_stats(self, tenant) -> dict:
        """Get current usage statistics for the tenant."""
        from django.apps import apps
        
        stats = {}
        
        try:
            # Tenants count (for super admin)
            Tenant = apps.get_model('tenants', 'Tenant')
            stats['tenants_count'] = Tenant.objects.filter(status='active').count()
        except Exception:
            stats['tenants_count'] = 0
        
        try:
            # Users count
            User = apps.get_model('accounts', 'User')
            stats['users_count'] = User.objects.filter(tenant=tenant, is_active=True).count()
        except Exception:
            stats['users_count'] = 0
        
        try:
            # Proxies count
            Proxy = apps.get_model('nodes', 'Proxy')
            stats['proxies_count'] = Proxy.objects.filter(tenant=tenant, status='online').count()
        except Exception:
            stats['proxies_count'] = 0
        
        try:
            # Storage used (GB) - from repositories
            Repository = apps.get_model('repository', 'Repository')
            repos = Repository.objects.filter(tenant=tenant)
            stats['storage_used_gb'] = sum(r.storage_used_gb or 0 for r in repos)
        except Exception:
            stats['storage_used_gb'] = 0
        
        try:
            # Gateways count
            Gateway = apps.get_model('nodes', 'Gateway')
            stats['gateways_count'] = Gateway.objects.filter(tenant=tenant, status='online').count()
        except Exception:
            stats['gateways_count'] = 0
        
        try:
            # AI Insights used this month
            stats['ai_insights_used'] = QuotaUsage.get_monthly_usage(
                tenant=tenant, 
                quota_type='ai_insights'
            )
        except Exception:
            stats['ai_insights_used'] = 0
        
        try:
            # Backup tasks count
            BackupTask = apps.get_model('backup_tasks', 'BackupTask')
            stats['backup_tasks_count'] = BackupTask.objects.filter(tenant=tenant).count()
        except Exception:
            stats['backup_tasks_count'] = 0
        
        try:
            # Recovery tasks count
            RecoveryTask = apps.get_model('recovery_tasks', 'RecoveryTask')
            stats['recovery_tasks_count'] = RecoveryTask.objects.filter(tenant=tenant).count()
        except Exception:
            stats['recovery_tasks_count'] = 0
        
        try:
            # Source resources count
            SourceResource = apps.get_model('source_resources', 'SourceResource')
            stats['source_resources_count'] = SourceResource.objects.filter(tenant=tenant).count()
        except Exception:
            stats['source_resources_count'] = 0
        
        try:
            # Policies count
            Policy = apps.get_model('policies', 'Policy')
            stats['policies_count'] = Policy.objects.filter(tenant=tenant).count()
        except Exception:
            stats['policies_count'] = 0
        
        try:
            # Repositories count
            Repository = apps.get_model('repository', 'Repository')
            stats['repositories_count'] = Repository.objects.filter(tenant=tenant).count()
        except Exception:
            stats['repositories_count'] = 0
        
        return stats
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def current(self, request):
        """
        Get the current active license for the tenant with usage statistics.
        
        Returns:
        - is_valid: Whether license is valid
        - license: License details with limits
        - usage: Current usage statistics
        - machine_code: Auto-generated machine code for activation
        """
        try:
            tenant = request.user.tenant
            
            # Auto-generate machine code if not exists
            machine_code = self._get_or_create_machine_code(request)
            
            # Get active license
            license = License.get_active_license(tenant=tenant)
            
            if not license:
                return Response({
                    'is_valid': False,
                    'message': _('No active license found'),
                    'machine_code': machine_code,
                    'usage': self._get_usage_stats(tenant),
                })
            
            # Get usage statistics
            usage_stats = self._get_usage_stats(tenant)
            
            return Response({
                'is_valid': license.is_valid,
                'license': LicenseSerializer(license).data,
                'limits': license.get_limits(),
                'days_until_expiry': license.days_until_expiry,
                'usage': usage_stats,
                'machine_code': machine_code,
            })
        except Exception as e:
            return Response({
                'is_valid': False,
                'error': str(e),
            })
    
    @action(detail=False, methods=['get', 'post'], permission_classes=[IsAuthenticated])
    def machine_code(self, request):
        """
        Get existing machine code or force regenerate.
        
        GET: Get existing machine code (auto-generated if not exists)
        POST: Force regenerate machine code (when hardware changed)
        
        Note: Machine code is auto-generated on first access to /current/ endpoint.
        """
        force_regenerate = request.method == 'POST'
        
        try:
            tenant = request.user.tenant
            
            # Check if machine code already exists
            existing = MachineCode.objects.filter(tenant=tenant).first()
            
            if existing and not force_regenerate:
                # Return existing machine code
                return Response({
                    'machine_code': existing.code,
                    'tenant_name': tenant.name,
                    'created_at': existing.created_at.isoformat(),
                    'message': _('Machine code for activation'),
                })
            
            # Generate new machine code
            machine_code, components = generate_machine_code(
                tenant_id=str(tenant.id),
                user_id=str(request.user.id)
            )
            
            # Delete old record if force regenerate
            if existing:
                existing.delete()
            
            # Store new machine code
            machine_code_record = MachineCode.objects.create(
                code=machine_code,
                tenant=tenant,
                user=request.user,
                mac_address=components.get('mac', ''),
                cpu_id=components.get('cpu_id', ''),
                hostname=components.get('hostname', ''),
            )
            
            return Response({
                'machine_code': machine_code,
                'tenant_name': tenant.name,
                'components': {
                    'source': components.get('source', 'unknown'),
                },
                'message': _('Machine code generated'),
            })
            
        except Exception as e:
            return Response({
                'error': 'generation_failed',
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def activate(self, request):
        """
        Activate, renew, or upgrade license.
        
        Request body:
        {
            "activation_code": "HFL-ACT-..."
        }
        
        Behavior:
        - Initial: Create new license if none exists
        - Renewal: Extend expiry date, keep limits
        - Upgrade: Update limits (and optionally expiry)
        
        History is preserved for audit.
        """
        activation_code = request.data.get('activation_code')
        
        if not activation_code:
            return Response({
                'error': 'missing_activation_code',
                'message': _('Activation code is required'),
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify and decode activation code
            activation_data = LicenseCrypto.verify(activation_code)
            
            license_key = activation_data['license_key']
            machine_code = activation_data['machine_code']
            
            # Verify machine code matches
            tenant = request.user.tenant
            current_machine_code_record = MachineCode.objects.filter(tenant=tenant).first()
            
            if not current_machine_code_record:
                return Response({
                    'error': 'machine_code_not_found',
                    'message': _('Please refresh the page to generate a machine code'),
                }, status=status.HTTP_400_BAD_REQUEST)
            
            current_machine_code = current_machine_code_record.code
            
            if machine_code != current_machine_code:
                return Response({
                    'error': 'machine_code_mismatch',
                    'message': _('Activation code is not for this machine'),
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Parse dates
            issued_at = datetime.fromisoformat(
                activation_data['issued_at'].replace('Z', '+00:00')
            )
            expires_at = None
            if activation_data.get('expires_at'):
                expires_at = datetime.fromisoformat(
                    activation_data['expires_at'].replace('Z', '+00:00')
                )
            
            limits = activation_data['limits']
            
            # Check for existing license
            existing_license = License.objects.filter(tenant=tenant).first()
            
            if existing_license:
                # Determine change type
                change_type, reason = self._determine_change_type(
                    existing_license, limits, expires_at
                )
                
                # Archive current license to history
                existing_license.archive_to_history(
                    change_type=change_type,
                    reason=reason,
                    changed_by=request.user,
                )
                
                # Update existing license
                existing_license.license_key = license_key
                existing_license.machine_code = machine_code
                existing_license.issued_at = issued_at
                existing_license.expires_at = expires_at
                
                # Update limits
                existing_license.max_tenants = limits.get('max_tenants', 1)
                existing_license.max_users = limits.get('max_users', 10)
                existing_license.max_proxies = limits.get('max_proxies', 5)
                existing_license.max_storage_gb = limits.get('max_storage_gb', 100)
                existing_license.max_gateways = limits.get('max_gateways', 1)
                existing_license.ai_insights_quota = limits.get('ai_insights_quota', 100)
                existing_license.max_backup_tasks = limits.get('max_backup_tasks', 10)
                existing_license.max_recovery_tasks = limits.get('max_recovery_tasks', 10)
                existing_license.max_source_resources = limits.get('max_source_resources', 10)
                existing_license.max_policies = limits.get('max_policies', 10)
                existing_license.max_repositories = limits.get('max_repositories', 5)
                
                existing_license.save()
                
                license_obj = existing_license
            else:
                # Create new license
                license_obj = License.objects.create(
                    tenant=tenant,
                    license_key=license_key,
                    machine_code=machine_code,
                    issued_at=issued_at,
                    expires_at=expires_at,
                    max_tenants=limits.get('max_tenants', 1),
                    max_users=limits.get('max_users', 10),
                    max_proxies=limits.get('max_proxies', 5),
                    max_storage_gb=limits.get('max_storage_gb', 100),
                    max_gateways=limits.get('max_gateways', 1),
                    ai_insights_quota=limits.get('ai_insights_quota', 100),
                    max_backup_tasks=limits.get('max_backup_tasks', 10),
                    max_recovery_tasks=limits.get('max_recovery_tasks', 10),
                    max_source_resources=limits.get('max_source_resources', 10),
                    max_policies=limits.get('max_policies', 10),
                    max_repositories=limits.get('max_repositories', 5),
                )
                
                # Archive to history
                license_obj.archive_to_history(
                    change_type='initial',
                    reason='Initial license activation',
                    changed_by=request.user,
                )
            
            return Response({
                'success': True,
                'message': _('License activated successfully'),
                'license': LicenseSerializer(license_obj).data,
                'change_type': 'initial' if not existing_license else change_type,
            })
            
        except ValueError as e:
            return Response({
                'error': 'invalid_activation_code',
                'message': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'activation_failed',
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _determine_change_type(self, existing_license, new_limits, new_expires_at):
        """Determine if this is a renewal, upgrade, or downgrade."""
        reason_parts = []
        
        # Check expiry change
        if new_expires_at and existing_license.expires_at:
            if new_expires_at > existing_license.expires_at:
                reason_parts.append('expiry extended')
            elif new_expires_at < existing_license.expires_at:
                reason_parts.append('expiry shortened')
        
        # Check limits change
        limit_fields = [
            'max_tenants', 'max_users', 'max_proxies', 'max_storage_gb',
            'max_gateways', 'ai_insights_quota', 'max_backup_tasks',
            'max_recovery_tasks', 'max_source_resources', 'max_policies', 'max_repositories'
        ]
        
        upgrades = 0
        downgrades = 0
        
        for field in limit_fields:
            old_val = getattr(existing_license, field, 0)
            new_val = new_limits.get(field, 0)
            if new_val > old_val:
                upgrades += 1
            elif new_val < old_val:
                downgrades += 1
        
        # Determine change type
        if upgrades > 0 and downgrades == 0:
            change_type = 'upgrade'
            reason = f"Limits upgraded ({upgrades} items increased)"
        elif downgrades > 0 and upgrades == 0:
            change_type = 'downgrade'
            reason = f"Limits downgraded ({downgrades} items decreased)"
        elif new_expires_at and existing_license.expires_at and new_expires_at > existing_license.expires_at:
            change_type = 'renewal'
            reason = 'License renewed'
        else:
            change_type = 'upgrade' if upgrades >= downgrades else 'downgrade'
            reason = f"Mixed change: {upgrades} upgrades, {downgrades} downgrades"
        
        return change_type, reason
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def history(self, request):
        """
        Get license history for audit.
        
        Returns all license changes for the current tenant.
        """
        tenant = request.user.tenant
        
        history = LicenseHistory.objects.filter(
            tenant=tenant
        ).order_by('-archived_at')
        
        page = self.paginate_queryset(history)
        if page is not None:
            serializer = LicenseHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = LicenseHistorySerializer(history, many=True)
        return Response({
            'results': serializer.data,
            'count': history.count(),
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def validate(self, request):
        """
        Validate if the current license is valid for a specific operation.
        
        Query params:
        - quota_type: Type of quota to check (users, storage, etc.)
        - amount: Amount to check (default 1)
        """
        quota_type = request.query_params.get('quota_type')
        amount = int(request.query_params.get('amount', 1))
        
        if not quota_type:
            return Response({
                'error': 'missing_quota_type',
                'message': _('quota_type parameter is required'),
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            license = License.get_active_license(tenant=request.user.tenant)
            
            if not license:
                return Response({
                    'is_valid': False,
                    'message': _('No active license'),
                })
            
            # Map quota_type to license field
            quota_map = {
                'users': ('max_users', 'users_count'),
                'proxies': ('max_proxies', 'proxies_count'),
                'storage_gb': ('max_storage_gb', 'storage_used_gb'),
                'gateways': ('max_gateways', 'gateways_count'),
                'ai_insights': ('ai_insights_quota', 'ai_insights_used'),
                'backup_tasks': ('max_backup_tasks', 'backup_tasks_count'),
                'recovery_tasks': ('max_recovery_tasks', 'recovery_tasks_count'),
                'source_resources': ('max_source_resources', 'source_resources_count'),
                'policies': ('max_policies', 'policies_count'),
                'repositories': ('max_repositories', 'repositories_count'),
                'tenants': ('max_tenants', 'tenants_count'),
            }
            
            if quota_type not in quota_map:
                return Response({
                    'is_valid': False,
                    'message': f'Unknown quota type: {quota_type}',
                })
            
            limit_field, usage_field = quota_map[quota_type]
            limit = getattr(license, limit_field, 0)
            current_usage = self._get_usage_stats(request.user.tenant).get(usage_field, 0)
            
            is_within_limit = (current_usage + amount) <= limit
            
            return Response({
                'is_valid': is_within_limit,
                'quota_type': quota_type,
                'limit': limit,
                'current_usage': current_usage,
                'requested': amount,
                'remaining': max(0, limit - current_usage),
                'message': _('Within limit') if is_within_limit else _('Quota exceeded'),
            })
            
        except Exception as e:
            return Response({
                'is_valid': False,
                'error': str(e),
            })
