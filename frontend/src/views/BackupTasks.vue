<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import {
  backupTasksApi,
  insightsApi,
  nodesApi,
  policiesApi,
  recoveryExportsApi,
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
import BackupTaskWizard from "@/components/BackupTaskWizard.vue";
import BackupTaskDetailHeader from "@/components/backup-tasks/BackupTaskDetailHeader.vue";
import BackupTaskOverviewTab from "@/components/backup-tasks/BackupTaskOverviewTab.vue";
import BackupTaskEditModal from "@/components/backup-tasks/BackupTaskEditModal.vue";
import BackupTaskRunsTab from "@/components/backup-tasks/BackupTaskRunsTab.vue";
import BackupTaskSnapshotsTab from "@/components/backup-tasks/BackupTaskSnapshotsTab.vue";
import BackupTaskStatsCards from "@/components/backup-tasks/BackupTaskStats.vue";
import BackupTaskTable from "@/components/backup-tasks/BackupTaskTable.vue";
import BackupTaskToolbar from "@/components/backup-tasks/BackupTaskToolbar.vue";
import SnapshotHoverCard from "@/components/backup-tasks/SnapshotHoverCard.vue";
import {
  isNoChangeSnapshotReference,
  isSnapshotBrowsable,
  snapshotDisplaySize,
  snapshotDisplayTime,
} from "@/features/backup-tasks/snapshotDisplay";
import { useSnapshotFileBrowser } from "@/features/backup-tasks/useSnapshotFileBrowser";
import {
  PlusIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  BoltIcon,
  PauseIcon,
  XCircleIcon,
} from "@heroicons/vue/24/outline";

const { t, locale } = useI18n();
const router = useRouter();
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
const collapseNoChangeSnapshots = ref(false);
const snapshotGroupBy = ref<"all" | "day" | "month" | "change" | "size">("all");
const snapshotViewMode = ref<"grid" | "timeline" | "blocks">("grid");
const snapshotsLoading = ref(false);
const runsLoading = ref(false);
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

const {
  selectedSnapshot,
  selectedSnapshotFiles,
  snapshotFilesError,
  snapshotFilesLoading,
  expandedSnapshotPaths,
  selectedSnapshotPaths,
  loadingSnapshotPaths,
  resetSnapshotBrowser,
  clearSelectedSnapshotIf,
  loadSnapshotFiles,
  visibleSnapshotFiles,
  toggleSnapshotDirectory,
  toggleSnapshotPathSelection,
  getSnapshotSelectionState,
  clearSnapshotPathSelection,
} = useSnapshotFileBrowser();

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
const snapshotCurrentPage = ref(1);
const snapshotPageSize = ref(getPageSize("backup-task-snapshots") || 50);
const PAGE_STORAGE_KEY = "backup-tasks";
const SNAPSHOT_PAGE_STORAGE_KEY = "backup-task-snapshots";

watch(pageSize, (newSize) => {
  setPageSize(newSize, PAGE_STORAGE_KEY);
});

watch(snapshotPageSize, (newSize) => {
  setPageSize(newSize, SNAPSHOT_PAGE_STORAGE_KEY);
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
  return snapshots.filter((snapshot) => !isNoChangeSnapshotReference(snapshot));
});

const hiddenNoChangeSnapshotCount = computed(
  () =>
    selectedTaskSnapshots.value.length - displayedTaskSnapshots.value.length,
);

const paginatedDisplayedTaskSnapshots = computed(() => {
  const start = (snapshotCurrentPage.value - 1) * snapshotPageSize.value;
  const end = start + snapshotPageSize.value;
  return displayedTaskSnapshots.value.slice(start, end);
});

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
  { value: "blocks" as const, label: t("backupTasks.detail.blocksView") },
]);

