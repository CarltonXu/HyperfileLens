import { computed, ref, type Ref } from "vue";
import { backupTasksApi } from "@/api";
import { getApiErrorMessage } from "@/utils/errors";
import type { BackupTask, BackupTaskUpdateData } from "@/types/backup";

type Translate = (key: string, params?: Record<string, any>) => string;
type AppStore = {
  error: (message: string) => void;
  showToast: (toast: {
    type: "error" | "success" | "warning" | "info";
    title: string;
    message: string;
  }) => string;
};

export type EditTaskForm = {
  name: string;
  description: string;
  priority: "low" | "normal" | "high";
  is_enabled: boolean;
  execution_mode: "pinned" | "preferred" | "auto";
  preferred_execution_node: string | null;
  schedule: string | null;
  override_schedule: boolean;
  schedule_mode: "manual" | "interval" | "time" | "cron";
  interval: string;
  time_of_day: string;
  cron_expression: string;
  retention_mode: "policy" | "custom";
  retention_days: number;
  max_snapshots: number;
  keep_latest: number;
  keep_hourly: number;
  keep_daily: number;
  keep_weekly: number;
  keep_monthly: number;
  keep_annual: number;
  backup_paths_text: string;
  exclude_patterns_text: string;
  dot_ignore_files_text: string;
  one_file_system: boolean;
  ignore_file_errors: boolean;
  ignore_dir_errors: boolean;
  compression_enabled: boolean;
  compression_type: string;
  compression_level: number;
  encryption_enabled: boolean;
  verify_checksum: boolean;
  enable_checkpoint: boolean;
  checkpoint_interval_minutes: number;
  max_concurrent_files: number;
  bandwidth_limit_kbps: number | null;
  max_retries: number;
};

function createEditForm(): EditTaskForm {
  return {
    name: "",
    description: "",
    priority: "normal",
    is_enabled: true,
    execution_mode: "pinned",
    preferred_execution_node: null,
    schedule: null,
    override_schedule: false,
    schedule_mode: "manual",
    interval: "24h",
    time_of_day: "02:00",
    cron_expression: "",
    retention_mode: "custom",
    retention_days: 30,
    max_snapshots: 10,
    keep_latest: 10,
    keep_hourly: 0,
    keep_daily: 30,
    keep_weekly: 0,
    keep_monthly: 0,
    keep_annual: 0,
    backup_paths_text: "",
    exclude_patterns_text: "",
    dot_ignore_files_text: ".kopiaignore",
    one_file_system: false,
    ignore_file_errors: false,
    ignore_dir_errors: false,
    compression_enabled: true,
    compression_type: "zstd",
    compression_level: 6,
    encryption_enabled: true,
    verify_checksum: true,
    enable_checkpoint: true,
    checkpoint_interval_minutes: 15,
    max_concurrent_files: 4,
    bandwidth_limit_kbps: null,
    max_retries: 3,
  };
}

function listToText(value?: string[] | null) {
  return Array.isArray(value) ? value.join("\n") : "";
}

