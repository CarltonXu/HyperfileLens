<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  backupTasksApi,
  nodesApi,
  policiesApi,
  repositoriesApi,
  sourceResourcesApi,
} from "@/api";
import { useAppStore } from "@/stores/app";
import { getApiErrorMessage } from "@/utils/errors";
import type {
  BackupTask,
  BackupTaskCreateData,
  BackupTaskStats,
  BackupTaskUpdateData,
} from "@/types/backup";
import type { ProxyNode } from "@/types/proxy";
import type { Repository } from "@/types/repository";
import type { SourceResource } from "@/types/sourceResource";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import Pagination from "@/components/Pagination.vue";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";
import BackupTaskWizard from "@/components/BackupTaskWizard.vue";
import {
  CloudArrowUpIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  PlayIcon,
  StopIcon,
  EyeIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  BoltIcon,
  PauseIcon,
  XCircleIcon,
  PowerIcon,
  ListBulletIcon,
  CircleStackIcon,
  TrashIcon,
  FolderIcon,
  DocumentIcon,
  ShieldCheckIcon,
  ServerStackIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  PencilSquareIcon,
  QuestionMarkCircleIcon,
} from "@heroicons/vue/24/outline";

const { t, locale } = useI18n();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();

const isLoading = ref(true);
const tasks = ref<BackupTask[]>([]);
const stats = ref<BackupTaskStats | null>(null);
const nodes = ref<ProxyNode[]>([]);
const repositories = ref<Repository[]>([]);
const sourceResources = ref<SourceResource[]>([]);
const backupPolicies = ref<Array<Record<string, any>>>([]);
const showCreateModal = ref(false);
const showDetailModal = ref(false);
const showEditModal = ref(false);
const selectedTask = ref<BackupTask | null>(null);
const editingTask = ref<BackupTask | null>(null);
const detailTab = ref<"overview" | "snapshots" | "tasks">("overview");
const selectedTaskSnapshots = ref<any[]>([]);
const selectedTaskRuns = ref<any[]>([]);
const selectedSnapshot = ref<any | null>(null);
const selectedSnapshotFiles = ref<any[]>([]);
const snapshotFilesError = ref("");
const collapseNoChangeSnapshots = ref(false);
const snapshotGroupBy = ref<"all" | "day" | "month" | "change" | "size">("all");
const snapshotViewMode = ref<"grid" | "timeline">("grid");
const expandedSnapshotPaths = ref<Set<string>>(new Set());
const selectedSnapshotPaths = ref<Set<string>>(new Set());
const loadingSnapshotPaths = ref<Set<string>>(new Set());
const snapshotsLoading = ref(false);
const runsLoading = ref(false);
const snapshotFilesLoading = ref(false);
const snapshotOperationLoading = ref(false);
const detailLoading = ref(false);
const detailRefreshing = ref(false);
const editLoading = ref(false);
const editSaving = ref(false);
const selectedStatus = ref<string>("all");
const searchQuery = ref("");
const detailAutoRefresh = ref(false);
const detailRefreshInterval = ref(10);
const detailRefreshTimer = ref<ReturnType<typeof setInterval> | null>(null);
const snapshotHelpTooltip = ref<{
  key: string;
  top: number;
  left: number;
} | null>(null);
let snapshotHelpTooltipHideTimer: ReturnType<typeof setTimeout> | null = null;
const snapshotHoverTooltip = ref<{
  snapshot: any;
  top: number;
  left: number;
  placement: "top" | "bottom";
} | null>(null);
let snapshotHoverTooltipHideTimer: ReturnType<typeof setTimeout> | null = null;

type EditTaskForm = {
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

const editForm = ref<EditTaskForm>({
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
});

const editRetentionFields = [
  { key: "keep_latest", label: "latest" },
  { key: "keep_hourly", label: "hourly" },
  { key: "keep_daily", label: "daily" },
  { key: "keep_weekly", label: "weekly" },
  { key: "keep_monthly", label: "monthly" },
  { key: "keep_annual", label: "annual" },
] as const;

// Pagination
const currentPage = ref(1);
const pageSize = ref(getPageSize("backup-tasks"));
const PAGE_STORAGE_KEY = "backup-tasks";

watch(pageSize, (newSize) => {
  setPageSize(newSize, PAGE_STORAGE_KEY);
});

const newTask = ref<BackupTaskCreateData>({
  name: "",
  source_resource: "",
  target_repository: "",
  backup_paths: [],
  task_type: "incremental",
  priority: "normal",
  retention_days: 30,
  compression_enabled: true,
  encryption_enabled: true,
});

const taskStats = computed(
  () =>
    stats.value || {
      total_tasks: 0,
      active_tasks: 0,
      running_tasks: 0,
      completed_tasks: 0,
      failed_tasks: 0,
      total_size: 0,
      total_size_bytes: 0,
      total_files: 0,
    },
);

const totalBackupSize = computed(() => {
  const value = taskStats.value as BackupTaskStats;
  return value.total_size || value.total_size_bytes || 0;
});

const filteredTasks = computed(() => {
  let result = tasks.value;
  if (selectedStatus.value !== "all") {
    result = result.filter((t) => t.status === selectedStatus.value);
  }
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    result = result.filter((t) => t.name.toLowerCase().includes(query));
  }
  return result;
});

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

function snapshotDisplayTime(snapshot: any) {
  return (
    snapshot?.metadata?.snapshot_time ||
    snapshot?.metadata?.kopia_start_time ||
    snapshot?.metadata?.kopia_snapshot?.startTime ||
    snapshot?.metadata?.kopia_end_time ||
    snapshot?.metadata?.kopia_snapshot?.endTime ||
    snapshot?.created_at ||
    snapshot?.metadata?.last_seen_at
  );
}

function isNoChangeSnapshotReference(snapshot: any) {
  return (
    snapshot?.metadata?.no_changes === true ||
    snapshot?.metadata?.last_no_changes === true
  );
}

function isLatestDisplayedSnapshot(snapshot: any) {
  return displayedTaskSnapshots.value[0]?.id === snapshot?.id;
}

function snapshotDisplaySize(snapshot: any) {
  return isNoChangeSnapshotReference(snapshot)
    ? 0
    : Number(snapshot?.total_size || 0);
}

function snapshotDisplayFileCount(snapshot: any) {
  return isNoChangeSnapshotReference(snapshot)
    ? 0
    : Number(snapshot?.file_count || 0);
}

function snapshotReferencedId(snapshot: any) {
  return (
    snapshot?.metadata?.referenced_snapshot_id ||
    snapshot?.metadata?.referenced_manifest_id ||
    snapshot?.metadata?.referenced_storage_path ||
    snapshot?.metadata?.root_object_id ||
    snapshot?.storage_path ||
    snapshot?.version ||
    ""
  );
}

function snapshotStatusLabel(snapshot: any) {
  const status = snapshot?.snapshot_status || "available";
  return t(`backupTasks.detail.snapshotStatuses.${status}`);
}

function snapshotStatusClass(snapshot: any) {
  const status = snapshot?.snapshot_status || "available";
  const classes: Record<string, string> = {
    available:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300",
    pending_prune:
      "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
    missing:
      "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    pruned: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
    delete_failed:
      "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300",
  };
  return classes[status] || classes.available;
}

function isSnapshotBrowsable(snapshot: any) {
  return (snapshot?.snapshot_status || "available") === "available";
}

function snapshotCardClass(snapshot: any) {
  const status = snapshot?.snapshot_status || "available";
  const selected = selectedSnapshot?.value?.id === snapshot?.id;
  if (status === "available") {
    return selected
      ? "border-emerald-500 bg-emerald-50 text-emerald-950 shadow-sm dark:bg-emerald-950/30 dark:text-emerald-50"
      : "border-border bg-card hover:border-emerald-400 hover:bg-emerald-50/70 dark:hover:bg-emerald-950/20";
  }
  if (status === "pending_prune") {
    return "cursor-not-allowed border-amber-300 bg-amber-50/70 text-amber-950 opacity-90 dark:border-amber-900/60 dark:bg-amber-950/20 dark:text-amber-50";
  }
  if (status === "delete_failed") {
    return "cursor-not-allowed border-red-300 bg-red-50/70 text-red-950 opacity-90 dark:border-red-900/60 dark:bg-red-950/20 dark:text-red-50";
  }
  return "cursor-not-allowed border-slate-300 bg-slate-100/80 text-slate-600 opacity-75 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400";
}

function snapshotTimelineClass(snapshot: any) {
  const status = snapshot?.snapshot_status || "available";
  const selected = selectedSnapshot?.value?.id === snapshot?.id;
  if (status === "available") {
    return selected
      ? "border-emerald-500 bg-emerald-50/70 dark:bg-emerald-950/20"
      : "border-border hover:bg-hover";
  }
  if (status === "pending_prune") {
    return "border-amber-300 bg-amber-50/70 opacity-90 dark:border-amber-900/60 dark:bg-amber-950/20";
  }
  if (status === "delete_failed") {
    return "border-red-300 bg-red-50/70 opacity-90 dark:border-red-900/60 dark:bg-red-950/20";
  }
  return "border-slate-300 bg-slate-100/80 opacity-75 dark:border-slate-700 dark:bg-slate-900/50";
}

function snapshotTimelineDotClass(snapshot: any) {
  const status = snapshot?.snapshot_status || "available";
  if (selectedSnapshot?.value?.id === snapshot?.id) {
    return "border-emerald-500 ring-4 ring-emerald-100 dark:ring-emerald-950/40";
  }
  if (status === "pending_prune") return "border-amber-500";
  if (status === "delete_failed") return "border-red-500";
  if (status !== "available") return "border-slate-400";
  return isNoChangeSnapshotReference(snapshot) ? "border-amber-500" : "border-emerald-400";
}

type BackupTaskColumnKey =
  | "name"
  | "policy"
  | "source"
  | "repository"
  | "status"
  | "last_backup"
  | "next_backup"
  | "actions";

const backupTaskColumns = computed(() => [
  { key: "name" as const, label: t("common.name"), min: 220, max: 420 },
  {
    key: "policy" as const,
    label: t("backupTasks.form.policy"),
    min: 220,
    max: 380,
  },
  {
    key: "source" as const,
    label: t("backupTasks.form.sourceNode"),
    min: 190,
    max: 340,
  },
  {
    key: "repository" as const,
    label: t("backupTasks.form.repository"),
    min: 200,
    max: 360,
  },
  { key: "status" as const, label: t("common.status"), min: 140, max: 220 },
  {
    key: "last_backup" as const,
    label: t("backupTasks.lastBackup"),
    min: 150,
    max: 260,
  },
  {
    key: "next_backup" as const,
    label: t("backupTasks.nextBackup"),
    min: 150,
    max: 260,
  },
  {
    key: "actions" as const,
    label: t("common.actions"),
    min: 160,
    max: 220,
    sortable: false,
    align: "right" as const,
  },
]);

const backupTaskTable = useResizableSortableTable<
  BackupTask,
  BackupTaskColumnKey
>({
  storageKey: "hyperfilelens:backup-tasks:columns",
  columns: backupTaskColumns,
  rows: filteredTasks,
  defaultSort: { key: "name", direction: "asc" },
  minTableWidth: 1440,
  getSortValue: (task, key) => {
    if (key === "name") return task.name;
    if (key === "policy") return task.schedule_name || "";
    if (key === "source") return task.source_resource_name || "";
    if (key === "repository") return task.target_repository_name || "";
    if (key === "status") return task.status || "";
    if (key === "last_backup")
      return task.last_run_time ? new Date(task.last_run_time).getTime() : 0;
    if (key === "next_backup")
      return task.next_run_time ? new Date(task.next_run_time).getTime() : 0;
    return "";
  },
  getColumnText: (task, key) => {
    if (key === "name") return `${task.name} ${task.task_type || ""}`;
    if (key === "policy")
      return `${task.schedule_name || ""} ${getTaskPolicySummary(task)}`;
    if (key === "source")
      return `${task.source_resource_name || ""} ${task.execution_node_name || ""}`;
    if (key === "repository")
      return `${task.target_repository_name || ""} ${task.target_repository_type || ""}`;
    if (key === "status") return task.status || "";
    if (key === "last_backup") return formatDateTime(task.last_run_time);
    if (key === "next_backup") return formatDateTime(task.next_run_time);
    return "";
  },
});

// Paginated tasks for display
const paginatedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return backupTaskTable.sortedRows.value.slice(start, end);
});

const currentDetailTabLoading = computed(() => {
  if (detailTab.value === "overview") return detailRefreshing.value;
  if (detailTab.value === "snapshots") return snapshotsLoading.value;
  return runsLoading.value;
});

const displayedTaskSnapshots = computed(() => {
  const snapshots = [...selectedTaskSnapshots.value].sort(
    (a, b) =>
      new Date(snapshotDisplayTime(b) || 0).getTime() -
      new Date(snapshotDisplayTime(a) || 0).getTime(),
  );
  if (!collapseNoChangeSnapshots.value) {
    return snapshots;
  }
  return snapshots.filter(
    (snapshot) => !isNoChangeSnapshotReference(snapshot),
  );
});

const hiddenNoChangeSnapshotCount = computed(
  () =>
    selectedTaskSnapshots.value.length - displayedTaskSnapshots.value.length,
);

const snapshotGroupOptions = computed(() => [
  { value: "all" as const, label: t("backupTasks.detail.groupAll") },
  { value: "day" as const, label: t("backupTasks.detail.groupByDay") },
  { value: "month" as const, label: t("backupTasks.detail.groupByMonth") },
  { value: "change" as const, label: t("backupTasks.detail.groupByChange") },
  { value: "size" as const, label: t("backupTasks.detail.groupBySize") },
]);

const snapshotViewModeOptions = computed(() => [
  { value: "grid" as const, label: t("backupTasks.detail.gridView") },
  { value: "timeline" as const, label: t("backupTasks.detail.timelineView") },
]);

const groupedDisplayedTaskSnapshots = computed(() => {
  const snapshots = displayedTaskSnapshots.value;
  if (snapshotGroupBy.value === "all") {
    return [
      {
        key: "all",
        label: t("backupTasks.detail.allSnapshots"),
        description: snapshotGroupDescription(snapshots),
        snapshots,
      },
    ];
  }

  const groupMap = new Map<string, { label: string; snapshots: any[] }>();
  for (const snapshot of snapshots) {
    const group = snapshotGroupFor(snapshot, snapshotGroupBy.value);
    if (!groupMap.has(group.key)) {
      groupMap.set(group.key, { label: group.label, snapshots: [] });
    }
    groupMap.get(group.key)?.snapshots.push(snapshot);
  }

  return Array.from(groupMap.entries()).map(([key, group]) => ({
    key,
    label: group.label,
    description: snapshotGroupDescription(group.snapshots),
    snapshots: group.snapshots,
  }));
});

// Reset page when filters change
watch([selectedStatus, searchQuery], () => {
  currentPage.value = 1;
});

function stopDetailAutoRefresh() {
  if (detailRefreshTimer.value) {
    clearInterval(detailRefreshTimer.value);
    detailRefreshTimer.value = null;
  }
}

