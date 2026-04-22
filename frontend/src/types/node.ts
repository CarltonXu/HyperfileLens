// Node types
export type NodeType = 'source_proxy' | 'target_gateway'
export type NodeStatus = 'pending' | 'active' | 'inactive' | 'error' | 'maintenance'
export type OperatingSystem = 'windows' | 'linux' | 'macos'

export interface Node {
  id: number
  node_id: string
  name: string
  node_type: NodeType
  hostname: string
  port: number
  protocol: string
  operating_system: OperatingSystem
  version?: string
  cpu_cores?: number
  memory_total?: number
  disk_total?: number
  status: NodeStatus
  last_heartbeat?: string
  heartbeat_interval: number
  capabilities: Record<string, any>
  tags: Record<string, any>
  metadata: Record<string, any>
  created_at: string
  updated_at: string
  registered_at?: string
  owner?: number
  is_online?: boolean
  uptime_seconds?: number
  heartbeat_count?: number
}

export interface NodeCreateData {
  name: string
  node_type: NodeType
  hostname: string
  port?: number
  protocol?: string
  operating_system: OperatingSystem
  heartbeat_interval?: number
  tags?: Record<string, any>
  metadata?: Record<string, any>
}

export interface NodeHeartbeat {
  id: number
  timestamp: string
  cpu_usage?: number
  memory_usage?: number
  disk_usage?: number
  network_in?: number
  network_out?: number
  active_tasks: number
  metadata?: Record<string, any>
}

export interface NodeConnection {
  id: number
  connection_id: string
  node: number
  node_name: string
  status: 'connected' | 'disconnected' | 'error'
  remote_address?: string
  user_agent: string
  connected_at: string
  disconnected_at?: string
  last_message_at?: string
  message_count: number
}

export interface NodeStats {
  total_nodes: number
  online_nodes: number
  offline_nodes: number
  nodes_by_type: Record<NodeType, number>
  nodes_by_status: Record<NodeStatus, number>
  average_uptime: number
}
