// Repository types
export type RepositoryType = 'local' | 's3' | 'azure' | 'gcs' | 'nfs' | 'smb'
export type RepositoryStatus = 'active' | 'inactive' | 'error' | 'syncing'
export type RepositoryHealthStatus = 'healthy' | 'warning' | 'critical' | 'unknown'

export interface Repository {
  id: number
  repository_id: string
  name: string
  description?: string
  repository_type: RepositoryType
  status: RepositoryStatus
  health_status: RepositoryHealthStatus
  config: RepositoryConfig
  capacity_bytes?: number
  used_bytes?: number
  available_bytes?: number
  snapshot_count?: number
  total_size_bytes?: number
  last_snapshot_at?: string
  node?: number
  node_name?: string
  owner: number
  is_default?: boolean
  is_encrypted?: boolean
  encryption_algorithm?: string
  compression_enabled?: boolean
  compression_algorithm?: string
  retention_policy?: RetentionPolicy
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface RepositoryConfig {
  // Local repository
  path?: string
  
  // S3 compatible
  endpoint?: string
  bucket?: string
  region?: string
  access_key?: string
  secret_key?: string
  
  // NFS/SMB
  host?: string
  share_path?: string
  
  // Common
  username?: string
  password?: string
  tls_enabled?: boolean
  verify_ssl?: boolean
  bandwidth_limit?: number
}

export interface RetentionPolicy {
  retention_days?: number
  retention_weeks?: number
  retention_months?: number
  retention_years?: number
  keep_daily?: number
  keep_weekly?: number
  keep_monthly?: number
  keep_yearly?: number
}

export interface RepositoryCreateData {
  name: string
  description?: string
  repository_type: RepositoryType
  config: RepositoryConfig
  capacity_bytes?: number
  is_default?: boolean
  retention_policy?: RetentionPolicy
  metadata?: Record<string, any>
}

export interface RepositoryUpdateData {
  name?: string
  description?: string
  status?: RepositoryStatus
  config?: RepositoryConfig
  capacity_bytes?: number
  retention_policy?: RetentionPolicy
  metadata?: Record<string, any>
}

export interface RepositoryStats {
  total_repositories: number
  active_repositories: number
  total_capacity_bytes: number
  used_capacity_bytes: number
  available_capacity_bytes: number
  total_snapshots: number
  total_size_bytes: number
}

export interface RepositoryHealth {
  repository_id: number
  status: RepositoryHealthStatus
  last_check: string
  issues: RepositoryIssue[]
}

export interface RepositoryIssue {
  severity: 'info' | 'warning' | 'error'
  code: string
  message: string
  details?: Record<string, any>
}
