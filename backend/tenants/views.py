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
        user.tenant_role = User.TenantRole.ADMIN
        user.save()

    def destroy(self, request, *args, **kwargs):
        """Delete a tenant. Prevent deleting own tenant or administrator tenant."""
        tenant = self.get_object()
        user = request.user
        
        # 不允许删除 administrator 租户（系统保留租户）
        if tenant.name == 'administrator':
            return Response(
                {'detail': 'Cannot delete the system administrator tenant.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 不允许删除自己关联的租户
        if user.tenant and user.tenant.id == tenant.id:
            return Response(
                {'detail': 'Cannot delete your own tenant.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否有用户关联到此租户
        users_in_tenant = User.objects.filter(tenant=tenant).count()
        if users_in_tenant > 0:
            return Response(
                {'detail': f'Cannot delete tenant with {users_in_tenant} associated user(s). Remove users first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tenant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get statistics for a tenant."""
        tenant = self.get_object()
        usage = tenant.get_quota_usage()
        data = {
            'user_count': usage['users'],
            'proxy_count': usage['proxies'],
            'repository_count': usage['repositories'],
            'storage_used': usage['storage_used_gb'] * 1024 * 1024 * 1024,  # Convert GB to bytes
            'max_users': tenant.max_users,
            'max_proxies': tenant.max_proxies,
            'max_repositories': tenant.max_repositories,
            'max_storage_gb': tenant.max_storage_gb,
        }
        return Response(data)

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

    def deactivate(self, request, pk=None):
        """Deactivate a tenant (super admin only)."""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can deactivate tenants'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tenant = self.get_object()
        
        # 不允许停用 administrator 租户
        if tenant.name == 'administrator':
            return Response(
                {'error': 'Cannot deactivate the system administrator tenant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 不允许停用自己所在的租户
        if request.user.tenant and request.user.tenant.id == tenant.id:
            return Response(
                {'error': 'Cannot deactivate your own tenant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tenant.status = Tenant.TenantStatus.SUSPENDED
        tenant.save()
        return Response({'status': 'deactivated'})

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

    def users(self, request, pk=None):
        """List users in a tenant."""
        tenant = self.get_object()
        users = User.objects.filter(tenant=tenant).order_by('-date_joined')
        
        # Pagination
        from django.core.paginator import Paginator
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        paginator = Paginator(users, page_size)
        page_obj = paginator.get_page(page)
        
        from accounts.serializers import UserProfileSerializer
        serializer = UserProfileSerializer(page_obj.object_list, many=True)
        
        return Response({
            'results': serializer.data,
            'count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page,
        })

    def add_user(self, request, pk=None):
        """Add an existing user to a tenant (super admin only)."""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can add users to tenants'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tenant = self.get_object()
        email = request.data.get('email')
        role = request.data.get('role', 'member')
        is_superuser = request.data.get('is_superuser', False)
        
        if role not in ['admin', 'member']:
            return Response(
                {'error': 'Invalid role. Must be admin or member.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user.tenant = tenant
        user.tenant_role = role
        user.is_superuser = is_superuser
        user.save()
        
        from accounts.serializers import UserProfileSerializer
        return Response(UserProfileSerializer(user).data)

    def update_user(self, request, pk=None, user_id=None):
        """Update a user's role and permissions in a tenant (super admin only)."""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can update user permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tenant = self.get_object()
        role = request.data.get('role')
        is_superuser = request.data.get('is_superuser')
        
        try:
            user = User.objects.get(id=user_id, tenant=tenant)
        except (ValueError, User.DoesNotExist):
            return Response(
                {'error': 'User not found in this tenant'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if role and role in ['admin', 'member']:
            user.tenant_role = role
        if is_superuser is not None:
            user.is_superuser = is_superuser
        user.save()
        
        from accounts.serializers import UserProfileSerializer
        return Response(UserProfileSerializer(user).data)

    def remove_user(self, request, pk=None, user_id=None):
        """Remove a user from a tenant (super admin only)."""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can remove users from tenants'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tenant = self.get_object()
        
        # 不允许从 administrator 租户移除用户
        if tenant.name == 'administrator':
            return Response(
                {'error': 'Cannot remove users from the system administrator tenant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id, tenant=tenant)
        except (ValueError, User.DoesNotExist):
            return Response(
                {'error': 'User not found in this tenant'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 不允许移除自己
        if user.id == request.user.id:
            return Response(
                {'error': 'Cannot remove yourself from a tenant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 清除用户的租户关联
        user.tenant = None
        user.tenant_role = ''
        user.is_superuser = False
        user.save()
        
        return Response({'status': 'removed'})


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
