"""
Custom Email Backend with disabled SSL certificate verification.

This backend is used for environments where SSL certificates cannot be verified,
such as development environments or corporate networks with self-signed certificates.
"""

import ssl
import logging
from django.core.mail.backends.smtp import EmailBackend

logger = logging.getLogger(__name__)


class NoVerifyEmailBackend(EmailBackend):
    """
    Email backend that does not verify SSL certificates.

    This is useful for:
    - Development environments
    - Testing with self-signed certificates
    - Corporate networks with custom CA certificates

    WARNING: Disabling certificate verification reduces security.
    Use only in trusted environments.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def open(self):
        """
        Open a connection to the mail server with disabled certificate verification.
        """
        if self.connection:
            return False

        try:
            logger.info(f"Opening SMTP connection to {self.host}:{self.port} (SSL={self.use_ssl}, TLS={self.use_tls})")

            # Create SSL context with certificate verification disabled
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            if self.use_ssl:
                logger.debug(f"Using SSL connection")
                self.connection = self.connection_class(
                    self.host, self.port, timeout=self.timeout,
                    context=ssl_context
                )
            else:
                logger.debug(f"Using plain connection")
                self.connection = self.connection_class(
                    self.host, self.port, timeout=self.timeout
                )
                if self.use_tls:
                    logger.debug(f"Starting TLS")
                    self.connection.ehlo()
                    self.connection.starttls(context=ssl_context)
                    self.connection.ehlo()

            if self.username and self.password:
                logger.debug(f"Authenticating as {self.username}")
                self.connection.login(self.username, self.password)
            else:
                logger.debug(f"Skipping authentication (no username or password provided)")
            logger.info(f"SMTP connection opened successfully")
            return True
        except Exception as e:
            logger.exception(f"Failed to open SMTP connection: {e}")
            if not self.fail_silently:
                raise
            return False