function cancelSnapshotHelpTooltipHide() {
  if (snapshotHelpTooltipHideTimer) {
    clearTimeout(snapshotHelpTooltipHideTimer);
    snapshotHelpTooltipHideTimer = null;
  }
}

function showSnapshotHelpTooltip(event: MouseEvent | FocusEvent, key: string) {
  cancelSnapshotHelpTooltipHide();
  const target = event.currentTarget as HTMLElement | null;
  if (!target) return;
  const rect = target.getBoundingClientRect();
  snapshotHelpTooltip.value = {
    key,
    top: rect.bottom + 8,
    left: Math.min(
      Math.max(rect.left + rect.width / 2, 156),
      window.innerWidth - 156,
    ),
  };
}

function scheduleSnapshotHelpTooltipHide() {
  cancelSnapshotHelpTooltipHide();
  snapshotHelpTooltipHideTimer = setTimeout(() => {
    snapshotHelpTooltip.value = null;
  }, 120);
}

function cancelSnapshotHoverTooltipHide() {
  if (snapshotHoverTooltipHideTimer) {
    clearTimeout(snapshotHoverTooltipHideTimer);
    snapshotHoverTooltipHideTimer = null;
  }
}

function showSnapshotHoverTooltip(
  snapshot: any,
  event: MouseEvent | FocusEvent,
) {
  cancelSnapshotHoverTooltipHide();
  const target = event.currentTarget as HTMLElement | null;
  if (!target) return;
  const rect = target.getBoundingClientRect();
  const tooltipWidth = 288;
  const tooltipHeightEstimate = 220;
  const viewportPadding = 16;
  const left = Math.min(
    Math.max(rect.left + rect.width / 2, viewportPadding + tooltipWidth / 2),
    window.innerWidth - viewportPadding - tooltipWidth / 2,
  );
  const canShowBelow =
    rect.bottom + 10 + tooltipHeightEstimate < window.innerHeight;

  snapshotHoverTooltip.value = {
    snapshot,
    left,
    top: canShowBelow
      ? rect.bottom + 10
      : Math.max(rect.top - 10, viewportPadding),
    placement: canShowBelow ? "bottom" : "top",
  };
}

function scheduleSnapshotHoverTooltipHide() {
  cancelSnapshotHoverTooltipHide();
  snapshotHoverTooltipHideTimer = setTimeout(() => {
    snapshotHoverTooltip.value = null;
  }, 120);
}

function startDetailAutoRefresh() {
  stopDetailAutoRefresh();
  if (
    !showDetailModal.value ||
    !selectedTask.value ||
    !detailAutoRefresh.value
  ) {
    return;
  }
  detailRefreshTimer.value = setInterval(() => {
    refreshCurrentDetailTab(true);
  }, detailRefreshInterval.value * 1000);
}

watch(
  [detailAutoRefresh, detailRefreshInterval, detailTab, showDetailModal],
  () => {
    startDetailAutoRefresh();
  },
);

onUnmounted(() => {
  stopDetailAutoRefresh();
  cancelSnapshotHelpTooltipHide();
  cancelSnapshotHoverTooltipHide();
});

async function fetchTasks() {
  isLoading.value = true;
  try {
    const response = await backupTasksApi.list({ page_size: 500 });
    tasks.value = response.data.results || response.data;
  } catch (error) {
    console.error("Failed to fetch tasks:", error);
  } finally {
    isLoading.value = false;
  }
}

async function openTaskDetail(task: BackupTask) {
  selectedTask.value = task;
  detailTab.value = "overview";
  showDetailModal.value = true;
  detailLoading.value = true;
  selectedTaskSnapshots.value = [];
  selectedTaskRuns.value = [];
  selectedSnapshot.value = null;
  selectedSnapshotFiles.value = [];
  snapshotFilesError.value = "";
  try {
    await refreshTaskOverview(false);
  } finally {
    detailLoading.value = false;
  }
  startDetailAutoRefresh();
}

async function selectDetailTab(tab: "overview" | "snapshots" | "tasks") {
  detailTab.value = tab;
  await refreshCurrentDetailTab();
}

async function refreshCurrentDetailTab(silent = false) {
  if (!selectedTask.value) return;
  if (currentDetailTabLoading.value) return;
  if (detailTab.value === "overview") {
    await refreshTaskOverview(silent);
  } else if (detailTab.value === "snapshots") {
    await loadTaskSnapshots();
  } else if (detailTab.value === "tasks") {
    await loadTaskRuns();
  }
}

async function refreshTaskOverview(silent = false) {
  if (!selectedTask.value) return;
  if (silent || !detailLoading.value) {
    detailRefreshing.value = true;
  }
  try {
    const detailRes = await backupTasksApi.detail(selectedTask.value.id);
    selectedTask.value = detailRes.data;
  } catch (error) {
    console.error("Failed to fetch task detail:", error);
  } finally {
    if (silent || !detailLoading.value) {
      detailRefreshing.value = false;
    }
  }
}

async function loadTaskSnapshots() {
  if (!selectedTask.value) return;
  snapshotsLoading.value = true;
  try {
    const pageSize = 500;
    let page = 1;
    const snapshots: any[] = [];
    while (selectedTask.value) {
      const response = await backupTasksApi.snapshots(selectedTask.value.id, {
        page,
        page_size: pageSize,
      });
      const data = response.data;
      const results = data.results || data || [];
      snapshots.push(...results);
      if (!data.next || results.length < pageSize) break;
      page += 1;
    }
    selectedTaskSnapshots.value = snapshots;
    if (
      selectedSnapshot.value &&
      !isSnapshotBrowsable(selectedSnapshot.value)
    ) {
      selectedSnapshot.value = null;
      selectedSnapshotFiles.value = [];
      snapshotFilesError.value = "";
    }
    if (
      selectedSnapshot.value &&
      collapseNoChangeSnapshots.value &&
      isNoChangeSnapshotReference(selectedSnapshot.value)
    ) {
      selectedSnapshot.value = null;
      selectedSnapshotFiles.value = [];
      snapshotFilesError.value = "";
    }
  } catch (error) {
    console.error("Failed to fetch snapshots:", error);
  } finally {
    snapshotsLoading.value = false;
  }
}

async function loadTaskRuns() {
  if (!selectedTask.value) return;
  runsLoading.value = true;
  try {
    const response = await backupTasksApi.runs(selectedTask.value.id, {
      page_size: 100,
    });
    selectedTaskRuns.value = response.data.results || response.data || [];
  } catch (error) {
    console.error("Failed to fetch task runs:", error);
  } finally {
    runsLoading.value = false;
  }
}

async function syncSnapshotsFromKopia() {
  if (!selectedTask.value) return;
  snapshotOperationLoading.value = true;
  try {
    await backupTasksApi.syncSnapshots(selectedTask.value.id);
    appStore.success(t("backupTasks.detail.syncSnapshotsDispatched"));
  } catch (error) {
    appStore.error(getApiErrorMessage(error, t("common.updateFailed")));
  } finally {
    snapshotOperationLoading.value = false;
  }
}

async function evaluateRetentionNow() {
  if (!selectedTask.value) return;
  if (!window.confirm(t("backupTasks.detail.applyRetentionConfirm"))) return;
  snapshotOperationLoading.value = true;
  try {
    await backupTasksApi.evaluateRetention(selectedTask.value.id, {
      delete: true,
    });
    appStore.success(t("backupTasks.detail.retentionDispatched"));
    await loadTaskSnapshots();
  } catch (error) {
    appStore.error(getApiErrorMessage(error, t("common.updateFailed")));
  } finally {
    snapshotOperationLoading.value = false;
  }
}

async function runKopiaMaintenanceNow() {
  if (!selectedTask.value) return;
  snapshotOperationLoading.value = true;
  try {
    await backupTasksApi.runMaintenance(selectedTask.value.id, {
      full: true,
    });
    appStore.success(t("backupTasks.detail.maintenanceDispatched"));
  } catch (error) {
    appStore.error(getApiErrorMessage(error, t("common.updateFailed")));
  } finally {
    snapshotOperationLoading.value = false;
  }
}

async function loadSnapshotFiles(snapshot: any, path = "") {
  if (!snapshot?.id) return;
  if (!isSnapshotBrowsable(snapshot)) {
    appStore.error(t("backupTasks.detail.snapshotNotBrowsable"));
    return;
  }
  snapshotFilesError.value = "";
  if (!path) {
    snapshotFilesLoading.value = true;
  } else {
    loadingSnapshotPaths.value = new Set([...loadingSnapshotPaths.value, path]);
  }
  try {
    const response = await backupTasksApi.listFiles(snapshot.id, path);
    selectedSnapshot.value = snapshot;
    const files = response.data.results || response.data || [];
    if (!path) {
      selectedSnapshotFiles.value = normalizeSnapshotFiles(files, "");
      expandedSnapshotPaths.value = new Set();
      selectedSnapshotPaths.value = new Set();
      loadingSnapshotPaths.value = new Set();
    } else {
      mergeSnapshotChildren(path, files);
      expandedSnapshotPaths.value = new Set([
        ...expandedSnapshotPaths.value,
        path,
      ]);
    }
  } catch (error) {
    const message = getApiErrorMessage(
      error,
      t("backupTasks.detail.snapshotFilesLoadFailed"),
    );
    appStore.error(message);
    if (!path) {
      snapshotFilesError.value = message;
      selectedSnapshot.value = snapshot;
      selectedSnapshotFiles.value = [];
      expandedSnapshotPaths.value = new Set();
      selectedSnapshotPaths.value = new Set();
    }
  } finally {
    if (!path) {
      snapshotFilesLoading.value = false;
    } else {
      const next = new Set(loadingSnapshotPaths.value);
      next.delete(path);
      loadingSnapshotPaths.value = next;
    }
  }
}

function normalizeSnapshotFiles(files: any[], parentPath: string) {
  return files.map((file: any) => {
    const rawPath = file.relative_path || file.path || file.file_name || "";
    const rawCleanPath = String(rawPath)
      .replace(/^\/+/, "")
      .replace(/\/+$/, "");
    const cleanPath =
      parentPath && rawCleanPath && !rawCleanPath.startsWith(`${parentPath}/`)
        ? `${parentPath}/${rawCleanPath}`
        : rawCleanPath;
    const name =
      file.file_name ||
      rawCleanPath.split("/").filter(Boolean).pop() ||
      cleanPath;
    const type = file.type || file.entry_type || "";
    const isDirectory =
      file.is_dir === true ||
      type === "d" ||
      type === "dir" ||
      type === "directory";
    return {
      ...file,
      id: file.id || cleanPath || `${parentPath}/${name}`,
      relative_path: cleanPath,
      file_name: name,
      parent_path: parentPath,
      depth: parentPath ? parentPath.split("/").filter(Boolean).length + 1 : 0,
      is_dir: isDirectory,
      children_loaded: false,
    };
  });
}

function mergeSnapshotChildren(parentPath: string, files: any[]) {
  const children = normalizeSnapshotFiles(files, parentPath);
  const withoutOldChildren = selectedSnapshotFiles.value.filter(
    (file) => file.parent_path !== parentPath,
  );
  const parentIndex = withoutOldChildren.findIndex(
    (file) => file.relative_path === parentPath,
  );
  if (parentIndex === -1) {
    selectedSnapshotFiles.value = withoutOldChildren;
    return;
  }
  withoutOldChildren[parentIndex] = {
    ...withoutOldChildren[parentIndex],
    children_loaded: true,
  };
  withoutOldChildren.splice(parentIndex + 1, 0, ...children);
  selectedSnapshotFiles.value = withoutOldChildren;
}

function visibleSnapshotFiles() {
  return selectedSnapshotFiles.value.filter((file) => {
    if (!file.parent_path) return true;
    const ancestors = file.parent_path.split("/").filter(Boolean);
    let current = "";
    for (const part of ancestors) {
      current = current ? `${current}/${part}` : part;
      if (!expandedSnapshotPaths.value.has(current)) return false;
    }
    return true;
  });
}

async function toggleSnapshotDirectory(file: any) {
  if (!file.is_dir) return;
  const path = file.relative_path;
  const next = new Set(expandedSnapshotPaths.value);
  if (next.has(path)) {
    next.delete(path);
    expandedSnapshotPaths.value = next;
    return;
  }
  if (!file.children_loaded && selectedSnapshot.value) {
    await loadSnapshotFiles(selectedSnapshot.value, path);
    return;
  }
  next.add(path);
  expandedSnapshotPaths.value = next;
}

function toggleSnapshotPathSelection(file: any) {
  const path = file.relative_path;
  const next = new Set(selectedSnapshotPaths.value);
  if (next.has(path)) {
    next.delete(path);
  } else {
    next.add(path);
  }
  selectedSnapshotPaths.value = next;
}

async function fetchStats() {
  try {
    const response = await backupTasksApi.stats();
    stats.value = response.data;
  } catch (error) {
    console.error("Failed to fetch stats:", error);
  }
}

async function fetchNodesAndRepos() {
  try {
    const [nodesRes, reposRes, sourcesRes, policiesRes] = await Promise.all([
      nodesApi.list({ page_size: 100 }),
      repositoriesApi.list({ page_size: 100 }),
      sourceResourcesApi.list({ page_size: 100 }),
      policiesApi.list({ page_size: 100, is_active: true }),
    ]);
    nodes.value = nodesRes.data.results || nodesRes.data;
    repositories.value = reposRes.data.results || reposRes.data;
    sourceResources.value = sourcesRes.data.results || sourcesRes.data;
    backupPolicies.value = policiesRes.data.results || policiesRes.data;
  } catch (error) {
    console.error("Failed to fetch nodes/repos/source resources:", error);
  }
}

async function executeTask(task: BackupTask) {
  try {
    await backupTasksApi.execute(task.id);
    appStore.showToast({
      type: "success",
      title: t("common.success"),
      message: t("backupTasks.actions.runStarted"),
    });
    await fetchTasks();
    await fetchStats();
  } catch (error) {
    console.error("Failed to execute task:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(error, t("backupTasks.actions.runFailed")),
    });
  }
}

async function toggleTaskEnabled(task: BackupTask) {
  try {
    if (task.is_enabled === false) {
      await backupTasksApi.enable(task.id);
    } else {
      await backupTasksApi.disable(task.id);
    }
    await fetchTasks();
    if (selectedTask.value?.id === task.id) {
      selectedTask.value = {
        ...selectedTask.value,
        is_enabled: task.is_enabled === false,
      };
    }
  } catch (error) {
    console.error("Failed to update task enabled state:", error);
    appStore.error(getApiErrorMessage(error, t("common.updateFailed")));
  }
}

async function cancelTask(task: BackupTask) {
  try {
    await backupTasksApi.cancel(task.id);
    await fetchTasks();
  } catch (error) {
    console.error("Failed to cancel task:", error);
  }
}