function textToList(value: string) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function useBackupTaskEdit(options: {
  t: Translate;
  appStore: AppStore;
  backupPolicies: Ref<Array<Record<string, any>>>;
  selectedTask: Ref<BackupTask | null>;
  fetchTasks: () => Promise<void>;
  fetchStats: () => Promise<void>;
}) {
  const { t, appStore, backupPolicies, selectedTask, fetchTasks, fetchStats } =
    options;

  const showEditModal = ref(false);
  const editingTask = ref<BackupTask | null>(null);
  const editLoading = ref(false);
  const editSaving = ref(false);
  const editForm = ref<EditTaskForm>(createEditForm());

  const editRetentionFields = [
    { key: "keep_latest", label: "latest" },
    { key: "keep_hourly", label: "hourly" },
    { key: "keep_daily", label: "daily" },
    { key: "keep_weekly", label: "weekly" },
    { key: "keep_monthly", label: "monthly" },
    { key: "keep_annual", label: "annual" },
  ] as const;

  const selectedEditPolicy = computed(() => {
    if (!editForm.value.schedule) return null;
    return (
      backupPolicies.value.find(
        (policy) => String(policy.id) === String(editForm.value.schedule),
      ) || null
    );
  });

  const editPolicyScheduleSummary = computed(() => {
    const schedule = selectedEditPolicy.value?.snapshot_schedule || {};
    const mode = schedule.mode || "manual";
    if (mode === "interval") return schedule.interval || "24h";
    if (mode === "time") return schedule.time_of_day || "02:00";
    if (mode === "cron") return schedule.cron || "-";
    return t("policies.scheduleModes.manual");
  });

  const editPolicyRetentionSummary = computed(() => {
    const retention = selectedEditPolicy.value?.retention_policy || {};
    if (!selectedEditPolicy.value) return "-";
    return `L${retention.keep_latest ?? 0} H${retention.keep_hourly ?? 0} D${retention.keep_daily ?? 0} W${retention.keep_weekly ?? 0} M${retention.keep_monthly ?? 0} A${retention.keep_annual ?? 0}`;
  });

  function fillEditForm(task: BackupTask) {
    const filePolicy = task.policy_overrides?.file_policy || {};
    const scheduleOverride = task.policy_overrides?.snapshot_schedule || {};
    const retentionOverride = task.policy_overrides?.retention_policy || {};
    const hasScheduleOverride =
      scheduleOverride.override === true || !task.schedule;
    const hasRetentionOverride =
      retentionOverride.override === true || !task.schedule;
    const taskPolicy = task.schedule
      ? backupPolicies.value.find(
          (policy) => String(policy.id) === String(task.schedule),
        )
      : null;
    const policySchedule = taskPolicy?.snapshot_schedule || {};
    const policyRetention = taskPolicy?.retention_policy || {};
    const effectiveEditSchedule = hasScheduleOverride
      ? scheduleOverride
      : policySchedule;
    const effectiveEditRetention = hasRetentionOverride
      ? retentionOverride
      : policyRetention;
    editForm.value = {
      name: task.name || "",
      description: task.description || "",
      priority: task.priority || "normal",
      is_enabled: task.is_enabled !== false,
      execution_mode: task.execution_mode || "pinned",
      preferred_execution_node: task.preferred_execution_node || null,
      schedule: task.schedule || null,
      override_schedule: hasScheduleOverride,
      schedule_mode: effectiveEditSchedule.mode || "manual",
      interval: effectiveEditSchedule.interval || "24h",
      time_of_day: effectiveEditSchedule.time_of_day || "02:00",
      cron_expression: effectiveEditSchedule.cron || "",
      retention_mode: hasRetentionOverride ? "custom" : "policy",
      retention_days: task.retention_days ?? 30,
      max_snapshots: task.max_snapshots ?? 10,
      keep_latest: effectiveEditRetention.keep_latest ?? task.max_snapshots ?? 10,
      keep_hourly: effectiveEditRetention.keep_hourly ?? 0,
      keep_daily: effectiveEditRetention.keep_daily ?? task.retention_days ?? 30,
      keep_weekly: effectiveEditRetention.keep_weekly ?? 0,
      keep_monthly: effectiveEditRetention.keep_monthly ?? 0,
      keep_annual: effectiveEditRetention.keep_annual ?? 0,
      backup_paths_text: listToText(task.backup_paths),
      exclude_patterns_text: listToText(task.exclude_patterns),
      dot_ignore_files_text: listToText(
        filePolicy.dot_ignore_files || [".kopiaignore"],
      ),
      one_file_system: !!filePolicy.one_file_system,
      ignore_file_errors: !!filePolicy.ignore_file_errors,
      ignore_dir_errors: !!filePolicy.ignore_dir_errors,
      compression_enabled: task.compression_enabled !== false,
      compression_type: task.compression_type || "zstd",
      compression_level: task.compression_level ?? 6,
      encryption_enabled: task.encryption_enabled !== false,
      verify_checksum: task.verify_checksum !== false,
      enable_checkpoint: task.enable_checkpoint !== false,
      checkpoint_interval_minutes: task.checkpoint_interval_minutes ?? 15,
      max_concurrent_files: task.max_concurrent_files ?? 4,
      bandwidth_limit_kbps: task.bandwidth_limit_kbps ?? null,
      max_retries: task.max_retries ?? 3,
    };
  }

  async function openEditTask(task: BackupTask) {
    if (task.status === "running") {
      appStore.error(t("backupTasks.edit.runningReadonly"));
      return;
    }
    editingTask.value = task;
    showEditModal.value = true;
    editLoading.value = true;
    fillEditForm(task);
    try {
      const response = await backupTasksApi.detail(task.id);
      editingTask.value = response.data;
      fillEditForm(response.data);
    } catch (error) {
      console.error("Failed to fetch task for editing:", error);
    } finally {
      editLoading.value = false;
    }
  }

  async function updateTask() {
    if (!editingTask.value) return;
    if (!editForm.value.name.trim()) {
      appStore.error(t("backupTasks.edit.requiredFields"));
      return;
    }
    if (editForm.value.override_schedule || !editForm.value.schedule) {
      if (
        editForm.value.schedule_mode === "interval" &&
        !editForm.value.interval.trim()
      ) {
        appStore.error(t("policies.schedule.interval"));
        return;
      }
      if (
        editForm.value.schedule_mode === "time" &&
        !editForm.value.time_of_day
      ) {
        appStore.error(t("policies.schedule.timeOfDay"));
        return;
      }
      if (
        editForm.value.schedule_mode === "cron" &&
        !editForm.value.cron_expression.trim()
      ) {
        appStore.error(t("policies.schedule.cron"));
        return;
      }
    }

    const payload: BackupTaskUpdateData = {
      name: editForm.value.name.trim(),
      description: editForm.value.description.trim(),
      priority: editForm.value.priority,
      is_enabled: editForm.value.is_enabled,
      execution_mode: editForm.value.execution_mode,
      preferred_execution_node:
        editForm.value.execution_mode === "preferred"
          ? editForm.value.preferred_execution_node
          : null,
      schedule: editForm.value.schedule || null,
      policy_overrides: {
        ...(editingTask.value.policy_overrides || {}),
        ...(editForm.value.override_schedule || !editForm.value.schedule
          ? {
              snapshot_schedule: {
                override: true,
                mode: editForm.value.schedule_mode,
                interval:
                  editForm.value.schedule_mode === "interval"
                    ? editForm.value.interval.trim()
                    : "",
                time_of_day:
                  editForm.value.schedule_mode === "time"
                    ? editForm.value.time_of_day
                    : "",
                cron:
                  editForm.value.schedule_mode === "cron"
                    ? editForm.value.cron_expression.trim()
                    : "",
                run_missed: true,
              },
            }
          : { snapshot_schedule: {} }),
        ...(editForm.value.retention_mode === "custom" || !editForm.value.schedule
          ? {
              retention_policy: {
                override: true,
                keep_latest: Number(editForm.value.keep_latest) || 0,
                keep_hourly: Number(editForm.value.keep_hourly) || 0,
                keep_daily: Number(editForm.value.keep_daily) || 0,
                keep_weekly: Number(editForm.value.keep_weekly) || 0,
                keep_monthly: Number(editForm.value.keep_monthly) || 0,
                keep_annual: Number(editForm.value.keep_annual) || 0,
              },
            }
          : { retention_policy: {} }),
        file_policy: {
          ...((editingTask.value.policy_overrides || {}).file_policy || {}),
          override: true,
          ignore_patterns: textToList(editForm.value.exclude_patterns_text),
          additional_ignore_patterns:
            ((editingTask.value.policy_overrides || {}).file_policy || {})
              .additional_ignore_patterns || [],
          dot_ignore_files: textToList(editForm.value.dot_ignore_files_text),
          one_file_system: editForm.value.one_file_system,
          ignore_file_errors: editForm.value.ignore_file_errors,
          ignore_dir_errors: editForm.value.ignore_dir_errors,
        },
      },
      retention_days: Number(editForm.value.keep_daily) || 30,
      max_snapshots: Number(editForm.value.keep_latest) || 10,
      include_patterns: [],
      exclude_patterns: textToList(editForm.value.exclude_patterns_text),
      compression_enabled: editForm.value.compression_enabled,
      compression_type: editForm.value.compression_type,
      compression_level: Number(editForm.value.compression_level) || 0,
      encryption_enabled: editForm.value.encryption_enabled,
      verify_checksum: editForm.value.verify_checksum,
      enable_checkpoint: editForm.value.enable_checkpoint,
      checkpoint_interval_minutes:
        Number(editForm.value.checkpoint_interval_minutes) || 15,
      max_concurrent_files: Number(editForm.value.max_concurrent_files) || 1,
      bandwidth_limit_kbps: editForm.value.bandwidth_limit_kbps
        ? Number(editForm.value.bandwidth_limit_kbps)
        : null,
      max_retries: Number(editForm.value.max_retries) || 0,
    };

    editSaving.value = true;
    try {
      const taskId = editingTask.value.id;
      await backupTasksApi.update(taskId, payload);
      const detailResponse = await backupTasksApi.detail(taskId);
      const updated = detailResponse.data;
      showEditModal.value = false;
      editingTask.value = null;
      if (selectedTask.value?.id === taskId) {
        selectedTask.value = { ...selectedTask.value, ...updated };
      }
      appStore.showToast({
        type: "success",
        title: t("common.save"),
        message: t("backupTasks.edit.updateSuccess"),
      });
      await fetchTasks();
      await fetchStats();
    } catch (error) {
      console.error("Failed to update task:", error);
      appStore.error(getApiErrorMessage(error, t("common.updateFailed")));
    } finally {
      editSaving.value = false;
    }
  }

  return {
    showEditModal,
    editingTask,
    editLoading,
    editSaving,
    editForm,
    editRetentionFields,
    selectedEditPolicy,
    editPolicyScheduleSummary,
    editPolicyRetentionSummary,
    openEditTask,
    updateTask,
  };
}
