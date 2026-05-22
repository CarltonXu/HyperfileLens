// Recovery task types
export type RecoveryType = 'original' | 'new_location' | 'export'
export type RecoveryStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused'
export type RecoveryPriority = 'low' | 'normal' | 'high' | 'critical'
export type RecoveryScope = 'entire_snapshot' | 'selected_paths'
export type RecoveryConflictPolicy = 'skip' | 'overwrite' | 'rename'

export interface RecoveryTask {
  id: string
  name: string
  description?: string
  snapshot?: string
  snapshot_id?: string
  snapshot_name?: string
  target_node?: number | string
  target_node_name?: string
  target_node_status?: string
  target_node_id?: number | string
  repository_id?: string
  repository_name?: string
  backup_task_name?: string
  snapshot_storage_path?: string
  snapshot_manifest_path?: string
  snapshot_status?: string
  snapshot_size?: number
  snapshot_file_count?: number
  snapshot_created_at?: string
  snapshot_source_path?: string
  recovery_type: RecoveryType
  target_path: string
  restore_scope?: RecoveryScope
  selected_paths?: string[]
  conflict_policy?: RecoveryConflictPolicy
  file_patterns?: string[]
  exclude_patterns?: string[]
  status: RecoveryStatus
  priority?: RecoveryPriority
  progress?: number
  progress_percent?: number
  error_message?: string
  status_message?: string
  current_file?: string
  speed_mbps?: number
  eta?: string
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

export interface RecoveryRun {
  id: string
  task: string
  task_name?: string
  proxy_task?: string
  proxy_task_status?: string
  snapshot?: string
  snapshot_name?: string
  target_node?: string
  target_node_name?: string
  trigger_type: 'manual' | 'retry' | 'precheck'
  status: RecoveryStatus | 'dispatched'
  progress: number
  message?: string
  error_message?: string
  parameters?: Record<string, any>
  result?: Record<string, any>
  current_file?: string
  total_files?: number
  restored_files?: number
  total_size?: number
  restored_size?: number
  skipped_files?: number
  failed_files?: number
  speed_mbps?: number
  eta?: string
  created_at: string
  dispatched_at?: string
  started_at?: string
  completed_at?: string
  duration?: number
}

export interface RecoveryTaskCreateData {
  name: string
  description?: string
  node: number | string
  repository: number | string
  snapshot_id: string
  recovery_type: RecoveryType
  target_path: string
  restore_scope?: RecoveryScope
  selected_paths?: string[]
  conflict_policy?: RecoveryConflictPolicy
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
  task?: string
  task_name?: string
  name?: string
  source_path?: string
  snapshot_time?: string
  created_at?: string
  files_total?: number
  size_bytes?: number
  total_size?: number
  file_count?: number
  description?: string
  metadata?: Record<string, any>
  snapshot_status?: string
  retention_reasons?: string[]
  last_synced_at?: string
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
  total_files?: number
  total_size?: number
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
