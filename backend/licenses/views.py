"""
Views for Licenses API
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
import json

from .models import License, LicenseAuditLog
from .serializers import (
    LicenseSerializer,
    LicenseListSerializer,
    LicenseDetailSerializer,
    LicenseCreateSerializer,
    LicenseVerifySerializer,
    LicenseStatusSerializer,
    LicenseAuditLogSerializer
)


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission class for super admin only.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class LicenseViewSet(viewsets.ModelViewSet):
    """
    API endpoint for license management.

    Only super admins can manage licenses.
    Regular users can view the current license status.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return License.objects.all()
        # Regular users can only see active license
        return License.objects.filter(status=License.LicenseStatus.ACTIVE)

    def get_serializer_class(self):
        if self.action == 'list':
            return LicenseListSerializer
        if self.action == 'retrieve':
            return LicenseDetailSerializer
        if self.action == 'create':
            return LicenseCreateSerializer
        return LicenseSerializer

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsSuperAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Create a new license with audit log."""
        license_obj = serializer.save()
        LicenseAuditLog.objects.create(
            license=license_obj,
            event_type=LicenseAuditLog.EventType.CREATED,
            message=f"License created for {license_obj.licensee_name}",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get the current active license."""
        license_obj = License.get_active_license()
        if not license_obj:
            return Response(
                {'error': 'No active license found'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = LicenseDetailSerializer(license_obj)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get license status summary."""
        license_obj = License.get_active_license()

        if not license_obj:
            return Response({
                'is_valid': False,
                'edition': None,
                'licensee_name': None,
                'expires_at': None,
                'days_until_expiry': 0,
                'features': {},
                'limits': {},
                'warnings': ['No active license found']
            })

        warnings = []
        if license_obj.days_until_expiry <= 30:
            warnings.append(f'License expires in {license_obj.days_until_expiry} days')
        if license_obj.days_until_expiry <= 7:
            warnings.append('License expiring soon! Please renew.')

        data = {
            'is_valid': license_obj.is_valid,
            'edition': license_obj.edition,
            'licensee_name': license_obj.licensee_name,
            'expires_at': license_obj.expires_at,
            'days_until_expiry': license_obj.days_until_expiry,
            'features': license_obj.features,
            'limits': license_obj.get_limits(),
            'warnings': warnings
        }

        serializer = LicenseStatusSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def verify(self, request):
        """Verify a license key."""
        serializer = LicenseVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        license_key = serializer.validated_data['license_key']
        fingerprint = serializer.validated_data.get('fingerprint')

        try:
            license_obj = License.objects.get(license_key=license_key)
        except License.DoesNotExist:
            LicenseAuditLog.objects.create(
                license=None,
                event_type=LicenseAuditLog.EventType.FAILED,
                message=f"Verification failed: Invalid license key {license_key[:8]}...",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response(
                {'valid': False, 'error': 'Invalid license key'},
                status=status.HTTP_400_BAD_REQUEST
            )

        is_valid = license_obj.is_valid

        # Check fingerprint binding if set
        if fingerprint and license_obj.fingerprint and license_obj.fingerprint != fingerprint:
            is_valid = False

        LicenseAuditLog.objects.create(
            license=license_obj,
            event_type=LicenseAuditLog.EventType.VERIFIED if is_valid else LicenseAuditLog.EventType.FAILED,
            message=f"License verification: {'success' if is_valid else 'failed'}",
            details={'fingerprint': fingerprint} if fingerprint else {},
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return Response({
            'valid': is_valid,
            'license': LicenseDetailSerializer(license_obj).data if is_valid else None
        })

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a license (super admin only)."""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can activate licenses'},
                status=status.HTTP_403_FORBIDDEN
            )

        license_obj = self.get_object()
        license_obj.status = License.LicenseStatus.ACTIVE
        license_obj.save()

        LicenseAuditLog.objects.create(
            license=license_obj,
            event_type=LicenseAuditLog.EventType.ACTIVATED,
            message=f"License activated for {license_obj.licensee_name}",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return Response({'status': 'activated'})

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke a license (super admin only)."""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can revoke licenses'},
                status=status.HTTP_403_FORBIDDEN
            )

        license_obj = self.get_object()
        license_obj.status = License.LicenseStatus.REVOKED
        license_obj.save()

        LicenseAuditLog.objects.create(
            license=license_obj,
            event_type=LicenseAuditLog.EventType.REVOKED,
            message=f"License revoked for {license_obj.licensee_name}",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return Response({'status': 'revoked'})

    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        """Renew a license (super admin only)."""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can renew licenses'},
                status=status.HTTP_403_FORBIDDEN
            )

        license_obj = self.get_object()

        # Extend expiry by 1 year (or use provided duration)
        duration_days = request.data.get('duration_days', 365)
        if license_obj.expires_at:
            license_obj.expires_at = license_obj.expires_at + timezone.timedelta(days=duration_days)
        else:
            license_obj.expires_at = timezone.now() + timezone.timedelta(days=duration_days)

        license_obj.status = License.LicenseStatus.ACTIVE
        license_obj.save()

        LicenseAuditLog.objects.create(
            license=license_obj,
            event_type=LicenseAuditLog.EventType.RENEWED,
            message=f"License renewed for {license_obj.licensee_name}",
            details={'duration_days': duration_days},
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return Response({
            'status': 'renewed',
            'new_expiry': license_obj.expires_at
        })

    @action(detail=True, methods=['get'])
    def audit_logs(self, request, pk=None):
        """Get audit logs for a license."""
        license_obj = self.get_object()
        logs = license_obj.audit_logs.all()[:100]
        serializer = LicenseAuditLogSerializer(logs, many=True)
        return Response(serializer.data)


class LicenseAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for license audit logs (read-only).
    """

    serializer_class = LicenseAuditLogSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return LicenseAuditLog.objects.all()


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def check_feature(request, feature_name):
    """
    Check if a feature is enabled in the current license.

    This is a public endpoint that doesn't require authentication,
    useful for frontend feature gating.
    """
    license_obj = License.get_active_license()

    if not license_obj:
        return Response({'enabled': False})

    enabled = license_obj.has_feature(feature_name)
    return Response({'enabled': enabled})
