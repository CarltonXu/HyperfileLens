"""
License Cryptography Module for HyperFileLens

Improved machine code generation with:
1. Stable hardware identifiers (motherboard UUID, disk serial)
2. Cloud platform instance IDs support
3. Persistence to avoid regeneration issues
4. Tenant-level binding (not user-level)
"""

import hashlib
import json
import base64
import secrets
import subprocess
import platform
import uuid
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple

from django.conf import settings

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
except Exception:  # pragma: no cover - optional dependency guard
    InvalidSignature = Exception
    Ed25519PublicKey = None
    load_pem_public_key = None


# Shared secret for signature verification
# MUST match the value in license_generator.py
LICENSE_SECRET_KEY = "HFL_LICENSE_SECRET_2024_DO_NOT_SHARE"


def canonical_json(data: Dict[str, Any]) -> str:
    """Return stable JSON used for signatures and payload hashes."""
    return json.dumps(data, sort_keys=True, separators=(',', ':'))


def payload_hash(data: Dict[str, Any]) -> str:
    """Return SHA256 hash for a verified license payload."""
    return hashlib.sha256(canonical_json(data).encode()).hexdigest()


def _b64url_decode(value: str) -> bytes:
    padding = '=' * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode())


def _verify_ed25519_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Verify the public-key license token format:
    HFL-LIC-v1.<base64url-json-payload>.<base64url-ed25519-signature>
    """
    if not token.startswith("HFL-LIC-v1."):
        return False, None, "Unsupported license token format"

    if not Ed25519PublicKey or not load_pem_public_key:
        return False, None, "Ed25519 verification dependency is unavailable"

    public_keys = getattr(settings, 'LICENSE_PUBLIC_KEYS', None) or []
    public_key = getattr(settings, 'LICENSE_PUBLIC_KEY', '')
    if public_key:
        public_keys = [public_key, *public_keys]
    if not public_keys:
        return False, None, "No license public key configured"

    try:
        _, payload_part, signature_part = token.split('.', 2)
        payload_bytes = _b64url_decode(payload_part)
        signature = _b64url_decode(signature_part)
        payload = json.loads(payload_bytes.decode())
    except Exception as exc:
        return False, None, f"Invalid license token encoding: {exc}"

    for key_text in public_keys:
        try:
            key = load_pem_public_key(key_text.encode() if isinstance(key_text, str) else key_text)
            key.verify(signature, payload_bytes)
            return True, payload, ""
        except InvalidSignature:
            continue
        except Exception:
            continue

    return False, None, "Invalid license token signature"


class MachineCodeGenerator:
    """
    Generate stable and unique machine codes for license binding.
    
    Improved design:
    1. Use stable hardware identifiers (motherboard UUID, disk serial)
    2. Support cloud platform instance IDs (AWS, GCP, Azure)
    3. Persist generated code to avoid regeneration issues
    4. Bind to tenant, not user (tenant can have multiple admins)
    
    Machine Code = SHA256(Stable Hardware ID + Cloud Instance ID + Tenant ID)
    """
    
    # Persistence file path
    MACHINE_CODE_FILE = "/var/lib/hyperfilelens/machine_code.json"
    
    @staticmethod
    def get_motherboard_uuid() -> str:
        """Get motherboard UUID - most stable hardware identifier."""
        system = platform.system()
        
        try:
            if system == "Linux":
                # Try DMI UUID (requires root or /sys access)
                try:
                    with open('/sys/class/dmi/id/product_uuid', 'r') as f:
                        return f.read().strip()
                except (FileNotFoundError, PermissionError):
                    pass
                
                # Try board serial
                try:
                    with open('/sys/class/dmi/id/board_serial', 'r') as f:
                        return f.read().strip()
                except (FileNotFoundError, PermissionError):
                    pass
                
                # Try dmidecode (requires root)
                try:
                    result = subprocess.run(
                        ['dmidecode', '-s', 'system-uuid'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout.strip()
                except Exception:
                    pass
                    
            elif system == "Windows":
                try:
                    result = subprocess.run(
                        ['wmic', 'csproduct', 'get', 'UUID'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            return lines[1].strip()
                except Exception:
                    pass
                    
            elif system == "Darwin":  # macOS
                try:
                    result = subprocess.run(
                        ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'IOPlatformUUID' in line:
                                return line.split('"')[-2]
                except Exception:
                    pass
                    
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def get_disk_serial() -> str:
        """Get boot disk serial number."""
        system = platform.system()
        
        try:
            if system == "Linux":
                # Try to get root disk serial
                try:
                    # Find root device
                    result = subprocess.run(
                        ['lsblk', '-no', 'SERIAL', '-d', '/dev/sda'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout.strip()
                except Exception:
                    pass
                
                # Alternative: use /sys/block
                try:
                    for device in os.listdir('/sys/block'):
                        if device.startswith('sd') or device.startswith('vd') or device.startswith('nvme'):
                            serial_path = f'/sys/block/{device}/serial'
                            if os.path.exists(serial_path):
                                with open(serial_path, 'r') as f:
                                    return f.read().strip()
                except Exception:
                    pass
                    
            elif system == "Windows":
                try:
                    result = subprocess.run(
                        ['wmic', 'diskdrive', 'get', 'SerialNumber'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            return lines[1].strip()
                except Exception:
                    pass
                    
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def get_cloud_instance_id() -> str:
        """Get cloud platform instance ID (AWS, GCP, Azure)."""
        
        # AWS EC2 Instance ID
        try:
            result = subprocess.run(
                ['curl', '-s', '--max-time', '2', 
                 'http://169.254.169.254/latest/meta-data/instance-id'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.startswith('i-'):
                return f"aws:{result.stdout.strip()}"
        except Exception:
            pass
        
        # GCP Instance ID
        try:
            result = subprocess.run(
                ['curl', '-s', '--max-time', '2', '-H', 
                 'Metadata-Flavor: Google',
                 'http://metadata.google.internal/computeMetadata/v1/instance/id'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return f"gcp:{result.stdout.strip()}"
        except Exception:
            pass
        
        # Azure VM ID
        try:
            result = subprocess.run(
                ['curl', '-s', '--max-time', '2', '-H', 
                 'Metadata: true',
                 'http://169.254.169.254/metadata/instance/compute/vmId?api-version=2021-02-01&format=text'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return f"azure:{result.stdout.strip()}"
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def get_machine_id() -> str:
        """
        Get the most stable machine identifier available.
        Priority: Cloud Instance ID > Motherboard UUID > Disk Serial > Fallback
        """
        # 1. Cloud instance ID (most stable in cloud environments)
        cloud_id = MachineCodeGenerator.get_cloud_instance_id()
        if cloud_id:
            return cloud_id
        
        # 2. Motherboard UUID (stable in physical servers)
        mb_uuid = MachineCodeGenerator.get_motherboard_uuid()
        if mb_uuid:
            return mb_uuid
        
        # 3. Disk serial (fallback)
        disk_serial = MachineCodeGenerator.get_disk_serial()
        if disk_serial:
            return f"disk:{disk_serial}"
        
        # 4. Last resort: combine multiple identifiers
        mac = MachineCodeGenerator._get_mac_address()
        hostname = platform.node()
        return f"fallback:{mac}:{hostname}"
    
    @staticmethod
    def _get_mac_address() -> str:
        """Get primary MAC address (private helper)."""
        try:
            mac = uuid.getnode()
            return ':'.join(['{:02X}'.format((mac >> elements) & 0xFF) 
                           for elements in range(0, 2*6, 2)][::-1])
        except Exception:
            return "UNKNOWN_MAC"
    
    @staticmethod
    def _load_persisted_code() -> Optional[Dict[str, Any]]:
        """Load persisted machine code data."""
        try:
            if os.path.exists(MachineCodeGenerator.MACHINE_CODE_FILE):
                with open(MachineCodeGenerator.MACHINE_CODE_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None
    
    @staticmethod
    def _persist_code(data: Dict[str, Any]) -> bool:
        """Persist machine code data to file."""
        try:
            os.makedirs(os.path.dirname(MachineCodeGenerator.MACHINE_CODE_FILE), exist_ok=True)
            with open(MachineCodeGenerator.MACHINE_CODE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            pass
        return False
    
    @staticmethod
    def generate(tenant_id: str, force_regenerate: bool = False) -> Tuple[str, Dict[str, str]]:
        """
        Generate a unique machine code for a tenant.
        
        If a code already exists for this tenant, return it (unless force_regenerate=True).
        This ensures stability across restarts and minor hardware changes.
        
        Args:
            tenant_id: Tenant UUID
            force_regenerate: Force regeneration even if code exists
            
        Returns:
            (machine_code, components_dict)
        """
        tenant_id = str(tenant_id)
        
        # Check for persisted code
        if not force_regenerate:
            persisted = MachineCodeGenerator._load_persisted_code()
            if persisted and persisted.get('tenant_id') == tenant_id:
                return persisted['machine_code'], persisted.get('components', {})
        
        # Generate new code
        machine_id = MachineCodeGenerator.get_machine_id()
        
        components = {
            'machine_id': machine_id,
            'tenant_id': tenant_id,
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }
        
        # Create combined string
        combined = f"{machine_id}|{tenant_id}"
        
        # Generate SHA256 hash
        hash_value = hashlib.sha256(combined.encode()).hexdigest()[:32]
        
        # Format as HFL-MCH-XXXX-XXXX-XXXX-XXXX
        chunks = [hash_value[i:i+4].upper() for i in range(0, 16, 4)]
        machine_code = "HFL-MCH-" + "-".join(chunks)
        
        # Persist
        MachineCodeGenerator._persist_code({
            'machine_code': machine_code,
            'tenant_id': tenant_id,
            'components': components,
        })
        
        return machine_code, components
    
    @staticmethod
    def verify(stored_code: str, tenant_id: str) -> Tuple[bool, str]:
        """
        Verify if current machine matches stored machine code.
        
        Returns:
            (is_valid, error_message)
        """
        tenant_id = str(tenant_id)
        
        # Load persisted code first
        persisted = MachineCodeGenerator._load_persisted_code()
        if persisted and persisted.get('machine_code') == stored_code:
            if persisted.get('tenant_id') == tenant_id:
                return True, ""
            return False, "License is bound to a different tenant"
        
        # Regenerate and compare
        current_code, _ = MachineCodeGenerator.generate(tenant_id)
        
        if current_code == stored_code:
            return True, ""
        
        # Check if it's just a minor hardware change
        # Allow re-verification if machine_id matches but hash differs
        # (This handles cases like MAC address changes)
        return False, "Machine identifier mismatch. Please regenerate machine code."


class ActivationCodeGenerator:
    """
    Generate and verify activation codes for license binding.
    
    Activation Code = Base64(JSON({
        license_key: str,
        machine_code: str,
        limits: dict,
        issued_at: datetime,
        expires_at: datetime,
        signature: HMAC-SHA256
    }))
    """
    
    @staticmethod
    def generate(
        license_key: str,
        machine_code: str,
        limits: Dict[str, int],
        validity_days: int = 365
    ) -> str:
        """
        Generate an activation code.
        
        Args:
            license_key: Unique license key
            machine_code: Target machine code
            limits: Dictionary of quota limits
            validity_days: License validity in days
            
        Returns:
            Activation code string
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=validity_days)
        
        data = {
            'license_key': license_key,
            'machine_code': machine_code,
            'limits': limits,
            'issued_at': now.isoformat(),
            'expires_at': expires_at.isoformat(),
        }
        
        # Generate signature
        data_str = json.dumps(data, sort_keys=True)
        signature = hashlib.sha256(
            (data_str + LICENSE_SECRET_KEY).encode()
        ).hexdigest()
        data['signature'] = signature
        
        # Encode to base64
        json_str = json.dumps(data)
        encoded = base64.b64encode(json_str.encode()).decode()
        
        return f"HFL-ACT-{encoded}"
    
    @staticmethod
    def verify(activation_code: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Verify an activation code.
        
        Returns:
            (is_valid, decoded_data, error_message)
        """
        try:
            if not activation_code.startswith("HFL-ACT-"):
                return False, None, "Invalid activation code format"
            
            # Decode
            encoded = activation_code[8:]  # Remove "HFL-ACT-"
            json_str = base64.b64decode(encoded).decode()
            data = json.loads(json_str)
            
            # Verify signature
            stored_signature = data.get('signature')
            if not stored_signature:
                return False, None, "Missing signature"
            
            # Create a copy without signature for verification
            verification_data = {k: v for k, v in data.items() if k != 'signature'}
            data_str = json.dumps(verification_data, sort_keys=True)
            expected_signature = hashlib.sha256(
                (data_str + LICENSE_SECRET_KEY).encode()
            ).hexdigest()
            
            if stored_signature != expected_signature:
                return False, None, "Invalid signature - activation code has been tampered"
            
            # Check expiration
            if data.get('expires_at'):
                expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
                if datetime.now(timezone.utc) > expires_at:
                    return False, data, "License has expired"
            
            # Return data WITH signature (needed for License creation)
            return True, data, ""
            
        except Exception as e:
            return False, None, f"Failed to verify activation code: {str(e)}"


def verify_license_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Verify a license token and return its signed payload.

    New commercial tokens should use the Ed25519 HFL-LIC-v1 format. The legacy
    HFL-ACT format is accepted for backward compatibility with existing tools.
    """
    if token.startswith("HFL-LIC-v1."):
        return _verify_ed25519_token(token)
    return ActivationCodeGenerator.verify(token)


class LicenseCrypto:
    """
    Wrapper class for license cryptographic operations.
    Provides a simple interface for views.
    """
    
    @staticmethod
    def verify(activation_code: str) -> Dict[str, Any]:
        """
        Verify and decode an activation code.
        
        Args:
            activation_code: The activation code string
            
        Returns:
            Decoded data dictionary
            
        Raises:
            ValueError: If verification fails
        """
        is_valid, data, error = verify_license_token(activation_code)
        
        if not is_valid:
            raise ValueError(error)
        
        return data
    
    @staticmethod
    def generate(license_key: str, machine_code: str, limits: Dict[str, int], 
                 validity_days: int = 365) -> str:
        """
        Generate an activation code.
        """
        return ActivationCodeGenerator.generate(license_key, machine_code, limits, validity_days)
    
    @staticmethod
    def generate_machine_code(tenant_id: str, force_regenerate: bool = False) -> Tuple[str, Dict[str, str]]:
        """
        Generate a machine code for a tenant.
        """
        return MachineCodeGenerator.generate(tenant_id, force_regenerate)
