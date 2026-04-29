#!/usr/bin/env python3
"""
License Activation Code Generator

Usage:
    # Quick: Use preset tier
    python license_generator.py --machine-code HFL-MCH-XXXX --tier pro
    
    # Custom: Override specific limits on tier
    python license_generator.py --machine-code HFL-MCH-XXXX --tier pro --max-users 200 --max-proxies 50
    
    # Full custom: Define all limits
    python license_generator.py --machine-code HFL-MCH-XXXX --tier custom \
        --max-tenants 10 --max-users 500 --max-proxies 100 --max-storage-gb 10000 \
        --max-gateways 5 --ai-insights-quota 5000 \
        --max-backup-tasks 200 --max-recovery-tasks 200 \
        --max-source-resources 100 --max-policies 500 --max-repositories 20
    
    # Perpetual license (never expires)
    python license_generator.py --machine-code HFL-MCH-XXXX --tier enterprise --perpetual
    
    # Verify an activation code
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
        'custom': {
            # Default custom values (will be overridden by command line args)
            'max_tenants': 1,
            'max_users': 10,
            'max_proxies': 5,
            'max_storage_gb': 500,
            'max_gateways': 1,
            'ai_insights_quota': 500,
            'max_backup_tasks': 50,
            'max_recovery_tasks': 50,
            'max_source_resources': 20,
            'max_policies': 50,
            'max_repositories': 5,
        },
    }
    return tiers.get(tier.lower(), tiers['trial']).copy()


LIMIT_FIELDS = [
    ('max_tenants', 'Maximum number of tenants'),
    ('max_users', 'Maximum number of users'),
    ('max_proxies', 'Maximum number of proxies'),
    ('max_storage_gb', 'Maximum storage in GB'),
    ('max_gateways', 'Maximum number of gateways'),
    ('ai_insights_quota', 'AI Insights monthly quota'),
    ('max_backup_tasks', 'Maximum backup tasks'),
    ('max_recovery_tasks', 'Maximum recovery tasks'),
    ('max_source_resources', 'Maximum source resources'),
    ('max_policies', 'Maximum backup policies'),
    ('max_repositories', 'Maximum repositories'),
]


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
    validity_days: Optional[int] = 365,
    custom_limits: Optional[Dict[str, int]] = None
) -> dict:
    """
    Generate an activation code for a machine code.
    
    Args:
        machine_code: Target machine code (HFL-MCH-XXXX-...)
        tier: License tier (trial, pro, enterprise, custom)
        validity_days: Number of days until expiration (None = perpetual)
        custom_limits: Optional custom limits (overrides tier defaults)
    
    Returns:
        dict with license_key, activation_code, and other details
    """
    # Validate machine code format
    if not machine_code.startswith('HFL-MCH-'):
        raise ValueError("Invalid machine code format. Must start with HFL-MCH-")
    
    code_part = machine_code[8:]  # Remove 'HFL-MCH-' prefix
    code_part_clean = code_part.replace('-', '')
    if len(code_part_clean) < 16:
        raise ValueError(f"Machine code too short. Expected at least 16 hex chars, got {len(code_part_clean)}")
    
    # Generate license key
    license_key = generate_license_key(tier)
    
    # Get limits: start with tier defaults, then apply custom overrides
    limits = get_tier_limits(tier)
    if custom_limits:
        limits.update(custom_limits)
    
    # Calculate dates
    issued_at = datetime.now()
    if validity_days is None:
        # Perpetual license - expires at year 9999
        expires_at = datetime(9999, 12, 31, 23, 59, 59)
        is_perpetual = True
    else:
        expires_at = issued_at + timedelta(days=validity_days)
        is_perpetual = False
    
    # Create activation data
    activation_data = {
        'license_key': license_key,
        'machine_code': machine_code,
        'limits': limits,
        'issued_at': issued_at.isoformat() + '+00:00',
        'expires_at': expires_at.isoformat() + '+00:00',
        'is_perpetual': is_perpetual,
    }
    
    # Generate signature
    signature = generate_signature(activation_data)
    activation_data['signature'] = signature
    
    # Encode to base64
    json_str = json.dumps(activation_data)
    activation_code = base64.b64encode(json_str.encode()).decode()
    
    return {
        'license_key': license_key,
        'machine_code': machine_code,
        'tier': tier,
        'activation_code': f'HFL-ACT-{activation_code}',
        'limits': limits,
        'issued_at': issued_at.isoformat(),
        'expires_at': expires_at.isoformat() if not is_perpetual else 'Perpetual',
        'validity_days': validity_days if not is_perpetual else None,
        'is_perpetual': is_perpetual,
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
        
        # Verify signature
        expected_signature = generate_signature(verification_data)
        if not hmac.compare_digest(stored_signature, expected_signature):
            return {'valid': False, 'error': 'Invalid signature (code may have been tampered with)'}
        
        # Check expiration (unless perpetual)
        is_perpetual = data.get('is_perpetual', False)
        if not is_perpetual and data.get('expires_at'):
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
    parser = argparse.ArgumentParser(
        description='Generate License Activation Codes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick: Use preset tier
  %(prog)s --machine-code HFL-MCH-XXXX --tier pro
  
  # Custom: Override specific limits
  %(prog)s --machine-code HFL-MCH-XXXX --tier pro --max-users 200 --max-proxies 50
  
  # Full custom: Define all limits
  %(prog)s --machine-code HFL-MCH-XXXX --tier custom \\
      --max-tenants 10 --max-users 500 --max-proxies 100 --max-storage-gb 10000 \\
      --max-gateways 5 --ai-insights-quota 5000 \\
      --max-backup-tasks 200 --max-recovery-tasks 200 \\
      --max-source-resources 100 --max-policies 500 --max-repositories 20
  
  # Perpetual license
  %(prog)s --machine-code HFL-MCH-XXXX --tier enterprise --perpetual
  
  # Verify activation code
  %(prog)s --verify "HFL-ACT-..."
        """
    )
    
    # Required for generation
    parser.add_argument('--machine-code', '-m', help='Target machine code (HFL-MCH-...)')
    
    # Tier selection
    parser.add_argument('--tier', '-t', choices=['trial', 'pro', 'enterprise', 'custom'], 
                        default='pro', help='License tier (default: pro)')
    
    # Validity options
    validity_group = parser.add_mutually_exclusive_group()
    validity_group.add_argument('--days', '-d', type=int, default=365,
                                help='Validity in days (default: 365)')
    validity_group.add_argument('--perpetual', '-p', action='store_true',
                                help='Generate perpetual license (never expires)')
    
    # Custom limit options
    limit_group = parser.add_argument_group('Custom Limits (override tier defaults)')
    limit_group.add_argument('--max-tenants', type=int, help='Maximum number of tenants')
    limit_group.add_argument('--max-users', type=int, help='Maximum number of users')
    limit_group.add_argument('--max-proxies', type=int, help='Maximum number of proxies')
    limit_group.add_argument('--max-storage-gb', type=int, help='Maximum storage in GB')
    limit_group.add_argument('--max-gateways', type=int, help='Maximum number of gateways')
    limit_group.add_argument('--ai-insights-quota', type=int, help='AI Insights monthly quota')
    limit_group.add_argument('--max-backup-tasks', type=int, help='Maximum backup tasks')
    limit_group.add_argument('--max-recovery-tasks', type=int, help='Maximum recovery tasks')
    limit_group.add_argument('--max-source-resources', type=int, help='Maximum source resources')
    limit_group.add_argument('--max-policies', type=int, help='Maximum backup policies')
    limit_group.add_argument('--max-repositories', type=int, help='Maximum repositories')
    
    # Other options
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
                data = result['data']
                print(f"\nLicense Key: {data['license_key']}")
                print(f"Machine Code: {data['machine_code']}")
                print(f"Perpetual: {'Yes' if data.get('is_perpetual') else 'No'}")
                if not data.get('is_perpetual'):
                    print(f"Expires At: {data['expires_at']}")
                print(f"\nLimits:")
                for key, value in data['limits'].items():
                    print(f"  {key}: {value}")
            else:
                print(f"✗ {result['error']}")
        return
    
    # Generate mode
    if not args.machine_code:
        parser.error("--machine-code is required when not verifying")
    
    # Build custom limits from command line args
    custom_limits = {}
    for field, _ in LIMIT_FIELDS:
        arg_name = field.replace('_', '-')
        value = getattr(args, field, None)
        if value is not None:
            custom_limits[field] = value
    
    # Determine validity
    validity_days = None if args.perpetual else args.days
    
    result = generate_activation_code(
        machine_code=args.machine_code,
        tier=args.tier,
        validity_days=validity_days,
        custom_limits=custom_limits if custom_limits else None
    )
    
    if args.output == 'json':
        print(json.dumps(result, indent=2))
    else:
        print("=" * 70)
        print("LICENSE ACTIVATION CODE GENERATED")
        print("=" * 70)
        print(f"\nLicense Key:   {result['license_key']}")
        print(f"Machine Code:  {result['machine_code']}")
        print(f"Tier:          {result['tier'].upper()}")
        
        if result['is_perpetual']:
            print(f"Validity:      PERPETUAL (Never Expires)")
        else:
            print(f"Validity:      {result['validity_days']} days")
        
        print(f"Issued At:     {result['issued_at']}")
        print(f"Expires At:    {result['expires_at']}")
        
        print(f"\n{'─' * 70}")
        print("QUOTA LIMITS:")
        print("─" * 70)
        
        # Format limits in a nice table
        limit_names = {
            'max_tenants': 'Tenants',
            'max_users': 'Users',
            'max_proxies': 'Proxies',
            'max_storage_gb': 'Storage (GB)',
            'max_gateways': 'Gateways',
            'ai_insights_quota': 'AI Insights/mo',
            'max_backup_tasks': 'Backup Tasks',
            'max_recovery_tasks': 'Recovery Tasks',
            'max_source_resources': 'Source Resources',
            'max_policies': 'Policies',
            'max_repositories': 'Repositories',
        }
        
        for key, value in result['limits'].items():
            name = limit_names.get(key, key)
            print(f"  {name:20} {value:>10,}")
        
        print(f"\n{'=' * 70}")
        print("ACTIVATION CODE:")
        print("=" * 70)
        # Split long code into multiple lines for readability
        code = result['activation_code']
        print(code[:80])
        if len(code) > 80:
            print(code[80:])
        print("=" * 70)
        print("\n⚠️  IMPORTANT: Send this activation code to the customer.")
        print("   They will enter it in: Settings > License > Activate License")


if __name__ == '__main__':
    main()
