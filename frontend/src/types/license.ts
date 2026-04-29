/**
 * License type definitions
 */

export interface License {
  id: number
  tenant: number
  tenant_name?: string
  license_key: string
  machine_code: string
  issued_at: string
  expires_at: string | null
  is_perpetual: boolean
  is_valid: boolean
  days_until_expiry: number
  
  // Quota limits
  max_tenants: number
  max_users: number
  max_proxies: number
  max_storage_gb: number
  max_gateways: number
  ai_insights_quota: number
  max_backup_tasks: number
  max_recovery_tasks: number
  max_source_resources: number
  max_policies: number
  max_repositories: number
  
  created_at: string
  updated_at: string
}

export interface LicenseHistory {
  id: string
  tenant: string
  license_key: string
  version: number
  machine_code: string
  
  // Quota limits (snapshot at archive time)
  max_tenants: number
  max_users: number
  max_proxies: number
  max_storage_gb: number
  max_gateways: number
  ai_insights_quota: number
  max_backup_tasks: number
  max_recovery_tasks: number
  max_source_resources: number
  max_policies: number
  max_repositories: number
  
  // Timestamps
  issued_at: string
  expires_at: string | null
  is_perpetual: boolean
  activated_at: string | null
  archived_at: string
  
  // Status and change info
  status: string
  change_type: 'initial' | 'renewal' | 'upgrade' | 'downgrade' | 'expired'
  change_reason: string | null
  
  // Audit info
  changed_by: string | null
  ip_address: string | null
}

export interface MachineCode {
  machine_code: string
  tenant_name: string
  created_at?: string
  message?: string
}

export interface LicenseUsage {
  tenants_count: number
  users_count: number
  proxies_count: number
  storage_used_gb: number
  gateways_count: number
  ai_insights_used: number
  backup_tasks_count: number
  recovery_tasks_count: number
  source_resources_count: number
  policies_count: number
  repositories_count: number
}

export interface LicenseCurrentResponse {
  is_valid: boolean
  license?: License
  limits?: Record<string, number>
  usage: LicenseUsage
  machine_code: string
  message?: string
  days_until_expiry?: number
}

export interface ActivateLicenseRequest {
  activation_code: string
}

export interface ActivateLicenseResponse {
  success: boolean
  message: string
  license: License
  change_type: string
}

export interface LicenseHistoryResponse {
  results: LicenseHistory[]
  count: number
}
