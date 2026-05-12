"""
Models for System Settings Application

This module provides models for storing system-wide configurations.
"""

from django.db import models
from django.utils import timezone
import uuid


class SystemSetting(models.Model):
    """
    System-wide settings stored in database.
    Allows dynamic configuration without code changes.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    key = models.CharField(
        max_length=100,
        unique=True,
        help_text='Setting key (e.g., smtp_host, smtp_port)'
    )
    value = models.TextField(
        blank=True,
        help_text='Setting value (can be string, JSON, etc.)'
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text='Description of this setting'
    )
    is_secret = models.BooleanField(
        default=False,
        help_text='Whether this setting contains sensitive data'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'system_settings'
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
        ordering = ['key']
    
    def __str__(self):
        return self.key
    
    @classmethod
    def get(cls, key: str, default=None):
        """Get a setting value by key."""
        try:
            setting = cls.objects.get(key=key)
            return setting.value
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set(cls, key: str, value: str, description: str = '', is_secret: bool = False):
        """Set a setting value."""
        setting, created = cls.objects.update_or_create(
            key=key,
            defaults={
                'value': value,
                'description': description,
                'is_secret': is_secret
            }
        )
        return setting


class SMTPConfig(models.Model):
    """
    SMTP Configuration for email sending.
    Supports multiple SMTP configurations.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=100,
        default='Default',
        help_text='Configuration name'
    )
    host = models.CharField(
        max_length=255,
        help_text='SMTP server hostname'
    )
    port = models.IntegerField(
        default=587,
        help_text='SMTP server port'
    )
    username = models.CharField(
        max_length=255,
        blank=True,
        help_text='SMTP authentication username'
    )
    password = models.CharField(
        max_length=255,
        blank=True,
        help_text='SMTP authentication password (encrypted)'
    )
    use_tls = models.BooleanField(
        default=True,
        help_text='Use TLS encryption'
    )
    use_ssl = models.BooleanField(
        default=False,
        help_text='Use SSL encryption'
    )
    from_email = models.EmailField(
        default='noreply@hyperfilelens.com',
        help_text='Default sender email address'
    )
    from_name = models.CharField(
        max_length=100,
        default='HyperFileLens',
        help_text='Default sender name'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this configuration is active'
    )
    is_default = models.BooleanField(
        default=False,
        help_text='Whether this is the default configuration'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'smtp_config'
        verbose_name = 'SMTP Configuration'
        verbose_name_plural = 'SMTP Configurations'
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.host}:{self.port})"
    
    def save(self, *args, **kwargs):
        # Ensure only one default configuration
        if self.is_default:
            SMTPConfig.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
    
    def get_connection_config(self):
        """Get connection configuration for Django email backend."""
        return {
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'use_tls': self.use_tls,
            'use_ssl': self.use_ssl,
        }
    
    def test_connection(self):
        """Test SMTP connection."""
        import smtplib
        from socket import timeout as SocketTimeout
        
        try:
            if self.use_ssl:
                smtp = smtplib.SMTP_SSL(self.host, self.port, timeout=10)
            else:
                smtp = smtplib.SMTP(self.host, self.port, timeout=10)
            
            if self.use_tls and not self.use_ssl:
                smtp.starttls()
            
            if self.username and self.password:
                smtp.login(self.username, self.password)
            
            smtp.quit()
            return True, "SMTP connection successful"
        
        except smtplib.SMTPAuthenticationError as e:
            return False, f"Authentication failed: {str(e)}"
        except smtplib.SMTPConnectError as e:
            return False, f"Connection failed: {str(e)}"
        except SocketTimeout:
            return False, "Connection timed out"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def send_test_email(self, to_email: str):
        """Send a test email."""
        from django.core.mail import EmailMessage
        
        try:
            # Use this configuration's settings
            with self.get_connection() as connection:
                email = EmailMessage(
                    subject='HyperFileLens SMTP Test',
                    body='This is a test email from HyperFileLens. If you received this, your SMTP configuration is working correctly.',
                    from_email=f'{self.from_name} <{self.from_email}>',
                    to=[to_email],
                    connection=connection,
                )
                email.send()
            return True, f"Test email sent to {to_email}"
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
    
    def get_connection(self):
        """Get Django email connection."""
        from django.core.mail import get_connection as django_get_connection

        # Use custom backend that disables SSL certificate verification
        return django_get_connection(
            backend='system_settings.email_backend.NoVerifyEmailBackend',
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            use_tls=self.use_tls,
            use_ssl=self.use_ssl,
        )


class EmailTemplate(models.Model):
    """
    Email templates for various notifications.
    """
    
    class TemplateType(models.TextChoices):
        VERIFICATION = 'verification', 'Email Verification'
        PASSWORD_RESET = 'password_reset', 'Password Reset'
        MFA_CODE = 'mfa_code', 'MFA Code'
        WELCOME = 'welcome', 'Welcome Email'
        NOTIFICATION = 'notification', 'General Notification'
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=100,
        help_text='Template name'
    )
    template_type = models.CharField(
        max_length=20,
        choices=TemplateType.choices,
        help_text='Type of email template'
    )
    subject = models.CharField(
        max_length=255,
        help_text='Email subject template'
    )
    html_body = models.TextField(
        help_text='HTML email body template'
    )
    text_body = models.TextField(
        blank=True,
        help_text='Plain text email body template'
    )
    variables = models.JSONField(
        default=list,
        help_text='List of template variables'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this template is active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_template'
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'
        ordering = ['template_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
