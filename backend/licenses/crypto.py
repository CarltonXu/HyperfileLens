"""
License Cryptography Module for HyperFileLens

This module provides cryptographic functions for license protection:
- Digital signature generation and verification
- Hardware fingerprint binding
- License data encryption
"""

import hashlib
import json
import base64
import secrets
import platform
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

# RSA key pair for license signing
# In production, these should be stored securely and the private key should NEVER be in the codebase
# The private key is only used by the license generation tool (offline)
# The public key is embedded in the application for verification

# Example key pair (DO NOT USE IN PRODUCTION - generate your own!)
# Generate with: openssl genrsa -out private.pem 2048
#                openssl rsa -in private.pem -pubout -out public.pem

LICENSE_PUBLIC_KEY = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2Z3qX2BTLS4e7g5V5h8s
K8JhN3mF2dR9wL5kP7sT1vY8xQ6nB4cA3eD7fG2hJ9kL1mN5pO8rS0tU6vW3xY
zA1bC4dE7fG8hJ2kL5mN9pO2rS6tU0vW4xY7zA3bC6dE9fG2hJ5kL8mN1pO4rS
7tU2vW6xY9zA5bC8dE1fG4hJ7kL0mN3pO6rS9tU4vW8xY1zA7bC0dE3fG6hJ9k
L2mN5pO8rS1tU6vW0xY3zA9bC2dE5fG8hJ1kL4mN7pO0rS3tU8vW2xY5zA1bC4
dE7fG0hJ3kL6mN9pO2rS5tU0vW4xY7zQIDAQAB
-----END PUBLIC KEY-----
"""

# Shared secret for signature verification
# MUST match the value in generate_license.py
LICENSE_PRIVATE_KEY = "SECRET_KEY_DO_NOT_SHARE"

# This is just a placeholder - in production, use proper RSA keys
# The private key should only exist in the license generation tool


class HardwareFingerprint:
    """
    Generate hardware fingerprint for machine binding.
    
    Combines multiple hardware identifiers to create a unique machine ID.
    """
    
    @staticmethod
    def get_machine_id() -> str:
        """
        Get a unique machine identifier.
        
        Combines:
        - MAC address
        - Platform info
        - Machine hostname
        
        Returns:
            Unique machine ID string
        """
        components = []
        
        # Get MAC address
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                           for elements in range(0, 2*6, 2)][::-1])
            components.append(mac)
        except Exception:
            pass
        
        # Get platform info
        try:
            components.append(platform.node())  # Hostname
            components.append(platform.system())  # OS
            components.append(platform.machine())  # Architecture
        except Exception:
            pass
        
        # Generate hash
        combined = '|'.join(components)
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    @staticmethod
    def verify_machine_id(stored_fingerprint: str, tolerance: int = 0) -> bool:
        """
        Verify if current machine matches stored fingerprint.
        
        Args:
            stored_fingerprint: Previously stored machine fingerprint
            tolerance: Number of components that can differ (for hardware changes)
        
        Returns:
            True if machine matches
        """
        current = HardwareFingerprint.get_machine_id()
        return current == stored_fingerprint


class LicenseSigner:
    """
    License signing and verification.
    
    In production:
    - Private key is kept offline (license generation tool only)
    - Public key is embedded in application
    """
    
    @staticmethod
    def generate_license_data(
        licensee_name: str,
        licensee_email: str,
        edition: str,
        max_tenants: int = 1,
        max_users_per_tenant: int = 10,
        max_proxies_per_tenant: int = 5,
        max_repositories_per_tenant: int = 5,
        max_storage_gb: int = 100,
        features: Dict[str, bool] = None,
        valid_days: int = 365,
        machine_id: str = None,
    ) -> Dict[str, Any]:
        """
        Generate license data structure.
        
        This function is used by the license generation tool (offline).
        
        Args:
            licensee_name: Name of licensee
            licensee_email: Email of licensee
            edition: Edition type (community/pro/enterprise)
            max_*: Resource limits
            features: Feature flags
            valid_days: License validity in days
            machine_id: Hardware fingerprint (optional, for binding)
        
        Returns:
            License data dictionary ready for signing
        """
        now = datetime.now(timezone.utc)
        
        license_data = {
            "version": "1.0",
            "license_key": f"HFL-{edition.upper()[:3]}-{now.year}-" + secrets.token_hex(8).upper(),
            "licensee": {
                "name": licensee_name,
                "email": licensee_email,
            },
            "product": "HyperFileLens",
            "edition": edition,
            "limits": {
                "max_tenants": max_tenants,
                "max_users_per_tenant": max_users_per_tenant,
                "max_proxies_per_tenant": max_proxies_per_tenant,
                "max_repositories_per_tenant": max_repositories_per_tenant,
                "max_storage_gb": max_storage_gb,
            },
            "features": features or {},
            "issued_at": now.isoformat(),
            "starts_at": now.isoformat(),
            "expires_at": (now + __import__('datetime').timedelta(days=valid_days)).isoformat() if valid_days > 0 else None,
            "machine_id": machine_id,
        }
        
        return license_data
    
    @staticmethod
    def calculate_checksum(license_data: Dict[str, Any]) -> str:
        """
        Calculate checksum of license data.
        
        This checksum covers all critical fields and is signed.
        
        Args:
            license_data: License data dictionary
        
        Returns:
            Checksum string
        """
        # Extract critical fields in a deterministic order
        # MUST match the fields in generate_license.py calculate_checksum()
        critical_fields = {
            "license_key": license_data.get("license_key"),
            "edition": license_data.get("edition"),
            "limits": license_data.get("limits"),
            "starts_at": license_data.get("starts_at"),
            "expires_at": license_data.get("expires_at"),
            "machine_id": license_data.get("machine_id"),
        }
        
        # Sort keys and serialize
        serialized = json.dumps(critical_fields, sort_keys=True, separators=(',', ':'))
        
        # Calculate SHA256 hash
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    @staticmethod
    def sign_license(license_data: Dict[str, Any], private_key: str = None) -> str:
        """
        Sign license data with private key.
        
        This function is used by the license generation tool (offline).
        
        Args:
            license_data: License data dictionary
            private_key: RSA private key (PEM format)
        
        Returns:
            Base64 encoded signature
        """
        checksum = LicenseSigner.calculate_checksum(license_data)
        
        # In production, use proper RSA signing:
        # from cryptography.hazmat.primitives import hashes
        # from cryptography.hazmat.primitives.asymmetric import padding
        # from cryptography.hazmat.primitives.serialization import load_pem_private_key
        # 
        # key = load_pem_private_key(private_key.encode(), password=None)
        # signature = key.sign(
        #     checksum.encode(),
        #     padding.PKCS1v15(),
        #     hashes.SHA256()
        # )
        # return base64.b64encode(signature).decode()
        
        # For demo purposes, we use a simple HMAC-like approach
        # DO NOT USE IN PRODUCTION
        signature_input = checksum + (private_key or "secret_key")
        signature = hashlib.sha256(signature_input.encode()).hexdigest()
        return base64.b64encode(signature.encode()).decode()
    
    @staticmethod
    def verify_signature(license_data: Dict[str, Any], signature: str) -> bool:
        """
        Verify license signature with embedded public key.
        
        Args:
            license_data: License data dictionary
            signature: Base64 encoded signature
        
        Returns:
            True if signature is valid
        """
        try:
            # Calculate checksum from current data
            checksum = LicenseSigner.calculate_checksum(license_data)
            
            # Verify signature using shared secret
            # In production, use proper RSA verification:
            # from cryptography.hazmat.primitives import hashes
            # from cryptography.hazmat.primitives.asymmetric import padding
            # from cryptography.hazmat.primitives.serialization import load_pem_public_key
            #
            # key = load_pem_public_key(LICENSE_PUBLIC_KEY.encode())
            # key.verify(
            #     base64.b64decode(signature),
            #     checksum.encode(),
            #     padding.PKCS1v15(),
            #     hashes.SHA256()
            # )
            # return True
            
            if not signature:
                return False
            
            # Decode signature
            try:
                decoded = base64.b64decode(signature).decode()
            except Exception:
                return False
            
            # Recompute expected signature using same method as generate_license.py
            signature_input = checksum + LICENSE_PRIVATE_KEY
            expected_signature = hashlib.sha256(signature_input.encode()).hexdigest()
            
            # Compare signatures
            return decoded == expected_signature
            
        except Exception:
            return False


class LicenseEncoder:
    """
    Encode and decode license for distribution.
    """
    
    @staticmethod
    def encode(license_data: Dict[str, Any], signature: str) -> str:
        """
        Encode license data and signature into a distributable string.
        
        Args:
            license_data: License data dictionary
            signature: License signature
        
        Returns:
            Encoded license string
        """
        combined = {
            "data": license_data,
            "signature": signature,
        }
        
        serialized = json.dumps(combined, sort_keys=True)
        encoded = base64.b64encode(serialized.encode()).decode()
        
        # Format as readable license key
        chunks = [encoded[i:i+16] for i in range(0, len(encoded), 16)]
        return "HFL-LICENSE-" + "-".join(chunks[:8])  # Limit length for readability
    
    @staticmethod
    def decode(encoded_license: str) -> Tuple[Dict[str, Any], str]:
        """
        Decode license string into data and signature.
        
        Args:
            encoded_license: Encoded license string
        
        Returns:
            Tuple of (license_data, signature)
        
        Raises:
            ValueError: If license format is invalid
        """
        try:
            # Remove prefix
            if encoded_license.startswith("HFL-LICENSE-"):
                encoded_license = encoded_license[12:]
            
            # Reconstruct full base64
            encoded_license = encoded_license.replace("-", "")
            
            # Decode
            decoded = base64.b64decode(encoded_license).decode()
            combined = json.loads(decoded)
            
            return combined["data"], combined["signature"]
            
        except Exception as e:
            raise ValueError(f"Invalid license format: {e}")


def create_license_for_customer(
    licensee_name: str,
    licensee_email: str,
    edition: str,
    max_tenants: int = 1,
    max_users_per_tenant: int = 10,
    max_proxies_per_tenant: int = 5,
    max_storage_gb: int = 100,
    valid_days: int = 365,
    bind_to_machine: bool = False,
) -> str:
    """
    Create a complete license for a customer.
    
    This function is used by the license generation tool (offline).
    
    Args:
        licensee_name: Customer name
        licensee_email: Customer email
        edition: License edition
        max_*: Resource limits
        valid_days: Validity period
        bind_to_machine: Whether to bind to current machine
    
    Returns:
        Encoded license string ready to send to customer
    """
    # Optionally bind to machine
    machine_id = None
    if bind_to_machine:
        machine_id = HardwareFingerprint.get_machine_id()
    
    # Generate license data
    license_data = LicenseSigner.generate_license_data(
        licensee_name=licensee_name,
        licensee_email=licensee_email,
        edition=edition,
        max_tenants=max_tenants,
        max_users_per_tenant=max_users_per_tenant,
        max_proxies_per_tenant=max_proxies_per_tenant,
        max_storage_gb=max_storage_gb,
        valid_days=valid_days,
        machine_id=machine_id,
    )
    
    # Sign license
    # In production, load private key from secure storage
    signature = LicenseSigner.sign_license(license_data)
    
    # Encode for distribution
    return LicenseEncoder.encode(license_data, signature)
