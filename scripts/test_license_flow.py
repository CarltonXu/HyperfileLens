#!/usr/bin/env python3
"""
Test script to verify the License activation flow.

This script demonstrates the complete flow:
1. Generate machine code
2. Generate activation code
3. Activate license
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from licenses.crypto import MachineCodeGenerator, ActivationCode
from licenses.models import License, MachineCode, QuotaUsage
from tenants.models import Tenant
from accounts.models import User


def test_machine_code_generation():
    """Test machine code generation."""
    print("\n" + "=" * 60)
    print("Test 1: Machine Code Generation")
    print("=" * 60)
    
    # Get first tenant and user
    tenant = Tenant.objects.first()
    user = User.objects.first()
    
    if not tenant or not user:
        print("ERROR: No tenant or user found. Please create them first.")
        return False
    
    print(f"Tenant: {tenant.name} ({tenant.id})")
    print(f"User: {user.username} ({user.id})")
    
    # Generate machine code
    machine_code, components = MachineCodeGenerator.generate(
        tenant_id=str(tenant.id),
        user_id=str(user.id)
    )
    
    print(f"\nGenerated Machine Code: {machine_code}")
    print("\nComponents:")
    for key, value in components.items():
        print(f"  {key}: {value}")
    
    return machine_code, tenant, user


def test_activation_code_generation(machine_code):
    """Test activation code generation."""
    print("\n" + "=" * 60)
    print("Test 2: Activation Code Generation")
    print("=" * 60)
    
    # Generate activation code
    limits = {
        'max_tenants': 5,
        'max_users': 100,
        'max_proxies': 20,
        'max_storage_gb': 1000,
        'max_gateways': 3,
        'ai_insights_quota': 1000,
        'max_backup_tasks': 50,
        'max_recovery_tasks': 50,
        'max_source_resources': 50,
        'max_policies': 100,
        'max_repositories': 10,
    }
    
    activation_code = ActivationCode.generate(
        machine_code=machine_code,
        limits=limits,
        valid_days=365
    )
    
    print(f"\nGenerated Activation Code:")
    print(activation_code)
    print(f"\n(Length: {len(activation_code)} characters)")
    
    return activation_code


def test_activation_code_verification(activation_code):
    """Test activation code verification."""
    print("\n" + "=" * 60)
    print("Test 3: Activation Code Verification")
    print("=" * 60)
    
    try:
        # Decode
        data = ActivationCode.decode(activation_code)
        
        print("\nDecoded Activation Data:")
        print(f"  License Key: {data['license_key']}")
        print(f"  Machine Code: {data['machine_code']}")
        print(f"  Issued At: {data['issued_at']}")
        print(f"  Expires At: {data['expires_at']}")
        
        print("\n  Limits:")
        for key, value in data['limits'].items():
            print(f"    {key}: {value}")
        
        # Verify signature
        is_valid = ActivationCode.verify(data)
        print(f"\n  Signature Valid: {is_valid}")
        
        return data, is_valid
        
    except Exception as e:
        print(f"ERROR: {e}")
        return None, False


def test_license_activation(activation_data, tenant, user):
    """Test license activation."""
    print("\n" + "=" * 60)
    print("Test 4: License Activation (Database)")
    print("=" * 60)
    
    # Check if license already exists
    existing = License.objects.filter(
        machine_code=activation_data['machine_code']
    ).first()
    
    if existing:
        print(f"\nLicense already exists: {existing.license_key}")
        print(f"Status: {existing.status}")
        return existing
    
    # Create license
    from datetime import datetime
    
    issued_at = datetime.fromisoformat(
        activation_data['issued_at'].replace('Z', '+00:00')
    )
    
    expires_at = None
    if activation_data.get('expires_at'):
        expires_at = datetime.fromisoformat(
            activation_data['expires_at'].replace('Z', '+00:00')
        )
    
    limits = activation_data['limits']
    
    license = License.objects.create(
        license_key=activation_data['license_key'],
        machine_code=activation_data['machine_code'],
        tenant=tenant,
        activated_by=user,
        max_tenants=limits.get('max_tenants', 1),
        max_users=limits.get('max_users', 10),
        max_proxies=limits.get('max_proxies', 5),
        max_storage_gb=limits.get('max_storage_gb', 100),
        max_gateways=limits.get('max_gateways', 1),
        ai_insights_quota=limits.get('ai_insights_quota', 100),
        max_backup_tasks=limits.get('max_backup_tasks', 10),
        max_recovery_tasks=limits.get('max_recovery_tasks', 10),
        max_source_resources=limits.get('max_source_resources', 20),
        max_policies=limits.get('max_policies', 50),
        max_repositories=limits.get('max_repositories', 5),
        issued_at=issued_at,
        expires_at=expires_at,
        signature=activation_data['signature'],
        status=License.LicenseStatus.ACTIVE,
    )
    
    # Create quota usage
    QuotaUsage.objects.create(license=license)
    
    print(f"\nLicense created successfully!")
    print(f"  License Key: {license.license_key}")
    print(f"  Machine Code: {license.machine_code}")
    print(f"  Tenant: {license.tenant.name}")
    print(f"  Activated By: {license.activated_by.username}")
    print(f"  Status: {license.status}")
    print(f"  Expires At: {license.expires_at or 'Never'}")
    print(f"  Is Valid: {license.is_valid}")
    
    return license


def test_limit_check(license):
    """Test limit checking."""
    print("\n" + "=" * 60)
    print("Test 5: Limit Checking")
    print("=" * 60)
    
    quota = license.quota_usage
    
    # Check various limits
    print("\nChecking limits...")
    
    # Users
    allowed, msg = quota.check_limit('users', 1)
    print(f"  Users (+1): {'OK' if allowed else 'BLOCKED - ' + msg}")
    
    # Proxies
    allowed, msg = quota.check_limit('proxies', 5)
    print(f"  Proxies (+5): {'OK' if allowed else 'BLOCKED - ' + msg}")
    
    # Storage
    allowed, msg = quota.check_limit('storage_gb', 100)
    print(f"  Storage (+100GB): {'OK' if allowed else 'BLOCKED - ' + msg}")
    
    # Exceed limit test
    allowed, msg = quota.check_limit('users', 1000)
    print(f"  Users (+1000): {'OK' if allowed else 'BLOCKED - ' + msg}")


def main():
    print("=" * 60)
    print("HyperFileLens License Flow Test")
    print("=" * 60)
    
    # Test 1: Machine code generation
    result = test_machine_code_generation()
    if not result:
        return 1
    
    machine_code, tenant, user = result
    
    # Test 2: Activation code generation
    activation_code = test_activation_code_generation(machine_code)
    
    # Test 3: Verification
    activation_data, is_valid = test_activation_code_verification(activation_code)
    if not is_valid:
        print("\nERROR: Activation code verification failed!")
        return 1
    
    # Test 4: Activation
    license = test_license_activation(activation_data, tenant, user)
    
    # Test 5: Limit checking
    test_limit_check(license)
    
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    exit(main())
