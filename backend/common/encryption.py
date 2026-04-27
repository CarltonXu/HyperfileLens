"""
Encryption utilities for sensitive data.

Uses AES-256-GCM (Galois/Counter Mode) for encryption, which is recommended
by NIST and provides both confidentiality and authenticity.

References:
- NIST SP 800-38D: Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM)
- RFC 5116: An Interface and Algorithms for Authenticated Encryption
"""

import os
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from django.conf import settings


def get_encryption_key() -> bytes:
    """
    Get or derive the encryption key from Django settings.
    
    The key is derived from SECRET_KEY using HKDF (HMAC-based Key Derivation Function)
    to ensure a consistent 256-bit key for AES-256.
    """
    # Use a fixed salt for deterministic key derivation
    # In production, consider using a separate encryption key setting
    salt = b'HyperFileLens.Repository.Encryption.v1'
    
    # Derive a 256-bit (32 bytes) key using SHA-256 based HKDF
    key = hashlib.pbkdf2_hmac(
        'sha256',
        settings.SECRET_KEY.encode('utf-8'),
        salt,
        iterations=100000,  # OWASP recommended minimum
        dklen=32  # 256 bits for AES-256
    )
    return key


def encrypt_value(plaintext: str) -> str:
    """
    Encrypt a plaintext string using AES-256-GCM.
    
    Args:
        plaintext: The string to encrypt
        
    Returns:
        Base64-encoded string containing: nonce (12 bytes) + ciphertext + tag (16 bytes)
        Format: base64(nonce || ciphertext || tag)
        
    Raises:
        ValueError: If plaintext is None or empty
    """
    if not plaintext:
        return plaintext
    
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    
    # Generate a random 96-bit (12 bytes) nonce
    # NIST recommends 96 bits for GCM for optimal security and performance
    nonce = os.urandom(12)
    
    # Encrypt the plaintext
    # AES-GCM returns ciphertext with 16-byte authentication tag appended
    ciphertext_with_tag = aesgcm.encrypt(
        nonce,
        plaintext.encode('utf-8'),
        None  # No additional authenticated data
    )
    
    # Combine nonce and ciphertext, then base64 encode
    encrypted = nonce + ciphertext_with_tag
    
    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt an encrypted string using AES-256-GCM.
    
    Args:
        encrypted_value: Base64-encoded string from encrypt_value()
        
    Returns:
        The original plaintext string
        
    Raises:
        ValueError: If encrypted_value is None or empty
        cryptography.exceptions.InvalidTag: If decryption fails (tampered data or wrong key)
    """
    if not encrypted_value:
        return encrypted_value
    
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    
    # Decode base64
    encrypted = base64.b64decode(encrypted_value.encode('utf-8'))
    
    # Extract nonce (first 12 bytes) and ciphertext with tag (remaining)
    nonce = encrypted[:12]
    ciphertext_with_tag = encrypted[12:]
    
    # Decrypt
    plaintext = aesgcm.decrypt(
        nonce,
        ciphertext_with_tag,
        None  # No additional authenticated data
    )
    
    return plaintext.decode('utf-8')


def is_encrypted(value: str) -> bool:
    """
    Check if a value appears to be encrypted (base64 encoded with correct length).
    
    This is a heuristic check to determine if a value needs decryption.
    """
    if not value:
        return False
    
    try:
        decoded = base64.b64decode(value.encode('utf-8'))
        # Encrypted values should have at least: 12 (nonce) + 16 (tag) = 28 bytes
        # Plus at least 1 byte of ciphertext
        return len(decoded) >= 28
    except Exception:
        return False


def mask_access_key(access_key: str) -> str:
    """
    Mask an access key for display, showing only first 4 and last 4 characters.
    
    Example: AKIAIOSFODNN7EXAMPLE -> AKIA****AMPLE
    """
    if not access_key or len(access_key) <= 8:
        return '****' if access_key else ''
    
    return f"{access_key[:4]}{'*' * (len(access_key) - 8)}{access_key[-4:]}"
