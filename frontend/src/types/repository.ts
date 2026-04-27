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
  repository_type: RepositoryType
  status: RepositoryStatus
  
  // Connection config
  config?: RepositoryConfig
  
  // Credentials (encrypted, not returned in API usually)
  credentials?: {
    access_key?: string
    secret_key?: string
    username?: string
    password?: string
    account_key?: string
    credentials_json?: string
  }
  
  // Bound node for operations
  bound_node?: string | null
  bound_node_name?: string
  
  // Kopia repository state
  kopia_initialized: boolean
  kopia_repository_id?: string
  
  // Connection status (reported by node)
  connection_status: ConnectionStatus
  last_connection_test?: string
  connection_error?: string
  
  // Storage stats
  capacity: number
  used_space: number
  
  // Timestamps
  created_at: string
  updated_at: string
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
  repository_type: RepositoryType
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
