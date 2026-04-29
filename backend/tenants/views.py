"""
Views for Tenants API
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Count

from .models import Tenant, TenantInvitation
from .serializers import (
    TenantSerializer,
    TenantListSerializer,
    TenantDetailSerializer,
    TenantInvitationSerializer,
    AcceptInvitationSerializer,
    TenantQuotaSerializer
)
from accounts.models import User


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission class for super admin only.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class IsTenantAdmin(permissions.BasePermission):
    """
    Permission class for tenant admin or super admin.
    """

    def has_permission(self, request, view):
        if not request.user:
            return False
        if request.user.is_superuser:
            return True
        return request.user.tenant_role in ['owner', 'admin']


class TenantViewSet(viewsets.ModelViewSet):
    """
    API endpoint for tenant management.

    Regular users can only see their own tenant.
    Super admins can manage all tenants.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Tenant.objects.all()
        if user.tenant:
            return Tenant.objects.filter(pk=user.tenant.pk)
        return Tenant.objects.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return TenantListSerializer
        if self.action == 'retrieve':
            return TenantDetailSerializer
        return TenantSerializer

    def perform_create(self, serializer):
        """Create a new tenant."""
        tenant = serializer.save()
        # Assign the creator as owner
        user = self.request.user
        user.tenant = tenant
        user.tenant_role = User.TenantRole.OWNER
        user.save()

    @action(detail=True, methods=['get'])
    def quota(self, request, pk=None):
        """Get quota usage for a tenant."""
        tenant = self.get_object()
        usage = tenant.get_quota_usage()
        data = {
            'max_proxies': tenant.max_proxies,
            'max_repositories': tenant.max_repositories,
            'max_storage_gb': tenant.max_storage_gb,
            'max_users': tenant.max_users,
            'max_backup_tasks': tenant.max_backup_tasks,
            'current_proxies': usage['proxies'],
            'current_repositories': usage['repositories'],
            'current_users': usage['users'],
            'current_storage_gb': usage['storage_used_gb'],
        }
        return Response(data)

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend a tenant (super admin only)."""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can suspend tenants'},
                status=status.HTTP_403_FORBIDDEN
            )
        tenant = self.get_object()
        tenant.status = Tenant.TenantStatus.SUSPENDED
        tenant.save()
        return Response({'status': 'suspended'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a tenant (super admin only)."""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can activate tenants'},
                status=status.HTTP_403_FORBIDDEN
            )
        tenant = self.get_object()
        tenant.status = Tenant.TenantStatus.ACTIVE
        tenant.save()
        return Response({'status': 'activated'})

    @action(detail=True, methods=['get'])
    def invitations(self, request, pk=None):
        """List pending invitations for a tenant."""
        tenant = self.get_object()
        invitations = tenant.invitations.filter(
            status=TenantInvitation.InvitationStatus.PENDING,
            expires_at__gt=timezone.now()
        )
        serializer = TenantInvitationSerializer(invitations, many=True)
        return Response(serializer.data)


class TenantInvitationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for tenant invitations.
    """

    serializer_class = TenantInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return TenantInvitation.objects.all()
        if user.tenant and user.tenant_role in ['owner', 'admin']:
            return TenantInvitation.objects.filter(tenant=user.tenant)
        return TenantInvitation.objects.none()

    def perform_create(self, serializer):
        """Create an invitation."""
        user = self.request.user
        if not user.tenant:
            raise ValueError("User must belong to a tenant to send invitations")
        serializer.save(
            tenant=user.tenant,
            invited_by=user,
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def accept(self, request):
        """Accept an invitation."""
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        try:
            invitation = TenantInvitation.objects.get(token=token)
        except TenantInvitation.DoesNotExist:
            return Response(
                {'error': 'Invalid invitation token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not invitation.is_valid():
            return Response(
                {'error': 'Invitation has expired or already been used'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user exists
        email = invitation.email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Create new user
            password = serializer.validated_data.get('password')
            first_name = serializer.validated_data.get('first_name', '')
            last_name = serializer.validated_data.get('last_name', '')
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

        # Assign tenant and role
        user.tenant = invitation.tenant
        user.tenant_role = invitation.role
        user.save()

        # Mark invitation as accepted
        invitation.status = TenantInvitation.InvitationStatus.ACCEPTED
        invitation.accepted_at = timezone.now()
        invitation.save()

        return Response({
            'status': 'accepted',
            'tenant': invitation.tenant.name,
            'role': invitation.role
        })

    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """Resend an invitation."""
        invitation = self.get_object()
        if invitation.status != TenantInvitation.InvitationStatus.PENDING:
            return Response(
                {'error': 'Can only resend pending invitations'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invitation.expires_at = timezone.now() + timezone.timedelta(days=7)
        invitation.save()

        # TODO: Send email notification

        return Response({'status': 'resent'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an invitation."""
        invitation = self.get_object()
        invitation.status = TenantInvitation.InvitationStatus.DECLINED
        invitation.save()
        return Response({'status': 'cancelled'})
