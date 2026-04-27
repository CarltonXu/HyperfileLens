// Proxy Node Types

// Alias for backward compatibility
export type { ProxyNode as Proxy }

export interface ProxyNode {
  id: string
  name: string
  role: 'agent' | 'sync'
  status: 'active' | 'pending' | 'offline' | 'error' | 'maintenance' | 'installing'
  
  // Owner info
  owner: string | null
  owner_name: string | null
  
  // Connection info
  hostname: string | null
  internal_ip: string | null
  
  // System info
  os: string | null
  os_version: string | null
  operating_system: string | null
  cpu_cores: number | null
  total_memory: number | null
  total_disk: number | null
  
  // Resource usage
  cpu_usage: number | null
  memory_usage: number | null
  disk_usage: number | null
  
  // Status info
  is_online: boolean
  last_heartbeat: string | null
  uptime_seconds: number | null
  
  // Version info
  version: string | null
  kopia_version: string | null
  
  // Configuration
  heartbeat_interval: number
  capabilities: Record<string, boolean>
  labels: string[]
  tags: Record<string, string>
  
  // Installation info (only for pending status)
  api_token: string | null
  install_token: string | null
  install_command: string | null
  install_token_used: boolean
  
  // Timestamps
  created_at: string
  updated_at: string
  registered_at: string | null
}

export interface ProxyStats {
  total_proxies: number
  online_proxies: number
  agent_proxies: number
  sync_proxies: number
  by_status: Record<string, number>
  by_os: Record<string, number>
}

export interface ProxyTask {
  id: string
  proxy: string
  task_id: string
  task_type: 'backup' | 'restore' | 'mount' | 'snapshot_list' | 'verify' | 'cleanup'
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  error_message: string | null
  duration_seconds: number | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface ProxyHeartbeat {
  id: string
  proxy: string
  cpu_usage: number | null
  memory_usage: number | null
  disk_usage: number | null
  uptime_seconds: number | null
  network_rx_bytes: number | null
  network_tx_bytes: number | null
  active_tasks: number
  created_at: string
}

export interface GenerateInstallCommandRequest {
  name: string
  role: 'agent' | 'sync'
  os: 'linux' | 'windows' | 'macos'
  labels?: string[]
}

export interface GenerateInstallCommandResponse {
  proxy_id: string
  name: string
  role: string
  install_token: string
  api_token: string
  install_command: string
  windows_command: string
  config_yaml: string
  expires_at: string
}

export interface ProxyCreateData {
  name: string
  role: 'agent' | 'sync'
  hostname?: string
  heartbeat_interval?: number
  labels?: string[]
  tags?: Record<string, string>
}

export interface ProxyUpdateData {
  name?: string
  hostname?: string
  heartbeat_interval?: number
  labels?: string[]
  tags?: Record<string, string>
  capabilities?: Record<string, boolean>
}
