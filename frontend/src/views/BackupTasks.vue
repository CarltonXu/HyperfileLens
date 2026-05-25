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
import { snapshotDisplayTime } from "@/features/backup-tasks/snapshotDisplay";
import {
  backupTaskProcessedBytes,
  backupTaskProcessedFiles,
  backupTaskProgressPercent,
  backupTaskSpeedBytesPerSecond,
} from "@/features/backup-tasks/progressDisplay";
import { useSnapshotFileBrowser } from "@/features/backup-tasks/useSnapshotFileBrowser";
import { useSnapshotTooltips } from "@/features/backup-tasks/useSnapshotTooltips";
import { useBackupTaskFormatting } from "@/features/backup-tasks/useBackupTaskFormatting";
import { useBackupTaskSnapshots } from "@/features/backup-tasks/useBackupTaskSnapshots";
import { useBackupTaskEdit } from "@/features/backup-tasks/useBackupTaskEdit";
import { PlusIcon } from "@heroicons/vue/24/outline";

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
const selectedTask = ref<BackupTask | null>(null);
const detailTab = ref<"overview" | "snapshots" | "tasks">("overview");
const selectedTaskRuns = ref<any[]>([]);
const runsLoading = ref(false);
const detailLoading = ref(false);
const detailRefreshing = ref(false);
const selectedStatus = ref<string>("all");
const searchQuery = ref("");
const detailAutoRefresh = ref(false);
const detailRefreshInterval = ref(10);
const detailRefreshTimer = ref<ReturnType<typeof setInterval> | null>(null);

// Runs pagination and filters
const runsCurrentPage = ref(1);
const runsPageSize = ref(20);
const runsTotalCount = ref(0);
const runsStatusFilter = ref("all");
const runsTriggerFilter = ref("all");
const runsOrdering = ref("-created_at");
const {
  snapshotHelpTooltip,
  snapshotHoverTooltip,
  cancelSnapshotHelpTooltipHide,
  showSnapshotHelpTooltip,
  scheduleSnapshotHelpTooltipHide,
  cancelSnapshotHoverTooltipHide,
  showSnapshotHoverTooltip,
  scheduleSnapshotHoverTooltipHide,
} = useSnapshotTooltips();

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

const {
  formatBytes,
  getStatusColor,
  getStatusIcon,
  formatDateTime,
  formatCompactDateTime,
  snapshotGroupDescription,
  snapshotGroupFor,
  formatSpeed,
  getTaskPolicySummary,
  sourceDetailRows,
  repositoryDetailRows,
  runDuration,
} = useBackupTaskFormatting(t, locale, backupPolicies);

const {
  selectedTaskSnapshots,
  collapseNoChangeSnapshots,
  snapshotGroupBy,
  snapshotViewMode,
  snapshotsLoading,
  snapshotOperationLoading,
  snapshotCurrentPage,
  snapshotPageSize,
  displayedTaskSnapshots,
  hiddenNoChangeSnapshotCount,
  groupedDisplayedTaskSnapshots,
  snapshotGroupOptions,
  snapshotViewModeOptions,
  loadTaskSnapshots,
  syncSnapshotsFromKopia,
  evaluateRetentionNow,
  runKopiaMaintenanceNow,
  resetTaskSnapshots,
} = useBackupTaskSnapshots({
  selectedTask,
  t,
  appStore,
  clearSelectedSnapshotIf,
  snapshotGroupDescription,
  snapshotGroupFor,
});

const {
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
} = useBackupTaskEdit({
  t,
  appStore,
  backupPolicies,
  selectedTask,
  fetchTasks,
  fetchStats,
});

// Pagination
const currentPage = ref(1);
const pageSize = ref(getPageSize("backup-tasks"));
const PAGE_STORAGE_KEY = "backup-tasks";

