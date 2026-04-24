// Backup task types
export type BackupType = 'full' | 'incremental' | 'differential'
export type BackupStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type BackupPriority = 'low' | 'normal' | 'high' | 'critical'

export interface BackupTask {
  id: number
  task_id: string
  name: string
  node: number
  node_name?: string
  repository: number
  repository_name?: string
  source_path: string
  backup_type: BackupType
  status: BackupStatus
  priority: BackupPriority
  schedule?: number
  schedule_name?: string
  snapshot_id?: string
  files_total?: number
  files_processed?: number
  bytes_total?: number
  bytes_processed?: number
  progress_percent?: number
  estimated_completion?: string
  error_message?: string
  started_at?: string
  completed_at?: string
  created_at: string
  updated_at: string
  owner: number
  metadata: Record<string, any>
}

export interface BackupTaskCreateData {
  name: string
  node: number
  repository: number
  source_path: string
  backup_type: BackupType
  priority?: BackupPriority
  schedule?: number
  metadata?: Record<string, any>
}

export interface BackupTaskUpdateData {
  name?: string
  status?: BackupStatus
  priority?: BackupPriority
  schedule?: number
  metadata?: Record<string, any>
}

export interface BackupTaskStats {
  total_tasks: number
  pending_tasks: number
  running_tasks: number
  completed_tasks: number
  failed_tasks: number
  total_size_bytes: number
  total_files: number
}
