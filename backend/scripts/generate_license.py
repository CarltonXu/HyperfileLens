#!/usr/bin/env python3
"""
License Generation Tool for HyperFileLens

This script generates license keys for customers.
It should be run OFFLINE and the private key should be kept secure.

Usage:
    python generate_license.py --edition enterprise --name "Company Name" --email "admin@company.com" --days 365 --tenants 10 --users 100

DO NOT distribute this script or the private key to customers.
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta

# Add the backend to path
sys.path.insert(0, '/workspace/projects/backend')

# Import crypto functions
# In production, use: from licenses.crypto import create_license_for_customer
# We'll implement a simple version here

import hashlib
import base64
import secrets


def generate_license_key(edition: str) -> str:
    """Generate a unique license key."""
    year = datetime.now().year
    random_part = secrets.token_hex(8).upper()
    return f"HFL-{edition.upper()[:3]}-{year}-{random_part}"


def calculate_checksum(data: dict) -> str:
    """Calculate SHA256 checksum of license data."""
    critical_fields = {
        "license_key": data.get("license_key"),
        "edition": data.get("edition"),
        "limits": data.get("limits"),
        "starts_at": data.get("starts_at"),
        "expires_at": data.get("expires_at"),
        "machine_id": data.get("machine_id"),
    }
    
    import json
    serialized = json.dumps(critical_fields, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode()).hexdigest()


def sign_license(data: dict, private_key: str = "SECRET_KEY_DO_NOT_SHARE") -> str:
    """Sign license with private key."""
    checksum = calculate_checksum(data)
    signature_input = checksum + private_key
    signature = hashlib.sha256(signature_input.encode()).hexdigest()
    return base64.b64encode(signature.encode()).decode()


def generate_license(
    name: str,
    email: str,
    edition: str,
    tenants: int = 1,
    users: int = 10,
    proxies: int = 5,
    repositories: int = 5,
    storage: int = 100,
    days: int = 365,
    machine_id: str = None,
):
    """Generate a license."""
    
    now = datetime.now(timezone.utc)
    
    license_data = {
        "version": "1.0",
        "license_key": generate_license_key(edition),
        "licensee": {
            "name": name,
            "email": email,
        },
        "product": "HyperFileLens",
        "edition": edition,
        "limits": {
            "max_tenants": tenants,
            "max_users_per_tenant": users,
            "max_proxies_per_tenant": proxies,
            "max_repositories_per_tenant": repositories,
            "max_storage_gb": storage,
        },
        "features": {
            "ai_query": edition in ["pro", "enterprise"],
            "advanced_backup": edition in ["pro", "enterprise"],
            "advanced_recovery": edition in ["pro", "enterprise"],
            "policy_management": edition in ["pro", "enterprise"],
            "audit_log": edition in ["pro", "enterprise"],
        },
        "issued_at": now.isoformat(),
        "starts_at": now.isoformat(),
        "expires_at": (now + timedelta(days=days)).isoformat() if days > 0 else None,
        "machine_id": machine_id,
    }
    
    # Sign the license
    signature = sign_license(license_data)
    
    # Combine data and signature
    combined = {
        "data": license_data,
        "signature": signature,
    }
    
    # Encode for distribution
    serialized = json.dumps(combined, sort_keys=True)
    encoded = base64.b64encode(serialized.encode()).decode()
    
    # Format as license string (no truncation)
    chunks = [encoded[i:i+16] for i in range(0, len(encoded), 16)]
    license_string = "HFL-LICENSE-" + "-".join(chunks)
    
    return {
        "license_key": license_data["license_key"],
        "license_string": license_string,
        "data": license_data,
        "signature": signature,
    }


def print_license(result: dict, output_file: str = None):
    """Print and optionally save the license."""
    
    print("\n" + "=" * 70)
    print("                    HYPERFILELENS LICENSE")
    print("=" * 70)
    print(f"\nLicense Key:     {result['license_key']}")
    print(f"Edition:         {result['data']['edition'].upper()}")
    print(f"Licensee:        {result['data']['licensee']['name']}")
    print(f"Email:           {result['data']['licensee']['email']}")
    print(f"\nValid From:      {result['data']['starts_at'][:10]}")
    print(f"Valid Until:     {result['data']['expires_at'][:10] if result['data']['expires_at'] else 'Perpetual'}")
    print(f"\nResource Limits:")
    print(f"  - Tenants:     {result['data']['limits']['max_tenants']}")
    print(f"  - Users/Tenant: {result['data']['limits']['max_users_per_tenant']}")
    print(f"  - Proxies/Tenant: {result['data']['limits']['max_proxies_per_tenant']}")
    print(f"  - Repositories: {result['data']['limits']['max_repositories_per_tenant']}")
    print(f"  - Storage (GB): {result['data']['limits']['max_storage_gb']}")
    print(f"\nFeatures:")
    for feature, enabled in result['data']['features'].items():
        status = "✓" if enabled else "✗"
        print(f"  [{status}] {feature}")
    print("\n" + "-" * 70)
    print("LICENSE STRING (Copy and send to customer):")
    print("-" * 70)
    print(result['license_string'])
    print("=" * 70 + "\n")
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"License saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate HyperFileLens License',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a 1-year Enterprise license
  python generate_license.py --edition enterprise --name "Acme Corp" --email "admin@acme.com" --tenants 10 --users 100

  # Generate a trial license
  python generate_license.py --edition community --name "Test User" --email "test@example.com" --days 30

  # Generate a perpetual license
  python generate_license.py --edition enterprise --name "Corp" --email "admin@corp.com" --days 0
        """
    )
    
    parser.add_argument('--name', required=True, help='Licensee name')
    parser.add_argument('--email', required=True, help='Licensee email')
    parser.add_argument('--edition', required=True, 
                       choices=['community', 'pro', 'enterprise'],
                       help='License edition')
    parser.add_argument('--tenants', type=int, default=1, help='Max tenants (default: 1)')
    parser.add_argument('--users', type=int, default=10, help='Max users per tenant (default: 10)')
    parser.add_argument('--proxies', type=int, default=5, help='Max proxies per tenant (default: 5)')
    parser.add_argument('--repositories', type=int, default=5, help='Max repositories per tenant (default: 5)')
    parser.add_argument('--storage', type=int, default=100, help='Max storage in GB (default: 100)')
    parser.add_argument('--days', type=int, default=365, help='Validity in days (0 = perpetual, default: 365)')
    parser.add_argument('--machine-id', help='Bind to specific machine fingerprint')
    parser.add_argument('--output', '-o', help='Output file for license JSON')
    
    args = parser.parse_args()
    
    # Generate license
    result = generate_license(
        name=args.name,
        email=args.email,
        edition=args.edition,
        tenants=args.tenants,
        users=args.users,
        proxies=args.proxies,
        repositories=args.repositories,
        storage=args.storage,
        days=args.days,
        machine_id=args.machine_id,
    )
    
    print_license(result, args.output)


if __name__ == '__main__':
    main()
