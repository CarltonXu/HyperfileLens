#!/usr/bin/env python3
"""
HyperFileLens License Generator

This is an OFFLINE tool used by the sales team to generate activation codes.

Usage:
    python license_generator.py --machine-code HFL-MCH-XXXX-XXXX-XXXX-XXXX

The generated activation code should be sent to the customer.
"""

import argparse
import hashlib
import json
import base64
import secrets
from datetime import datetime, timezone, timedelta


# MUST match the value in backend/licenses/crypto.py
LICENSE_SECRET_KEY = "HFL_LICENSE_SECRET_2024_DO_NOT_SHARE"


# Predefined license tiers
LICENSE_TIERS = {
    'trial': {
        'name': 'Trial',
        'valid_days': 30,
        'limits': {
            'max_tenants': 1,
            'max_users': 5,
            'max_proxies': 2,
            'max_storage_gb': 50,
            'max_gateways': 1,
            'ai_insights_quota': 100,
            'max_backup_tasks': 5,
            'max_recovery_tasks': 5,
            'max_source_resources': 5,
            'max_policies': 10,
            'max_repositories': 2,
        }
    },
    'pro': {
        'name': 'Professional',
        'valid_days': 365,
        'limits': {
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
    },
    'enterprise': {
        'name': 'Enterprise',
        'valid_days': 365,
        'limits': {
            'max_tenants': 100,
            'max_users': 10000,
            'max_proxies': 500,
            'max_storage_gb': 100000,
            'max_gateways': 50,
            'ai_insights_quota': 100000,
            'max_backup_tasks': 500,
            'max_recovery_tasks': 500,
            'max_source_resources': 500,
            'max_policies': 1000,
            'max_repositories': 100,
        }
    },
    'perpetual': {
        'name': 'Perpetual (Never Expires)',
        'valid_days': 0,  # 0 = perpetual
        'limits': {
            'max_tenants': 999999,
            'max_users': 999999,
            'max_proxies': 999999,
            'max_storage_gb': 999999,
            'max_gateways': 999999,
            'ai_insights_quota': 999999,
            'max_backup_tasks': 999999,
            'max_recovery_tasks': 999999,
            'max_source_resources': 999999,
            'max_policies': 999999,
            'max_repositories': 999999,
        }
    }
}


def sign(data: dict) -> str:
    """
    Sign activation data with shared secret.
    
    IMPORTANT: Must match the verification logic in backend/licenses/crypto.py
    - Use json.dumps with sort_keys=True (no compact separators)
    - Signature = SHA256(json_string + secret_key)
    """
    # Remove signature if present (shouldn't be, but just in case)
    sign_data = {k: v for k, v in data.items() if k != 'signature'}
    
    # Use same serialization as backend
    canonical = json.dumps(sign_data, sort_keys=True)
    
    # Generate signature
    signature = hashlib.sha256((canonical + LICENSE_SECRET_KEY).encode()).hexdigest()
    return signature


def generate_activation_code(
    machine_code: str,
    tier: str = 'pro',
    valid_days: int = None,
    custom_limits: dict = None,
) -> dict:
    """
    Generate activation code.
    
    Args:
        machine_code: Target machine code
        tier: License tier (trial/pro/enterprise/perpetual)
        valid_days: Override default validity days (0 = perpetual)
        custom_limits: Override tier limits
        
    Returns:
        Dict with activation code and details
    """
    if tier not in LICENSE_TIERS:
        raise ValueError(f"Invalid tier: {tier}. Must be one of: {list(LICENSE_TIERS.keys())}")
    
    tier_config = LICENSE_TIERS[tier]
    
    # Use override or tier default
    if valid_days is None:
        valid_days = tier_config['valid_days']
    
    # Use custom limits or tier defaults
    limits = custom_limits or tier_config['limits']
    
    # Generate license key
    now = datetime.now(timezone.utc)
    year = now.year
    random_part = secrets.token_hex(8).upper()
    license_key = f"HFL-{tier.upper()[:3]}-{year}-{random_part}"
    
    # Calculate expiration
    expires_at = None
    if valid_days > 0:
        expires_at = (now + timedelta(days=valid_days)).isoformat()
    
    # Build activation data (order matches backend verification)
    activation_data = {
        "license_key": license_key,
        "machine_code": machine_code,
        "limits": limits,
        "issued_at": now.isoformat(),
        "expires_at": expires_at,
    }
    
    # Sign
    signature = sign(activation_data)
    activation_data["signature"] = signature
    
    # Encode - use same format as backend (no compact separators)
    json_str = json.dumps(activation_data)
    encoded = base64.b64encode(json_str.encode()).decode()
    activation_code = f"HFL-ACT-{encoded}"
    
    return {
        'license_key': license_key,
        'activation_code': activation_code,
        'tier': tier,
        'tier_name': tier_config['name'],
        'machine_code': machine_code,
        'valid_days': valid_days if valid_days > 0 else 'Perpetual',
        'expires_at': expires_at,
        'limits': limits,
        'issued_at': now.isoformat(),
    }


def verify_activation_code(activation_code: str) -> tuple:
    """
    Verify an activation code (for testing purposes).
    
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
        stored_signature = data.pop('signature', None)
        if not stored_signature:
            return False, None, "Missing signature"
        
        data_str = json.dumps(data, sort_keys=True)
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
        
        return True, data, ""
        
    except Exception as e:
        return False, None, f"Failed to verify activation code: {str(e)}"


def main():
    parser = argparse.ArgumentParser(
        description='HyperFileLens License Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate trial license
  python license_generator.py --machine-code HFL-MCH-1234-5678-9ABC-DEF0 --tier trial
  
  # Generate pro license
  python license_generator.py --machine-code HFL-MCH-1234-5678-9ABC-DEF0 --tier pro
  
  # Generate perpetual license
  python license_generator.py --machine-code HFL-MCH-1234-5678-9ABC-DEF0 --tier perpetual
  
  # Custom validity period
  python license_generator.py --machine-code HFL-MCH-1234-5678-9ABC-DEF0 --tier pro --valid-days 730
  
  # Custom limits
  python license_generator.py --machine-code HFL-MCH-1234-5678-9ABC-DEF0 --tier pro --max-users 500 --max-storage-gb 2000
  
  # Verify an activation code
  python license_generator.py --verify "HFL-ACT-..."
"""
    )
    
    parser.add_argument(
        '--machine-code', '-m',
        help='Machine code from customer (format: HFL-MCH-XXXX-XXXX-XXXX-XXXX)'
    )
    
    parser.add_argument(
        '--tier', '-t',
        choices=list(LICENSE_TIERS.keys()),
        default='pro',
        help='License tier (default: pro)'
    )
    
    parser.add_argument(
        '--valid-days', '-d',
        type=int,
        help='Override validity days (0 = perpetual)'
    )
    
    parser.add_argument(
        '--max-users',
        type=int,
        help='Override max users limit'
    )
    
    parser.add_argument(
        '--max-proxies',
        type=int,
        help='Override max proxies limit'
    )
    
    parser.add_argument(
        '--max-storage-gb',
        type=int,
        help='Override max storage limit (GB)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file for activation code (default: print to console)'
    )
    
    parser.add_argument(
        '--verify', '-v',
        help='Verify an activation code'
    )
    
    args = parser.parse_args()
    
    # Verify mode
    if args.verify:
        is_valid, data, error = verify_activation_code(args.verify)
        if is_valid:
            print("=" * 60)
            print("Activation Code Verification: VALID")
            print("=" * 60)
            print(f"\nLicense Key:  {data.get('license_key')}")
            print(f"Machine Code: {data.get('machine_code')}")
            print(f"Issued At:    {data.get('issued_at')}")
            print(f"Expires At:   {data.get('expires_at') or 'Never'}")
            print("\nLimits:")
            for key, value in data.get('limits', {}).items():
                print(f"  {key}: {value}")
        else:
            print("=" * 60)
            print("Activation Code Verification: INVALID")
            print("=" * 60)
            print(f"\nError: {error}")
        return 0 if is_valid else 1
    
    # Generate mode
    if not args.machine_code:
        parser.error("--machine-code is required for generating activation codes")
    
    # Validate machine code format
    if not args.machine_code.startswith('HFL-MCH-'):
        print(f"Error: Invalid machine code format. Expected: HFL-MCH-XXXX-XXXX-XXXX-XXXX")
        return 1
    
    # Build custom limits if provided
    custom_limits = None
    if any([args.max_users, args.max_proxies, args.max_storage_gb]):
        tier_limits = LICENSE_TIERS[args.tier]['limits'].copy()
        if args.max_users:
            tier_limits['max_users'] = args.max_users
        if args.max_proxies:
            tier_limits['max_proxies'] = args.max_proxies
        if args.max_storage_gb:
            tier_limits['max_storage_gb'] = args.max_storage_gb
        custom_limits = tier_limits
    
    # Generate activation code
    try:
        result = generate_activation_code(
            machine_code=args.machine_code,
            tier=args.tier,
            valid_days=args.valid_days,
            custom_limits=custom_limits
        )
        
        output_lines = [
            "=" * 60,
            "HyperFileLens License Generator",
            "=" * 60,
            "",
            f"License Key:    {result['license_key']}",
            f"Tier:           {result['tier_name']}",
            f"Machine Code:   {result['machine_code']}",
            f"Valid Days:     {result['valid_days']}",
            f"Expires At:     {result['expires_at'] or 'Never (Perpetual)'}",
            f"Issued At:      {result['issued_at']}",
            "",
            "Limits:",
        ]
        
        for key, value in result['limits'].items():
            output_lines.append(f"  {key}: {value}")
        
        output_lines.extend([
            "",
            "-" * 60,
            "ACTIVATION CODE:",
            "-" * 60,
            result['activation_code'],
            "-" * 60,
            "",
            "Send the ACTIVATION CODE above to the customer.",
            "The customer will input this code in the License Management page.",
            "",
        ])
        
        output_text = "\n".join(output_lines)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_text)
            print(f"Activation code saved to: {args.output}")
        else:
            print(output_text)
        
        # Verify the generated code
        print("\nVerifying generated code...")
        is_valid, _, error = verify_activation_code(result['activation_code'])
        if is_valid:
            print("✓ Code verification: PASSED")
        else:
            print(f"✗ Code verification: FAILED - {error}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())