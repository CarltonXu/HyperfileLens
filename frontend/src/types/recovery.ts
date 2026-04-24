// Recovery task types
export type RecoveryType = 'original' | 'original_location' | 'new_location' | 'browse'
export type RecoveryStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type RecoveryPriority = 'low' | 'normal' | 'high' | 'critical'

export interface RecoveryTask {
  id: string
  name: string
  description?: string
  snapshot?: string
  snapshot_id?: string
  snapshot_name?: string
  target_node?: number
  target_node_name?: string
  target_node_id?: number
  recovery_type: RecoveryType
  target_path: string
  file_patterns?: string[]
  exclude_patterns?: string[]
  status: RecoveryStatus
  priority?: RecoveryPriority
  progress?: number
  progress_percent?: number
  error_message?: string
  user?: number
  user_email?: string
  started_at?: string
  completed_at?: string
  created_at: string
  updated_at: string
  total_files?: number
  restored_files?: number
  total_size?: number
  restored_size?: number
  skipped_files?: number
  failed_files?: number
  metadata?: Record<string, any>
}

export interface RecoveryTaskCreateData {
  name: string
  node: number
  repository: number
  snapshot_id: string
  recovery_type: RecoveryType
  target_path: string
  priority?: RecoveryPriority
  metadata?: Record<string, any>
}

export interface RecoveryTaskUpdateData {
  name?: string
  status?: RecoveryStatus
  priority?: RecoveryPriority
  metadata?: Record<string, any>
}

export interface SnapshotInfo {
  id: string
  name?: string
  source_path?: string
  snapshot_time: string
  files_total?: number
  size_bytes?: number
  total_size?: number
  file_count?: number
  description?: string
  tags?: Record<string, any>
  manifests?: SnapshotManifest[]
}

export interface SnapshotManifest {
  path: string
  type: 'file' | 'directory'
  size?: number
  modified?: string
  permissions?: string
}

// Backend returns these field names
export interface RecoveryTaskStatsBackend {
  total: number
  pending: number
  running: number
  completed: number
  failed: number
}

export interface RecoveryTaskStats {
  total_tasks: number
  pending_tasks: number
  running_tasks: number
  completed_tasks: number
  failed_tasks: number
  total_size_bytes: number
  total_files: number
}
