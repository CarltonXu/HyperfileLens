"""
Views for Tenants API
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count, Q
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import EmailMessage

from .models import Tenant, TenantInvitation
from .serializers import (
    TenantSerializer,
    TenantListSerializer,
    TenantDetailSerializer,
    TenantInvitationSerializer,
    AcceptInvitationSerializer,
    TenantQuotaSerializer
)
from accounts.models import APIToken, User
from accounts.serializers import UserProfileSerializer
from audit_log.services import AuditService
from licenses.quota import enforce_license_quota, enforce_platform_tenant_quota


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
        """Create a new tenant.
        
        Note: New tenant is created without any users assigned.
        Users need to be explicitly added via user management.
        """
        enforce_platform_tenant_quota()
        tenant = serializer.save()
        # Record audit log
        AuditService.log_tenant_create(self.request, tenant)

    def destroy(self, request, *args, **kwargs):
        """Delete a tenant. Prevent deleting own tenant or administrator tenant."""
        tenant = self.get_object()
        user = request.user
        tenant_name = tenant.name
        tenant_id = tenant.id
        
        # 不允许删除 administrator 租户（系统保留租户）
        if tenant.name == 'administrator':
            error_msg = 'Cannot delete the system administrator tenant.'
            AuditService.log_tenant_delete(
                request, tenant, 
                result='failure', 
                error_message=error_msg
            )
            return Response(
                {'detail': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 不允许删除自己关联的租户
        if user.tenant and user.tenant.id == tenant.id:
            error_msg = 'Cannot delete your own tenant.'
            AuditService.log_tenant_delete(
                request, tenant, 
                result='failure', 
                error_message=error_msg
            )
            return Response(
                {'detail': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否有用户关联到此租户
        users_in_tenant = User.objects.filter(tenant=tenant).count()
        if users_in_tenant > 0:
            error_msg = f'Cannot delete tenant with {users_in_tenant} associated user(s). Remove users first.'
            AuditService.log_tenant_delete(
                request, tenant, 
                result='failure', 
                error_message=error_msg
            )
            return Response(
                {'detail': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 检查是否有其他资源关联到此租户
        from nodes.models import ProxyNode
        from repository.models import Repository
        from source_resources.models import SourceResource
        from backup_tasks.models import BackupTask
        
        resource_counts = {}
        proxy_count = ProxyNode.objects.filter(tenant=tenant).count()
        if proxy_count > 0:
            resource_counts['proxies'] = proxy_count
        
        repository_count = Repository.objects.filter(tenant=tenant).count()
        if repository_count > 0:
            resource_counts['repositories'] = repository_count
        
        source_count = SourceResource.objects.filter(tenant=tenant).count()
        if source_count > 0:
            resource_counts['source_resources'] = source_count
        
        backup_count = BackupTask.objects.filter(tenant=tenant).count()
        if backup_count > 0:
            resource_counts['backup_tasks'] = backup_count
        
        if resource_counts:
            resource_details = ', '.join([f"{v} {k}" for k, v in resource_counts.items()])
            error_msg = f'Cannot delete tenant with associated resources: {resource_details}. Remove resources first.'
            AuditService.log_tenant_delete(
                request, tenant, 
                result='failure', 
                error_message=error_msg
            )
            return Response(
                {'detail': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 记录成功的审计日志
        AuditService.log_tenant_delete(request, tenant, result='success')
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
        AuditService.log_tenant_activate(request, tenant)
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
        AuditService.log_tenant_deactivate(request, tenant)
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

    def user_candidates(self, request, pk=None):
        """List users that can be added to this tenant."""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can search tenant user candidates'},
                status=status.HTTP_403_FORBIDDEN
            )

        self.get_object()
        search = (request.query_params.get('search') or '').strip()
        users = User.objects.filter(
            tenant__isnull=True,
            is_superuser=False,
            is_active=True,
        )

        if search:
            users = users.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(username__icontains=search)
            )

        users = users.order_by('email')[:10]

        from accounts.serializers import UserProfileSerializer
        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data)

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

        if user.id == request.user.id:
            return Response(
                {'error': 'Cannot add yourself to a tenant'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_superuser:
            return Response(
                {'error': 'Platform admins cannot be managed from tenant users'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.tenant_id == tenant.id:
            return Response(
                {'error': 'User is already in this tenant'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.tenant_id:
            return Response(
                {'error': 'User already belongs to another tenant'},
                status=status.HTTP_400_BAD_REQUEST
            )

        enforce_license_quota(tenant, 'users')

        user.tenant = tenant
        user.tenant_role = role
        user.is_superuser = False
        user.save()
        
        AuditService.log_tenant_add_user(request, tenant, user)
        
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
        
        try:
            user = User.objects.get(id=user_id, tenant=tenant)
        except (ValueError, User.DoesNotExist):
            return Response(
                {'error': 'User not found in this tenant'},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.id == request.user.id:
            return Response(
                {'error': 'Cannot change your own tenant role'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_superuser:
            return Response(
                {'error': 'Platform admins cannot be managed from tenant users'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if role and role in ['admin', 'member']:
            user.tenant_role = role
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
        
        # 检查用户是否有关联的资源
        from nodes.models import ProxyNode
        from repository.models import Repository
        from source_resources.models import SourceResource
        from policies.models import BackupPolicy
        from backup_tasks.models import BackupTask
        from recovery_tasks.models import RecoveryTask
        from gateways.models import Gateway

        resource_counts = {}
        
        proxy_count = ProxyNode.objects.filter(
            Q(owner=user) | Q(installed_by=user),
            tenant=tenant,
        ).count()
        if proxy_count > 0:
            resource_counts['proxies'] = proxy_count
            
        repo_count = Repository.objects.filter(user=user, tenant=tenant).count()
        if repo_count > 0:
            resource_counts['repositories'] = repo_count
            
        source_count = SourceResource.objects.filter(user=user, tenant=tenant).count()
        if source_count > 0:
            resource_counts['source_resources'] = source_count
            
        policy_count = BackupPolicy.objects.filter(user=user, tenant=tenant).count()
        if policy_count > 0:
            resource_counts['policies'] = policy_count
            
        backup_count = BackupTask.objects.filter(user=user, tenant=tenant).count()
        if backup_count > 0:
            resource_counts['backup_tasks'] = backup_count
            
        recovery_count = RecoveryTask.objects.filter(user=user, tenant=tenant).count()
        if recovery_count > 0:
            resource_counts['recovery_tasks'] = recovery_count
            
        gateway_count = Gateway.objects.filter(
            Q(owner=user) | Q(installed_by=user),
            tenant=tenant,
        ).count()
        if gateway_count > 0:
            resource_counts['gateways'] = gateway_count

        if resource_counts:
            resource_details = ', '.join([f"{v} {k}" for k, v in resource_counts.items()])
            error_msg = f'Cannot remove user with associated resources: {resource_details}. Transfer or delete resources first.'
            return Response(
                {
                    'error': 'Cannot remove user with associated resources',
                    'detail': f'User has created resources that belong to this tenant. Transfer ownership or delete resources before removing the user.',
                    'resources': resource_counts
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 清除用户的租户关联
        user.tenant = None
        user.tenant_role = ''
        user.is_superuser = False
        user.save()
        
        AuditService.log_tenant_remove_user(request, tenant, user)
        
        return Response({'status': 'removed'})


class TenantInvitationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for tenant invitations.
    """

    serializer_class = TenantInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['validate', 'accept']:
            return [permissions.AllowAny()]
        return super().get_permissions()

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
        tenant = self._resolve_invitation_tenant(user)
        email = serializer.validated_data['email'].strip().lower()

        if User.objects.filter(email=email, tenant=tenant).exists():
            raise ValidationError({'error': "User already belongs to this tenant"})
        if TenantInvitation.objects.filter(
            tenant=tenant,
            email=email,
            status=TenantInvitation.InvitationStatus.PENDING,
            expires_at__gt=timezone.now()
        ).exists():
            raise ValidationError({'error': "A pending invitation already exists for this email"})

        enforce_license_quota(tenant, 'users')
        with transaction.atomic():
            invitation = serializer.save(
                tenant=tenant,
                email=email,
                invited_by=user,
                expires_at=timezone.now() + timezone.timedelta(days=7)
            )
            self._send_invitation_email(self.request, invitation)

    def _resolve_invitation_tenant(self, user):
        tenant_id = self.request.data.get('tenant') or self.request.data.get('tenant_id')
        if user.is_superuser:
            if not tenant_id:
                raise ValidationError({'error': "Tenant is required for platform admin invitations"})
            return get_object_or_404(Tenant, pk=tenant_id)
        if not user.tenant:
            raise ValidationError({'error': "User must belong to a tenant to send invitations"})
        return user.tenant

    def _invitation_link(self, request, invitation):
        base_url = (
            getattr(settings, 'FRONTEND_BASE_URL', '')
            or request.headers.get('Origin')
            or request.build_absolute_uri('/').rstrip('/')
        )
        return f"{base_url.rstrip('/')}/accept-invitation?token={invitation.token}"

    def _send_invitation_email(self, request, invitation):
        from system_settings.models import SMTPConfig

        smtp_config = (
            SMTPConfig.objects.filter(is_active=True, is_default=True).first()
            or SMTPConfig.objects.filter(is_active=True).first()
        )
        if not smtp_config:
            raise ValidationError({'error': "No active SMTP configuration found"})

        invitation_link = self._invitation_link(request, invitation)
        subject = f"HyperFileLens invitation to {invitation.tenant.name}"
        body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 640px; margin: 0 auto;">
          <div style="padding: 20px 24px; background: #111827; color: #fff;">
            <h1 style="margin: 0; font-size: 20px;">HyperFileLens</h1>
          </div>
          <div style="padding: 24px; background: #f9fafb; color: #111827;">
            <h2 style="margin-top: 0;">You have been invited</h2>
            <p>You have been invited to join tenant <strong>{invitation.tenant.name}</strong> as <strong>{invitation.role}</strong>.</p>
            <p>This invitation expires on {invitation.expires_at.strftime('%Y-%m-%d %H:%M:%S %Z')}.</p>
            <p style="margin: 24px 0;">
              <a href="{invitation_link}" style="display: inline-block; padding: 10px 16px; background: #4f46e5; color: #fff; text-decoration: none; border-radius: 6px;">Accept invitation</a>
            </p>
            <p style="font-size: 12px; color: #6b7280;">If the button does not work, open this link: {invitation_link}</p>
            <p style="margin-top: 18px; font-size: 11px; color: #9ca3af;">This is a system email, please do not reply</p>
          </div>
        </div>
        """
        try:
            with smtp_config.get_connection() as connection:
                message = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=f'{smtp_config.from_name} <{smtp_config.from_email}>',
                    to=[invitation.email],
                    connection=connection,
                )
                message.content_subtype = 'html'
                message.send(fail_silently=False)
        except Exception as exc:
            raise ValidationError({'error': f"Failed to send invitation email: {exc}"})

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def validate(self, request):
        """Validate an invitation token and return public invitation info."""
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'Invitation token is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            invitation = TenantInvitation.objects.select_related('tenant').get(token=token)
        except TenantInvitation.DoesNotExist:
            return Response({'error': 'Invalid invitation token'}, status=status.HTTP_400_BAD_REQUEST)
        if not invitation.is_valid():
            return Response({'error': 'Invitation has expired or already been used'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=invitation.email).first()
        return Response({
            'email': invitation.email,
            'tenant': invitation.tenant.name,
            'role': invitation.role,
            'expires_at': invitation.expires_at,
            'user_exists': bool(user),
        })

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
            password = serializer.validated_data.get('password')
            if not password or not user.check_password(password):
                return Response(
                    {'error': 'A valid password is required for this existing account'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            # Create new user
            password = serializer.validated_data.get('password')
            if not password:
                return Response(
                    {'error': 'Password is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                validate_password(password)
            except DjangoValidationError as exc:
                return Response({'error': ' '.join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
            first_name = serializer.validated_data.get('first_name', '')
            last_name = serializer.validated_data.get('last_name', '')
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

        if user.is_superuser:
            return Response(
                {'error': 'Platform admin users cannot accept tenant invitations'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not user.is_active:
            return Response(
                {'error': 'User account is disabled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if user.tenant and user.tenant_id != invitation.tenant_id:
            return Response(
                {'error': 'User already belongs to another tenant'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Assign tenant and role
        enforce_license_quota(invitation.tenant, 'users')
        user.tenant = invitation.tenant
        user.tenant_role = invitation.role
        user.save()

        # Mark invitation as accepted
        invitation.status = TenantInvitation.InvitationStatus.ACCEPTED
        invitation.accepted_at = timezone.now()
        invitation.save()

        import secrets
        token_key = secrets.token_urlsafe(32)
        api_token = APIToken.objects.create(
            user=user,
            name='Invitation API Token',
            key=token_key,
            prefix=token_key[:8]
        )
        User.objects.filter(pk=user.pk).update(last_login_at=timezone.now())
        login(request, user)

        response_data = UserProfileSerializer(user).data
        response_data['token'] = api_token.key
        response_data.update({
            'status': 'accepted',
            'tenant': invitation.tenant.name,
            'role': invitation.role
        })
        return Response(response_data)

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

        self._send_invitation_email(request, invitation)

        return Response({'status': 'resent'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an invitation."""
        invitation = self.get_object()
        invitation.status = TenantInvitation.InvitationStatus.DECLINED
        invitation.save()
        return Response({'status': 'cancelled'})
