"""
Services for Accounts Application

This module provides business logic for:
- Captcha generation and validation
- Email services (password reset, MFA)
- MFA (Multi-Factor Authentication)
"""

import random
import string
import io
import uuid
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from django.core.mail import EmailMessage

# Try to import PIL for captcha image generation
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class CaptchaService:
    """
    Service for generating and validating captcha codes.
    """
    
    CAPTCHA_LENGTH = 5
    CAPTCHA_EXPIRE_SECONDS = 300  # 5 minutes
    CAPTCHA_PREFIX = 'captcha:'
    
    @classmethod
    def generate(cls) -> tuple[str, bytes]:
        """
        Generate a new captcha code and image.
        
        Returns:
            tuple: (captcha_key, image_bytes)
        """
        # Generate random captcha code
        chars = string.ascii_uppercase + string.digits
        chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '')  # Remove confusing chars
        captcha_code = ''.join(random.choices(chars, k=cls.CAPTCHA_LENGTH))
        
        # Generate unique key
        captcha_key = str(uuid.uuid4())
        
        # Store in cache
        cache_key = f"{cls.CAPTCHA_PREFIX}{captcha_key}"
        cache.set(cache_key, captcha_code.upper(), cls.CAPTCHA_EXPIRE_SECONDS)
        
        # Generate image
        image_bytes = cls._generate_image(captcha_code)
        
        return captcha_key, image_bytes
    
    @classmethod
    def validate(cls, captcha_key: str, captcha_code: str) -> bool:
        """
        Validate a captcha code.
        
        Args:
            captcha_key: The captcha key
            captcha_code: The user-entered code
            
        Returns:
            bool: True if valid, False otherwise
        """
        cache_key = f"{cls.CAPTCHA_PREFIX}{captcha_key}"
        stored_code = cache.get(cache_key)
        
        if stored_code is None:
            return False
        
        # Delete after validation (one-time use)
        cache.delete(cache_key)
        
        return stored_code.upper() == captcha_code.upper()
    
    @classmethod
    def _generate_image(cls, code: str) -> bytes:
        """
        Generate a captcha image.
        
        Args:
            code: The captcha code to render
            
        Returns:
            bytes: PNG image bytes
        """
        if not PIL_AVAILABLE:
            # Return a simple placeholder if PIL is not available
            return b''
        
        # Render at a readable native size. The frontend displays this at
        # roughly the same aspect ratio, so remote browsers do not upscale a
        # tiny raster image into blurry text.
        width, height = 140, 46

        # Create image
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)

        # Try to use a real bold font. PIL's default bitmap font is too small
        # for captcha use, especially in production slim containers.
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
        except (OSError, IOError):
            try:
                # Try macOS system font
                font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 26)
            except (OSError, IOError):
                try:
                    # Try Windows system font
                    font = ImageFont.truetype('arial.ttf', 26)
                except (OSError, IOError):
                    # Last resort: use default font (note: will be small)
                    font = ImageFont.load_default()
        
        # Draw background noise (dots) - reduced for better readability
        for _ in range(90):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            draw.point((x, y), fill=(random.randint(205, 245), random.randint(205, 245), random.randint(205, 245)))
        
        # Draw interference lines
        for _ in range(5):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            draw.line((x1, y1, x2, y2), fill=(random.randint(135, 200), random.randint(135, 200), random.randint(135, 200)), width=1)
        
        # Draw text with darker color for better readability
        text_color = (random.randint(0, 45), random.randint(0, 45), random.randint(0, 45))
        text_x = 20
        try:
            bbox = font.getbbox('A')
            glyph_height = bbox[3] - bbox[1]
            text_y = max(0, int((height - glyph_height) / 2) - 2)
        except AttributeError:
            text_y = 9

        for i, char in enumerate(code):
            # Add some rotation to each character
            char_image = Image.new('RGBA', (28, 34), (255, 255, 255, 0))
            char_draw = ImageDraw.Draw(char_image)
            char_draw.text((2, 0), char, font=font, fill=text_color)

            # Rotate
            angle = random.randint(-10, 10)
            char_image = char_image.rotate(angle, expand=False)
            char_image = char_image.filter(ImageFilter.GaussianBlur(radius=0.35))

            # Paste onto main image
            image.paste(char_image, (text_x + i * 21, text_y), char_image)

        # Convert to bytes
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()