async function deleteTask(task: BackupTask) {
  if (
    !window.confirm(t("backupTasks.actions.deleteConfirm", { name: task.name }))
  ) {
    return;
  }
  try {
    await backupTasksApi.delete(task.id);
    if (selectedTask.value?.id === task.id) {
      showDetailModal.value = false;
      selectedTask.value = null;
    }
    await fetchTasks();
    await fetchStats();
  } catch (error) {
    console.error("Failed to delete task:", error);
    appStore.error(getApiErrorMessage(error, t("common.deleteFailed")));
  }
}

async function createTask() {
  try {
    await backupTasksApi.create(newTask.value);
    showCreateModal.value = false;
    newTask.value = {
      name: "",
      source_resource: "",
      target_repository: "",
      backup_paths: [],
      task_type: "incremental",
      priority: "normal",
      retention_days: 30,
      compression_enabled: true,
      encryption_enabled: true,
    };
    await fetchTasks();
    await fetchStats();
  } catch (error) {
    console.error("Failed to create task:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(error, t("common.createFailed")),
    });
  }
}

async function createTaskFromWizard(payload: BackupTaskCreateData) {
  newTask.value = payload;
  await createTask();
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

function sourceForTask(task: BackupTask | null) {
  if (!task?.source_resource) return null;
  return (
    sourceResources.value.find(
      (source) => source.id === task.source_resource,
    ) || null
  );
}

function repositoryForTask(task: BackupTask | null) {
  if (!task?.target_repository) return null;
  return (
    repositories.value.find((repo) => repo.id === task.target_repository) ||
    null
  );
}

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
    failed: ExclamationTriangleIcon,
    paused: PauseIcon,
    cancelled: XCircleIcon,
  };
  return icons[status] || ClockIcon;
}

