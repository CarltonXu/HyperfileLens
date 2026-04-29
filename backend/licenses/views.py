"""
License Views for HyperFileLens

API endpoints for license management with machine binding.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import License, MachineCode, QuotaUsage, LicenseAuditLog
from .serializers import (
    LicenseSerializer,
    LicenseStatusSerializer,
    MachineCodeSerializer,
    ActivationSerializer,
    QuotaUsageSerializer,
)
from .crypto import MachineCodeGenerator, ActivationCode


class IsSuperUser(IsAdminUser):
    """Permission class for superuser only."""
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)


class LicenseViewSet(viewsets.ModelViewSet):
    """
    License Management API.
    
    Security Notes:
    - Licenses can only be activated with valid activation code
    - Machine code binds license to specific machine + tenant + user
    - All limits are verified on resource creation
    """
    
    queryset = License.objects.all()
    serializer_class = LicenseSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see licenses for their tenant."""
        user = self.request.user
        if user.is_superuser:
            return License.objects.all()
        return License.objects.filter(tenant=user.tenant)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def current(self, request):
        """Get current active license for user's tenant."""
        license = License.get_active_license(request.user.tenant)
        
        if not license:
            return Response({
                'is_valid': False,
                'message': 'No active license found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(license)
        return Response({
            'is_valid': license.is_valid,
            'license': serializer.data,
            'limits': license.get_limits(),
            'days_until_expiry': license.days_until_expiry,
            'is_perpetual': license.is_perpetual,
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def activate(self, request):
        """
        Activate a license using activation code.
        
        Request body:
        {
            "activation_code": "HFL-ACT-XXXXXXXX"
        }
        """
        activation_code = request.data.get('activation_code')
        
        if not activation_code:
            return Response({
                'error': 'activation_code_required',
                'message': _('Activation code is required')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Decode activation code
            activation_data = ActivationCode.decode(activation_code)
            
            # Verify signature
            if not ActivationCode.verify(activation_data):
                return Response({
                    'error': 'invalid_signature',
                    'message': _('Activation code signature verification failed')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate current machine code
            current_machine_code, components = MachineCodeGenerator.generate(
                tenant_id=request.user.tenant.id,
                user_id=request.user.id
            )
            
            # Verify machine code matches
            if activation_data['machine_code'] != current_machine_code:
                return Response({
                    'error': 'machine_code_mismatch',
                    'message': _(
                        'This activation code is bound to a different machine or tenant. '
                        'Please generate a new machine code for this environment.'
                    ),
                    'expected_machine_code': activation_data['machine_code'],
                    'current_machine_code': current_machine_code,
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if already activated
            if License.objects.filter(machine_code=current_machine_code).exists():
                return Response({
                    'error': 'already_activated',
                    'message': _('This machine has already activated a license')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if license key already used
            license_key = activation_data['license_key']
            if License.objects.filter(license_key=license_key).exists():
                return Response({
                    'error': 'license_key_used',
                    'message': _('This license key has already been used')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Parse dates
            from datetime import datetime
            issued_at = datetime.fromisoformat(
                activation_data['issued_at'].replace('Z', '+00:00')
            )
            
            expires_at = None
            if activation_data.get('expires_at'):
                expires_at = datetime.fromisoformat(
                    activation_data['expires_at'].replace('Z', '+00:00')
                )
            
            # Create license
            limits = activation_data['limits']
            license = License.objects.create(
                license_key=license_key,
                machine_code=current_machine_code,
                tenant=request.user.tenant,
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
            
            # Update machine code record
            MachineCode.objects.filter(code=current_machine_code).update(used_at=timezone.now())
            
            # Log activation
            LicenseAuditLog.objects.create(
                license=license,
                action=LicenseAuditLog.ActionType.ACTIVATED,
                details={
                    'license_key': license_key,
                    'machine_code': current_machine_code,
                    'tenant': str(request.user.tenant.id),
                    'user': str(request.user.id),
                },
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            
            return Response({
                'success': True,
                'message': _('License activated successfully'),
                'license': LicenseSerializer(license).data,
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({
                'error': 'invalid_activation_code',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'activation_failed',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def machine_code(self, request):
        """
        Generate and return machine code for current environment.
        
        The user should send this code to sales team to get an activation code.
        """
        # Generate machine code
        machine_code, components = MachineCodeGenerator.generate(
            tenant_id=request.user.tenant.id,
            user_id=request.user.id
        )
        
        # Store machine code record
        machine_code_record, created = MachineCode.objects.update_or_create(
            code=machine_code,
            defaults={
                'tenant': request.user.tenant,
                'user': request.user,
                'mac_address': components['mac'],
                'cpu_id': components['cpu_id'],
                'hostname': components['hostname'],
            }
        )
        
        # Log generation
        LicenseAuditLog.objects.create(
            machine_code=machine_code_record,
            action=LicenseAuditLog.ActionType.GENERATED,
            details={
                'machine_code': machine_code,
                'tenant': str(request.user.tenant.id),
                'user': str(request.user.id),
            },
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        return Response({
            'machine_code': machine_code,
            'components': {
                'mac_address': components['mac'],
                'cpu_id': components['cpu_id'][:20] + '...' if len(components['cpu_id']) > 20 else components['cpu_id'],
                'hostname': components['hostname'],
                'tenant_id': str(request.user.tenant.id),
                'tenant_name': request.user.tenant.name,
            },
            'instructions': _(
                'Please send this machine code to the sales team to get your activation code. '
                'The activation code can only be used in this environment with your current account.'
            )
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def usage(self, request):
        """Get current usage against license limits."""
        license = License.get_active_license(request.user.tenant)
        
        if not license:
            return Response({
                'error': 'no_license',
                'message': _('No active license found')
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            quota = license.quota_usage
        except QuotaUsage.DoesNotExist:
            quota = QuotaUsage.objects.create(license=license)
        
        return Response({
            'license': LicenseSerializer(license).data,
            'limits': license.get_limits(),
            'usage': QuotaUsageSerializer(quota).data,
            'usage_percentage': {
                'users': round(quota.users_count / license.max_users * 100, 1) if license.max_users > 0 else 0,
                'proxies': round(quota.proxies_count / license.max_proxies * 100, 1) if license.max_proxies > 0 else 0,
                'storage_gb': round(quota.storage_used_gb / license.max_storage_gb * 100, 1) if license.max_storage_gb > 0 else 0,
                'gateways': round(quota.gateways_count / license.max_gateways * 100, 1) if license.max_gateways > 0 else 0,
            }
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperUser])
    def revoke(self, request, pk=None):
        """Revoke a license (superuser only)."""
        license = self.get_object()
        license.status = License.LicenseStatus.REVOKED
        license.save(update_fields=['status'])
        
        # Log revocation
        LicenseAuditLog.objects.create(
            license=license,
            action=LicenseAuditLog.ActionType.REVOKED,
            details={'reason': request.data.get('reason', 'No reason provided')},
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        return Response({'message': _('License revoked successfully')})
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
