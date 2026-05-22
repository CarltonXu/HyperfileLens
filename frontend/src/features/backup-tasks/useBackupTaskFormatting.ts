import type { Ref } from "vue";
import {
  BoltIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  PauseIcon,
  XCircleIcon,
} from "@heroicons/vue/24/outline";
import type { BackupTask } from "@/types/backup";
import type { Repository } from "@/types/repository";
import type { SourceResource } from "@/types/sourceResource";
import {
  isNoChangeSnapshotReference,
  snapshotDisplaySize,
  snapshotDisplayTime,
} from "@/features/backup-tasks/snapshotDisplay";

type Translate = (key: string, params?: Record<string, any>) => string;

export function useBackupTaskFormatting(
  t: Translate,
  locale: Ref<string>,
  backupPolicies: Ref<Array<Record<string, any>>>,
) {
  function formatBytes(bytes: number): string {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  function getStatusColor(status: string): string {
    const colors: Record<string, string> = {
      pending:
        "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
      queued: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
      dispatched:
        "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
      running:
        "bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400",
      paused:
        "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400",
      completed:
        "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400",
      partial:
        "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
      failed: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400",
      cancelled: "bg-background-tertiary text-slate-600",
    };
    return colors[status] || "bg-background-tertiary text-slate-600";
  }

  function getStatusIcon(status: string) {
    const icons: Record<string, any> = {
      pending: ClockIcon,
      running: BoltIcon,
      completed: CheckCircleIcon,
      partial: ExclamationTriangleIcon,
      failed: ExclamationTriangleIcon,
      paused: PauseIcon,
      cancelled: XCircleIcon,
    };
    return icons[status] || ClockIcon;
  }

  function currentLocale() {
    return String(locale.value || "en");
  }

  function formatDateTime(value?: string | null) {
    return value ? new Date(value).toLocaleString(currentLocale()) : "-";
  }

  function formatCompactDateTime(value?: string | null) {
    if (!value) return "-";
    return new Date(value).toLocaleString(currentLocale(), {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function localDateKey(date: Date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function localMonthKey(date: Date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    return `${year}-${month}`;
  }

  function formatSnapshotGroupDay(value?: string | null) {
    if (!value) return t("backupTasks.detail.unknownTime");
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return t("backupTasks.detail.unknownTime");
    const weekday = new Intl.DateTimeFormat(currentLocale(), {
      weekday: "short",
    }).format(date);
    return `${localDateKey(date)} ${weekday}`;
  }

  function formatSnapshotGroupMonth(value?: string | null) {
    if (!value) return t("backupTasks.detail.unknownTime");
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return t("backupTasks.detail.unknownTime");
    return date.toLocaleDateString(currentLocale(), {
      year: "numeric",
      month: "long",
    });
  }

  function snapshotGroupDescription(snapshots: any[]) {
    const totalSize = snapshots.reduce(
      (sum, snapshot) => sum + snapshotDisplaySize(snapshot),
      0,
    );
    return t("backupTasks.detail.snapshotGroupSummary", {
      count: snapshots.length,
      size: formatBytes(totalSize),
    });
  }

  function snapshotGroupFor(
    snapshot: any,
    mode: "day" | "month" | "change" | "size",
  ) {
    const displayTime = snapshotDisplayTime(snapshot);
    if (mode === "day") {
      const date = displayTime ? new Date(displayTime) : null;
      return {
        key:
          date && !Number.isNaN(date.getTime()) ? localDateKey(date) : "unknown",
        label: formatSnapshotGroupDay(displayTime),
      };
    }

    if (mode === "month") {
      const date = displayTime ? new Date(displayTime) : null;
      return {
        key:
          date && !Number.isNaN(date.getTime())
            ? localMonthKey(date)
            : "unknown",
        label: formatSnapshotGroupMonth(displayTime),
      };
    }

    if (mode === "change") {
      const noChanges = isNoChangeSnapshotReference(snapshot);
      return {
        key: noChanges ? "no-changes" : "changed",
        label: noChanges
          ? t("backupTasks.detail.noChangeSnapshots")
          : t("backupTasks.detail.changedSnapshots"),
      };
    }

    const size = snapshotDisplaySize(snapshot);
    if (size === 0) {
      return { key: "zero", label: t("backupTasks.detail.sizeZero") };
    }
    if (size < 1024 * 1024 * 1024) {
      return { key: "small", label: t("backupTasks.detail.sizeSmall") };
    }
    if (size < 10 * 1024 * 1024 * 1024) {
      return { key: "medium", label: t("backupTasks.detail.sizeMedium") };
    }
    return { key: "large", label: t("backupTasks.detail.sizeLarge") };
  }

  function formatDurationSeconds(value?: number | null) {
    if (!value && value !== 0) return "-";
    const seconds = Math.max(0, Math.floor(value));
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const rest = seconds % 60;
    if (hours) return `${hours}h ${minutes}m ${rest}s`;
    if (minutes) return `${minutes}m ${rest}s`;
    return `${rest}s`;
  }

  function formatSpeed(bytesPerSecond?: number | null) {
    return bytesPerSecond ? `${formatBytes(bytesPerSecond)}/s` : "-";
  }

  function masked(value?: string | null) {
    if (!value) return "-";
    if (value.length <= 8) return "****";
    return `${value.slice(0, 4)}****${value.slice(-4)}`;
  }

  function policyForTask(task: BackupTask) {
    if (!task.schedule) return null;
    return (
      backupPolicies.value.find(
        (policy) => String(policy.id) === String(task.schedule),
      ) || null
    );
  }

  function getTaskPolicyScheduleSummary(task: BackupTask) {
    const policy = policyForTask(task);
    const effectivePolicy = task.effective_policy || {};
    const schedule =
      policy?.snapshot_schedule || effectivePolicy.snapshot_schedule || {};
    const mode = schedule.mode || policy?.frequency || "manual";

    if (mode === "interval") {
      return `${t("policies.scheduleModes.interval")} ${schedule.interval || "24h"}`;
    }
    if (mode === "time") {
      return `${t("policies.scheduleModes.time")} ${schedule.time_of_day || policy?.schedule_time || "-"}`;
    }
    if (mode === "cron") {
      return `${t("policies.scheduleModes.cron")} ${schedule.cron || "-"}`;
    }
    if (
      mode === "hourly" ||
      mode === "daily" ||
      mode === "weekly" ||
      mode === "monthly"
    ) {
      return t(`policies.scheduleTypes.${mode}`);
    }
    return t("policies.scheduleModes.manual");
  }

  function getTaskPolicyRetentionSummary(task: BackupTask) {
    const policy = policyForTask(task);
    const effectivePolicy = task.effective_policy || {};
    const retention =
      policy?.retention_policy || effectivePolicy.retention_policy || null;

    if (retention) {
      return `L${retention.keep_latest ?? 0} H${retention.keep_hourly ?? 0} D${retention.keep_daily ?? 0} W${retention.keep_weekly ?? 0} M${retention.keep_monthly ?? 0} A${retention.keep_annual ?? 0}`;
    }

    return t("backupTasks.policySummary.taskRetention", {
      days: task.retention_days || "-",
      snapshots: task.max_snapshots || "-",
    });
  }

  function getTaskPolicySummary(task: BackupTask) {
    if (!task.schedule) {
      return t("backupTasks.policySummary.taskSettings", {
        retention: getTaskPolicyRetentionSummary(task),
      });
    }
    return `${getTaskPolicyScheduleSummary(task)} · ${getTaskPolicyRetentionSummary(task)}`;
  }

  function sourceDetailRows(source: SourceResource | null): Array<[string, any]> {
    if (!source) return [];
    const config = (source.config || {}) as Record<string, any>;
    const rows: Array<[string, any]> = [
      [t("common.name"), source.name],
      [t("common.type"), source.resource_type_display || source.resource_type],
      [t("backupTasks.detail.boundNode"), source.bound_node?.name || "-"],
      [t("common.status"), source.status_display || source.status],
    ];
    if (source.resource_type === "local") {
      rows.push([
        t("backupTasks.repositoryDetails.path"),
        config.path || config.root_path || "-",
      ]);
    } else if (["nas", "nfs", "cifs"].includes(source.resource_type)) {
      rows.push(
        [t("backupTasks.repositoryDetails.endpoint"), config.server || "-"],
        [
          t("backupTasks.repositoryDetails.path"),
          config.export_path || config.share || "-",
        ],
        [
          t("backupTasks.repositoryDetails.mountPoint"),
          source.mount_point || "-",
        ],
      );
    } else if (source.resource_type === "s3") {
      rows.push(
        [t("backupTasks.repositoryDetails.endpoint"), config.endpoint || "-"],
        [t("backupTasks.repositoryDetails.bucket"), config.bucket || "-"],
        [t("backupTasks.repositoryDetails.region"), config.region || "-"],
        [t("backupTasks.repositoryDetails.prefix"), config.prefix || "-"],
        [
          t("backupTasks.repositoryDetails.accessKey"),
          masked(source.credentials?.access_key || config.access_key),
        ],
        [
          t("backupTasks.repositoryDetails.secretKey"),
          masked(source.credentials?.secret_key || config.secret_key),
        ],
        [t("backupTasks.detail.urlStyle"), config.url_style || "-"],
        [
          t("backupTasks.detail.useTls"),
          config.use_tls ? t("common.yes") : t("common.no"),
        ],
      );
    }
    return rows;
  }

  function repositoryDetailRows(repo: Repository | null): Array<[string, any]> {
    if (!repo) return [];
    const config = repo.config || {};
    const rows: Array<[string, any]> = [
      [t("common.name"), repo.name],
      [
        t("backupTasks.repositoryDetails.type"),
        repo.repo_type_display || repo.repo_type,
      ],
      [t("common.status"), repo.status_display || repo.status],
      [t("backupTasks.repositoryDetails.boundNode"), repo.bound_node_name || "-"],
      [
        t("backupTasks.repositoryDetails.kopia"),
        repo.kopia_initialized ? t("common.yes") : t("common.no"),
      ],
    ];
    if (repo.repo_type === "local") {
      rows.push([t("backupTasks.repositoryDetails.path"), config.path || "-"]);
    } else if (repo.repo_type === "s3") {
      rows.push(
        [t("backupTasks.repositoryDetails.endpoint"), config.endpoint || "-"],
        [t("backupTasks.repositoryDetails.bucket"), config.bucket || "-"],
        [t("backupTasks.repositoryDetails.region"), config.region || "-"],
        [t("backupTasks.repositoryDetails.prefix"), config.prefix || "-"],
        [
          t("backupTasks.repositoryDetails.accessKey"),
          masked(config.access_key || repo.credentials_masked?.access_key),
        ],
        [
          t("backupTasks.repositoryDetails.secretKey"),
          masked(config.secret_key || repo.credentials_masked?.secret_key),
        ],
        [t("backupTasks.detail.urlStyle"), config.url_style || "-"],
        [
          t("backupTasks.detail.useTls"),
          config.use_tls ? t("common.yes") : t("common.no"),
        ],
      );
    } else if (["nas", "nfs"].includes(repo.repo_type)) {
      rows.push(
        [t("backupTasks.repositoryDetails.endpoint"), config.server || "-"],
        [t("backupTasks.repositoryDetails.path"), config.export_path || "-"],
        [
          t("backupTasks.repositoryDetails.mountOptions"),
          config.mount_options || "-",
        ],
      );
    }
    return rows;
  }

  function runDuration(run: any) {
    if (run.duration_seconds || run.duration) {
      return formatDurationSeconds(run.duration_seconds || run.duration);
    }
    const start = run.started_at ? new Date(run.started_at).getTime() : null;
    const end = run.completed_at ? new Date(run.completed_at).getTime() : null;
    return start && end ? formatDurationSeconds((end - start) / 1000) : "-";
  }

  return {
    formatBytes,
    getStatusColor,
    getStatusIcon,
    formatDateTime,
    formatCompactDateTime,
    snapshotGroupDescription,
    snapshotGroupFor,
    formatDurationSeconds,
    formatSpeed,
    getTaskPolicyScheduleSummary,
    getTaskPolicyRetentionSummary,
    getTaskPolicySummary,
    sourceDetailRows,
    repositoryDetailRows,
    runDuration,
  };
}