class EmailService:
    """
    Service for sending emails.
    """
    
    @classmethod
    def send_verification_code(cls, email: str, code: str, purpose: str = 'verification') -> bool:
        """
        Send a verification code email.
        
        Args:
            email: Recipient email
            code: Verification code
            purpose: Purpose of the code (password_reset, mfa, etc.)
            
        Returns:
            bool: True if sent successfully
        """
        try:
            subject_map = {
                'password_reset': 'Password Reset Code',
                'mfa': 'MFA Verification Code',
                'verification': 'Verification Code'
            }
            
            subject = f"HyperFileLens - {subject_map.get(purpose, 'Verification Code')}"
            
            context = {
                'code': code,
                'purpose': purpose,
                'expire_minutes': 5
            }
            
            html_message = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">HyperFileLens</h1>
                </div>
                <div style="padding: 30px; background: #f9f9f9;">
                    <h2 style="color: #333;">Verification Code</h2>
                    <p style="color: #666;">Your verification code is:</p>
                    <div style="background: white; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                        <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #667eea;">{code}</span>
                    </div>
                    <p style="color: #999; font-size: 12px;">This code will expire in {context['expire_minutes']} minutes.</p>
                    <p style="color: #999; font-size: 12px;">If you did not request this code, please ignore this email.</p>
                </div>
            </div>
            """
            
            plain_message = f"Your verification code is: {code}. It will expire in 5 minutes."
            
            from system_settings.models import SMTPConfig

            smtp_config = (
                SMTPConfig.objects.filter(is_active=True, is_default=True).first()
                or SMTPConfig.objects.filter(is_active=True).first()
            )
            if not smtp_config:
                print("Failed to send email: no active SMTP configuration")
                return False

            with smtp_config.get_connection() as connection:
                message = EmailMessage(
                    subject=subject,
                    body=html_message or plain_message,
                    from_email=f'{smtp_config.from_name} <{smtp_config.from_email}>',
                    to=[email],
                    connection=connection,
                )
                message.content_subtype = 'html'
                message.send(fail_silently=False)
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False


class MFAService:
    """
    Service for MFA (Multi-Factor Authentication).
    """
    
    MFA_CODE_EXPIRE_SECONDS = 300  # 5 minutes
    MFA_CODE_PREFIX = 'mfa_code:'
    MFA_SECRET_PREFIX = 'mfa_secret:'
    
    @classmethod
    def generate_secret(cls) -> str:
        """
        Generate a new MFA secret.
        
        Returns:
            str: Base32 encoded secret
        """
        import base64
        import os
        return base64.b32encode(os.urandom(10)).decode('utf-8')
    
    @classmethod
    def store_secret(cls, user_id: str, secret: str) -> None:
        """
        Store MFA secret temporarily (until verified).
        
        Args:
            user_id: User ID
            secret: MFA secret
        """
        cache_key = f"{cls.MFA_SECRET_PREFIX}{user_id}"
        cache.set(cache_key, secret, 600)  # 10 minutes to verify
    
    @classmethod
    def get_secret(cls, user_id: str) -> str | None:
        """
        Get pending MFA secret.
        
        Args:
            user_id: User ID
            
        Returns:
            str | None: MFA secret or None
        """
        cache_key = f"{cls.MFA_SECRET_PREFIX}{user_id}"
        return cache.get(cache_key)
    
    @classmethod
    def clear_secret(cls, user_id: str) -> None:
        """
        Clear pending MFA secret.
        """
        cache_key = f"{cls.MFA_SECRET_PREFIX}{user_id}"
        cache.delete(cache_key)
    
    @classmethod
    def generate_code(cls, email: str) -> str:
        """
        Generate and store an MFA code.
        
        Args:
            email: User email
            
        Returns:
            str: 6-digit code
        """
        code = ''.join(random.choices(string.digits, k=6))
        cache_key = f"{cls.MFA_CODE_PREFIX}{email}"
        cache.set(cache_key, code, cls.MFA_CODE_EXPIRE_SECONDS)
        return code
    
    @classmethod
    def verify_code(cls, email: str, code: str) -> bool:
        """
        Verify an MFA code.
        
        Args:
            email: User email
            code: User-entered code
            
        Returns:
            bool: True if valid
        """
        cache_key = f"{cls.MFA_CODE_PREFIX}{email}"
        stored_code = cache.get(cache_key)
        
        if stored_code is None:
            return False
        
        # Delete after verification
        cache.delete(cache_key)
        
        return stored_code == code
    
    @classmethod
    def generate_totp_uri(cls, email: str, secret: str) -> str:
        """
        Generate a TOTP URI for QR code.
        
        Args:
            email: User email
            secret: MFA secret
            
        Returns:
            str: otpauth:// URI
        """
        import urllib.parse
        issuer = "HyperFileLens"
        label = f"{issuer}:{email}"
        return f"otpauth://totp/{urllib.parse.quote(label)}?secret={secret}&issuer={urllib.parse.quote(issuer)}&algorithm=SHA1&digits=6&period=30"


class PasswordResetService:
    """
    Service for password reset functionality.
    """
    
    RESET_TOKEN_PREFIX = 'password_reset:'
    RESET_TOKEN_EXPIRE_SECONDS = 1800  # 30 minutes
    VERIFICATION_CODE_EXPIRE_SECONDS = 300  # 5 minutes
    VERIFICATION_CODE_PREFIX = 'pw_reset_code:'
    
    @classmethod
    def generate_reset_token(cls, email: str) -> str:
        """
        Generate a password reset token.
        
        Args:
            email: User email
            
        Returns:
            str: Reset token
        """
        token = str(uuid.uuid4())
        cache_key = f"{cls.RESET_TOKEN_PREFIX}{token}"
        cache.set(cache_key, email, cls.RESET_TOKEN_EXPIRE_SECONDS)
        return token
    
    @classmethod
    def validate_reset_token(cls, token: str) -> str | None:
        """
        Validate a password reset token.
        
        Args:
            token: Reset token
            
        Returns:
            str | None: Email if valid, None otherwise
        """
        cache_key = f"{cls.RESET_TOKEN_PREFIX}{token}"
        return cache.get(cache_key)
    
    @classmethod
    def invalidate_reset_token(cls, token: str) -> None:
        """
        Invalidate a password reset token.
        """
        cache_key = f"{cls.RESET_TOKEN_PREFIX}{token}"
        cache.delete(cache_key)
    
    @classmethod
    def generate_verification_code(cls, email: str) -> str:
        """
        Generate a verification code for password reset.
        
        Args:
            email: User email
            
        Returns:
            str: 6-digit code
        """
        code = ''.join(random.choices(string.digits, k=6))
        cache_key = f"{cls.VERIFICATION_CODE_PREFIX}{email}"
        cache.set(cache_key, code, cls.VERIFICATION_CODE_EXPIRE_SECONDS)
        return code
    
    @classmethod
    def verify_code(cls, email: str, code: str) -> bool:
        """
        Verify a password reset code.
        
        Args:
            email: User email
            code: User-entered code
            
        Returns:
            bool: True if valid
        """
        cache_key = f"{cls.VERIFICATION_CODE_PREFIX}{email}"
        stored_code = cache.get(cache_key)
        
        if stored_code is None:
            return False
        
        # Don't delete immediately - allow multiple attempts
        return stored_code == code
    
    @classmethod
    def invalidate_code(cls, email: str) -> None:
        """
        Invalidate a verification code.
        """
        cache_key = f"{cls.VERIFICATION_CODE_PREFIX}{email}"
        cache.delete(cache_key)
