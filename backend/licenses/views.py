"""
License Views for HyperFileLens

Provides API endpoints for:
- Machine code generation
- License activation (initial/renewal/upgrade)
- License status checking
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
    - GET /api/v1/licenses/current/ - Get current active license
    - GET/POST /api/v1/licenses/machine_code/ - Generate machine code
    - POST /api/v1/licenses/activate/ - Activate/Renew/Upgrade license
    - GET /api/v1/licenses/history/ - View license history (admin)
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
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def current(self, request):
        """
        Get the current active license for the tenant.
        
        Returns license details including:
        - Limits (users, storage, etc.)
        - Expiry date
        - Status
        """
        try:
            license = License.get_active_license(tenant=request.user.tenant)
            
            if not license:
                return Response({
                    'is_valid': False,
                    'message': _('No active license found'),
                })
            
            return Response({
                'is_valid': license.is_valid,
                'license': LicenseSerializer(license).data,
                'limits': license.get_limits(),
                'days_until_expiry': license.days_until_expiry,
            })
        except Exception as e:
            return Response({
                'is_valid': False,
                'error': str(e),
            })
    
    @action(detail=False, methods=['get', 'post'], permission_classes=[IsAuthenticated])
    def machine_code(self, request):
        """
        Generate machine code for license activation.
        
        GET: Get existing or generate new machine code
        POST: Force regenerate machine code (when hardware changed)
        
        Flow:
        1. User exports machine code from platform
        2. User sends code to sales team
        3. Sales generates activation code using this machine code
        4. User inputs activation code in platform
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
                    'message': _('Use this machine code to request an activation code'),
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
                'message': _('Machine code generated. Send this to sales team to get activation code.'),
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
                    'message': _('Please generate a machine code first'),
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
                    reason=reason
                )
                
                # Update existing license
                existing_license.license_key = license_key
                existing_license.version += 1
                existing_license.change_type = change_type
                existing_license.change_reason = reason
                existing_license.signature = activation_data['signature']
                existing_license.issued_at = issued_at
                existing_license.expires_at = expires_at
                existing_license.activated_by = request.user
                existing_license.status = License.LicenseStatus.ACTIVE
                
                # Update limits (for upgrade)
                existing_license.max_tenants = limits.get('max_tenants', existing_license.max_tenants)
                existing_license.max_users = limits.get('max_users', existing_license.max_users)
                existing_license.max_proxies = limits.get('max_proxies', existing_license.max_proxies)
                existing_license.max_storage_gb = limits.get('max_storage_gb', existing_license.max_storage_gb)
                existing_license.max_gateways = limits.get('max_gateways', existing_license.max_gateways)
                existing_license.ai_insights_quota = limits.get('ai_insights_quota', existing_license.ai_insights_quota)
                existing_license.max_backup_tasks = limits.get('max_backup_tasks', existing_license.max_backup_tasks)
                existing_license.max_recovery_tasks = limits.get('max_recovery_tasks', existing_license.max_recovery_tasks)
                existing_license.max_source_resources = limits.get('max_source_resources', existing_license.max_source_resources)
                existing_license.max_policies = limits.get('max_policies', existing_license.max_policies)
                existing_license.max_repositories = limits.get('max_repositories', existing_license.max_repositories)
                
                existing_license.save()
                
                license = existing_license
                
            else:
                # Initial activation
                license = License.objects.create(
                    license_key=license_key,
                    version=1,
                    change_type=License.ChangeType.INITIAL,
                    machine_code=current_machine_code,
                    tenant=tenant,
                    activated_by=request.user,
                    max_tenants=limits.get('max_tenants', 1),
                    max_users=limits.get('max_users', 10),
                    max_proxies=limits.get('max_proxies', 5),
                    max_storage_gb=limits.get('max_storage_gb', 100),
                    max_gateways=limits.get('max_gateways', 1),
                    ai_insights_quota=limits.get('ai_insights_quota', 100),
                    max_backup_tasks=limits.get('max_backup_tasks', 10),
                    max_recovery_tasks=limits.get('max_recovery_tasks', 10),
                    max_source_resources=limits.get('max_source_resources', 20),
                    max_policies=limits.get('max_policies', 50),
                    max_repositories=limits.get('max_repositories', 5),
                    issued_at=issued_at,
                    expires_at=expires_at,
                    signature=activation_data['signature'],
                    status=License.LicenseStatus.ACTIVE,
                )
                
                # Create quota usage tracker
                QuotaUsage.objects.create(license=license)
            
            return Response({
                'success': True,
                'message': self._get_success_message(license.change_type),
                'change_type': license.change_type,
                'license': LicenseSerializer(license).data,
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
        """
        Determine if this is a renewal or upgrade.
        
        Renewal: Same limits, extended expiry
        Upgrade: Increased limits (may also extend expiry)
        """
        # Check if limits changed
        limits_changed = (
            new_limits.get('max_users', existing_license.max_users) > existing_license.max_users or
            new_limits.get('max_proxies', existing_license.max_proxies) > existing_license.max_proxies or
            new_limits.get('max_storage_gb', existing_license.max_storage_gb) > existing_license.max_storage_gb or
            new_limits.get('max_gateways', existing_license.max_gateways) > existing_license.max_gateways or
            new_limits.get('ai_insights_quota', existing_license.ai_insights_quota) > existing_license.ai_insights_quota or
            new_limits.get('max_tenants', existing_license.max_tenants) > existing_license.max_tenants or
            new_limits.get('max_backup_tasks', existing_license.max_backup_tasks) > existing_license.max_backup_tasks or
            new_limits.get('max_recovery_tasks', existing_license.max_recovery_tasks) > existing_license.max_recovery_tasks or
            new_limits.get('max_source_resources', existing_license.max_source_resources) > existing_license.max_source_resources or
            new_limits.get('max_policies', existing_license.max_policies) > existing_license.max_policies or
            new_limits.get('max_repositories', existing_license.max_repositories) > existing_license.max_repositories
        )
        
        if limits_changed:
            reason = f"Upgraded limits"
            return License.ChangeType.UPGRADE, reason
        
        # Check if expiry extended
        if new_expires_at and existing_license.expires_at:
            if new_expires_at > existing_license.expires_at:
                reason = f"Extended from {existing_license.expires_at.date()} to {new_expires_at.date()}"
                return License.ChangeType.RENEWAL, reason
        
        # Default to renewal
        reason = "License renewed"
        return License.ChangeType.RENEWAL, reason
    
    def _get_success_message(self, change_type):
        """Get appropriate success message."""
        messages = {
            License.ChangeType.INITIAL: _('License activated successfully'),
            License.ChangeType.RENEWAL: _('License renewed successfully'),
            License.ChangeType.UPGRADE: _('License upgraded successfully'),
        }
        return messages.get(change_type, _('License updated successfully'))
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def history(self, request):
        """
        Get license history for current tenant.
        
        Shows all previous versions of the license for audit.
        """
        history = LicenseHistory.objects.filter(
            tenant=request.user.tenant
        ).order_by('-archived_at')
        
        return Response({
            'count': history.count(),
            'results': LicenseHistorySerializer(history, many=True).data,
        })


class LicenseHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin view for all license history."""
    
    queryset = LicenseHistory.objects.all()
    serializer_class = LicenseHistorySerializer
    permission_classes = [IsAdminUser]
