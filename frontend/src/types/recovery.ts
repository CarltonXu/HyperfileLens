// Recovery task types
export type RecoveryType = 'original_location' | 'new_location' | 'browse'
export type RecoveryStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type RecoveryPriority = 'low' | 'normal' | 'high' | 'critical'

export interface RecoveryTask {
  id: number
  task_id: string
  name: string
  node: number
  node_name?: string
  repository: number
  repository_name?: string
  backup_task?: number
  snapshot_id: string
  recovery_type: RecoveryType
  target_path: string
  status: RecoveryStatus
  priority: RecoveryPriority
  files_total?: number
  files_processed?: number
  bytes_total?: number
  bytes_processed?: number
  progress_percent?: number
  error_message?: string
  started_at?: string
  completed_at?: string
  created_at: string
  updated_at: string
  owner: number
  metadata: Record<string, any>
}

export interface RecoveryTaskCreateData {
  name: string
  node: number
  repository: number
  backup_task?: number
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
  source_path: string
  snapshot_time: string
  files_total: number
  size_bytes: number
  description?: string
  tags: Record<string, any>
  manifests?: SnapshotManifest[]
}

export interface SnapshotManifest {
  path: string
  type: 'file' | 'directory'
  size?: number
  modified?: string
  permissions?: string
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
