"""
Views for System Settings Application
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils.translation import gettext_lazy as _

from .models import SystemSetting, SMTPConfig, EmailTemplate
from .serializers import (
    SystemSettingSerializer,
    SMTPConfigSerializer,
    SMTPConfigBriefSerializer,
    SMTPTestSerializer,
    EmailTemplateSerializer,
)


class SystemSettingViewSet(viewsets.ModelViewSet):
    """
    API endpoint for system settings management.
    Only admin users can manage system settings.
    """
    
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filterset_fields = ['key', 'is_secret']
    search_fields = ['key', 'description']
    ordering_fields = ['key', 'created_at']
    
    @action(detail=False, methods=['get'])
    def by_key(self, request):
        """Get setting value by key."""
        key = request.query_params.get('key')
        if not key:
            return Response(
                {'error': 'Key parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            setting = SystemSetting.objects.get(key=key)
            serializer = self.get_serializer(setting)
            return Response(serializer.data)
        except SystemSetting.DoesNotExist:
            return Response(
                {'error': f'Setting not found: {key}'},
                status=status.HTTP_404_NOT_FOUND
            )


class SMTPConfigViewSet(viewsets.ModelViewSet):
    """
    API endpoint for SMTP configuration management.
    Only admin users can manage SMTP configurations.
    """
    
    queryset = SMTPConfig.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]
    filterset_fields = ['is_active', 'is_default']
    search_fields = ['name', 'host']
    ordering_fields = ['name', 'created_at']
    
    def get_serializer_class(self):
        """Use brief serializer for list action."""
        if self.action == 'list':
            return SMTPConfigBriefSerializer
        return SMTPConfigSerializer
    
    def perform_create(self, serializer):
        """Log SMTP configuration creation."""
        from audit_log.services import AuditService
        instance = serializer.save()
        AuditService.log_create(
            resource_type='smtp_config',
            resource_id=str(instance.id),
            resource_name=instance.name,
            request=self.request,
            details={'host': instance.host, 'port': instance.port}
        )
    
    def perform_update(self, serializer):
        """Log SMTP configuration update."""
        from audit_log.services import AuditService
        instance = serializer.save()
        AuditService.log_update(
            resource_type='smtp_config',
            resource_id=str(instance.id),
            resource_name=instance.name,
            request=self.request,
            details={'host': instance.host, 'port': instance.port}
        )
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test SMTP connection."""
        smtp_config = self.get_object()
        success, message = smtp_config.test_connection()
        
        return Response({
            'success': success,
            'message': message
        })
    
    @action(detail=True, methods=['post'])
    def send_test_email(self, request, pk=None):
        """Send test email."""
        smtp_config = self.get_object()
        serializer = SMTPTestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        to_email = serializer.validated_data['to_email']
        success, message = smtp_config.send_test_email(to_email)
        
        return Response({
            'success': success,
            'message': message
        })
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set this configuration as default."""
        smtp_config = self.get_object()
        
        # Remove default from other configs
        SMTPConfig.objects.filter(is_default=True).update(is_default=False)
        
        # Set this as default
        smtp_config.is_default = True
        smtp_config.save()
        
        return Response({
            'success': True,
            'message': f'{smtp_config.name} set as default configuration'
        })
    
    @action(detail=False, methods=['get'])
    def default(self, request):
        """Get the default SMTP configuration."""
        try:
            smtp_config = SMTPConfig.objects.get(is_default=True)
            serializer = SMTPConfigBriefSerializer(smtp_config)
            return Response(serializer.data)
        except SMTPConfig.DoesNotExist:
            return Response(
                {'error': 'No default SMTP configuration found'},
                status=status.HTTP_404_NOT_FOUND
            )


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """
    API endpoint for email template management.
    Only admin users can manage email templates.
    """
    
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filterset_fields = ['template_type', 'is_active']
    search_fields = ['name', 'subject']
    ordering_fields = ['name', 'template_type', 'created_at']
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get template by type."""
        template_type = request.query_params.get('type')
        if not template_type:
            return Response(
                {'error': 'Type parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            template = EmailTemplate.objects.get(
                template_type=template_type,
                is_active=True
            )
            serializer = self.get_serializer(template)
            return Response(serializer.data)
        except EmailTemplate.DoesNotExist:
            return Response(
                {'error': f'Template not found for type: {template_type}'},
                status=status.HTTP_404_NOT_FOUND
            )
