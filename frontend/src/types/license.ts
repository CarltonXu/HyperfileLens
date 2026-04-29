/**
 * License types for product authorization
 */

export interface License {
  id: string;
  license_key: string;
  name: string;
  licensee_name: string;
  licensee_email: string;
  licensee_company?: string;
  product: string;
  edition: 'community' | 'pro' | 'enterprise';
  license_type: 'trial' | 'standard' | 'professional' | 'enterprise';
  version: string;
  issued_at: string;
  starts_at: string;
  expires_at?: string;
  max_tenants: number;
  max_users: number;
  max_users_per_tenant: number;
  max_proxies: number;
  max_proxies_per_tenant: number;
  max_repositories: number;
  max_repositories_per_tenant: number;
  max_storage_gb: number;
  features: string[] | Record<string, boolean>;
  modules: string[];
  status: 'active' | 'expired' | 'revoked' | 'trial' | 'valid' | 'invalid';
  is_valid: boolean;
  days_until_expiry: number;
  days_remaining?: number;
  is_perpetual: boolean;
  tenant?: string;
  tenant_name?: string;
  created_at: string;
  updated_at: string;
}

export interface LicenseLimits {
  max_tenants: number;
  max_users: number;
  max_users_per_tenant: number;
  max_proxies: number;
  max_proxies_per_tenant: number;
  max_repositories: number;
  max_repositories_per_tenant: number;
  max_storage_gb: number;
}

export interface LicenseStatus {
  is_valid: boolean;
  edition: string;
  licensee_name: string;
  expires_at?: string;
  days_until_expiry: number;
  features: Record<string, boolean>;
  limits: LicenseLimits;
  warnings: string[];
}

export interface LicenseAuditLog {
  id: string;
  license: string;
  license_key: string;
  event_type: 'created' | 'activated' | 'expired' | 'revoked' | 'renewed' | 'verified' | 'failed';
  message: string;
  details: Record<string, unknown>;
  ip_address?: string;
  created_at: string;
}

export interface CreateLicenseRequest {
  name: string;
  license_key: string;
}

export type LicenseEdition = 'community' | 'pro' | 'enterprise';
