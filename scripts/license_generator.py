#!/usr/bin/env python3
"""
License Activation Code Generator

Usage:
    python license_generator.py --machine-code HFL-MCH-XXXX-XXXX-XXXX-XXXX --tier pro
    python license_generator.py --machine-code HFL-MCH-XXXX-XXXX-XXXX-XXXX --tier enterprise
    python license_generator.py --verify "HFL-ACT-..."
"""

import argparse
import json
import base64
import hashlib
import hmac
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional

# License secret key (must match backend)
LICENSE_SECRET_KEY = os.environ.get('LICENSE_SECRET_KEY', 'HFL_LICENSE_SECRET_2024_DO_NOT_SHARE')


def generate_license_key(tier: str) -> str:
    """Generate a unique license key."""
    import random
    import string
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=8))
    year = datetime.now().year
    return f"HFL-{tier.upper()}-{year}-{random_part}"


def get_tier_limits(tier: str) -> Dict[str, int]:
    """Get limits based on tier."""
    tiers = {
        'trial': {
            'max_tenants': 1,
            'max_users': 5,
            'max_proxies': 2,
            'max_storage_gb': 100,
            'max_gateways': 1,
            'ai_insights_quota': 100,
            'max_backup_tasks': 10,
            'max_recovery_tasks': 10,
            'max_source_resources': 10,
            'max_policies': 20,
            'max_repositories': 3,
        },
        'pro': {
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
        },
        'enterprise': {
            'max_tenants': 100,
            'max_users': 10000,
            'max_proxies': 500,
            'max_storage_gb': 100000,
            'max_gateways': 50,
            'ai_insights_quota': 100000,
            'max_backup_tasks': 1000,
            'max_recovery_tasks': 1000,
            'max_source_resources': 1000,
            'max_policies': 2000,
            'max_repositories': 100,
        },
    }
    return tiers.get(tier.lower(), tiers['trial'])


def generate_signature(data: dict) -> str:
    """Generate SHA256 signature for the data (matching backend)."""
    # Sort keys and create JSON string (no separators to match backend)
    sorted_data = json.dumps(data, sort_keys=True)
    # Generate SHA256 hash with secret key appended
    signature = hashlib.sha256(
        (sorted_data + LICENSE_SECRET_KEY).encode()
    ).hexdigest()
    return signature


def generate_activation_code(
    machine_code: str,
    tier: str = 'pro',
    validity_days: int = 365,
    custom_limits: Optional[Dict[str, int]] = None
) -> dict:
    """
    Generate an activation code for a machine code.
    
    Args:
        machine_code: Target machine code (HFL-MCH-XXXX-...)
        tier: License tier (trial, pro, enterprise)
        validity_days: Number of days until expiration
        custom_limits: Optional custom limits (overrides tier defaults)
    
    Returns:
        dict with license_key, activation_code, and other details
    """
    # Validate machine code format
    if not machine_code.startswith('HFL-MCH-'):
        raise ValueError("Invalid machine code format. Must start with HFL-MCH-")
    
    # Generate license key
    license_key = generate_license_key(tier)
    
    # Get limits
    limits = custom_limits or get_tier_limits(tier)
    
    # Calculate dates
    issued_at = datetime.now()
    expires_at = issued_at + timedelta(days=validity_days)
    
    # Create activation data
    activation_data = {
        'license_key': license_key,
        'machine_code': machine_code,
        'limits': limits,
        'issued_at': issued_at.isoformat() + '+00:00',
        'expires_at': expires_at.isoformat() + '+00:00',
    }
    
    # Generate signature
    signature = generate_signature(activation_data)
    activation_data['signature'] = signature
    
    # Encode to base64 (no separators to match backend)
    json_str = json.dumps(activation_data)
    activation_code = base64.b64encode(json_str.encode()).decode()
    
    return {
        'license_key': license_key,
        'machine_code': machine_code,
        'tier': tier,
        'activation_code': f'HFL-ACT-{activation_code}',
        'limits': limits,
        'issued_at': issued_at.isoformat(),
        'expires_at': expires_at.isoformat(),
        'validity_days': validity_days,
    }


