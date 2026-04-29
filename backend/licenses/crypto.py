"""
License Cryptography Module for HyperFileLens

Simplified license activation with machine binding.
Machine Code = MAC + CPU ID + Tenant ID + User ID
"""

import hashlib
import json
import base64
import secrets
import subprocess
import platform
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple


# RSA key pair for license signing
# In production, these should be stored securely and the private key should NEVER be in the codebase

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
# MUST match the value in license_generator.py
LICENSE_SECRET_KEY = "HFL_LICENSE_SECRET_2024_DO_NOT_SHARE"


class MachineCodeGenerator:
    """
    Generate unique machine codes for license binding.
    
    Machine Code = SHA256(MAC + CPU ID + Hostname + Tenant ID + User ID)
    """
    
    @staticmethod
    def get_mac_address() -> str:
        """Get primary MAC address."""
        try:
            # Get MAC address using uuid.getnode()
            mac = uuid.getnode()
            # Format as XX:XX:XX:XX:XX:XX
            return ':'.join(['{:02X}'.format((mac >> elements) & 0xFF) 
                           for elements in range(0, 2*6, 2)][::-1])
        except Exception:
            return "UNKNOWN_MAC"
    
    @staticmethod
    def get_cpu_id() -> str:
        """Get CPU ID/Serial number."""
        try:
            system = platform.system()
            
            if system == "Linux":
                # Try to get CPU info from /proc/cpuinfo
                try:
                    with open('/proc/cpuinfo', 'r') as f:
                        for line in f:
                            if 'Serial' in line or 'UUID' in line:
                                return line.split(':')[1].strip()
                        # Fallback to model name
                        f.seek(0)
                        for line in f:
                            if 'model name' in line.lower():
                                return line.split(':')[1].strip()[:50]
                except Exception:
                    pass
                
                # Try dmidecode (requires root)
                try:
                    result = subprocess.run(
                        ['dmidecode', '-s', 'processor-id'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout.strip()[:50]
                except Exception:
                    pass
                    
            elif system == "Windows":
                try:
                    result = subprocess.run(
                        ['wmic', 'cpu', 'get', 'ProcessorId'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            return lines[1].strip()[:50]
                except Exception:
                    pass
                    
            elif system == "Darwin":  # macOS
                try:
                    result = subprocess.run(
                        ['sysctl', '-n', 'machdep.cpu.brand_string'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        return result.stdout.strip()[:50]
                except Exception:
                    pass
            
            return "UNKNOWN_CPU"
            
        except Exception:
            return "UNKNOWN_CPU"
    
    @staticmethod
    def get_hostname() -> str:
        """Get machine hostname."""
        try:
            return platform.node()[:50]
        except Exception:
            return "UNKNOWN_HOST"
    
    @staticmethod
    def generate(tenant_id: str, user_id: str) -> Tuple[str, Dict[str, str]]:
        """
        Generate a unique machine code.
        
        Args:
            tenant_id: Tenant UUID
            user_id: User UUID
            
        Returns:
            (machine_code, components_dict)
        """
        components = {
            'mac': MachineCodeGenerator.get_mac_address(),
            'cpu_id': MachineCodeGenerator.get_cpu_id(),
            'hostname': MachineCodeGenerator.get_hostname(),
            'tenant_id': str(tenant_id),
            'user_id': str(user_id),
        }
        
        # Create combined string
        combined = "|".join([
            components['mac'],
            components['cpu_id'],
            components['hostname'],
            components['tenant_id'],
            components['user_id'],
        ])
        
        # Generate SHA256 hash
        hash_value = hashlib.sha256(combined.encode()).hexdigest()[:32]
        
        # Format as HFL-MCH-XXXX-XXXX-XXXX-XXXX
        chunks = [hash_value[i:i+4].upper() for i in range(0, 16, 4)]
        machine_code = "HFL-MCH-" + "-".join(chunks)
        
        return machine_code, components
    
    @staticmethod
    def verify(stored_code: str, tenant_id: str, user_id: str) -> bool:
        """
        Verify if current machine matches stored machine code.
        
        Args:
            stored_code: Previously stored machine code
            tenant_id: Current tenant ID
            user_id: Current user ID
            
        Returns:
            True if machine code matches
        """
        current_code, _ = MachineCodeGenerator.generate(tenant_id, user_id)
        return current_code == stored_code


class ActivationCode:
    """
    Activation code generation and verification.
    
    Activation Code Structure:
    HFL-ACT-{base64_encoded_json}
    
    JSON contains:
    - license_key: Unique license identifier
    - machine_code: Bound machine code
    - limits: Quantity limits
    - expires_at: Expiration date
    - signature: Digital signature
    """
    
    @staticmethod
    def generate(
        machine_code: str,
        limits: Dict[str, int],
        valid_days: int = 365,
        license_key: str = None,
    ) -> str:
        """
        Generate an activation code (used by license generator tool).
        
        This is used OFFLINE by the sales team.
        
        Args:
            machine_code: Target machine code
            limits: Quantity limits dict
            valid_days: Validity period (0 = perpetual)
            license_key: Optional license key (auto-generated if not provided)
            
        Returns:
            Activation code string
        """
        now = datetime.now(timezone.utc)
        
        # Generate license key if not provided
        if not license_key:
            year = now.year
            random_part = secrets.token_hex(8).upper()
            license_key = f"HFL-PRO-{year}-{random_part}"
        
        # Calculate expiration
        expires_at = None
        if valid_days > 0:
            expires_at = (now + timedelta(days=valid_days)).isoformat()
        
        # Build activation data
        activation_data = {
            "license_key": license_key,
            "machine_code": machine_code,
            "limits": limits,
            "issued_at": now.isoformat(),
            "expires_at": expires_at,
        }
        
        # Calculate signature
        signature = ActivationCode._sign(activation_data)
        activation_data["signature"] = signature
        
        # Encode
        json_str = json.dumps(activation_data, sort_keys=True, separators=(',', ':'))
        encoded = base64.b64encode(json_str.encode()).decode()
        
        # Format as HFL-ACT-XXXX
        return f"HFL-ACT-{encoded}"
    
    @staticmethod
    def decode(activation_code: str) -> Dict[str, Any]:
        """
        Decode and validate an activation code.
        
        Args:
            activation_code: Activation code string
            
        Returns:
            Decoded activation data
            
        Raises:
            ValueError: If code is invalid
        """
        try:
            # Remove prefix
            if activation_code.startswith("HFL-ACT-"):
                encoded = activation_code[8:]
            else:
                raise ValueError("Invalid activation code format")
            
            # Decode base64
            json_str = base64.b64decode(encoded).decode()
            activation_data = json.loads(json_str)
            
            # Verify required fields
            required = ['license_key', 'machine_code', 'limits', 'signature']
            for field in required:
                if field not in activation_data:
                    raise ValueError(f"Missing required field: {field}")
            
            return activation_data
            
        except Exception as e:
            raise ValueError(f"Invalid activation code: {str(e)}")
    
    @staticmethod
    def verify(activation_data: Dict[str, Any]) -> bool:
        """
        Verify activation code signature.
        
        Args:
            activation_data: Decoded activation data
            
        Returns:
            True if signature is valid
        """
        try:
            stored_signature = activation_data.get("signature")
            if not stored_signature:
                return False
            
            # Recompute signature
            expected_signature = ActivationCode._sign(activation_data)
            
            return stored_signature == expected_signature
            
        except Exception:
            return False
    
    @staticmethod
    def _sign(data: Dict[str, Any]) -> str:
        """
        Sign activation data.
        
        In production, this should use proper RSA signing with private key.
        For now, we use HMAC-SHA256 with shared secret.
        """
        # Create canonical representation (without signature)
        sign_data = {k: v for k, v in data.items() if k != 'signature'}
        canonical = json.dumps(sign_data, sort_keys=True, separators=(',', ':'))
        
        # Sign with HMAC-SHA256
        signature = hashlib.sha256(
            (canonical + LICENSE_SECRET_KEY).encode()
        ).hexdigest()
        
        return signature


def check_license_limit(limit_type: str, increment: int = 1, tenant=None) -> Tuple[bool, str]:
    """
    Check if operation would exceed license limit.
    
    This is a utility function to be called before creating resources.
    
    Args:
        limit_type: Type of limit to check
        increment: Amount to increment
        tenant: Tenant to check (default: first tenant)
        
    Returns:
        (allowed, error_message)
    """
    from .models import License
    
    license = License.get_active_license(tenant)
    
    if not license:
        return False, "No valid license found"
    
    if not license.is_valid:
        return False, "License is not valid"
    
    try:
        quota = license.quota_usage
    except Exception:
        # Create quota usage if not exists
        from .models import QuotaUsage
        quota = QuotaUsage.objects.create(license=license)
    
    return quota.check_limit(limit_type, increment)
