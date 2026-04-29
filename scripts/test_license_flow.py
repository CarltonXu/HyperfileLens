#!/usr/bin/env python3
"""
HyperFileLens License Flow Test

Test the complete license activation flow with improved machine code generation.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/workspace/projects/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from licenses.crypto import MachineCodeGenerator, ActivationCodeGenerator
from licenses.models import License, QuotaUsage
from tenants.models import Tenant
from accounts.models import User


def test_machine_code_stability():
    """Test that machine codes are stable across multiple calls."""
    print("=" * 60)
    print("Test: Machine Code Stability")
    print("=" * 60)
    
    tenant_id = "test-tenant-123"
    
    # Generate machine code multiple times
    codes = []
    for i in range(3):
        code, components = MachineCodeGenerator.generate(tenant_id)
        codes.append(code)
        print(f"  Generation {i+1}: {code}")
        print(f"    Machine ID: {components.get('machine_id', 'N/A')[:50]}...")
    
    # All codes should be identical
    if len(set(codes)) == 1:
        print("\n✓ Machine code is stable across multiple calls")
        return True
    else:
        print("\n✗ Machine code changed between calls!")
        return False


def test_cloud_instance_detection():
    """Test cloud instance ID detection."""
    print("\n" + "=" * 60)
    print("Test: Cloud Instance Detection")
    print("=" * 60)
    
    machine_id = MachineCodeGenerator.get_machine_id()
    print(f"  Detected Machine ID: {machine_id}")
    
    if machine_id.startswith('aws:'):
        print("  ✓ Running on AWS EC2")
    elif machine_id.startswith('gcp:'):
        print("  ✓ Running on Google Cloud")
    elif machine_id.startswith('azure:'):
        print("  ✓ Running on Azure")
    elif machine_id.startswith('disk:'):
        print("  ✓ Using disk serial as identifier")
    else:
        print("  ℹ Using fallback identifiers")
    
    return True


def test_activation_flow():
    """Test complete activation flow."""
    print("\n" + "=" * 60)
    print("Test: Complete Activation Flow")
    print("=" * 60)
    
    # Get or create test tenant
    tenant, _ = Tenant.objects.get_or_create(
        name='Test Company',
        defaults={'slug': 'test-company', 'status': 'active'}
    )
    
    # Get or create test user
    user, _ = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@test.com', 'is_staff': True, 'is_superuser': True}
    )
    
    print(f"\n1. Tenant: {tenant.name} ({tenant.id})")
    print(f"   User: {user.username} ({user.id})")
    
    # Step 1: Generate machine code
    print("\n2. Generating machine code...")
    machine_code, components = MachineCodeGenerator.generate(str(tenant.id))
    print(f"   Machine Code: {machine_code}")
    print(f"   Machine ID: {components.get('machine_id', 'N/A')[:50]}...")
    
    # Step 2: Generate activation code (sales team side)
    print("\n3. Generating activation code...")
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
    
    activation_code = ActivationCodeGenerator.generate(
        license_key="HFL-PRO-2026-TEST123",
        machine_code=machine_code,
        limits=limits,
        validity_days=365
    )
    
    print(f"   Activation Code: {activation_code[:50]}...")
    print(f"   (Length: {len(activation_code)} characters)")
    
    # Step 3: Verify activation code
    print("\n4. Verifying activation code...")
    is_valid, decoded_data, error = ActivationCodeGenerator.verify(activation_code)
    
    if not is_valid:
        print(f"   ✗ Verification failed: {error}")
        return False
    
    print("   ✓ Verification successful")
    print(f"   License Key: {decoded_data['license_key']}")
    print(f"   Machine Code: {decoded_data['machine_code']}")
    print(f"   Expires: {decoded_data['expires_at']}")
    
    # Step 4: Check machine code binding
    print("\n5. Checking machine code binding...")
    
    # Simulate different tenant - should fail
    wrong_tenant_id = "wrong-tenant-456"
    wrong_code, _ = MachineCodeGenerator.generate(wrong_tenant_id)
    
    if wrong_code != machine_code:
        print(f"   ✓ Different tenant produces different machine code")
    else:
        print(f"   ✗ Different tenant produced same machine code!")
        return False
    
    # Same tenant should get same code
    same_code, _ = MachineCodeGenerator.generate(str(tenant.id))
    if same_code == machine_code:
        print(f"   ✓ Same tenant gets same machine code")
    else:
        print(f"   ✗ Same tenant got different machine code!")
        return False
    
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
    return True


def main():
    print("\n" + "=" * 60)
    print("HyperFileLens License Flow Test")
    print("Testing Improved Machine Code Generation")
    print("=" * 60)
    
    results = []
    
    results.append(("Machine Code Stability", test_machine_code_stability()))
    results.append(("Cloud Instance Detection", test_cloud_instance_detection()))
    results.append(("Activation Flow", test_activation_flow()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    exit(main())
