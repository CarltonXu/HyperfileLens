/**
 * License types for HyperFileLens
 * 
 * Simplified License model - only quantity limits, no feature restrictions
 */

export interface License {
  id: string;
  license_key: string;
  machine_code: string;
  
  // Binding
  tenant: string;
  tenant_name: string;
  activated_by: string;
  activated_by_name: string;
  
  // Quantity limits
  max_tenants: number;
  max_users: number;
  max_proxies: number;
  max_storage_gb: number;
  max_gateways: number;
  ai_insights_quota: number;
  max_backup_tasks: number;
  max_recovery_tasks: number;
  max_source_resources: number;
  max_policies: number;
  max_repositories: number;
  
  // Time
  issued_at: string;
  expires_at?: string;
  activated_at: string;
  
  // Status
  status: 'active' | 'expired' | 'revoked';
  is_valid: boolean;
  is_expired: boolean;
  is_perpetual: boolean;
  days_until_expiry: number;
}

export interface QuotaUsage {
  users_count: number;
  proxies_count: number;
  storage_used_gb: number;
  gateways_count: number;
  backup_tasks_count: number;
  recovery_tasks_count: number;
  source_resources_count: number;
  policies_count: number;
  repositories_count: number;
  ai_insights_used: number;
  ai_insights_period: string;
  ai_insights_reset_at?: string;
  updated_at: string;
}

export interface MachineCodeResponse {
  machine_code: string;
  components: {
    mac_address: string;
    cpu_id: string;
    hostname: string;
    tenant_id: string;
    tenant_name: string;
  };
  instructions: string;
}

export interface ActivateRequest {
  activation_code: string;
}

export interface ActivateResponse {
  success: boolean;
  message: string;
  license: License;
}

export interface LicenseUsageResponse {
  license: License;
  limits: Record<string, number>;
  usage: QuotaUsage;
  usage_percentage: Record<string, number>;
}
