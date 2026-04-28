// Repository types
export type RepositoryType = 'local' | 's3' | 'nas' | 'nfs' | 'azure' | 'gcs'
export type RepositoryStatus = 'active' | 'inactive' | 'error' | 'maintenance' | 'initializing'
export type ConnectionStatus = 'connected' | 'disconnected' | 'error' | 'unknown'

export interface RepositoryConfig {
  // Local repository
  path?: string
  
  // S3 compatible
  endpoint?: string
  bucket?: string
  region?: string
  prefix?: string
  use_ssl?: boolean
  url_style?: 'virtual' | 'path'  // S3 URL style: virtual hosted or path style
  
  // S3 credentials (stored in config for simplicity)
  access_key?: string
  secret_key?: string
  
  // NAS / NFS / CIFS
  server?: string
  export_path?: string
  nas_type?: 'nfs' | 'cifs'
  mount_options?: string
  
  // CIFS credentials
  username?: string
  password?: string
  
  // Azure
  account_name?: string
  container?: string
  
  // GCS
  project_id?: string
  bucket_name?: string
}

export interface Repository {
  id: string
  name: string
  description?: string
  repo_type: RepositoryType
  repo_type_display?: string
  status: RepositoryStatus
  status_display?: string
  
  // Connection config
  config?: RepositoryConfig
  
  // Masked credentials (access_key visible, secret_key/password masked)
  credentials_masked?: {
    access_key?: string
    secret_key?: string  // Masked, e.g. "AKIA****AMPLE"
    username?: string
    password?: string    // Always "****"
  }
  
  // Bound node for operations
  bound_node?: string | null
  bound_node_name?: string
  bound_node_status?: string
  
  // Kopia repository state
  kopia_initialized: boolean
  kopia_repository_id?: string
  encryption_algorithm?: string
  
  // Connection status
  last_connection_test?: string
  connection_test_result?: string
  status_message?: string
  
  // Storage stats
  capacity?: number
  capacity_formatted?: string
  used_space?: number
  used_space_formatted?: string
  available_space_formatted?: string
  usage_percentage?: number
  usage_percentage_formatted?: string
  
  // Snapshot stats
  snapshot_count?: number
  last_backup_at?: string
  
  // Flags
  is_ready?: boolean
  supports_compression?: boolean
  supports_encryption?: boolean
  compression_type?: string
  is_readonly?: boolean
  
  // User info
  user?: string
  user_email?: string
  
  // Timestamps
  created_at: string
  updated_at?: string
}

export interface RepositoryCredentials {
  // S3
  access_key?: string
  secret_key?: string
  
  // Azure
  account_key?: string
  
  // GCS
  credentials_json?: string
  
  // NFS/Local (usually empty)
  username?: string
  password?: string
}

export interface RepositoryCreateData {
  name: string
  description?: string
  repo_type: RepositoryType
  config: RepositoryConfig
  credentials?: RepositoryCredentials
  bound_node?: string | null
  capacity?: number
}

export interface RepositoryUpdateData {
  name?: string
  description?: string
  config?: RepositoryConfig
  credentials?: RepositoryCredentials
  bound_node?: string | null
  status?: RepositoryStatus
}

export interface RepositoryStats {
  total: number
  active: number
  initialized: number
  total_capacity: number
  total_used: number
}

// Directory info for local path browsing
export interface DirectoryInfo {
  name: string
  path: string
  is_dir: boolean
  size?: number
  modified?: string
}