function canRunTask(task: BackupTask) {
  return task.status !== "running" && task.is_enabled !== false;
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

function currentLocale() {
  return String(locale.value || "en");
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
        date && !Number.isNaN(date.getTime()) ? localMonthKey(date) : "unknown",
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

const selectedSource = computed(() => {
  return sourceForTask(selectedTask.value);
});

const selectedRepository = computed(() => {
  return repositoryForTask(selectedTask.value);
});

const syncProxies = computed(() =>
  nodes.value.filter((node) => node.role === "sync"),
);

function canUseAutoPlacementForTask(task: BackupTask | null) {
  const source = sourceForTask(task);
  const repo = repositoryForTask(task);
  if (!source || !repo) return false;
  return source.resource_type !== "local" && repo.repo_type !== "local";
}

function sourceDetailRows(source: SourceResource | null) {
  if (!source) return [];
  const config = (source.config || {}) as Record<string, any>;
  const rows = [
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

function repositoryDetailRows(repo: Repository | null) {
  if (!repo) return [];
  const config = repo.config || {};
  const rows = [
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

onMounted(() => {
  fetchTasks();
  fetchStats();
  fetchNodesAndRepos();
});
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">
          {{ t("backupTasks.title") }}
        </h1>
        <p class="text-slate-500 mt-1">{{ t("backupTasks.subtitle") }}</p>
      </div>
      <button
        @click="showCreateModal = true"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t("backupTasks.createTask") }}
      </button>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
        <p class="text-xs text-foreground-secondary">{{ t("common.total") }}</p>
        <p class="text-xl font-bold text-foreground mt-1">
          {{ taskStats.total_tasks }}
        </p>
      </div>
      <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
        <p class="text-xs text-foreground-secondary">
          {{ t("backupTasks.status.running") }}
        </p>
        <p class="text-xl font-bold text-indigo-600 mt-1">
          {{ taskStats.running_tasks }}
        </p>
      </div>
      <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
        <p class="text-xs text-foreground-secondary">
          {{ t("backupTasks.status.completed") }}
        </p>
        <p class="text-xl font-bold text-emerald-600 mt-1">
          {{ taskStats.completed_tasks }}
        </p>
      </div>
      <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
        <p class="text-xs text-foreground-secondary">
          {{ t("backupTasks.status.failed") }}
        </p>
        <p class="text-xl font-bold text-red-600 mt-1">
          {{ taskStats.failed_tasks }}
        </p>
      </div>
      <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
        <p class="text-xs text-foreground-secondary">
          {{ t("backupTasks.progress.size") }}
        </p>
        <p class="text-xl font-bold text-pink-800 mt-1">
          {{ totalBackupSize ? formatBytes(totalBackupSize) : "0 B" }}
        </p>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex flex-wrap items-center gap-3">
        <div class="relative flex-1 min-w-[200px]">
          <MagnifyingGlassIcon
            class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
          />
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('common.search')"
            class="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <select
          v-model="selectedStatus"
          class="px-3 py-2 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">
            {{ t("common.status") }}: {{ t("common.all") }}
          </option>
          <option value="pending">{{ t("backupTasks.status.pending") }}</option>
          <option value="running">{{ t("backupTasks.status.running") }}</option>
          <option value="completed">
            {{ t("backupTasks.status.completed") }}
          </option>
          <option value="failed">{{ t("backupTasks.status.failed") }}</option>
        </select>
        <button
          @click="fetchTasks"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm text-foreground-secondary border border-border rounded-lg hover:bg-hover"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t("common.refresh") }}
        </button>
      </div>
    </div>

    <!-- Tasks List -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <div
        class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"
      />
    </div>

    <div
      v-else-if="filteredTasks.length === 0"
      class="bg-card rounded-xl border border-border p-12 text-center"
    >
      <div
        class="w-16 h-16 bg-background-tertiary rounded-full flex items-center justify-center mx-auto mb-4"
      >
        <CloudArrowUpIcon class="w-8 h-8 text-slate-400" />
      </div>
      <h3 class="text-lg font-medium text-foreground mb-1">
        {{ t("backupTasks.empty.title") }}
      </h3>
      <p class="text-foreground-secondary">
        {{ t("backupTasks.empty.description") }}
      </p>
    </div>

    <div v-else class="bg-card rounded-xl border border-border shadow-sm">
      <div class="overflow-x-auto">
        <table
          class="w-full table-fixed"
          :style="{ minWidth: backupTaskTable.tableMinWidth.value }"
        >
          <colgroup>
            <col
              v-for="column in backupTaskColumns"
              :key="column.key"
              :style="backupTaskTable.columnStyle(column.key)"
            />
          </colgroup>
          <thead class="bg-background-secondary border-b border-border">
            <tr>
              <ResizableSortableTh
                v-for="column in backupTaskColumns"
                :key="column.key"
                :column-key="column.key"
                :label="column.label"
                :style-value="backupTaskTable.columnStyle(column.key)"
                :sortable="column.sortable !== false"
                :active="backupTaskTable.sort.value.key === column.key"
                :align="column.align"
                :sort-icon="backupTaskTable.getSortIcon(column.key)"
                :resizing="backupTaskTable.resizingColumn.value === column.key"
                @sort="
                  backupTaskTable.toggleSort($event as BackupTaskColumnKey)
                "
                @resize-start="
                  (key, event) =>
                    backupTaskTable.startResize(
                      key as BackupTaskColumnKey,
                      event,
                    )
                "
                @resize-reset="
                  backupTaskTable.resetColumnWidth(
                    $event as BackupTaskColumnKey,
                  )
                "
              />
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 dark:divide-slate-700">
            <tr
              v-for="task in paginatedTasks"
              :key="task.id"
              class="hover:bg-hover transition-colors"
            >
              <td
                class="px-4 py-4"
                :style="backupTaskTable.columnStyle('name')"
              >
                <div class="flex items-center gap-3">
                  <div
                    :class="[
                      'w-9 h-9 rounded-lg flex items-center justify-center',
                      task.status === 'running'
                        ? 'bg-indigo-100'
                        : task.status === 'completed'
                          ? 'bg-emerald-100'
                          : task.status === 'failed'
                            ? 'bg-red-100'
                            : 'bg-slate-100',
                    ]"
                  >
                    <CloudArrowUpIcon
                      :class="[
                        'w-5 h-5',
                        task.status === 'running'
                          ? 'text-indigo-600'
                          : task.status === 'completed'
                            ? 'text-emerald-600'
                            : task.status === 'failed'
                              ? 'text-red-600'
                              : 'text-slate-400',
                      ]"
                    />
                  </div>
                  <div>
                    <div class="flex items-center gap-2">
                      <span
                        :class="[
                          'h-2.5 w-2.5 rounded-full shrink-0',
                          task.is_enabled === false
                            ? 'bg-red-500'
                            : 'bg-emerald-500',
                        ]"
                        :title="
                          task.is_enabled === false
                            ? t('backupTasks.disabled')
                            : t('backupTasks.enabled')
                        "
                      />
                      <button
                        type="button"
                        class="text-left text-sm font-medium text-foreground hover:text-primary"
                        @click="openTaskDetail(task)"
                      >
                        {{ task.name }}
                      </button>
                    </div>
                    <p class="text-xs text-foreground-secondary">
                      {{ t(`backupTasks.types.${task.task_type || "full"}`) }} ·
                      {{ task.snapshot_count || 0 }}
                      {{ t("backupTasks.snapshots") }}
                    </p>
                  </div>
                </div>
              </td>
              <td
                class="px-4 py-4"
                :style="backupTaskTable.columnStyle('policy')"
              >
                <p class="text-sm font-medium text-foreground">
                  {{ task.schedule_name || t("backupTasks.form.noPolicy") }}
                </p>
                <p
                  class="mt-1 max-w-[260px] truncate text-xs text-foreground-muted"
                >
                  {{ getTaskPolicySummary(task) }}
                </p>
              </td>
              <td
                class="px-4 py-4"
                :style="backupTaskTable.columnStyle('source')"
              >
                <p class="text-sm text-foreground">
                  {{ task.source_resource_name || "-" }}
                </p>
                <p class="text-xs text-foreground-muted">
                  {{ task.execution_node_name || "-" }}
                </p>
              </td>
              <td
                class="px-4 py-4"
                :style="backupTaskTable.columnStyle('repository')"
              >
                <p class="text-sm text-foreground">
                  {{ task.target_repository_name || "-" }}
                </p>
                <p class="text-xs text-foreground-muted">
                  {{ task.target_repository_type || "-" }}
                </p>
              </td>
              <td
                class="px-4 py-4"
                :style="backupTaskTable.columnStyle('status')"
              >
                <span
                  :class="[
                    'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium',
                    getStatusColor(task.status),
                  ]"
                >
                  <component
                    :is="getStatusIcon(task.status)"
                    class="w-3.5 h-3.5"
                  />
                  {{ t(`backupTasks.status.${task.status}`) }}
                </span>
              </td>
              <td
                class="px-4 py-4 text-sm text-foreground-secondary"
                :style="backupTaskTable.columnStyle('last_backup')"
              >
                {{ formatDateTime(task.last_run_time || task.completed_at) }}
              </td>
              <td
                class="px-4 py-4 text-sm text-foreground-secondary"
                :style="backupTaskTable.columnStyle('next_backup')"
              >
                {{ formatDateTime(task.next_run_time) }}
              </td>
              <td
                class="px-4 py-4 text-right"
                :style="backupTaskTable.columnStyle('actions')"
              >
                <div class="flex items-center justify-end gap-2">
                  <button
                    v-if="canRunTask(task)"
                    @click="executeTask(task)"
                    class="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                    :title="t('backupTasks.actions.runNow')"
                  >
                    <PlayIcon class="w-4 h-4" />
                  </button>
                  <button
                    @click="toggleTaskEnabled(task)"
                    :class="[
                      'p-1.5 rounded-lg transition-colors',
                      task.is_enabled === false
                        ? 'text-emerald-600 hover:bg-emerald-50'
                        : 'text-amber-600 hover:bg-amber-50',
                    ]"
                    :title="
                      task.is_enabled === false
                        ? t('backupTasks.actions.enable')
                        : t('backupTasks.actions.disable')
                    "
                  >
                    <PowerIcon class="w-4 h-4" />
                  </button>
                  <button
                    v-if="task.status === 'running'"
                    @click="cancelTask(task)"
                    class="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    :title="t('backupTasks.actions.cancel')"
                  >
                    <StopIcon class="w-4 h-4" />
                  </button>
                  <button
                    @click="openTaskDetail(task)"
                    class="p-1.5 text-slate-500 hover:bg-background-tertiary rounded-lg transition-colors"
                    :title="t('common.details')"
                  >
                    <EyeIcon class="w-4 h-4" />
                  </button>
                  <button
                    :disabled="task.status === 'running'"
                    @click="openEditTask(task)"
                    class="p-1.5 text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    :title="t('backupTasks.edit.title')"
                  >
                    <PencilSquareIcon class="w-4 h-4" />
                  </button>
                  <button
                    @click="deleteTask(task)"
                    class="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                    :title="t('backupTasks.actions.delete')"
                  >
                    <TrashIcon class="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <Pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total-items="filteredTasks.length"
      />
    </div>

    <BackupTaskWizard
      v-if="showCreateModal"
      :sources="sourceResources"
      :repositories="repositories"
      :policies="backupPolicies"
      :nodes="nodes"
      @close="showCreateModal = false"
      @save="createTaskFromWizard"
    />

    <!-- Legacy Create Modal -->
    <Teleport to="body">
      <div
        v-if="false && showCreateModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div
          class="absolute inset-0 bg-black/50"
          @click="showCreateModal = false"
        />
        <div
          class="relative modal-surface rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        >
          <div
            class="sticky top-0 modal-surface px-6 py-4 border-b border-border flex items-center justify-between"
          >
            <h2 class="text-lg font-semibold text-foreground">
              {{ t("backupTasks.createTask") }}
            </h2>
            <button
              @click="showCreateModal = false"
              class="p-1 hover:bg-background-tertiary rounded-lg"
            >
              <XCircleIcon class="w-5 h-5 text-slate-400" />
            </button>
          </div>
          <div class="p-6 space-y-4">
            <div>
              <label
                class="block text-sm font-medium text-foreground-secondary mb-1"
                >{{ t("common.name") }}</label
              >
              <input
                v-model="newTask.name"
                type="text"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary mb-1"
                  >{{ t("backupTasks.form.sourceNode") }}</label
                >
                <select
                  v-model="newTask.source_resource"
                  class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option :value="0">Select</option>
                  <option
                    v-for="source in sourceResources"
                    :key="source.id"
                    :value="source.id"
                  >
                    {{ source.name }}
                  </option>
                </select>
              </div>
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary mb-1"
                  >{{ t("backupTasks.form.repository") }}</label
                >
                <select
                  v-model="newTask.target_repository"
                  class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option :value="0">Select</option>
                  <option
                    v-for="repo in repositories"
                    :key="repo.id"
                    :value="repo.id"
                  >
                    {{ repo.name }}
                  </option>
                </select>
              </div>
            </div>
            <div>
              <label
                class="block text-sm font-medium text-foreground-secondary mb-1"
                >{{ t("backupTasks.form.taskType") }}</label
              >
              <select
                v-model="newTask.task_type"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="full">{{ t("backupTasks.types.full") }}</option>
                <option value="incremental">
                  {{ t("backupTasks.types.incremental") }}
                </option>
              </select>
            </div>
          </div>
          <div
            class="sticky bottom-0 modal-surface px-6 py-4 border-t border-border flex justify-end gap-3"
          >
            <button
              @click="showCreateModal = false"
              class="px-4 py-2 text-sm text-foreground-secondary border border-border rounded-lg hover:bg-hover"
            >
              {{ t("common.cancel") }}
            </button>
            <button
              @click="createTask"
              class="px-4 py-2 text-sm text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
            >
              {{ t("common.create") }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Edit Modal -->
    <Teleport to="body">
      <div
        v-if="showEditModal && editingTask"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div
          class="absolute inset-0 bg-black/50"
          @click="showEditModal = false"
        />
        <form
          class="relative modal-surface w-full max-w-5xl max-h-[90vh] rounded-xl shadow-xl border border-border overflow-hidden flex flex-col"
          @submit.prevent="updateTask"
        >
          <div
            class="px-6 py-4 border-b border-border flex items-start justify-between gap-4"
          >
            <div>
              <h2 class="text-lg font-semibold text-foreground">
                {{ t("backupTasks.edit.title") }}
              </h2>
              <p class="mt-1 text-sm text-foreground-secondary">
                {{ t("backupTasks.edit.subtitle") }}
              </p>
            </div>
            <button
              type="button"
              @click="showEditModal = false"
              class="p-2 hover:bg-background-tertiary rounded-lg"
            >
              <XCircleIcon class="w-5 h-5 text-slate-400" />
            </button>
          </div>

          <div
            v-if="editLoading"
            class="p-10 text-center text-foreground-secondary"
          >
            {{ t("common.loading") }}
          </div>

          <div v-else class="p-6 overflow-y-auto space-y-5">
            <div
              class="rounded-lg border border-border bg-background-secondary p-4"
            >
              <div class="mb-4 flex items-center gap-2">
                <CloudArrowUpIcon class="h-5 w-5 text-primary" />
                <h3 class="font-semibold text-foreground">
                  {{ t("backupTasks.edit.sections.readonly") }}
                </h3>
              </div>
              <p class="mb-4 text-xs text-foreground-secondary">
                {{ t("backupTasks.edit.sections.readonlyDesc") }}
              </p>
              <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <div class="rounded-lg border border-border bg-card p-3">
                  <div class="mb-3 flex items-center gap-2">
                    <FolderIcon class="h-4 w-4 text-primary" />
                    <div>
                      <p class="text-sm font-semibold text-foreground">
                        {{ t("backupTasks.backupSource") }}
                      </p>
                      <p class="text-xs text-foreground-muted">
                        {{
                          sourceForTask(editingTask)?.name ||
                          editingTask.source_resource_name ||
                          "-"
                        }}
                      </p>
                    </div>
                  </div>
                  <div class="grid grid-cols-1 gap-2 md:grid-cols-2">
                    <div
                      v-for="[label, value] in sourceDetailRows(
                        sourceForTask(editingTask),
                      )"
                      :key="label"
                      class="rounded-md border border-border bg-background/60 p-2"
                    >
                      <p class="text-xs text-foreground-secondary">
                        {{ label }}
                      </p>
                      <p
                        class="mt-0.5 break-all text-sm font-medium text-foreground"
                      >
                        {{ value }}
                      </p>
                    </div>
                  </div>
                  <div
                    class="mt-3 rounded-md border border-border bg-background/60 p-2"
                  >
                    <p class="text-xs text-foreground-secondary">
                      {{ t("backupTasks.form.sourcePaths") }}
                    </p>
                    <div
                      v-if="editingTask.backup_paths?.length"
                      class="mt-1 space-y-1.5"
                    >
                      <p
                        v-for="(path, index) in editingTask.backup_paths"
                        :key="index"
                        class="rounded-md border border-border bg-background px-2 py-1.5 font-mono text-xs text-foreground"
                      >
                        {{ path }}
                      </p>
                    </div>
                    <p v-else class="mt-1 text-sm text-foreground-muted">-</p>
                  </div>
                </div>
                <div class="rounded-lg border border-border bg-card p-3">
                  <div class="mb-3 flex items-center gap-2">
                    <ServerStackIcon class="h-4 w-4 text-primary" />
                    <div>
                      <p class="text-sm font-semibold text-foreground">
                        {{ t("backupTasks.backupRepository") }}
                      </p>
                      <p class="text-xs text-foreground-muted">
                        {{
                          repositoryForTask(editingTask)?.name ||
                          editingTask.target_repository_name ||
                          "-"
                        }}
                      </p>
                    </div>
                  </div>
                  <div class="grid grid-cols-1 gap-2 md:grid-cols-2">
                    <div
                      v-for="[label, value] in repositoryDetailRows(
                        repositoryForTask(editingTask),
                      )"
                      :key="label"
                      class="rounded-md border border-border bg-background/60 p-2"
                    >
                      <p class="text-xs text-foreground-secondary">
                        {{ label }}
                      </p>
                      <p
                        class="mt-0.5 break-all text-sm font-medium text-foreground"
                      >
                        {{ value }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <p class="mt-3 text-xs text-foreground-secondary">
                {{ t("backupTasks.edit.readonlyHint") }}
              </p>
            </div>

            <section class="rounded-lg border border-border bg-card p-4">
              <div class="mb-2 flex items-center gap-2">
                <DocumentIcon class="h-5 w-5 text-primary" />
                <h3 class="font-semibold text-foreground">
                  {{ t("backupTasks.detail.basic") }}
                </h3>
              </div>
              <p class="mb-4 text-xs text-foreground-secondary">
                {{ t("backupTasks.edit.sections.basicDesc") }}
              </p>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("backupTasks.form.taskName") }}
                  </label>
                  <input
                    v-model="editForm.name"
                    type="text"
                    :placeholder="t('backupTasks.edit.placeholders.name')"
                    class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    required
                  />
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{ t("backupTasks.edit.fieldDescriptions.name") }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("backupTasks.form.priority") }}
                  </label>
                  <select
                    v-model="editForm.priority"
                    class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="low">Low</option>
                    <option value="normal">Normal</option>
                    <option value="high">High</option>
                  </select>
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{ t("backupTasks.edit.fieldDescriptions.priority") }}
                  </p>
                </div>
                <div class="md:col-span-2">
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("common.description") }}
                  </label>
                  <textarea
                    v-model="editForm.description"
                    rows="3"
                    :placeholder="
                      t('backupTasks.edit.placeholders.description')
                    "
                    class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{ t("backupTasks.edit.fieldDescriptions.description") }}
                  </p>
                </div>
                <label
                  class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground md:col-span-2"
                >
                  <input
                    v-model="editForm.is_enabled"
                    type="checkbox"
                    class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <span>
                    <span class="font-medium">{{
                      t("backupTasks.enabled")
                    }}</span>
                    <span
                      class="mt-1 block text-xs leading-5 text-foreground-muted"
                    >
                      {{ t("backupTasks.edit.fieldDescriptions.enabled") }}
                    </span>
                  </span>
                </label>
              </div>
            </section>

            <section class="rounded-lg border border-border bg-card p-4">
              <div class="mb-2 flex items-center gap-2">
                <ServerStackIcon class="h-5 w-5 text-primary" />
                <h3 class="font-semibold text-foreground">
                  {{ t("backupTasks.execution.title") }}
                </h3>
              </div>
              <p class="mb-4 text-xs text-foreground-secondary">
                {{ t("backupTasks.execution.description") }}
              </p>
              <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("backupTasks.execution.title") }}
                  </label>
                  <select
                    v-model="editForm.execution_mode"
                    :disabled="!canUseAutoPlacementForTask(editingTask)"
                    class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <option value="pinned">
                      {{ t("backupTasks.executionModes.pinned") }}
                    </option>
                    <option value="preferred">
                      {{ t("backupTasks.executionModes.preferred") }}
                    </option>
                    <option value="auto">
                      {{ t("backupTasks.executionModes.auto") }}
                    </option>
                  </select>
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{
                      canUseAutoPlacementForTask(editingTask)
                        ? t("backupTasks.execution.description")
                        : t("backupTasks.execution.autoUnavailable")
                    }}
                  </p>
                </div>
                <div v-if="editForm.execution_mode === 'preferred'">
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("backupTasks.execution.preferredProxy") }}
                  </label>
                  <select
                    v-model="editForm.preferred_execution_node"
                    class="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option :value="null">
                      {{ t("backupTasks.execution.selectPreferredProxy") }}
                    </option>
                    <option
                      v-for="node in syncProxies"
                      :key="node.id"
                      :value="node.id"
                    >
                      {{ node.name }} · {{ node.status }}
                    </option>
                  </select>
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{ t("backupTasks.execution.preferredProxyDesc") }}
                  </p>
                </div>
              </div>
            </section>

            <section class="rounded-lg border border-border bg-card p-4">
              <div class="mb-2 flex items-center gap-2">
                <ClockIcon class="h-5 w-5 text-primary" />
                <h3 class="font-semibold text-foreground">
                  {{ t("backupTasks.detail.scheduleRetention") }}
                </h3>
              </div>
              <p class="mb-4 text-xs text-foreground-secondary">
                {{ t("backupTasks.edit.sections.scheduleRetentionDesc") }}
              </p>
              <div class="space-y-5">
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("backupTasks.form.policy") }}
                  </label>
                  <select
                    v-model="editForm.schedule"
                    @change="
                      ((editForm.retention_mode = editForm.schedule
                        ? 'policy'
                        : 'custom'),
                      (editForm.override_schedule = false))
                    "
                    class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option :value="null">
                      {{ t("backupTasks.form.noPolicy") }}
                    </option>
                    <option
                      v-for="policy in backupPolicies"
                      :key="policy.id"
                      :value="policy.id"
                    >
                      {{ policy.name }}
                    </option>
                  </select>
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{ t("backupTasks.edit.fieldDescriptions.policy") }}
                  </p>
                </div>

                <div
                  v-if="selectedEditPolicy"
                  class="grid grid-cols-1 gap-3 md:grid-cols-2"
                >
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3 text-sm"
                  >
                    <p class="text-xs text-foreground-muted">
                      {{ t("backupTasks.policyOverrides.schedule") }}
                    </p>
                    <p class="mt-1 font-medium text-foreground">
                      {{ editPolicyScheduleSummary }}
                    </p>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3 text-sm"
                  >
                    <p class="text-xs text-foreground-muted">
                      {{ t("backupTasks.policyOverrides.retention") }}
                    </p>
                    <p class="mt-1 font-medium text-foreground">
                      {{ editPolicyRetentionSummary }}
                    </p>
                  </div>
                </div>

                <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                  <div
                    class="rounded-lg border border-border bg-background/30 p-4 space-y-4"
                  >
                    <div class="flex items-center gap-2">
                      <ClockIcon class="h-5 w-5 text-primary" />
                      <p class="text-sm font-semibold text-foreground">
                        {{ t("backupTasks.form.schedule") }}
                      </p>
                    </div>
                    <template v-if="selectedEditPolicy">
                      <label
                        class="flex items-start gap-2 text-sm text-foreground"
                      >
                        <input
                          :checked="!editForm.override_schedule"
                          type="radio"
                          class="mt-1 border-border"
                          @change="editForm.override_schedule = false"
                        />
                        <span>
                          <span class="font-medium">
                            {{
                              t("backupTasks.policyOverrides.usePolicySchedule")
                            }}
                          </span>
                          <span
                            class="mt-1 block text-xs text-foreground-muted"
                          >
                            {{ editPolicyScheduleSummary }}
                          </span>
                        </span>
                      </label>
                      <label
                        class="flex items-start gap-2 text-sm text-foreground"
                      >
                        <input
                          :checked="editForm.override_schedule"
                          type="radio"
                          class="mt-1 border-border"
                          @change="editForm.override_schedule = true"
                        />
                        <span>
                          <span class="font-medium">
                            {{
                              t("backupTasks.policyOverrides.overrideSchedule")
                            }}
                          </span>
                          <span
                            class="mt-1 block text-xs text-foreground-muted"
                          >
                            {{
                              t(
                                "backupTasks.policyOverrides.overrideScheduleDesc",
                              )
                            }}
                          </span>
                        </span>
                      </label>
                    </template>

                    <div
                      v-if="!selectedEditPolicy || editForm.override_schedule"
                    >
                      <label
                        class="mb-1 block text-sm font-medium text-foreground"
                      >
                        {{ t("policies.schedule.title") }}
                      </label>
                      <select
                        v-model="editForm.schedule_mode"
                        class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                      >
                        <option value="manual">
                          {{ t("policies.scheduleModes.manual") }}
                        </option>
                        <option value="interval">
                          {{ t("policies.scheduleModes.interval") }}
                        </option>
                        <option value="time">
                          {{ t("policies.scheduleModes.time") }}
                        </option>
                        <option value="cron">
                          {{ t("policies.scheduleModes.cron") }}
                        </option>
                      </select>
                      <p class="mt-1 text-xs text-foreground-muted">
                        {{
                          t(
                            `policies.schedule.modeDescriptions.${editForm.schedule_mode}`,
                          )
                        }}
                      </p>
                    </div>

                    <div
                      v-if="
                        (!selectedEditPolicy || editForm.override_schedule) &&
                        editForm.schedule_mode === 'interval'
                      "
                    >
                      <label
                        class="block text-sm font-medium text-foreground mb-1"
                      >
                        {{ t("policies.schedule.interval") }}
                      </label>
                      <input
                        v-model="editForm.interval"
                        placeholder="24h"
                        class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                      <p class="mt-1 text-xs text-foreground-muted">
                        {{ t("policies.schedule.intervalDesc") }}
                      </p>
                    </div>

                    <div
                      v-if="
                        (!selectedEditPolicy || editForm.override_schedule) &&
                        editForm.schedule_mode === 'time'
                      "
                    >
                      <label
                        class="block text-sm font-medium text-foreground mb-1"
                      >
                        {{ t("policies.schedule.timeOfDay") }}
                      </label>
                      <input
                        v-model="editForm.time_of_day"
                        type="time"
                        class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                      <p class="mt-1 text-xs text-foreground-muted">
                        {{ t("policies.schedule.timeOfDayDesc") }}
                      </p>
                    </div>

                    <div
                      v-if="
                        (!selectedEditPolicy || editForm.override_schedule) &&
                        editForm.schedule_mode === 'cron'
                      "
                    >
                      <label
                        class="block text-sm font-medium text-foreground mb-1"
                      >
                        {{ t("policies.schedule.cron") }}
                      </label>
                      <input
                        v-model="editForm.cron_expression"
                        placeholder="0 2 * * *"
                        class="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                      <p class="mt-1 text-xs text-foreground-muted">
                        {{ t("policies.schedule.cronDesc") }}
                      </p>
                    </div>
                  </div>

                  <div
                    class="rounded-lg border border-border bg-background/30 p-4 space-y-4"
                  >
                    <div class="flex items-center gap-2">
                      <ShieldCheckIcon class="h-5 w-5 text-primary" />
                      <p class="text-sm font-semibold text-foreground">
                        {{ t("backupTasks.retention.title") }}
                      </p>
                    </div>
                    <template v-if="selectedEditPolicy">
                      <label
                        class="flex items-center gap-2 text-sm text-foreground"
                      >
                        <input
                          v-model="editForm.retention_mode"
                          type="radio"
                          value="policy"
                          class="border-border"
                        />
                        {{
                          t("backupTasks.policyOverrides.usePolicyRetention")
                        }}
                      </label>
                      <label
                        class="flex items-center gap-2 text-sm text-foreground"
                      >
                        <input
                          v-model="editForm.retention_mode"
                          type="radio"
                          value="custom"
                          class="border-border"
                        />
                        {{ t("backupTasks.policyOverrides.overrideRetention") }}
                      </label>
                    </template>
                    <p v-else class="text-sm text-foreground-secondary">
                      {{ t("backupTasks.policyOverrides.taskRetentionDesc") }}
                    </p>
                    <div
                      v-if="
                        editForm.retention_mode === 'custom' ||
                        !selectedEditPolicy
                      "
                      class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3"
                    >
                      <label
                        v-for="field in editRetentionFields"
                        :key="field.key"
                        class="block"
                      >
                        <span class="text-xs text-foreground-secondary">
                          {{ t(`backupTasks.retention.${field.label}`) }}
                        </span>
                        <input
                          v-model.number="editForm[field.key]"
                          type="number"
                          min="0"
                          class="mt-1 w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                        />
                        <p
                          class="mt-1 text-[11px] leading-4 text-foreground-muted"
                        >
                          {{ t(`backupTasks.retention.${field.label}Desc`) }}
                        </p>
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="rounded-lg border border-border bg-card p-4">
              <div class="mb-2 flex items-center gap-2">
                <FolderIcon class="h-5 w-5 text-primary" />
                <h3 class="font-semibold text-foreground">
                  {{ t("backupTasks.files.title") }}
                </h3>
              </div>
              <p class="mb-4 text-xs text-foreground-secondary">
                {{ t("backupTasks.edit.sections.pathsDesc") }}
              </p>
              <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("backupTasks.files.exclusionPatterns") }}
                  </label>
                  <textarea
                    v-model="editForm.exclude_patterns_text"
                    rows="6"
                    :placeholder="
                      t('backupTasks.edit.placeholders.excludePatterns')
                    "
                    class="w-full font-mono text-sm px-3 py-2 rounded-lg border border-border bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{
                      t("backupTasks.edit.fieldDescriptions.excludePatterns")
                    }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("backupTasks.files.dotIgnoreFiles") }}
                  </label>
                  <textarea
                    v-model="editForm.dot_ignore_files_text"
                    rows="4"
                    placeholder=".kopiaignore"
                    class="w-full font-mono text-sm px-3 py-2 rounded-lg border border-border bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{ t("backupTasks.files.dotIgnoreFilesDesc") }}
                  </p>
                </div>
                <div class="space-y-3">
                  <label
                    class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
                  >
                    <input
                      v-model="editForm.one_file_system"
                      type="checkbox"
                      class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
                    />
                    <span>
                      <span class="font-medium">
                        {{ t("backupTasks.files.oneFileSystem") }}
                      </span>
                      <span
                        class="mt-1 block text-xs leading-5 text-foreground-muted"
                      >
                        {{ t("backupTasks.files.oneFileSystemDesc") }}
                      </span>
                    </span>
                  </label>
                  <label
                    class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
                  >
                    <input
                      v-model="editForm.ignore_file_errors"
                      type="checkbox"
                      class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
                    />
                    <span>
                      <span class="font-medium">
                        {{ t("backupTasks.files.ignoreFileErrors") }}
                      </span>
                      <span
                        class="mt-1 block text-xs leading-5 text-foreground-muted"
                      >
                        {{ t("backupTasks.files.ignoreFileErrorsDesc") }}
                      </span>
                    </span>
                  </label>
                  <label
                    class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
                  >
                    <input
                      v-model="editForm.ignore_dir_errors"
                      type="checkbox"
                      class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
                    />
                    <span>
                      <span class="font-medium">
                        {{ t("backupTasks.files.ignoreDirErrors") }}
                      </span>
                      <span
                        class="mt-1 block text-xs leading-5 text-foreground-muted"
                      >
                        {{ t("backupTasks.files.ignoreDirErrorsDesc") }}
                      </span>
                    </span>
                  </label>
                </div>
              </div>
              <p class="mt-2 text-xs text-foreground-secondary">
                {{ t("backupTasks.edit.onePerLine") }}
              </p>
            </section>

            <section class="rounded-lg border border-border bg-card p-4">
              <div class="mb-2 flex items-center gap-2">
                <ShieldCheckIcon class="h-5 w-5 text-primary" />
                <h3 class="font-semibold text-foreground">
                  {{ t("backupTasks.detail.securityCompression") }}
                </h3>
              </div>
              <p class="mb-4 text-xs text-foreground-secondary">
                {{ t("backupTasks.edit.sections.securityDesc") }}
              </p>
              <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <label
                  class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
                >
                  <input
                    v-model="editForm.encryption_enabled"
                    type="checkbox"
                    class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <span>
                    <span class="font-medium">{{
                      t("backupTasks.detail.encryption")
                    }}</span>
                    <span
                      class="mt-1 block text-xs leading-5 text-foreground-muted"
                    >
                      {{ t("backupTasks.edit.fieldDescriptions.encryption") }}
                    </span>
                  </span>
                </label>
                <label
                  class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
                >
                  <input
                    v-model="editForm.verify_checksum"
                    type="checkbox"
                    class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <span>
                    <span class="font-medium">{{
                      t("backupTasks.detail.checksum")
                    }}</span>
                    <span
                      class="mt-1 block text-xs leading-5 text-foreground-muted"
                    >
                      {{ t("backupTasks.edit.fieldDescriptions.checksum") }}
                    </span>
                  </span>
                </label>
                <label
                  class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
                >
                  <input
                    v-model="editForm.compression_enabled"
                    type="checkbox"
                    class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <span>
                    <span class="font-medium">{{
                      t("backupTasks.detail.compression")
                    }}</span>
                    <span
                      class="mt-1 block text-xs leading-5 text-foreground-muted"
                    >
                      {{ t("backupTasks.edit.fieldDescriptions.compression") }}
                    </span>
                  </span>
                </label>
                <label
                  class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground"
                >
                  <input
                    v-model="editForm.enable_checkpoint"
                    type="checkbox"
                    class="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <span>
                    <span class="font-medium">{{
                      t("backupTasks.detail.checkpoint")
                    }}</span>
                    <span
                      class="mt-1 block text-xs leading-5 text-foreground-muted"
                    >
                      {{ t("backupTasks.edit.fieldDescriptions.checkpoint") }}
                    </span>
                  </span>
                </label>
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("backupTasks.detail.compression") }}
                  </label>
                  <select
                    v-model="editForm.compression_type"
                    :disabled="!editForm.compression_enabled"
                    class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                  >
                    <option value="zstd">zstd</option>
                    <option value="gzip">gzip</option>
                    <option value="none">{{ t("common.none") }}</option>
                  </select>
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{
                      t("backupTasks.edit.fieldDescriptions.compressionType")
                    }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("backupTasks.detail.compressionLevel") }}
                  </label>
                  <input
                    v-model.number="editForm.compression_level"
                    type="number"
                    min="0"
                    max="9"
                    :disabled="!editForm.compression_enabled"
                    :placeholder="
                      t('backupTasks.edit.placeholders.compressionLevel')
                    "
                    class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                  />
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{
                      t("backupTasks.edit.fieldDescriptions.compressionLevel")
                    }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("backupTasks.detail.checkpoint") }}
                  </label>
                  <input
                    v-model.number="editForm.checkpoint_interval_minutes"
                    type="number"
                    min="1"
                    :disabled="!editForm.enable_checkpoint"
                    :placeholder="
                      t('backupTasks.edit.placeholders.checkpointInterval')
                    "
                    class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                  />
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{
                      t("backupTasks.edit.fieldDescriptions.checkpointInterval")
                    }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("backupTasks.detail.concurrency") }}
                  </label>
                  <input
                    v-model.number="editForm.max_concurrent_files"
                    type="number"
                    min="1"
                    :placeholder="
                      t('backupTasks.edit.placeholders.concurrency')
                    "
                    class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{ t("backupTasks.edit.fieldDescriptions.concurrency") }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("backupTasks.edit.bandwidthLimit") }}
                  </label>
                  <input
                    v-model.number="editForm.bandwidth_limit_kbps"
                    type="number"
                    min="0"
                    :placeholder="
                      t('backupTasks.edit.placeholders.bandwidthLimit')
                    "
                    class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{ t("backupTasks.edit.fieldDescriptions.bandwidthLimit") }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground mb-1">
                    {{ t("backupTasks.detail.retries") }}
                  </label>
                  <input
                    v-model.number="editForm.max_retries"
                    type="number"
                    min="0"
                    :placeholder="t('backupTasks.edit.placeholders.maxRetries')"
                    class="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <p class="mt-1 text-xs text-foreground-muted">
                    {{ t("backupTasks.edit.fieldDescriptions.maxRetries") }}
                  </p>
                </div>
              </div>
            </section>
          </div>

          <div
            class="px-6 py-4 border-t border-border flex items-center justify-end gap-3"
          >
            <button
              type="button"
              @click="showEditModal = false"
              class="px-4 py-2 text-sm font-medium text-foreground-secondary border border-border rounded-lg hover:bg-hover"
            >
              {{ t("common.cancel") }}
            </button>
            <button
              type="submit"
              :disabled="editSaving || editLoading"
              class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ArrowPathIcon v-if="editSaving" class="w-4 h-4 animate-spin" />
              <PencilSquareIcon v-else class="w-4 h-4" />
              {{ editSaving ? t("common.saving") : t("common.save") }}
            </button>
          </div>
        </form>
      </div>
    </Teleport>

    <!-- Detail Drawer -->
    <Teleport to="body">
      <div
        v-if="showDetailModal && selectedTask"
        class="fixed inset-0 z-50 flex justify-end"
      >
        <div
          class="absolute inset-0 bg-black/50"
          @click="showDetailModal = false"
        />
        <aside
          class="relative drawer-panel h-full w-full lg:w-[60vw] max-w-none border-l border-border overflow-y-auto"
        >
          <div
            class="sticky top-0 z-10 modal-surface px-6 py-4 border-b border-border flex items-start justify-between gap-4"
          >
            <div>
              <h2 class="text-lg font-semibold text-foreground">
                {{ selectedTask.name }}
              </h2>
              <p class="mt-1 text-sm text-foreground-secondary">
                {{ selectedTask.source_resource_name || "-" }} →
                {{ selectedTask.target_repository_name || "-" }}
              </p>
            </div>
            <button
              @click="showDetailModal = false"
              class="p-2 hover:bg-background-tertiary rounded-lg"
            >
              <XCircleIcon class="w-5 h-5 text-slate-400" />
            </button>
          </div>

          <div
            class="px-6 py-3 border-b border-border flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3"
          >
            <div class="flex flex-wrap items-center gap-2">
              <div
                class="inline-flex flex-wrap gap-1 rounded-lg border border-border bg-background-secondary p-1"
                role="tablist"
              >
                <button
                  v-for="tab in ['overview', 'snapshots', 'tasks']"
                  :key="tab"
                  type="button"
                  role="tab"
                  :aria-selected="detailTab === tab"
                  @click="selectDetailTab(tab as any)"
                  :class="[
                    'inline-flex items-center rounded-md border px-3 py-1.5 text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-primary/40',
                    detailTab === tab
                      ? 'border-primary bg-primary text-primary-foreground shadow-sm'
                      : 'border-transparent text-foreground-secondary hover:border-border hover:bg-card hover:text-foreground',
                  ]"
                >
                  {{ t(`backupTasks.tabs.${tab}`) }}
                </button>
              </div>

              <div
                class="flex flex-wrap items-center gap-2 pl-0 xl:pl-3 xl:border-l xl:border-border"
              >
                <button
                  type="button"
                  :disabled="currentDetailTabLoading"
                  @click="refreshCurrentDetailTab()"
                  class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-border text-xs font-medium text-foreground hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ArrowPathIcon
                    :class="[
                      'w-3.5 h-3.5',
                      currentDetailTabLoading ? 'animate-spin' : '',
                    ]"
                  />
                  {{ t("common.refresh") }}
                </button>

                <label
                  class="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-border text-xs font-medium text-foreground hover:bg-hover"
                >
                  <input
                    v-model="detailAutoRefresh"
                    type="checkbox"
                    class="h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary"
                  />
                  {{ t("backupTasks.detail.autoRefresh") }}
                </label>

                <select
                  v-model.number="detailRefreshInterval"
                  :disabled="!detailAutoRefresh"
                  class="px-2.5 py-1.5 rounded-lg border border-border bg-background text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                >
                  <option :value="5">5s</option>
                  <option :value="10">10s</option>
                  <option :value="30">30s</option>
                  <option :value="60">60s</option>
                </select>
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2 xl:justify-end">
              <span
                :class="[
                  'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium',
                  getStatusColor(selectedTask.status),
                ]"
              >
                <component
                  :is="getStatusIcon(selectedTask.status)"
                  class="w-3.5 h-3.5"
                />
                {{ t(`backupTasks.status.${selectedTask.status}`) }}
              </span>
              <span
                :class="[
                  'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium',
                  selectedTask.is_enabled === false
                    ? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                    : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
                ]"
              >
                <span
                  :class="[
                    'h-2 w-2 rounded-full',
                    selectedTask.is_enabled === false
                      ? 'bg-red-500'
                      : 'bg-emerald-500',
                  ]"
                />
                {{
                  selectedTask.is_enabled === false
                    ? t("backupTasks.disabled")
                    : t("backupTasks.enabled")
                }}
              </span>
              <button
                v-if="canRunTask(selectedTask)"
                @click="executeTask(selectedTask)"
                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-medium hover:bg-emerald-700"
              >
                <PlayIcon class="w-3.5 h-3.5" />
                {{ t("backupTasks.actions.runNow") }}
              </button>
              <button
                @click="toggleTaskEnabled(selectedTask)"
                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs font-medium text-foreground hover:bg-hover"
              >
                <PowerIcon class="w-3.5 h-3.5" />
                {{
                  selectedTask.is_enabled === false
                    ? t("backupTasks.actions.enable")
                    : t("backupTasks.actions.disable")
                }}
              </button>
            </div>
          </div>

          <div class="p-6">
            <div
              v-if="detailLoading"
              class="py-10 text-center text-foreground-secondary"
            >
              {{ t("common.loading") }}
            </div>

            <div v-else-if="detailTab === 'overview'" class="space-y-5">
              <section
                class="rounded-xl border border-border bg-card p-4 shadow-sm"
              >
                <div class="mb-4 flex items-start gap-3">
                  <span
                    class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
                  >
                    <ListBulletIcon class="h-5 w-5" />
                  </span>
                  <div>
                    <h3 class="font-semibold text-foreground">
                      {{ t("backupTasks.detail.basic") }}
                    </h3>
                    <p class="mt-0.5 text-xs text-foreground-secondary">
                      {{ selectedTask.name }}
                    </p>
                  </div>
                </div>
                <dl class="grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3 md:col-span-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("common.description") }}
                    </dt>
                    <dd class="mt-1 text-sm leading-6 text-foreground">
                      {{ selectedTask.description || "-" }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.form.taskType") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{
                        t(
                          `backupTasks.types.${selectedTask.task_type || "full"}`,
                        )
                      }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.form.priority") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{ selectedTask.priority || "-" }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.detail.createdUpdated") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{ formatDateTime(selectedTask.created_at) }} /
                      {{ formatDateTime(selectedTask.updated_at) }}
                    </dd>
                  </div>
                </dl>
              </section>

              <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
                <section
                  class="rounded-xl border border-border bg-card p-4 shadow-sm"
                >
                  <div class="mb-4 flex items-start gap-3">
                    <span
                      class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-300"
                    >
                      <FolderIcon class="h-5 w-5" />
                    </span>
                    <div>
                      <h3 class="font-semibold text-foreground">
                        {{ t("backupTasks.backupSource") }}
                      </h3>
                      <p class="mt-0.5 text-xs text-foreground-secondary">
                        {{ selectedSource?.name || "-" }}
                      </p>
                    </div>
                  </div>
                  <div class="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
                    <div
                      v-for="[label, value] in sourceDetailRows(selectedSource)"
                      :key="label"
                      class="rounded-lg border border-border bg-background/50 p-3"
                    >
                      <p class="text-xs font-medium text-foreground-secondary">
                        {{ label }}
                      </p>
                      <p
                        class="mt-1 break-all text-sm font-medium text-foreground"
                      >
                        {{ value }}
                      </p>
                    </div>
                  </div>
                  <div
                    class="mt-4 rounded-lg border border-border bg-background/50 p-3"
                  >
                    <p
                      class="mb-2 text-xs font-medium text-foreground-secondary"
                    >
                      {{ t("backupTasks.form.sourcePaths") }}
                    </p>
                    <div class="space-y-1.5">
                      <p
                        v-for="(path, i) in selectedTask.backup_paths || []"
                        :key="i"
                        class="rounded-md border border-border bg-background-secondary px-2.5 py-1.5 font-mono text-xs text-foreground"
                      >
                        {{ path }}
                      </p>
                      <p
                        v-if="!selectedTask.backup_paths?.length"
                        class="text-sm text-foreground-muted"
                      >
                        -
                      </p>
                    </div>
                  </div>
                </section>

                <section
                  class="rounded-xl border border-border bg-card p-4 shadow-sm"
                >
                  <div class="mb-4 flex items-start gap-3">
                    <span
                      class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-300"
                    >
                      <ServerStackIcon class="h-5 w-5" />
                    </span>
                    <div>
                      <h3 class="font-semibold text-foreground">
                        {{ t("backupTasks.backupRepository") }}
                      </h3>
                      <p class="mt-0.5 text-xs text-foreground-secondary">
                        {{ selectedRepository?.name || "-" }}
                      </p>
                    </div>
                  </div>
                  <div class="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
                    <div
                      v-for="[label, value] in repositoryDetailRows(
                        selectedRepository,
                      )"
                      :key="label"
                      class="rounded-lg border border-border bg-background/50 p-3"
                    >
                      <p class="text-xs font-medium text-foreground-secondary">
                        {{ label }}
                      </p>
                      <p
                        class="mt-1 break-all text-sm font-medium text-foreground"
                      >
                        {{ value }}
                      </p>
                    </div>
                  </div>
                </section>
              </div>

              <section
                class="rounded-xl border border-border bg-card p-4 shadow-sm"
              >
                <div class="mb-4 flex items-start gap-3">
                  <span
                    class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-violet-500/10 text-violet-600 dark:text-violet-300"
                  >
                    <FolderIcon class="h-5 w-5" />
                  </span>
                  <div>
                    <h3 class="font-semibold text-foreground">
                      {{ t("backupTasks.detail.pathsAndFilters") }}
                    </h3>
                    <p class="mt-0.5 text-xs text-foreground-secondary">
                      {{ t("backupTasks.form.excludePaths") }}
                    </p>
                  </div>
                </div>
                <div class="grid grid-cols-1 gap-4">
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <p
                      class="mb-2 text-xs font-medium text-foreground-secondary"
                    >
                      {{ t("backupTasks.files.exclusionPatterns") }}
                    </p>
                    <div class="flex flex-wrap gap-2">
                      <span
                        v-for="(pattern, i) in selectedTask.exclude_patterns ||
                        []"
                        :key="i"
                        class="rounded-md border border-border bg-background-secondary px-2.5 py-1 text-xs font-medium text-foreground"
                      >
                        {{ pattern }}
                      </span>
                      <span
                        v-if="!selectedTask.exclude_patterns?.length"
                        class="text-sm text-foreground-muted"
                      >
                        -
                      </span>
                    </div>
                  </div>
                </div>
              </section>

              <section
                class="rounded-xl border border-border bg-card p-4 shadow-sm"
              >
                <div class="mb-4 flex items-start gap-3">
                  <span
                    class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-300"
                  >
                    <ClockIcon class="h-5 w-5" />
                  </span>
                  <div>
                    <h3 class="font-semibold text-foreground">
                      {{ t("backupTasks.detail.scheduleRetention") }}
                    </h3>
                    <p class="mt-0.5 text-xs text-foreground-secondary">
                      {{
                        selectedTask.schedule_name ||
                        t("backupTasks.form.noPolicy")
                      }}
                    </p>
                  </div>
                </div>
                <dl class="grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.form.policy") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{
                        selectedTask.schedule_name ||
                        t("backupTasks.form.noPolicy")
                      }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.nextBackup") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{ formatDateTime(selectedTask.next_run_time) }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.lastBackup") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{
                        formatDateTime(
                          selectedTask.last_run_time ||
                            selectedTask.completed_at,
                        )
                      }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.form.retentionDays") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{ selectedTask.retention_days || "-" }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.form.maxSnapshots") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{ selectedTask.max_snapshots || "-" }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.detail.retries") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{ selectedTask.retry_count || 0 }} /
                      {{ selectedTask.max_retries || 0 }}
                    </dd>
                  </div>
                </dl>
              </section>

              <section
                class="rounded-xl border border-border bg-card p-4 shadow-sm"
              >
                <div class="mb-4 flex items-start gap-3">
                  <span
                    class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-300"
                  >
                    <ShieldCheckIcon class="h-5 w-5" />
                  </span>
                  <div>
                    <h3 class="font-semibold text-foreground">
                      {{ t("backupTasks.detail.securityCompression") }}
                    </h3>
                    <p class="mt-0.5 text-xs text-foreground-secondary">
                      {{
                        selectedTask.compression_enabled
                          ? selectedTask.compression_type || "-"
                          : t("common.no")
                      }}
                    </p>
                  </div>
                </div>
                <dl class="grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.detail.encryption") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{
                        selectedTask.encryption_enabled
                          ? t("common.yes")
                          : t("common.no")
                      }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.detail.checksum") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{
                        selectedTask.verify_checksum
                          ? t("common.yes")
                          : t("common.no")
                      }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.detail.compression") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{
                        selectedTask.compression_enabled
                          ? selectedTask.compression_type || "-"
                          : t("common.no")
                      }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.detail.compressionLevel") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{ selectedTask.compression_level ?? "-" }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.detail.checkpoint") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{
                        selectedTask.enable_checkpoint
                          ? `${selectedTask.checkpoint_interval_minutes || "-"}m`
                          : t("common.no")
                      }}
                    </dd>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <dt class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.detail.concurrency") }}
                    </dt>
                    <dd class="mt-1 text-sm font-medium text-foreground">
                      {{ selectedTask.max_concurrent_files || "-" }}
                    </dd>
                  </div>
                </dl>
              </section>

              <section
                class="rounded-xl border border-border bg-card p-4 shadow-sm"
              >
                <div class="mb-4 flex items-start gap-3">
                  <span
                    class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
                  >
                    <BoltIcon class="h-5 w-5" />
                  </span>
                  <div>
                    <h3 class="font-semibold text-foreground">
                      {{ t("backupTasks.detail.observability") }}
                    </h3>
                    <p class="mt-0.5 text-xs text-foreground-secondary">
                      {{ selectedTask.progress || 0 }}%
                    </p>
                  </div>
                </div>
                <div
                  class="mb-4 rounded-lg border border-border bg-background/50 p-3"
                >
                  <div class="mb-2 flex items-center justify-between text-xs">
                    <span class="font-medium text-foreground-secondary">
                      {{ t("backupTasks.progress.progress") }}
                    </span>
                    <span class="font-semibold text-foreground">
                      {{ selectedTask.progress || 0 }}%
                    </span>
                  </div>
                  <div
                    class="h-2 overflow-hidden rounded-full bg-background-secondary"
                  >
                    <div
                      class="h-full rounded-full bg-primary transition-all"
                      :style="{
                        width: `${Math.min(
                          Math.max(selectedTask.progress || 0, 0),
                          100,
                        )}%`,
                      }"
                    ></div>
                  </div>
                </div>
                <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <p class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.progress.files") }}
                    </p>
                    <p class="mt-1 text-lg font-semibold text-foreground">
                      {{ selectedTask.backed_up_files || 0 }} /
                      {{ selectedTask.total_files || 0 }}
                    </p>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <p class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.progress.size") }}
                    </p>
                    <p class="mt-1 text-lg font-semibold text-foreground">
                      {{ formatBytes(selectedTask.backed_up_size || 0) }} /
                      {{ formatBytes(selectedTask.total_size || 0) }}
                    </p>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <p class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.progress.speed") }}
                    </p>
                    <p class="mt-1 text-lg font-semibold text-foreground">
                      {{ formatSpeed(selectedTask.bytes_per_second) }}
                    </p>
                  </div>
                  <div
                    class="rounded-lg border border-border bg-background/50 p-3"
                  >
                    <p class="text-xs font-medium text-foreground-secondary">
                      {{ t("backupTasks.detail.retries") }}
                    </p>
                    <p class="mt-1 text-lg font-semibold text-foreground">
                      {{ selectedTask.retry_count || 0 }} /
                      {{ selectedTask.max_retries || 0 }}
                    </p>
                  </div>
                </div>
              </section>
            </div>

            <div v-else-if="detailTab === 'snapshots'" class="space-y-4">
              <div
                v-if="snapshotsLoading"
                class="py-10 text-center text-foreground-secondary"
              >
                {{ t("common.loading") }}
              </div>
              <div
                v-else-if="selectedTaskSnapshots.length === 0"
                class="rounded-xl border border-dashed border-border bg-background/50 px-6 py-12 text-center"
              >
                <div
                  class="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-300"
                >
                  <CircleStackIcon class="h-7 w-7" />
                </div>
                <h3 class="mt-4 text-sm font-semibold text-foreground">
                  {{ t("backupTasks.emptyStates.snapshotsTitle") }}
                </h3>
                <p
                  class="mx-auto mt-2 max-w-md text-sm leading-6 text-foreground-secondary"
                >
                  {{ t("backupTasks.emptyStates.snapshotsDesc") }}
                </p>
              </div>
              <template v-else>
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <div
                    class="inline-flex items-center gap-2 rounded-full border border-border bg-card px-2.5 py-1.5 text-xs font-medium text-foreground shadow-sm"
                  >
                    <button
                      type="button"
                      role="switch"
                      :aria-checked="collapseNoChangeSnapshots"
                      class="inline-flex items-center gap-2 transition-colors hover:text-primary focus:outline-none"
                      @click="
                        collapseNoChangeSnapshots = !collapseNoChangeSnapshots
                      "
                    >
                      <span
                        :class="[
                          'relative inline-flex h-5 w-9 items-center rounded-full transition-colors',
                          collapseNoChangeSnapshots
                            ? 'bg-primary'
                            : 'bg-background-tertiary',
                        ]"
                      >
                        <span
                          :class="[
                            'inline-block h-4 w-4 rounded-full bg-white shadow transition-transform',
                            collapseNoChangeSnapshots
                              ? 'translate-x-4'
                              : 'translate-x-0.5',
                          ]"
                        />
                      </span>
                      <span>{{
                        t("backupTasks.detail.collapseNoChanges")
                      }}</span>
                    </button>
                    <button
                      type="button"
                      class="inline-flex h-5 w-5 items-center justify-center rounded-full text-foreground-muted transition-colors hover:bg-background-secondary hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                      @mouseenter="
                        showSnapshotHelpTooltip(
                          $event,
                          'backupTasks.detail.collapseNoChangesHelp',
                        )
                      "
                      @mouseleave="scheduleSnapshotHelpTooltipHide"
                      @focus="
                        showSnapshotHelpTooltip(
                          $event,
                          'backupTasks.detail.collapseNoChangesHelp',
                        )
                      "
                      @blur="scheduleSnapshotHelpTooltipHide"
                      @click.stop
                    >
                      <QuestionMarkCircleIcon class="h-4 w-4" />
                    </button>
                    <span
                      v-if="hiddenNoChangeSnapshotCount > 0"
                      class="rounded-full bg-background-secondary px-1.5 py-0.5 text-[11px] text-foreground-secondary"
                    >
                      {{ hiddenNoChangeSnapshotCount }}
                    </span>
                  </div>
                  <div class="flex flex-wrap items-center justify-end gap-2">
                    <div
                      class="inline-flex flex-wrap items-center gap-1 rounded-lg border border-border bg-card p-1 text-xs shadow-sm"
                    >
                      <button
                        type="button"
                        class="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 font-medium text-foreground-secondary transition-colors hover:bg-hover hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
                        :disabled="snapshotOperationLoading"
                        @mouseenter="
                          showSnapshotHelpTooltip(
                            $event,
                            'backupTasks.detail.syncSnapshotsHelp',
                          )
                        "
                        @mouseleave="scheduleSnapshotHelpTooltipHide"
                        @focus="
                          showSnapshotHelpTooltip(
                            $event,
                            'backupTasks.detail.syncSnapshotsHelp',
                          )
                        "
                        @blur="scheduleSnapshotHelpTooltipHide"
                        @click="syncSnapshotsFromKopia"
                      >
                        <ArrowPathIcon
                          :class="[
                            'h-3.5 w-3.5',
                            snapshotOperationLoading ? 'animate-spin' : '',
                          ]"
                        />
                        {{ t("backupTasks.detail.syncSnapshots") }}
                        <QuestionMarkCircleIcon class="h-3.5 w-3.5 text-foreground-muted" />
                      </button>
                      <button
                        type="button"
                        class="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 font-medium text-foreground-secondary transition-colors hover:bg-hover hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
                        :disabled="snapshotOperationLoading"
                        @mouseenter="
                          showSnapshotHelpTooltip(
                            $event,
                            'backupTasks.detail.applyRetentionHelp',
                          )
                        "
                        @mouseleave="scheduleSnapshotHelpTooltipHide"
                        @focus="
                          showSnapshotHelpTooltip(
                            $event,
                            'backupTasks.detail.applyRetentionHelp',
                          )
                        "
                        @blur="scheduleSnapshotHelpTooltipHide"
                        @click="evaluateRetentionNow"
                      >
                        {{ t("backupTasks.detail.applyRetention") }}
                        <QuestionMarkCircleIcon class="h-3.5 w-3.5 text-foreground-muted" />
                      </button>
                      <button
                        type="button"
                        class="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 font-medium text-foreground-secondary transition-colors hover:bg-hover hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
                        :disabled="snapshotOperationLoading"
                        @mouseenter="
                          showSnapshotHelpTooltip(
                            $event,
                            'backupTasks.detail.runMaintenanceHelp',
                          )
                        "
                        @mouseleave="scheduleSnapshotHelpTooltipHide"
                        @focus="
                          showSnapshotHelpTooltip(
                            $event,
                            'backupTasks.detail.runMaintenanceHelp',
                          )
                        "
                        @blur="scheduleSnapshotHelpTooltipHide"
                        @click="runKopiaMaintenanceNow"
                      >
                        {{ t("backupTasks.detail.runMaintenance") }}
                        <QuestionMarkCircleIcon class="h-3.5 w-3.5 text-foreground-muted" />
                      </button>
                    </div>
                    <div
                      class="inline-flex flex-wrap items-center gap-1 rounded-lg border border-border bg-card p-1 text-xs shadow-sm"
                    >
                      <button
                        v-for="option in snapshotViewModeOptions"
                        :key="option.value"
                        type="button"
                        :class="[
                          'rounded-md px-2.5 py-1.5 font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary',
                          snapshotViewMode === option.value
                            ? 'bg-primary text-white shadow-sm'
                            : 'text-foreground-secondary hover:bg-hover hover:text-foreground',
                        ]"
                        @click="snapshotViewMode = option.value"
                      >
                        {{ option.label }}
                      </button>
                    </div>
                    <div
                      class="inline-flex flex-wrap items-center gap-1 rounded-lg border border-border bg-card p-1 text-xs shadow-sm"
                    >
                      <button
                        v-for="option in snapshotGroupOptions"
                        :key="option.value"
                        type="button"
                        :class="[
                          'rounded-md px-2.5 py-1.5 font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary',
                          snapshotGroupBy === option.value
                            ? 'bg-primary text-white shadow-sm'
                            : 'text-foreground-secondary hover:bg-hover hover:text-foreground',
                        ]"
                        @click="snapshotGroupBy = option.value"
                      >
                        {{ option.label }}
                      </button>
                    </div>
                  </div>
                </div>
                <div
                  v-if="displayedTaskSnapshots.length === 0"
                  class="rounded-xl border border-dashed border-border bg-background/50 px-6 py-10 text-center text-sm text-foreground-secondary"
                >
                  {{ t("backupTasks.detail.noNormalSnapshots") }}
                </div>
                <div v-else class="space-y-4">
                  <section
                    v-for="group in groupedDisplayedTaskSnapshots"
                    :key="group.key"
                    class="space-y-2.5"
                  >
                    <div
                      v-if="snapshotGroupBy !== 'all'"
                      class="flex items-center justify-between gap-3 border-b border-border pb-2"
                    >
                      <div>
                        <h4 class="text-sm font-semibold text-foreground">
                          {{ group.label }}
                        </h4>
                        <p class="mt-0.5 text-xs text-foreground-secondary">
                          {{ group.description }}
                        </p>
                      </div>
                    </div>
                    <div
                      v-if="snapshotViewMode === 'grid'"
                      class="grid grid-cols-[repeat(auto-fill,minmax(108px,1fr))] gap-2.5"
                    >
                      <button
                        v-for="snapshot in group.snapshots"
                        :key="snapshot.id"
                        type="button"
                        :disabled="!isSnapshotBrowsable(snapshot)"
                        @click="loadSnapshotFiles(snapshot)"
                        @mouseenter="showSnapshotHoverTooltip(snapshot, $event)"
                        @mouseleave="scheduleSnapshotHoverTooltipHide"
                        @focus="showSnapshotHoverTooltip(snapshot, $event)"
                        @blur="scheduleSnapshotHoverTooltipHide"
                        :class="[
                          'group relative aspect-square overflow-visible rounded-lg border p-2.5 text-left transition-all focus:outline-none focus:ring-2 focus:ring-primary',
                          snapshotCardClass(snapshot),
                        ]"
                      >
                        <span
                          v-if="isNoChangeSnapshotReference(snapshot)"
                          :title="t('backupTasks.detail.noChanges')"
                          class="absolute left-2 top-2 h-2.5 w-2.5 rounded-full bg-amber-500 ring-2 ring-card dark:ring-background"
                        />
                        <div class="flex items-center justify-between gap-2">
                          <span
                            :class="[
                              'inline-flex h-7 w-7 items-center justify-center rounded-md',
                              !isSnapshotBrowsable(snapshot)
                                ? 'bg-slate-200 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
                                : selectedSnapshot?.id === snapshot.id
                                ? 'bg-emerald-600 text-white'
                                : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
                            ]"
                          >
                            <CircleStackIcon class="w-4 h-4" />
                          </span>
                          <span
                            v-if="isLatestDisplayedSnapshot(snapshot)"
                            class="px-1.5 py-0.5 rounded-full bg-emerald-600 text-white text-[10px] font-medium"
                          >
                            {{ t("backupTasks.detail.latest") }}
                          </span>
                        </div>
                        <p
                          class="mt-2 text-xs font-medium text-foreground truncate"
                        >
                          {{
                            formatCompactDateTime(snapshotDisplayTime(snapshot))
                          }}
                        </p>
                        <p
                          class="mt-1 text-[11px] text-foreground-secondary truncate"
                        >
                          {{ formatBytes(snapshotDisplaySize(snapshot)) }}
                        </p>
                        <span
                          :class="[
                            'mt-1 inline-flex max-w-full rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                            snapshotStatusClass(snapshot),
                          ]"
                        >
                          {{ snapshotStatusLabel(snapshot) }}
                        </span>
                        <div
                          class="mt-2 flex items-center justify-between text-[11px]"
                        >
                          <span class="text-foreground-muted">
                            {{
                              isNoChangeSnapshotReference(snapshot)
                                ? t("backupTasks.detail.changedFiles", {
                                    count: 0,
                                  })
                                : `${snapshotDisplayFileCount(snapshot)} ${t(
                                    "backupTasks.progress.files",
                                  )}`
                            }}
                          </span>
                          <span
                            v-if="
                              selectedSnapshot?.id === snapshot.id &&
                              isSnapshotBrowsable(snapshot)
                            "
                            class="h-2 w-2 rounded-full bg-emerald-500"
                          />
                        </div>
                      </button>
                    </div>
                    <div v-else class="relative space-y-2 pl-6">
                      <div
                        class="absolute bottom-3 left-[11px] top-3 w-px bg-border"
                      />
                      <div
                        v-for="snapshot in group.snapshots"
                        :key="snapshot.id"
                        class="relative"
                      >
                        <span
                          :class="[
                            'absolute -left-[19px] top-4 h-3.5 w-3.5 rounded-full border-2 bg-card',
                            snapshotTimelineDotClass(snapshot),
                          ]"
                        />
                        <div
                          :class="[
                            'rounded-lg border bg-card transition-colors',
                            snapshotTimelineClass(snapshot),
                          ]"
                        >
                          <button
                            type="button"
                            class="w-full px-3 py-2.5 text-left focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed"
                            :disabled="!isSnapshotBrowsable(snapshot)"
                            @click="loadSnapshotFiles(snapshot)"
                            @mouseenter="
                              showSnapshotHoverTooltip(snapshot, $event)
                            "
                            @mouseleave="scheduleSnapshotHoverTooltipHide"
                            @focus="showSnapshotHoverTooltip(snapshot, $event)"
                            @blur="scheduleSnapshotHoverTooltipHide"
                          >
                            <div
                              class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"
                            >
                              <div class="min-w-0">
                                <div class="flex flex-wrap items-center gap-2">
                                  <span
                                    class="text-sm font-semibold text-foreground"
                                  >
                                    {{
                                      formatDateTime(
                                        snapshotDisplayTime(snapshot),
                                      )
                                    }}
                                  </span>
                                  <span
                                    v-if="isLatestDisplayedSnapshot(snapshot)"
                                    class="rounded-full bg-emerald-600 px-1.5 py-0.5 text-[10px] font-medium text-white"
                                  >
                                    {{ t("backupTasks.detail.latest") }}
                                  </span>
                                  <span
                                    v-if="isNoChangeSnapshotReference(snapshot)"
                                    class="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
                                  >
                                    {{ t("backupTasks.detail.noChanges") }}
                                  </span>
                                  <span
                                    :class="[
                                      'rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                                      snapshotStatusClass(snapshot),
                                    ]"
                                  >
                                    {{ snapshotStatusLabel(snapshot) }}
                                  </span>
                                </div>
                                <p
                                  class="mt-1 truncate text-xs text-foreground-secondary"
                                >
                                  {{
                                    snapshot.name ||
                                    snapshot.version ||
                                    snapshot.id
                                  }}
                                </p>
                              </div>
                              <div
                                class="grid grid-cols-3 gap-2 text-right text-xs sm:min-w-[240px]"
                              >
                                <div>
                                  <p class="text-foreground-muted">
                                    {{ t("backupTasks.progress.size") }}
                                  </p>
                                  <p class="font-medium text-foreground">
                                    {{
                                      formatBytes(snapshotDisplaySize(snapshot))
                                    }}
                                  </p>
                                </div>
                                <div>
                                  <p class="text-foreground-muted">
                                    {{ t("backupTasks.progress.files") }}
                                  </p>
                                  <p class="font-medium text-foreground">
                                    {{
                                      isNoChangeSnapshotReference(snapshot)
                                        ? 0
                                        : snapshotDisplayFileCount(snapshot)
                                    }}
                                  </p>
                                </div>
                                <div>
                                  <p class="text-foreground-muted">
                                    {{ t("common.status") }}
                                  </p>
                                  <p class="font-medium text-foreground">
                                    {{
                                      isNoChangeSnapshotReference(snapshot)
                                        ? t("backupTasks.detail.noChanges")
                                        : t(
                                            "backupTasks.detail.changedSnapshots",
                                          )
                                    }}
                                  </p>
                                </div>
                              </div>
                            </div>
                          </button>
                          <div
                            v-if="selectedSnapshot?.id === snapshot.id"
                            class="border-t border-border bg-background/50"
                          >
                            <div
                              class="px-3 py-2 text-xs text-foreground-secondary"
                            >
                              {{
                                isNoChangeSnapshotReference(selectedSnapshot)
                                  ? t(
                                      "backupTasks.detail.showingReferencedSnapshot",
                                    )
                                  : t(
                                      "backupTasks.detail.timelineFileBrowserHint",
                                    )
                              }}
                            </div>
                            <div
                              class="grid grid-cols-[minmax(0,1fr)_120px] gap-4 border-y border-border bg-background-secondary px-3 py-2 text-xs font-medium text-foreground-secondary"
                            >
                              <span>{{ t("common.name") }}</span>
                              <span class="text-right">{{
                                t("backupTasks.progress.size")
                              }}</span>
                            </div>
                            <div
                              v-if="snapshotFilesLoading"
                              class="p-5 text-center text-foreground-secondary"
                            >
                              {{ t("common.loading") }}
                            </div>
                            <div
                              v-else-if="snapshotFilesError"
                              class="p-5 text-center"
                            >
                              <ExclamationTriangleIcon
                                class="mx-auto mb-3 h-8 w-8 text-warning"
                              />
                              <p class="text-sm font-medium text-foreground">
                                {{
                                  t(
                                    "backupTasks.detail.snapshotFilesLoadFailed",
                                  )
                                }}
                              </p>
                              <p
                                class="mx-auto mt-1 max-w-xl text-sm text-foreground-secondary"
                              >
                                {{ snapshotFilesError }}
                              </p>
                              <button
                                type="button"
                                class="mt-4 inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground hover:bg-hover"
                                @click="loadSnapshotFiles(selectedSnapshot)"
                              >
                                <ArrowPathIcon class="h-4 w-4" />
                                {{ t("common.retry") }}
                              </button>
                            </div>
                            <div
                              v-else-if="selectedSnapshotFiles.length === 0"
                              class="p-5 text-center text-foreground-secondary"
                            >
                              {{ t("backupTasks.detail.noSnapshotFiles") }}
                            </div>
                            <div v-else class="py-1">
                              <div
                                v-for="file in visibleSnapshotFiles()"
                                :key="file.relative_path || file.id"
                                class="group grid grid-cols-[minmax(0,1fr)_120px] gap-4 px-3 py-1.5 hover:bg-hover"
                              >
                                <div
                                  class="flex min-w-0 items-center gap-1.5"
                                  :style="{
                                    paddingLeft: `${(file.depth || 0) * 20}px`,
                                  }"
                                >
                                  <button
                                    type="button"
                                    class="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded hover:bg-background-tertiary"
                                    :class="
                                      file.is_dir ? 'visible' : 'invisible'
                                    "
                                    @click="toggleSnapshotDirectory(file)"
                                  >
                                    <ChevronDownIcon
                                      v-if="
                                        file.is_dir &&
                                        expandedSnapshotPaths.has(
                                          file.relative_path,
                                        )
                                      "
                                      class="h-4 w-4 text-foreground-muted"
                                    />
                                    <ChevronRightIcon
                                      v-else
                                      class="h-4 w-4 text-foreground-muted"
                                    />
                                  </button>
                                  <ArrowPathIcon
                                    v-if="
                                      loadingSnapshotPaths.has(
                                        file.relative_path,
                                      )
                                    "
                                    class="h-4 w-4 shrink-0 animate-spin text-primary"
                                  />
                                  <input
                                    type="checkbox"
                                    class="h-4 w-4 shrink-0 rounded border-border text-primary focus:ring-primary"
                                    :checked="
                                      selectedSnapshotPaths.has(
                                        file.relative_path,
                                      )
                                    "
                                    @change="toggleSnapshotPathSelection(file)"
                                  />
                                  <FolderIcon
                                    v-if="file.is_dir"
                                    class="h-4 w-4 shrink-0 text-amber-500"
                                  />
                                  <DocumentIcon
                                    v-else
                                    class="h-4 w-4 shrink-0 text-foreground-muted"
                                  />
                                  <div
                                    class="flex min-w-0 items-baseline gap-2"
                                  >
                                    <button
                                      type="button"
                                      class="truncate text-left text-sm text-foreground hover:text-primary"
                                      @click="
                                        file.is_dir
                                          ? toggleSnapshotDirectory(file)
                                          : undefined
                                      "
                                    >
                                      {{ file.file_name || file.relative_path }}
                                    </button>
                                    <span
                                      class="hidden truncate text-xs text-foreground-muted xl:inline"
                                    >
                                      {{ file.relative_path }}
                                    </span>
                                  </div>
                                </div>
                                <span
                                  class="text-right text-sm tabular-nums text-foreground-secondary"
                                >
                                  {{
                                    file.is_dir
                                      ? "-"
                                      : formatBytes(file.size || 0)
                                  }}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </section>
                </div>

                <div
                  v-if="snapshotViewMode === 'grid'"
                  class="rounded-lg border border-border bg-card overflow-hidden"
                >
                  <div
                    class="px-4 py-3 border-b border-border flex items-center justify-between"
                  >
                    <div>
                      <h3 class="font-semibold text-foreground">
                        {{ t("backupTasks.detail.fileBrowser") }}
                      </h3>
                      <p class="text-xs text-foreground-secondary">
                        {{
                          selectedSnapshot
                            ? isNoChangeSnapshotReference(selectedSnapshot)
                              ? t(
                                  "backupTasks.detail.showingReferencedSnapshot",
                                )
                              : selectedSnapshot.name || selectedSnapshot.id
                            : "-"
                        }}
                      </p>
                    </div>
                  </div>
                  <div
                    v-if="selectedSnapshot"
                    class="grid grid-cols-[minmax(0,1fr)_120px] gap-4 px-4 py-2 border-b border-border bg-background-secondary text-xs font-medium text-foreground-secondary"
                  >
                    <span>{{ t("common.name") }}</span>
                    <span class="text-right">{{
                      t("backupTasks.progress.size")
                    }}</span>
                  </div>
                  <div
                    v-if="snapshotFilesLoading"
                    class="p-6 text-center text-foreground-secondary"
                  >
                    {{ t("common.loading") }}
                  </div>
                  <div
                    v-else-if="!selectedSnapshot"
                    class="p-6 text-center text-foreground-secondary"
                  >
                    {{ t("backupTasks.detail.selectSnapshot") }}
                  </div>
                  <div v-else-if="snapshotFilesError" class="p-6 text-center">
                    <ExclamationTriangleIcon
                      class="mx-auto mb-3 h-8 w-8 text-warning"
                    />
                    <p class="text-sm font-medium text-foreground">
                      {{ t("backupTasks.detail.snapshotFilesLoadFailed") }}
                    </p>
                    <p
                      class="mx-auto mt-1 max-w-xl text-sm text-foreground-secondary"
                    >
                      {{ snapshotFilesError }}
                    </p>
                    <button
                      type="button"
                      class="mt-4 inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground hover:bg-hover"
                      @click="loadSnapshotFiles(selectedSnapshot)"
                    >
                      <ArrowPathIcon class="h-4 w-4" />
                      {{ t("common.retry") }}
                    </button>
                  </div>
                  <div
                    v-else-if="selectedSnapshotFiles.length === 0"
                    class="p-6 text-center text-foreground-secondary"
                  >
                    {{ t("backupTasks.detail.noSnapshotFiles") }}
                  </div>
                  <div v-else class="py-1">
                    <div
                      v-for="file in visibleSnapshotFiles()"
                      :key="file.relative_path || file.id"
                      class="group grid grid-cols-[minmax(0,1fr)_120px] gap-4 px-4 py-1.5 hover:bg-hover"
                    >
                      <div
                        class="flex items-center gap-1.5 min-w-0"
                        :style="{ paddingLeft: `${(file.depth || 0) * 20}px` }"
                      >
                        <button
                          type="button"
                          class="w-5 h-5 inline-flex items-center justify-center rounded hover:bg-background-tertiary shrink-0"
                          :class="file.is_dir ? 'visible' : 'invisible'"
                          @click="toggleSnapshotDirectory(file)"
                        >
                          <ChevronDownIcon
                            v-if="
                              file.is_dir &&
                              expandedSnapshotPaths.has(file.relative_path)
                            "
                            class="w-4 h-4 text-foreground-muted"
                          />
                          <ChevronRightIcon
                            v-else
                            class="w-4 h-4 text-foreground-muted"
                          />
                        </button>
                        <ArrowPathIcon
                          v-if="loadingSnapshotPaths.has(file.relative_path)"
                          class="w-4 h-4 animate-spin text-primary shrink-0"
                        />
                        <input
                          type="checkbox"
                          class="h-4 w-4 rounded border-border text-primary focus:ring-primary shrink-0"
                          :checked="
                            selectedSnapshotPaths.has(file.relative_path)
                          "
                          @change="toggleSnapshotPathSelection(file)"
                        />
                        <FolderIcon
                          v-if="file.is_dir"
                          class="w-4 h-4 text-amber-500 shrink-0"
                        />
                        <DocumentIcon
                          v-else
                          class="w-4 h-4 text-foreground-muted shrink-0"
                        />
                        <div class="min-w-0 flex items-baseline gap-2">
                          <button
                            type="button"
                            class="text-left text-sm text-foreground truncate hover:text-primary"
                            @click="
                              file.is_dir
                                ? toggleSnapshotDirectory(file)
                                : undefined
                            "
                          >
                            {{ file.file_name || file.relative_path }}
                          </button>
                          <span
                            class="text-xs text-foreground-muted truncate hidden xl:inline"
                          >
                            {{ file.relative_path }}
                          </span>
                        </div>
                      </div>
                      <span
                        class="text-sm text-foreground-secondary text-right tabular-nums"
                      >
                        {{ file.is_dir ? "-" : formatBytes(file.size || 0) }}
                      </span>
                    </div>
                  </div>
                </div>
              </template>
            </div>

            <div v-else class="space-y-3">
              <div
                v-if="runsLoading"
                class="py-10 text-center text-foreground-secondary"
              >
                {{ t("common.loading") }}
              </div>
              <div
                v-else-if="selectedTaskRuns.length === 0"
                class="rounded-xl border border-dashed border-border bg-background/50 px-6 py-12 text-center"
              >
                <div
                  class="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-violet-50 text-violet-600 dark:bg-violet-950/30 dark:text-violet-300"
                >
                  <ListBulletIcon class="h-7 w-7" />
                </div>
                <h3 class="mt-4 text-sm font-semibold text-foreground">
                  {{ t("backupTasks.emptyStates.runsTitle") }}
                </h3>
                <p
                  class="mx-auto mt-2 max-w-md text-sm leading-6 text-foreground-secondary"
                >
                  {{ t("backupTasks.emptyStates.runsDesc") }}
                </p>
              </div>
              <div v-else class="space-y-2">
                <div
                  v-for="run in selectedTaskRuns"
                  :key="run.id"
                  class="rounded-lg border border-border bg-card px-3 py-2.5 hover:bg-hover transition-colors"
                >
                  <div class="flex flex-col gap-2">
                    <div class="flex items-start justify-between gap-3">
                      <div class="flex min-w-0 items-start gap-2.5">
                        <span
                          class="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-background-secondary text-foreground-muted"
                        >
                          <ListBulletIcon class="w-4 h-4" />
                        </span>
                        <div class="min-w-0">
                          <p
                            class="truncate text-sm font-medium text-foreground"
                          >
                            {{ run.name }}
                          </p>
                          <p
                            class="mt-0.5 truncate text-xs text-foreground-secondary"
                          >
                            {{ formatDateTime(run.created_at) }}
                            <span v-if="run.proxy_name">
                              · {{ run.proxy_name }}</span
                            >
                          </p>
                          <p
                            v-if="run.message || run.error_message"
                            class="mt-1 truncate text-xs text-foreground-secondary"
                          >
                            {{ run.message || run.error_message }}
                          </p>
                        </div>
                      </div>
                      <span
                        :class="[
                          'inline-flex shrink-0 items-center px-2 py-0.5 rounded-full text-[11px] font-medium',
                          getStatusColor(run.status),
                        ]"
                      >
                        {{ t(`backupTasks.status.${run.status}`) }}
                      </span>
                    </div>

                    <div
                      class="grid grid-cols-2 gap-2 text-xs md:grid-cols-[90px_110px_1fr_100px]"
                    >
                      <div>
                        <p class="text-[11px] text-foreground-muted">
                          {{ t("backupTasks.progress.progress") }}
                        </p>
                        <p class="font-medium text-foreground">
                          {{ run.progress || 0 }}%
                        </p>
                      </div>
                      <div>
                        <p class="text-[11px] text-foreground-muted">
                          {{ t("alertsCenter.common.duration") }}
                        </p>
                        <p class="font-medium text-foreground">
                          {{ runDuration(run) }}
                        </p>
                      </div>
                      <div>
                        <p class="text-[11px] text-foreground-muted">
                          {{ t("backupTasks.progress.files") }}
                        </p>
                        <p class="font-medium text-foreground">
                          {{ run.processed_files || 0 }} /
                          {{ run.total_files || 0 }}
                        </p>
                      </div>
                      <div>
                        <p class="text-[11px] text-foreground-muted">
                          {{ t("backupTasks.progress.speed") }}
                        </p>
                        <p class="font-medium text-foreground">
                          {{
                            run.speed_mbps
                              ? `${run.speed_mbps.toFixed(2)} MB/s`
                              : "-"
                          }}
                        </p>
                      </div>
                    </div>

                    <div
                      class="h-1.5 rounded-full bg-background-tertiary overflow-hidden"
                    >
                      <div
                        class="h-full bg-primary transition-all"
                        :style="{
                          width: `${Math.min(run.progress || 0, 100)}%`,
                        }"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </Teleport>
    <Teleport to="body">
      <div
        v-if="snapshotHelpTooltip"
        class="fixed z-[2147483647] w-72 -translate-x-1/2 rounded-lg border border-border bg-card px-3 py-2 text-left text-xs font-normal leading-5 text-foreground-secondary shadow-2xl pointer-events-auto"
        :style="{
          top: `${snapshotHelpTooltip.top}px`,
          left: `${snapshotHelpTooltip.left}px`,
        }"
        @mouseenter="cancelSnapshotHelpTooltipHide"
        @mouseleave="scheduleSnapshotHelpTooltipHide"
      >
        {{ t(snapshotHelpTooltip.key) }}
      </div>
    </Teleport>
    <Teleport to="body">
      <div
        v-if="snapshotHoverTooltip"
        class="fixed z-[2147483647] w-72 -translate-x-1/2 rounded-lg border border-border bg-card p-3 text-xs shadow-2xl pointer-events-auto"
        :class="
          snapshotHoverTooltip.placement === 'top' ? '-translate-y-full' : ''
        "
        :style="{
          top: `${snapshotHoverTooltip.top}px`,
          left: `${snapshotHoverTooltip.left}px`,
        }"
        @mouseenter="cancelSnapshotHoverTooltipHide"
        @mouseleave="scheduleSnapshotHoverTooltipHide"
      >
        <div class="flex items-center gap-2 border-b border-border pb-2">
          <CircleStackIcon class="w-4 h-4 text-emerald-600" />
          <p class="font-semibold text-foreground truncate">
            {{
              snapshotHoverTooltip.snapshot.name ||
              snapshotHoverTooltip.snapshot.version ||
              snapshotHoverTooltip.snapshot.id
            }}
          </p>
        </div>
        <dl class="mt-2 grid grid-cols-[88px_minmax(0,1fr)] gap-x-2 gap-y-1.5">
          <dt class="text-foreground-muted">
            {{ t("backupTasks.detail.snapshotId") }}
          </dt>
          <dd class="text-foreground truncate">
            {{
              snapshotHoverTooltip.snapshot.version ||
              snapshotHoverTooltip.snapshot.id
            }}
          </dd>
          <dt class="text-foreground-muted">
            {{ t("common.date") }}
          </dt>
          <dd class="text-foreground">
            {{
              formatDateTime(snapshotDisplayTime(snapshotHoverTooltip.snapshot))
            }}
          </dd>
          <dt class="text-foreground-muted">
            {{
              isNoChangeSnapshotReference(snapshotHoverTooltip.snapshot)
                ? t("backupTasks.detail.dataWritten")
                : t("backupTasks.progress.size")
            }}
          </dt>
          <dd class="text-foreground">
            {{
              formatBytes(snapshotDisplaySize(snapshotHoverTooltip.snapshot))
            }}
          </dd>
          <dt class="text-foreground-muted">
            {{ t("backupTasks.progress.files") }}
          </dt>
          <dd class="text-foreground">
            {{
              isNoChangeSnapshotReference(snapshotHoverTooltip.snapshot)
                ? t("backupTasks.detail.changedFiles", { count: 0 })
                : snapshotDisplayFileCount(snapshotHoverTooltip.snapshot)
            }}
          </dd>
          <dt class="text-foreground-muted">
            {{ t("backupTasks.detail.kopiaState") }}
          </dt>
          <dd>
            <span
              :class="[
                'rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                snapshotStatusClass(snapshotHoverTooltip.snapshot),
              ]"
            >
              {{ snapshotStatusLabel(snapshotHoverTooltip.snapshot) }}
            </span>
          </dd>
          <dt
            v-if="isNoChangeSnapshotReference(snapshotHoverTooltip.snapshot)"
            class="text-foreground-muted"
          >
            {{ t("common.status") }}
          </dt>
          <dd
            v-if="isNoChangeSnapshotReference(snapshotHoverTooltip.snapshot)"
            class="text-amber-600 dark:text-amber-300"
          >
            {{ t("backupTasks.detail.noChanges") }}
          </dd>
          <dt
            v-if="isNoChangeSnapshotReference(snapshotHoverTooltip.snapshot)"
            class="text-foreground-muted"
          >
            {{ t("backupTasks.detail.referencedSnapshot") }}
          </dt>
          <dd
            v-if="isNoChangeSnapshotReference(snapshotHoverTooltip.snapshot)"
            class="text-foreground truncate"
          >
            {{ snapshotReferencedId(snapshotHoverTooltip.snapshot) || "-" }}
          </dd>
          <dt
            v-if="isNoChangeSnapshotReference(snapshotHoverTooltip.snapshot)"
            class="text-foreground-muted"
          >
            {{ t("backupTasks.detail.referencedSize") }}
          </dt>
          <dd
            v-if="isNoChangeSnapshotReference(snapshotHoverTooltip.snapshot)"
            class="text-foreground"
          >
            {{ formatBytes(snapshotHoverTooltip.snapshot.total_size || 0) }}
          </dd>
          <dt
            v-if="isNoChangeSnapshotReference(snapshotHoverTooltip.snapshot)"
            class="text-foreground-muted"
          >
            {{ t("backupTasks.detail.referencedFiles") }}
          </dt>
          <dd
            v-if="isNoChangeSnapshotReference(snapshotHoverTooltip.snapshot)"
            class="text-foreground"
          >
            {{ snapshotHoverTooltip.snapshot.file_count || 0 }}
          </dd>
          <dt
            v-if="snapshotHoverTooltip.snapshot.expires_at"
            class="text-foreground-muted"
          >
            {{ t("backupTasks.detail.expiresAt") }}
          </dt>
          <dd
            v-if="snapshotHoverTooltip.snapshot.expires_at"
            class="text-foreground"
          >
            {{ formatDateTime(snapshotHoverTooltip.snapshot.expires_at) }}
          </dd>
        </dl>
      </div>
    </Teleport>
  </div>
</template>