const groupedDisplayedTaskSnapshots = computed(() => {
  const snapshots = paginatedDisplayedTaskSnapshots.value;
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

watch([collapseNoChangeSnapshots, snapshotGroupBy, snapshotViewMode], () => {
  snapshotCurrentPage.value = 1;
});

watch(displayedTaskSnapshots, (snapshots) => {
  const totalPages = Math.max(
    1,
    Math.ceil(snapshots.length / snapshotPageSize.value),
  );
  if (snapshotCurrentPage.value > totalPages) {
    snapshotCurrentPage.value = totalPages;
  }
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
  resetSnapshotBrowser();
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
    snapshotCurrentPage.value = 1;
    clearSelectedSnapshotIf((snapshot) => !isSnapshotBrowsable(snapshot));
    clearSelectedSnapshotIf(
      (snapshot) =>
        collapseNoChangeSnapshots.value &&
        isNoChangeSnapshotReference(snapshot),
    );
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

async function exportSelectedSnapshotPaths() {
  if (!selectedSnapshot.value || selectedSnapshotPaths.value.size === 0) {
    appStore.warning(t("recoveryExports.selectRequired"));
    return;
  }
  const paths = Array.from(selectedSnapshotPaths.value);
  try {
    await recoveryExportsApi.create({
      name: `Export ${formatCompactDateTime(snapshotDisplayTime(selectedSnapshot.value))}`,
      snapshot_id: selectedSnapshot.value.id,
      selected_paths: paths,
      package_format: "zip",
      expires_in_hours: 24,
    });
    appStore.success(t("recoveryExports.created"));
    selectedSnapshotPaths.value = new Set();
    router.push("/recovery-exports");
  } catch (error) {
    appStore.error(
      getApiErrorMessage(error, t("recoveryExports.createFailed")),
    );
  }
}

async function indexSelectedSnapshot() {
  if (!selectedSnapshot.value?.id) return;
  snapshotOperationLoading.value = true;
  try {
    await insightsApi.indexSnapshot(selectedSnapshot.value.id, { force: true });
    appStore.success(t("snapshotInsights.indexStarted"));
  } catch (error) {
    appStore.error(
      getApiErrorMessage(error, t("snapshotInsights.indexFailed")),
    );
  } finally {
    snapshotOperationLoading.value = false;
  }
}

function openSelectedSnapshotInsights() {
  if (!selectedSnapshot.value?.id) return;
  router.push({
    name: "SnapshotInsights",
    params: { snapshotId: selectedSnapshot.value.id },
  });
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

async function createTaskFromWizard(payload: BackupTaskCreateData) {
  try {
    await backupTasksApi.create(payload);
    showCreateModal.value = false;
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

    <BackupTaskStatsCards
      :stats="taskStats"
      :total-backup-size="totalBackupSize"
      :format-bytes="formatBytes"
    />

    <BackupTaskToolbar
      v-model:search-query="searchQuery"
      v-model:selected-status="selectedStatus"
      @refresh="fetchTasks"
    />

    <BackupTaskTable
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :loading="isLoading"
      :total-items="filteredTasks.length"
      :tasks="paginatedTasks"
      :columns="backupTaskColumns"
      :table="backupTaskTable"
      :get-status-color="getStatusColor"
      :get-status-icon="getStatusIcon"
      :get-task-policy-summary="getTaskPolicySummary"
      :can-run-task="canRunTask"
      :format-date-time="formatDateTime"
      @execute="executeTask"
      @toggle-enabled="toggleTaskEnabled"
      @cancel="cancelTask"
      @detail="openTaskDetail"
      @edit="openEditTask"
      @delete="deleteTask"
    />

    <BackupTaskWizard
      v-if="showCreateModal"
      :sources="sourceResources"
      :repositories="repositories"
      :policies="backupPolicies"
      :nodes="nodes"
      @close="showCreateModal = false"
      @save="createTaskFromWizard"
    />

    <BackupTaskEditModal
      v-if="showEditModal && editingTask"
      v-model:form="editForm"
      :task="editingTask"
      :loading="editLoading"
      :saving="editSaving"
      :source="sourceForTask(editingTask)"
      :repository="repositoryForTask(editingTask)"
      :source-rows="sourceDetailRows(sourceForTask(editingTask))"
      :repository-rows="repositoryDetailRows(repositoryForTask(editingTask))"
      :policies="backupPolicies"
      :proxies="syncProxies"
      :selected-policy="selectedEditPolicy"
      :policy-schedule-summary="editPolicyScheduleSummary"
      :policy-retention-summary="editPolicyRetentionSummary"
      :retention-fields="editRetentionFields"
      :can-use-auto-placement="canUseAutoPlacementForTask(editingTask)"
      @close="showEditModal = false"
      @submit="updateTask"
    />

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
          <BackupTaskDetailHeader
            v-model:detail-tab="detailTab"
            v-model:auto-refresh="detailAutoRefresh"
            v-model:refresh-interval="detailRefreshInterval"
            :task="selectedTask"
            :current-loading="currentDetailTabLoading"
            :get-status-color="getStatusColor"
            :get-status-icon="getStatusIcon"
            :can-run-task="canRunTask"
            @close="showDetailModal = false"
            @select-tab="selectDetailTab"
            @refresh="refreshCurrentDetailTab()"
            @execute="executeTask"
            @toggle-enabled="toggleTaskEnabled"
          />

          <div class="p-6">
            <div
              v-if="detailLoading"
              class="py-10 text-center text-foreground-secondary"
            >
              {{ t("common.loading") }}
            </div>

            <BackupTaskOverviewTab
              v-else-if="detailTab === 'overview'"
              :task="selectedTask"
              :source="selectedSource"
              :repository="selectedRepository"
              :source-rows="sourceDetailRows(selectedSource)"
              :repository-rows="repositoryDetailRows(selectedRepository)"
              :format-date-time="formatDateTime"
              :format-bytes="formatBytes"
              :format-speed="formatSpeed"
            />

            <BackupTaskSnapshotsTab
              v-else-if="detailTab === 'snapshots'"
              v-model:collapse-no-change-snapshots="collapseNoChangeSnapshots"
              v-model:view-mode="snapshotViewMode"
              v-model:group-by="snapshotGroupBy"
              v-model:current-page="snapshotCurrentPage"
              v-model:page-size="snapshotPageSize"
              :loading="snapshotsLoading"
              :all-snapshots="selectedTaskSnapshots"
              :displayed-snapshots="displayedTaskSnapshots"
              :groups="groupedDisplayedTaskSnapshots"
              :hidden-no-change-snapshot-count="hiddenNoChangeSnapshotCount"
              :snapshot-operation-loading="snapshotOperationLoading"
              :view-mode-options="snapshotViewModeOptions"
              :group-options="snapshotGroupOptions"
              :selected-snapshot="selectedSnapshot"
              :files="selectedSnapshotFiles"
              :visible-files="visibleSnapshotFiles()"
              :files-loading="snapshotFilesLoading"
              :files-error="snapshotFilesError"
              :expanded-paths="expandedSnapshotPaths"
              :selected-paths="selectedSnapshotPaths"
              :loading-paths="loadingSnapshotPaths"
              :selection-state="getSnapshotSelectionState"
              :format-compact-date-time="formatCompactDateTime"
              :format-date-time="formatDateTime"
              :format-bytes="formatBytes"
              :snapshot-operation-button-loading="snapshotOperationLoading"
              @help="showSnapshotHelpTooltip"
              @hide-help="scheduleSnapshotHelpTooltipHide"
              @sync="syncSnapshotsFromKopia"
              @apply-retention="evaluateRetentionNow"
              @run-maintenance="runKopiaMaintenanceNow"
              @select="loadSnapshotFiles"
              @hover="showSnapshotHoverTooltip"
              @hide-hover="scheduleSnapshotHoverTooltipHide"
              @retry="loadSnapshotFiles(selectedSnapshot)"
              @toggle-directory="toggleSnapshotDirectory"
              @toggle-selection="toggleSnapshotPathSelection"
              @clear-selection="clearSnapshotPathSelection"
              @export-selected="exportSelectedSnapshotPaths"
              @index-snapshot="indexSelectedSnapshot"
              @view-insights="openSelectedSnapshotInsights"
            />

            <BackupTaskRunsTab
              v-else
              :runs="selectedTaskRuns"
              :loading="runsLoading"
              :get-status-color="getStatusColor"
              :format-date-time="formatDateTime"
              :run-duration="runDuration"
            />
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
    <SnapshotHoverCard
      :tooltip="snapshotHoverTooltip"
      :format-date-time="formatDateTime"
      :format-bytes="formatBytes"
      @mouseenter="cancelSnapshotHoverTooltipHide"
      @mouseleave="scheduleSnapshotHoverTooltipHide"
    />
  </div>
</template>
