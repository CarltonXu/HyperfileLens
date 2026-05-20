import type { BackupTask } from "@/types/backup";

const ACTIVE_STATUSES = new Set([
  "pending",
  "queued",
  "dispatched",
  "running",
  "paused",
]);

function numericValue(task: BackupTask, keys: Array<keyof BackupTask>) {
  for (const key of keys) {
    const value = task[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
  }
  return 0;
}

export function backupTaskProgressPercent(task: BackupTask) {
  const raw =
    typeof task.progress_percent === "number"
      ? task.progress_percent
      : typeof task.progress === "number"
        ? task.progress
        : task.status === "completed"
          ? 100
          : 0;
  return Math.max(0, Math.min(100, Math.round(raw)));
}

export function backupTaskProcessedFiles(task: BackupTask) {
  return numericValue(task, ["backed_up_files", "processed_files"]);
}

export function backupTaskTotalFiles(task: BackupTask) {
  return numericValue(task, ["total_files"]);
}

export function backupTaskProcessedBytes(task: BackupTask) {
  return numericValue(task, ["backed_up_size", "processed_bytes"]);
}

export function backupTaskTotalBytes(task: BackupTask) {
  return numericValue(task, ["total_size", "total_bytes"]);
}

export function backupTaskSpeedBytesPerSecond(task: BackupTask) {
  const direct = numericValue(task, ["bytes_per_second"]);
  if (direct > 0) return direct;
  const speedMbps = numericValue(task, ["speed_mbps"]);
  return speedMbps > 0 ? speedMbps * 1024 * 1024 : 0;
}

export function backupTaskEtaSeconds(task: BackupTask) {
  if (task.estimated_completion_at) {
    const diff =
      new Date(task.estimated_completion_at).getTime() - new Date().getTime();
    if (Number.isFinite(diff) && diff > 0) return Math.ceil(diff / 1000);
  }

  const speed = backupTaskSpeedBytesPerSecond(task);
  const totalBytes = backupTaskTotalBytes(task);
  const processedBytes = backupTaskProcessedBytes(task);
  if (speed <= 0 || totalBytes <= 0 || processedBytes <= 0) return null;

  const remaining = Math.max(0, totalBytes - processedBytes);
  return Math.ceil(remaining / speed);
}

export function isBackupTaskActive(task: BackupTask) {
  return ACTIVE_STATUSES.has(task.status);
}

export function hasBackupTaskProgress(task: BackupTask) {
  return (
    isBackupTaskActive(task) ||
    backupTaskProgressPercent(task) > 0 ||
    backupTaskProcessedFiles(task) > 0 ||
    backupTaskProcessedBytes(task) > 0 ||
    task.status === "completed" ||
    task.status === "partial" ||
    task.status === "failed"
  );
}
