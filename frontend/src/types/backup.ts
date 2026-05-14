export type BackupType = "full" | "incremental" | "differential";
export type BackupStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "paused";
export type BackupPriority = "low" | "normal" | "high";

export interface BackupTask {
  id: string;
  name: string;
  description?: string;
  source_resource?: string;
  source_resource_name?: string;
  source_resource_type?: string;
  target_repository?: string;
  target_repository_name?: string;
  target_repository_type?: string;
  execution_node_name?: string;
  schedule_name?: string;
  task_type: BackupType;
  priority: BackupPriority;
  is_enabled?: boolean;
  status: BackupStatus;
  progress?: number;
  progress_percent?: number;
  backup_paths?: string[];
  exclude_patterns?: string[];
  include_patterns?: string[];
  compression_enabled?: boolean;
  compression_type?: string;
  encryption_enabled?: boolean;
  schedule?: string | null;
  next_run_time?: string | null;
  last_run_time?: string | null;
  retention_days?: number;
  max_snapshots?: number;
  status_message?: string;
  error_message?: string;
  total_files?: number;
  backed_up_files?: number;
  total_size?: number;
  backed_up_size?: number;
  skipped_files?: number;
  failed_files?: number;
  bytes_per_second?: number;
  bandwidth_limit_kbps?: number | null;
  enable_checkpoint?: boolean;
  checkpoint_interval_minutes?: number;
  compression_level?: number;
  max_concurrent_files?: number;
  verify_checksum?: boolean;
  max_retries?: number;
  retry_count?: number;
  estimated_completion_at?: string | null;
  duration_formatted?: string;
  snapshot_count?: number;
  created_at: string;
  updated_at?: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface BackupTaskCreateData {
  name: string;
  description?: string;
  source_resource: string;
  target_repository: string;
  task_type: BackupType;
  priority?: BackupPriority;
  backup_paths: string[];
  exclude_patterns?: string[];
  include_patterns?: string[];
  compression_enabled?: boolean;
  compression_type?: string;
  encryption_enabled?: boolean;
  schedule?: string | null;
  retention_days?: number;
  max_snapshots?: number;
}

export interface BackupTaskUpdateData {
  name?: string;
  description?: string;
  backup_paths?: string[];
  exclude_patterns?: string[];
  include_patterns?: string[];
  compression_enabled?: boolean;
  compression_type?: string;
  encryption_enabled?: boolean;
  schedule?: string | null;
  retention_days?: number;
  max_snapshots?: number;
  priority?: BackupPriority;
  is_enabled?: boolean;
  bandwidth_limit_kbps?: number | null;
  enable_checkpoint?: boolean;
  checkpoint_interval_minutes?: number;
  compression_level?: number;
  max_concurrent_files?: number;
  verify_checksum?: boolean;
  max_retries?: number;
}

export interface BackupTaskStats {
  total_tasks: number;
  pending_tasks: number;
  running_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  cancelled_tasks?: number;
  total_size?: number;
  total_size_bytes?: number;
  total_files: number;
  avg_duration?: number | null;
}
