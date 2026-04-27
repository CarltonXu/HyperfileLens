// Repository types
export type RepositoryType = 'local' | 's3' | 'nas' | 'nfs' | 'azure' | 'gcs'
export type RepositoryStatus = 'active' | 'inactive' | 'error' | 'maintenance' | 'initializing'
export type ConnectionStatus = 'connected' | 'disconnected' | 'error' | 'unknown'

export interface Repository {
  id: string
  name: string
  description?: string
  repository_type: RepositoryType
  status: RepositoryStatus
  
  // Connection config
  config: RepositoryConfig
  
  // Credentials (encrypted, not returned in API usually)
  credentials?: RepositoryCredentials
  
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

export interface RepositoryConfig {
  // Local repository
  path?: string
  
  // S3 compatible
  endpoint?: string
  bucket?: string
  region?: string
  
  // NFS
  server?: string
  export_path?: string
  
  // Azure
  account_name?: string
  container?: string
  
  // GCS
  project_id?: string
  bucket_name?: string
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