watch(pageSize, (newSize) => {
  setPageSize(newSize, PAGE_STORAGE_KEY);
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

type BackupTaskColumnKey =
  | "name"
  | "policy"
  | "source"
  | "repository"
  | "status"
  | "progress"
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
    key: "progress" as const,
    label: t("backupTasks.progress.title"),
    min: 240,
    max: 380,
  },
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
  minTableWidth: 1620,
  getSortValue: (task, key) => {
    if (key === "name") return task.name;
    if (key === "policy") return task.schedule_name || "";
    if (key === "source") return task.source_resource_name || "";
    if (key === "repository") return task.target_repository_name || "";
    if (key === "status") return task.status || "";
    if (key === "progress") return backupTaskProgressPercent(task);
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
    if (key === "progress")
      return `${backupTaskProgressPercent(task)} ${backupTaskProcessedFiles(task)} ${backupTaskProcessedBytes(task)} ${backupTaskSpeedBytesPerSecond(task)}`;
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

// Reset page when filters change
watch([selectedStatus, searchQuery], () => {
  currentPage.value = 1;
});

// Reset runs page when filters change
watch([runsStatusFilter, runsTriggerFilter, runsOrdering], () => {
  runsCurrentPage.value = 1;
  if (detailTab.value === "tasks") {
    loadTaskRuns();
  }
});

// Reload runs when page size changes
watch([runsPageSize], () => {
  if (detailTab.value === "tasks") {
    loadTaskRuns();
  }
});

function stopDetailAutoRefresh() {
  if (detailRefreshTimer.value) {
    clearInterval(detailRefreshTimer.value);
    detailRefreshTimer.value = null;
  }
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

onUnmounted(stopDetailAutoRefresh);

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
  resetTaskSnapshots();
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

async function loadTaskRuns() {
  if (!selectedTask.value) return;
  runsLoading.value = true;
  try {
    const params: any = {
      page: runsCurrentPage.value,
      page_size: runsPageSize.value,
      ordering: runsOrdering.value,
    };
    if (runsStatusFilter.value !== 'all') {
      params.status = runsStatusFilter.value;
    }
    if (runsTriggerFilter.value !== 'all') {
      params.trigger_type = runsTriggerFilter.value;
    }
    const response = await backupTasksApi.runs(selectedTask.value.id, params);
    selectedTaskRuns.value = response.data.results || response.data || [];
    runsTotalCount.value = response.data.count || response.data.length || 0;
  } catch (error) {
    console.error("Failed to fetch task runs:", error);
  } finally {
    runsLoading.value = false;
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

function openRunInTaskManagement(run: any) {
  const taskId = run.management_task_id || run.proxy_task_id || run.id;
  if (!taskId) return;
  const route = router.resolve({
    name: "EventLog",
    query: { task: taskId },
  });
  window.open(route.href, "_blank", "noopener");
}

async function copyRunError(text: string) {
  try {
    if (navigator.clipboard?.writeText && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      const copied = document.execCommand("copy");
      document.body.removeChild(textarea);
      if (!copied) throw new Error("copy failed");
    }
    appStore.showToast({
      type: "success",
      title: t("common.copied"),
      message: t("backupTasks.runs.errorCopied"),
    });
  } catch (error) {
    console.error("Failed to copy run error:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: t("common.copyFailedToClipboard"),
    });
  }
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

function canRunTask(task: BackupTask) {
  return task.status !== "running" && task.is_enabled !== false;
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
      :format-bytes="formatBytes"
      :format-speed="formatSpeed"
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
              v-model:current-page="runsCurrentPage"
              v-model:page-size="runsPageSize"
              v-model:status-filter="runsStatusFilter"
              v-model:trigger-filter="runsTriggerFilter"
              v-model:ordering="runsOrdering"
              :runs="selectedTaskRuns"
              :loading="runsLoading"
              :total-count="runsTotalCount"
              :get-status-color="getStatusColor"
              :format-date-time="formatDateTime"
              :run-duration="runDuration"
              @open-management="openRunInTaskManagement"
              @copy-error="copyRunError"
              @reload="loadTaskRuns"
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
