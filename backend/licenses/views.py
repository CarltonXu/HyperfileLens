"""
License Views for HyperFileLens

API endpoints for license management with security enforcement.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import License, LicenseAuditLog, QuotaUsage
from .serializers import (
    LicenseSerializer,
    LicenseImportSerializer,
    LicenseStatusSerializer,
    QuotaUsageSerializer,
)
from .crypto import LicenseEncoder, HardwareFingerprint


class IsSuperUser(IsAdminUser):
    """Permission class for superuser only."""
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)


class LicenseViewSet(viewsets.ModelViewSet):
    """
    License Management API.
    
    Security Notes:
    - Licenses can only be created via import (encoded license string)
    - Direct modification of limit fields is prevented
    - Signature verification is enforced on every operation
    - Machine binding is verified on access
    """
    
    queryset = License.objects.all()
    serializer_class = LicenseSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Only superusers can manage licenses."""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'import_license']:
            return [IsSuperUser()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Non-superusers can only see current license status."""
        if not self.request.user.is_superuser:
            return License.objects.filter(status=License.LicenseStatus.ACTIVE)
        return License.objects.all()
    
    def perform_create(self, serializer):
        """Prevent direct creation - use import instead."""
        raise ValidationError(
            _("Licenses must be imported using the import endpoint. "
              "Direct creation is not allowed for security reasons.")
        )
    
    def perform_update(self, serializer):
        """Prevent modification of protected fields."""
        # Only status can be modified directly
        allowed_fields = {'status'}
        changed_fields = set(serializer.validated_data.keys())
        
        if changed_fields - allowed_fields:
            raise ValidationError(
                _("Cannot modify license limits directly. "
                  "Please import a new license to change limits.")
            )
        
        serializer.save()
    
    @action(detail=False, methods=['post'], permission_classes=[IsSuperUser])
    def import_license(self, request):
        """
        Import a license from encoded string or JSON data.
        
        This is the ONLY way to create a valid license.
        
        Request body (option 1):
        {
            "encoded_license": "HFL-LICENSE-XXXX-XXXX-..."
        }
        
        Request body (option 2):
        {
            "license_data": {...},
            "signature": "..."
        }
        
        Returns:
            Created license details
        """
        serializer = LicenseImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Support both formats
            if serializer.validated_data.get('encoded_license'):
                encoded_license = serializer.validated_data['encoded_license']
                license = License.import_license(encoded_license)
            else:
                license_data = serializer.validated_data['license_data']
                signature = serializer.validated_data['signature']
                license = License.import_from_data(license_data, signature)
            
            # Create quota usage tracker
            QuotaUsage.objects.create(license=license)
            
            # Log the import
            LicenseAuditLog.objects.create(
                license=license,
                action='imported',
                details={
                    'licensee': license.licensee_name,
                    'edition': license.edition,
                },
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            
            return Response(
                LicenseSerializer(license).data,
                status=status.HTTP_201_CREATED
            )
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Get the current active license.
        
        Returns:
            Current license details or null if none
        """
        license = License.get_active_license()
        
        if not license:
            return Response({
                'is_valid': False,
                'error': 'No active license found'
            })
        
        return Response(LicenseSerializer(license).data)
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Get comprehensive license status.
        
        Returns:
            License status with quota usage
        """
        license = License.get_active_license()
        
        if not license:
            return Response({
                'is_valid': False,
                'error': 'No active license found',
                'product': 'HyperFileLens',
                'edition': 'unlicensed',
            })
        
        # Get or create quota usage
        quota_usage, _ = QuotaUsage.objects.get_or_create(license=license)
        quota_usage.sync()  # Sync to latest
        
        return Response(LicenseStatusSerializer({
            'license': license,
            'quota': quota_usage,
        }).data)
    
    @action(detail=False, methods=['post'])
    def verify(self, request):
        """
        Verify license integrity.
        
        Request body:
        {
            "encoded_license": "HFL-LICENSE-XXXX..." (optional)
        }
        
        Returns:
            Verification result
        """
        encoded_license = request.data.get('encoded_license')
        
        if encoded_license:
            # Verify a specific license string
            try:
                license_data, signature = LicenseEncoder.decode(encoded_license)
                is_valid = LicenseSigner.verify_signature(license_data, signature)
                
                return Response({
                    'is_valid': is_valid,
                    'license_key': license_data.get('license_key', 'Unknown'),
                    'edition': license_data.get('edition', 'Unknown'),
                    'validity_period': {
                        'starts': license_data.get('starts_at'),
                        'expires': license_data.get('expires_at'),
                    },
                    'limits': license_data.get('limits', {}),
                })
            except ValueError as e:
                return Response({
                    'is_valid': False,
                    'error': str(e)
                })
        else:
            # Verify current active license
            license = License.get_active_license()
            
            if not license:
                return Response({
                    'is_valid': False,
                    'error': 'No active license'
                })
            
            return Response({
                'is_valid': license.is_valid,
                'license_key': license.license_key,
                'edition': license.edition,
                'integrity_ok': license.verify_integrity(),
                'machine_bound': bool(license.machine_fingerprint),
                'days_until_expiry': license.days_until_expiry,
            })
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperUser])
    def activate(self, request, pk=None):
        """
        Activate a license and bind to current machine.
        
        This is a one-time operation that binds the license to the 
        current server's hardware fingerprint.
        
        Request body (optional):
        {
            "force": false,  // Force re-activation on different machine
        }
        """
        license = self.get_object()
        
        if license.status == License.LicenseStatus.REVOKED:
            return Response(
                {'error': 'Cannot activate a revoked license'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get current machine fingerprint
        current_machine_id = HardwareFingerprint.get_machine_id()
        
        # Check if already bound to a different machine
        if license.machine_fingerprint and license.machine_fingerprint != current_machine_id:
            force = request.data.get('force', False)
            if not force:
                return Response({
                    'error': 'License is already bound to a different machine',
                    'current_machine': current_machine_id[:16] + '...',
                    'bound_machine': license.machine_fingerprint[:16] + '...',
                    'hint': 'Use force=true to re-activate on this machine (will invalidate the other installation)',
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Activate and bind to machine
        license.activate(current_machine_id)
        
        LicenseAuditLog.objects.create(
            license=license,
            action='activated',
            details={
                'machine_id': current_machine_id[:32],
                'bound_at': str(license.activated_at),
            },
            ip_address=self.get_client_ip(request)
        )
        
        return Response({
            **LicenseSerializer(license).data,
            'machine_bound': True,
            'message': 'License activated and bound to this machine',
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperUser])
    def deactivate(self, request, pk=None):
        """Deactivate a license."""
        license = self.get_object()
        reason = request.data.get('reason', '')
        
        license.revoke(reason)
        
        return Response(LicenseSerializer(license).data)
    
    @action(detail=False, methods=['get'])
    def machine_fingerprint(self, request):
        """
        Get current machine fingerprint.
        
        Used when generating licenses bound to specific hardware.
        """
        return Response({
            'machine_id': HardwareFingerprint.get_machine_id(),
        })
    
    @action(detail=False, methods=['get'])
    def usage(self, request):
        """Get current quota usage."""
        license = License.get_active_license()
        
        if not license:
            return Response({'error': 'No active license'}, status=404)
        
        try:
            quota_usage = license.quota_usage
            quota_usage.sync()
            return Response(QuotaUsageSerializer(quota_usage).data)
        except QuotaUsage.DoesNotExist:
            return Response({'error': 'Quota usage not found'}, status=404)
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


class QuotaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Quota Usage API (Read-only).
    
    Provides real-time quota usage information.
    """
    
    queryset = QuotaUsage.objects.all()
    serializer_class = QuotaUsageSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def check(self, request):
        """
        Check if quota limits are exceeded.
        
        Query params:
        - resource: Resource type to check (tenants, users, proxies, repositories, storage)
        
        Returns:
            Quota check result
        """
        license = License.get_active_license()
        
        if not license:
            return Response({
                'allowed': False,
                'error': 'No active license'
            })
        
        quota_usage, _ = QuotaUsage.objects.get_or_create(license=license)
        quota_usage.sync()
        
        resource_type = request.query_params.get('resource')
        limits = quota_usage.check_limits()
        
        if resource_type:
            limit_info = limits.get(resource_type)
            if limit_info:
                return Response({
                    'resource': resource_type,
                    **limit_info,
                    'allowed': not limit_info['exceeded'],
                })
        
        return Response({
            'limits': limits,
            'all_within_limits': all(not v['exceeded'] for v in limits.values()),
        })