def verify_activation_code(activation_code: str) -> dict:
    """
    Verify an activation code.
    
    Args:
        activation_code: Full activation code (HFL-ACT-...)
    
    Returns:
        dict with verification result
    """
    if not activation_code.startswith('HFL-ACT-'):
        return {'valid': False, 'error': 'Invalid activation code format'}
    
    try:
        # Decode base64
        encoded_part = activation_code.replace('HFL-ACT-', '')
        json_str = base64.b64decode(encoded_part).decode()
        data = json.loads(json_str)
        
        # Extract signature
        stored_signature = data.get('signature')
        if not stored_signature:
            return {'valid': False, 'error': 'Missing signature'}
        
        # Create a copy without signature for verification
        verification_data = {k: v for k, v in data.items() if k != 'signature'}
        
        # Verify signature (using hmac.compare_digest for timing-safe comparison)
        expected_signature = generate_signature(verification_data)
        if not hmac.compare_digest(stored_signature, expected_signature):
            return {'valid': False, 'error': 'Invalid signature (code may have been tampered with)'}
        
        # Check expiration
        if data.get('expires_at'):
            expires_at = datetime.fromisoformat(data['expires_at'].replace('+00:00', '').replace('Z', ''))
            if datetime.now() > expires_at:
                return {'valid': False, 'error': 'Activation code has expired'}
        
        return {
            'valid': True,
            'data': data,
            'message': 'Activation code is valid'
        }
        
    except Exception as e:
        return {'valid': False, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='Generate License Activation Codes')
    parser.add_argument('--machine-code', '-m', help='Target machine code (HFL-MCH-...)')
    parser.add_argument('--tier', '-t', choices=['trial', 'pro', 'enterprise'], default='pro',
                        help='License tier (default: pro)')
    parser.add_argument('--days', '-d', type=int, default=365,
                        help='Validity in days (default: 365)')
    parser.add_argument('--verify', '-v', help='Verify an activation code')
    parser.add_argument('--output', '-o', choices=['json', 'text'], default='text',
                        help='Output format')
    
    args = parser.parse_args()
    
    # Verify mode
    if args.verify:
        result = verify_activation_code(args.verify)
        if args.output == 'json':
            print(json.dumps(result, indent=2))
        else:
            if result['valid']:
                print(f"✓ {result['message']}")
                print(f"\nLicense Key: {result['data']['license_key']}")
                print(f"Machine Code: {result['data']['machine_code']}")
                print(f"Expires At: {result['data']['expires_at']}")
                print(f"\nLimits:")
                for key, value in result['data']['limits'].items():
                    print(f"  {key}: {value}")
            else:
                print(f"✗ {result['error']}")
        return
    
    # Generate mode
    if not args.machine_code:
        parser.error("--machine-code is required when not verifying")
    
    result = generate_activation_code(
        machine_code=args.machine_code,
        tier=args.tier,
        validity_days=args.days
    )
    
    if args.output == 'json':
        print(json.dumps(result, indent=2))
    else:
        print("=" * 60)
        print("LICENSE ACTIVATION CODE GENERATED")
        print("=" * 60)
        print(f"\nLicense Key:   {result['license_key']}")
        print(f"Machine Code:  {result['machine_code']}")
        print(f"Tier:          {result['tier'].upper()}")
        print(f"Validity:      {result['validity_days']} days")
        print(f"Issued At:     {result['issued_at']}")
        print(f"Expires At:    {result['expires_at']}")
        print(f"\nLimits:")
        for key, value in result['limits'].items():
            print(f"  {key}: {value}")
        print(f"\n{'=' * 60}")
        print("ACTIVATION CODE:")
        print("=" * 60)
        print(result['activation_code'])
        print("=" * 60)
        print("\n⚠️  IMPORTANT: Send this activation code to the customer.")
        print("   They will enter it in: Settings > License > Activate License")


if __name__ == '__main__':
    main()
