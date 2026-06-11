<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  recoveryTasksApi,
  backupTasksApi,
  nodesApi,
  repositoriesApi,
  sourceResourcesApi,
} from "@/api";
import { useAppStore } from "@/stores/app";
import { getApiErrorMessage } from "@/utils/errors";
import type {
  RecoveryTask,
  RecoveryTaskCreateData,
  RecoveryRun,
  RecoveryTaskStatsBackend,
  SnapshotInfo,
} from "@/types/recovery";
import type { ProxyNode } from "@/types/proxy";
import type { Repository } from "@/types/repository";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import RecoveryTaskDetailModal from "@/components/recovery-tasks/RecoveryTaskDetailModal.vue";
import RecoveryTaskListView from "@/components/recovery-tasks/RecoveryTaskListView.vue";
import RecoveryTaskStats from "@/components/recovery-tasks/RecoveryTaskStats.vue";
import RecoveryTaskToolbar from "@/components/recovery-tasks/RecoveryTaskToolbar.vue";
import RecoveryBasicInfoForm from "@/components/recovery-tasks/RecoveryBasicInfoForm.vue";
import RecoveryOptionsSelector from "@/components/recovery-tasks/RecoveryOptionsSelector.vue";
import RecoveryPointSelector from "@/components/recovery-tasks/RecoveryPointSelector.vue";
import RecoveryScopeSelector from "@/components/recovery-tasks/RecoveryScopeSelector.vue";
import RecoveryTargetSelector from "@/components/recovery-tasks/RecoveryTargetSelector.vue";
import RecoveryWizardReviewAside from "@/components/recovery-tasks/RecoveryWizardReviewAside.vue";
import RecoveryWizardStepper from "@/components/recovery-tasks/RecoveryWizardStepper.vue";
import PageTitle from "@/components/PageTitle.vue";
import {
  PlusIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  BoltIcon,
  PauseIcon,
  XCircleIcon,
  ArrowUturnLeftIcon,
} from "@heroicons/vue/24/outline";

const { t } = useI18n();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();

const isLoading = ref(true);
const tasks = ref<RecoveryTask[]>([]);
const stats = ref<RecoveryTaskStatsBackend | null>(null);
const nodes = ref<ProxyNode[]>([]);
const repositories = ref<Repository[]>([]);
const sourceResources = ref<any[]>([]);
const backupTasks = ref<any[]>([]);
const snapshots = ref<SnapshotInfo[]>([]);
const showCreateModal = ref(false);
const editingTaskId = ref<string | null>(null);
const showDetailModal = ref(false);
const selectedTask = ref<RecoveryTask | null>(null);
const detailTab = ref<"overview" | "runs">("overview");
const recoveryRuns = ref<RecoveryRun[]>([]);
const runsLoading = ref(false);
const selectedStatus = ref<string>("all");
const searchQuery = ref("");
const snapshotSearchQuery = ref("");
const snapshotKindFilter = ref("data");
const snapshotsLoading = ref(false);
const snapshotsLoadingMore = ref(false);
const snapshotPage = ref(1);
const snapshotTotal = ref(0);
const snapshotNextPage = ref<number | null>(null);
const recoverySnapshotFiles = ref<any[]>([]);
const recoverySnapshotFilesLoading = ref(false);
const recoverySnapshotFilesError = ref("");
const loadingRecoverySnapshotPaths = ref<Set<string>>(new Set());
const selectedSourceResourceId = ref("");
const selectedBackupTaskId = ref("");

// Pagination
const currentPage = ref(1);
const pageSize = ref(getPageSize("recovery-tasks"));
const PAGE_STORAGE_KEY = "recovery-tasks";

watch(pageSize, (newSize) => {
  setPageSize(newSize, PAGE_STORAGE_KEY);
});

const createStep = ref(0);

function createRecoveryDraft(): RecoveryTaskCreateData {
  return {
    name: "",
    description: "",
    node: "",
    repository: "",
    snapshot_id: "",
    recovery_type: "new_location",
    target_path: "",
    restore_scope: "entire_snapshot",
    selected_paths: [],
    conflict_policy: "skip",
    priority: "normal",
    metadata: {},
  };
}

const newRecovery = ref<RecoveryTaskCreateData>(createRecoveryDraft());

const recoveryWizardSteps = computed(() => [
  {
    key: "basic",
    label: t("recoveryTasks.wizard.basic"),
    description: t("recoveryTasks.wizard.basicHelp"),
  },
  {
    key: "point",
    label: t("recoveryTasks.wizard.recoveryPoint"),
    description: t("recoveryTasks.wizard.recoveryPointHelp"),
  },
  {
    key: "scope",
    label: t("recoveryTasks.wizard.scope"),
    description: t("recoveryTasks.wizard.scopeHelp"),
  },
  {
    key: "target",
    label: t("recoveryTasks.wizard.target"),
    description: t("recoveryTasks.wizard.targetHelp"),
  },
  {
    key: "review",
    label: t("recoveryTasks.wizard.review"),
    description: t("recoveryTasks.wizard.reviewHelp"),
  },
]);

const isLastCreateStep = computed(
  () => createStep.value === recoveryWizardSteps.value.length - 1,
);

const recoveryStats = computed(() => {
  if (!stats.value) {
    return {
      total_tasks: 0,
      pending_tasks: 0,
      running_tasks: 0,
      completed_tasks: 0,
      failed_tasks: 0,
      total_files: 0,
      total_size_bytes: 0,
    };
  }
  return {
    total_tasks: stats.value.total || 0,
    pending_tasks: stats.value.pending || 0,
    running_tasks: stats.value.running || 0,
    completed_tasks: stats.value.completed || 0,
    failed_tasks: stats.value.failed || 0,
    total_files: stats.value.total_files || 0,
    total_size_bytes: stats.value.total_size || 0,
  };
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

type RecoveryTaskColumnKey =
  | "name"
  | "type"
  | "status"
  | "snapshot"
  | "repository"
  | "recovery_target"
  | "progress"
  | "date"
  | "actions";

const recoveryTaskColumns = computed(() => [
  { key: "name" as const, label: t("common.name"), min: 200, max: 320 },
  {
    key: "type" as const,
    label: t("recoveryTasks.form.type"),
    min: 120,
    max: 160,
  },
  { key: "status" as const, label: t("common.status"), min: 120, max: 160 },
  {
    key: "snapshot" as const,
    label: t("recoveryTasks.columns.snapshot"),
    min: 200,
    max: 300,
  },
  {
    key: "repository" as const,
    label: t("recoveryTasks.columns.repository"),
    min: 180,
    max: 280,
  },
  {
    key: "recovery_target" as const,
    label: t("recoveryTasks.columns.recoveryTarget"),
    min: 200,
    max: 360,
  },
  {
    key: "progress" as const,
    label: t("recoveryTasks.progress.progress"),
    min: 200,
    max: 320,
  },
  { key: "date" as const, label: t("common.date"), min: 150, max: 200 },
  {
    key: "actions" as const,
    label: t("common.actions"),
    min: 130,
    max: 160,
    sortable: false,
    align: "right" as const,
  },
]);

const recoveryTaskTable = useResizableSortableTable<
  RecoveryTask,
  RecoveryTaskColumnKey
>({
  storageKey: "hyperfilelens:recovery-tasks:columns",
  columns: recoveryTaskColumns,
  rows: filteredTasks,
  defaultSort: { key: "date", direction: "desc" },
  minTableWidth: 1600,
  getSortValue: (task, key) => {
    if (key === "name") return task.name;
    if (key === "type") return task.recovery_type || "";
    if (key === "status") return task.status || "";
    if (key === "snapshot") return task.snapshot_name || "";
    if (key === "repository") return task.repository_name || "";
    if (key === "recovery_target") return task.target_node_name || "";
    if (key === "progress") return task.progress || 0;
    if (key === "date")
      return task.created_at ? new Date(task.created_at).getTime() : 0;
    return "";
  },
  getColumnText: (task, key) => {
    if (key === "name") return `${task.name} ${task.target_node_name || ""}`;
    if (key === "type")
      return t(`recoveryTasks.types.${task.recovery_type || "original"}`);
    if (key === "status") return task.status || "";
    if (key === "snapshot") return task.snapshot_name || "-";
    if (key === "repository") {
      // Show repository name with share path
      const repoName = task.repository_name || "-";
      const sharePath =
        task.snapshot_source_path || task.metadata?.source_path || "";
      return sharePath ? `${repoName}: ${sharePath}` : repoName;
    }
    if (key === "recovery_target") {
      // Show node name + target path
      const nodeName = task.target_node_name || "-";
      const targetPath = task.target_path || "";
      return targetPath ? `${nodeName}: ${targetPath}` : nodeName;
    }
    if (key === "progress") return String(task.progress || 0);
    if (key === "date") return formatDateTime(task.created_at);
    return "";
  },
});

// Paginated tasks for display
const paginatedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return recoveryTaskTable.sortedRows.value.slice(start, end);
});

// Reset page when filters change
watch([selectedStatus, searchQuery], () => {
  currentPage.value = 1;
});

async function fetchTasks() {
  isLoading.value = true;
  try {
    const response = await recoveryTasksApi.list();
    tasks.value = response.data.results || response.data;
  } catch (error) {
    console.error("Failed to fetch tasks:", error);
  } finally {
    isLoading.value = false;
  }
}

async function fetchStats() {
  try {
    const response = await recoveryTasksApi.stats();
    stats.value = response.data;
  } catch (error) {
    console.error("Failed to fetch stats:", error);
  }
}

async function fetchNodesAndRepos() {
  try {
    const [nodesRes, reposRes, sourceRes, tasksRes] = await Promise.all([
      nodesApi.list({ page_size: 100 }),
      repositoriesApi.list({ page_size: 100 }),
      sourceResourcesApi.list({ page_size: 1000 }),
      backupTasksApi.list({ page_size: 1000, ordering: "name" }),
    ]);
    nodes.value = nodesRes.data.results || nodesRes.data;
    repositories.value = reposRes.data.results || reposRes.data;
    sourceResources.value = sourceRes.data.results || sourceRes.data;
    backupTasks.value = tasksRes.data.results || tasksRes.data;
  } catch (error) {
    console.error("Failed to fetch recovery dependencies:", error);
  }
}

async function fetchSnapshots() {
  if (!selectedBackupTaskId.value) {
    snapshots.value = [];
    newRecovery.value.snapshot_id = "";
    snapshotPage.value = 1;
    snapshotTotal.value = 0;
    snapshotNextPage.value = null;
    return;
  }
  snapshotsLoading.value = true;
  snapshotPage.value = 1;
  try {
    const response = await backupTasksApi.listSnapshots({
      task: selectedBackupTaskId.value,
      search: snapshotSearchQuery.value.trim() || undefined,
      snapshot_status: "available",
      snapshot_kind:
        snapshotKindFilter.value === "all"
          ? undefined
          : snapshotKindFilter.value,
      page: 1,
      page_size: 50,
    });
    snapshots.value = response.data.results || response.data;
    snapshotTotal.value = response.data.count ?? snapshots.value.length;
    snapshotNextPage.value = response.data.next ? 2 : null;
  } catch (error) {
    console.error("Failed to fetch snapshots:", error);
  } finally {
    snapshotsLoading.value = false;
  }
}

async function loadMoreSnapshots() {
  if (
    !selectedBackupTaskId.value ||
    !snapshotNextPage.value ||
    snapshotsLoadingMore.value
  ) {
    return;
  }
  const page = snapshotNextPage.value;
  snapshotsLoadingMore.value = true;
  try {
    const response = await backupTasksApi.listSnapshots({
      task: selectedBackupTaskId.value,
      search: snapshotSearchQuery.value.trim() || undefined,
      snapshot_status: "available",
      snapshot_kind:
        snapshotKindFilter.value === "all"
          ? undefined
          : snapshotKindFilter.value,
      page,
      page_size: 50,
    });
    const nextResults = response.data.results || response.data || [];
    const existingIds = new Set(snapshots.value.map((snap) => snap.id));
    snapshots.value = [
      ...snapshots.value,
      ...nextResults.filter((snap: SnapshotInfo) => !existingIds.has(snap.id)),
    ];
    snapshotTotal.value = response.data.count ?? snapshots.value.length;
    snapshotPage.value = page;
    snapshotNextPage.value = response.data.next ? page + 1 : null;
  } catch (error) {
    console.error("Failed to load more snapshots:", error);
  } finally {
    snapshotsLoadingMore.value = false;
  }
}

watch(
  () => selectedBackupTaskId.value,
  (taskId) => {
    const task = backupTasks.value.find((item) => String(item.id) === taskId);
    newRecovery.value.repository = task?.target_repository || "";
    newRecovery.value.snapshot_id = "";
    snapshotSearchQuery.value = "";
    fetchSnapshots();
  },
);

let snapshotSearchTimer: number | null = null;
watch([snapshotSearchQuery, snapshotKindFilter], () => {
  if (!selectedBackupTaskId.value) return;
  if (snapshotSearchTimer) clearTimeout(snapshotSearchTimer);
  snapshotSearchTimer = window.setTimeout(() => {
    fetchSnapshots();
  }, 250);
});

watch(
  () => newRecovery.value.snapshot_id,
  () => {
    recoverySnapshotFiles.value = [];
    recoverySnapshotFilesError.value = "";
    loadingRecoverySnapshotPaths.value = new Set();
    newRecovery.value.selected_paths = [];
  },
);

watch(
  () => newRecovery.value.restore_scope,
  (scope) => {
    if (
      scope === "selected_paths" &&
      newRecovery.value.snapshot_id &&
      recoverySnapshotFiles.value.length === 0
    ) {
      loadRecoverySnapshotFiles();
    }
  },
);

const selectedSnapshot = computed(() =>
  snapshots.value.find((snap) => snap.id === newRecovery.value.snapshot_id),
);

const filteredSnapshots = computed(() => {
  return snapshots.value;
});

const filteredBackupTasks = computed(() => {
  if (!selectedSourceResourceId.value) return backupTasks.value;
  return backupTasks.value.filter(
    (task) => String(task.source_resource || "") === selectedSourceResourceId.value,
  );
});

const selectedTargetNode = computed(() =>
  nodes.value.find(
    (node) => String(node.id) === String(newRecovery.value.node),
  ),
);

const selectedRecoveryFileStats = computed(() => {
  const paths = newRecovery.value.selected_paths || [];
  const selected = new Set(paths);
  let knownFiles = 0;
  let knownBytes = 0;
  for (const file of recoverySnapshotFiles.value) {
    if (
      selected.has(file.relative_path) ||
      Array.from(selected).some((path) =>
        file.relative_path?.startsWith(`${path}/`),
      )
    ) {
      if (!file.is_dir) {
        knownFiles += 1;
        knownBytes += Number(file.size || 0);
      }
    }
  }
  return { paths: paths.length, knownFiles, knownBytes };
});

const canCreateRecovery = computed(() => {
  return Boolean(
    newRecovery.value.name &&
    newRecovery.value.node &&
    newRecovery.value.snapshot_id &&
    newRecovery.value.target_path,
  );
});

const canContinueRecoveryWizard = computed(() => {
  if (createStep.value === 0) {
    return Boolean(newRecovery.value.name);
  }
  if (createStep.value === 1) {
    return Boolean(selectedBackupTaskId.value && newRecovery.value.snapshot_id);
  }
  if (createStep.value === 2) {
    return (
      newRecovery.value.restore_scope === "entire_snapshot" ||
      Boolean(newRecovery.value.selected_paths?.length)
    );
  }
  if (createStep.value === 3) {
    return Boolean(newRecovery.value.node && newRecovery.value.target_path);
  }
  return canCreateRecovery.value;
});

function openCreateRecovery() {
  editingTaskId.value = null;
  newRecovery.value = createRecoveryDraft();
  selectedSourceResourceId.value = "";
  selectedBackupTaskId.value = "";
  snapshots.value = [];
  snapshotSearchQuery.value = "";
  createStep.value = 0;
  showCreateModal.value = true;
}

function openEditRecovery(task: RecoveryTask) {
  const repositoryId = task.repository_id || "";
  const snapshotId = task.snapshot || task.snapshot_id || "";
  editingTaskId.value = task.id;
  selectedSourceResourceId.value = "";
  selectedBackupTaskId.value = "";
  newRecovery.value = {
    name: task.name || "",
    description: task.description || "",
    node: task.target_node || "",
    repository: repositoryId,
    snapshot_id: snapshotId,
    recovery_type: task.recovery_type || "new_location",
    target_path: task.target_path || "",
    restore_scope: task.restore_scope || "entire_snapshot",
    selected_paths: [...(task.selected_paths || [])],
    conflict_policy: task.conflict_policy || "skip",
    priority: task.priority || "normal",
    metadata: task.metadata || {},
  };
  snapshots.value = snapshotId
    ? [
        {
          id: String(snapshotId),
          name: task.snapshot_name,
          total_size: task.snapshot_size,
          file_count: task.snapshot_file_count,
          snapshot_time: task.snapshot_created_at || task.created_at,
          source_path: task.snapshot_source_path || task.metadata?.source_path,
        } as SnapshotInfo,
      ]
    : [];
  createStep.value = 0;
  showCreateModal.value = true;
}

function copyRecovery(task: RecoveryTask) {
  openEditRecovery(task);
  editingTaskId.value = null;
  newRecovery.value.name = `${task.name} Copy`;
}

function closeCreateRecovery() {
  showCreateModal.value = false;
}

function updateSelectedSourceResource(value: string) {
  selectedSourceResourceId.value = value;
  selectedBackupTaskId.value = "";
  newRecovery.value.repository = "";
  newRecovery.value.snapshot_id = "";
  snapshots.value = [];
  snapshotSearchQuery.value = "";
  if (filteredBackupTasks.value.length === 1) {
    selectedBackupTaskId.value = String(filteredBackupTasks.value[0].id);
  }
}

function nextCreateStep() {
  if (!canContinueRecoveryWizard.value || isLastCreateStep.value) return;
  createStep.value += 1;
  if (
    createStep.value === 2 &&
    newRecovery.value.restore_scope === "selected_paths" &&
    newRecovery.value.snapshot_id &&
    recoverySnapshotFiles.value.length === 0
  ) {
    loadRecoverySnapshotFiles();
  }
}

function previousCreateStep() {
  if (createStep.value === 0) return;
  createStep.value -= 1;
}

async function executeRecovery(task: RecoveryTask) {
  try {
    await recoveryTasksApi.execute(task.id);
    appStore.showToast({
      type: "success",
      title: t("common.success"),
      message: t("recoveryTasks.messages.dispatched"),
    });
    await fetchTasks();
    await fetchStats();
  } catch (error) {
    console.error("Failed to execute recovery:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(
        error,
        t("recoveryTasks.messages.executeFailed"),
      ),
    });
  }
}

async function fetchRecoveryRuns(taskId: string) {
  runsLoading.value = true;
  try {
    const response = await recoveryTasksApi.runs(taskId, { page_size: 50 });
    recoveryRuns.value = response.data.results || response.data;
  } catch (error) {
    console.error("Failed to fetch recovery runs:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(
        error,
        t("recoveryTasks.messages.fetchRunsFailed"),
      ),
    });
  } finally {
    runsLoading.value = false;
  }
}

async function loadRecoverySnapshotFiles(path = "") {
  if (!newRecovery.value.snapshot_id) return;
  recoverySnapshotFilesError.value = "";
  if (!path) {
    recoverySnapshotFilesLoading.value = true;
  } else {
    loadingRecoverySnapshotPaths.value = new Set([
      ...loadingRecoverySnapshotPaths.value,
      path,
    ]);
  }
  try {
    const response = await backupTasksApi.listFiles(
      newRecovery.value.snapshot_id,
      path,
    );
    const files = response.data.results || response.data || [];
    if (!path) {
      recoverySnapshotFiles.value = normalizeRecoverySnapshotFiles(files, "");
      loadingRecoverySnapshotPaths.value = new Set();
    } else {
      mergeRecoverySnapshotChildren(path, files);
    }
  } catch (error) {
    const message = getApiErrorMessage(
      error,
      t("recoveryTasks.messages.snapshotFilesLoadFailed"),
    );
    recoverySnapshotFilesError.value = message;
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message,
    });
  } finally {
    if (!path) {
      recoverySnapshotFilesLoading.value = false;
    } else {
      const next = new Set(loadingRecoverySnapshotPaths.value);
      next.delete(path);
      loadingRecoverySnapshotPaths.value = next;
    }
  }
}

function normalizeRecoverySnapshotFiles(files: any[], parentPath: string) {
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

function mergeRecoverySnapshotChildren(parentPath: string, files: any[]) {
  const children = normalizeRecoverySnapshotFiles(files, parentPath);
  const withoutOldChildren = recoverySnapshotFiles.value.filter(
    (file) => file.parent_path !== parentPath,
  );
  const parentIndex = withoutOldChildren.findIndex(
    (file) => file.relative_path === parentPath,
  );
  if (parentIndex === -1) {
    recoverySnapshotFiles.value = withoutOldChildren;
    return;
  }
  withoutOldChildren[parentIndex] = {
    ...withoutOldChildren[parentIndex],
    children_loaded: true,
  };
  withoutOldChildren.splice(parentIndex + 1, 0, ...children);
  recoverySnapshotFiles.value = withoutOldChildren;
}

async function openTaskDetails(task: RecoveryTask) {
  try {
    const response = await recoveryTasksApi.detail(task.id);
    selectedTask.value = response.data;
  } catch {
    selectedTask.value = task;
  }
  detailTab.value = "overview";
  showDetailModal.value = true;
  recoveryRuns.value = [];
}

watch(detailTab, (tab) => {
  if (tab === "runs" && selectedTask.value) {
    fetchRecoveryRuns(selectedTask.value.id);
  }
});

async function cancelRecovery(task: RecoveryTask) {
  try {
    await recoveryTasksApi.cancel(task.id);
    appStore.showToast({
      type: "success",
      title: t("common.success"),
      message: t("recoveryTasks.messages.cancelled"),
    });
    await fetchTasks();
  } catch (error) {
    console.error("Failed to cancel recovery:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(error, t("common.saveFailed")),
    });
  }
}

async function pauseRecovery(task: RecoveryTask) {
  try {
    await recoveryTasksApi.pause(task.id);
    appStore.showToast({
      type: "success",
      title: t("common.success"),
      message: t("recoveryTasks.messages.paused"),
    });
    await fetchTasks();
    await fetchStats();
  } catch (error) {
    console.error("Failed to pause recovery:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(
        error,
        t("recoveryTasks.messages.pauseFailed"),
      ),
    });
  }
}

async function createRecovery() {
  try {
    if (editingTaskId.value) {
      await recoveryTasksApi.update(editingTaskId.value, {
        name: newRecovery.value.name,
        description: newRecovery.value.description,
        snapshot: newRecovery.value.snapshot_id,
        target_node: newRecovery.value.node,
        recovery_type: newRecovery.value.recovery_type,
        target_path: newRecovery.value.target_path,
        restore_scope: newRecovery.value.restore_scope,
        selected_paths: newRecovery.value.selected_paths,
        conflict_policy: newRecovery.value.conflict_policy,
        priority: newRecovery.value.priority,
        metadata: newRecovery.value.metadata,
      });
    } else {
      await recoveryTasksApi.create(newRecovery.value);
    }
    showCreateModal.value = false;
    editingTaskId.value = null;
    createStep.value = 0;
    newRecovery.value = createRecoveryDraft();
    await fetchTasks();
    await fetchStats();
  } catch (error) {
    console.error("Failed to create recovery:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(error, t("common.createFailed")),
    });
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function formatDateTime(value?: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending:
      "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
    dispatched:
      "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
    queued: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
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
    dispatched: ClockIcon,
    running: BoltIcon,
    completed: CheckCircleIcon,
    failed: ExclamationTriangleIcon,
    paused: PauseIcon,
    cancelled: XCircleIcon,
  };
  return icons[status] || ClockIcon;
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
      <PageTitle
        :icon="ArrowUturnLeftIcon"
        :title="t('recoveryTasks.title')"
        :subtitle="t('recoveryTasks.subtitle')"
        icon-class="text-emerald-600 dark:text-emerald-400"
      />
      <button
        data-tour="recovery-create-button"
        @click="openCreateRecovery"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-emerald-500 to-teal-600 rounded-lg hover:from-emerald-600 hover:to-teal-700 transition-all shadow-md hover:shadow-lg border border-emerald-600"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t("recoveryTasks.createTask") }}
      </button>
    </div>

    <RecoveryTaskStats :stats="recoveryStats" />

    <RecoveryTaskToolbar
      v-model:search-query="searchQuery"
      v-model:selected-status="selectedStatus"
      @refresh="fetchTasks"
    />

    <RecoveryTaskListView
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :loading="isLoading"
      :filtered-count="filteredTasks.length"
      :tasks="paginatedTasks"
      :columns="recoveryTaskColumns"
      :table="recoveryTaskTable"
      :format-date-time="formatDateTime"
      :get-status-color="getStatusColor"
      :get-status-icon="getStatusIcon"
      @execute="executeRecovery"
      @pause="pauseRecovery"
      @cancel="cancelRecovery"
      @edit="openEditRecovery"
      @copy="copyRecovery"
      @detail="openTaskDetails"
    />

    <!-- Create Modal -->
    <Teleport to="body">
      <div
        v-if="showCreateModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div
          class="absolute inset-0 bg-black/50"
          @click="closeCreateRecovery"
        />
        <div
          class="relative modal-surface rounded-2xl shadow-xl w-full max-w-5xl max-h-[90vh] overflow-y-auto"
        >
          <div
            class="sticky top-0 modal-surface px-6 py-4 border-b border-border flex items-center justify-between"
          >
            <h2 class="text-lg font-semibold text-foreground">
              {{
                editingTaskId
                  ? t("recoveryTasks.editTask")
                  : t("recoveryTasks.createTask")
              }}
            </h2>
            <button
              @click="closeCreateRecovery"
              class="p-1 hover:bg-background-tertiary rounded-lg"
            >
              <XCircleIcon class="w-5 h-5 text-slate-400" />
            </button>
          </div>

          <RecoveryWizardStepper
            :steps="recoveryWizardSteps"
            :current-step="createStep"
          />

          <div class="p-6 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
            <div class="space-y-5 min-h-[420px]">
              <RecoveryBasicInfoForm
                v-if="createStep === 0"
                v-model:name="newRecovery.name"
                v-model:description="newRecovery.description"
              />

              <RecoveryPointSelector
                v-if="createStep === 1"
                :selected-source-resource-id="selectedSourceResourceId"
                v-model:selected-backup-task-id="selectedBackupTaskId"
                v-model:selected-snapshot-id="newRecovery.snapshot_id"
                v-model:snapshot-search-query="snapshotSearchQuery"
                v-model:snapshot-kind-filter="snapshotKindFilter"
                :source-resources="sourceResources"
                :backup-tasks="filteredBackupTasks"
                :snapshots="filteredSnapshots"
                :snapshot-total="snapshotTotal"
                :snapshots-loading="snapshotsLoading"
                :snapshots-loading-more="snapshotsLoadingMore"
                :has-more-snapshots="Boolean(snapshotNextPage)"
                :format-bytes="formatBytes"
                :format-date-time="formatDateTime"
                @update:selected-source-resource-id="updateSelectedSourceResource"
                @load-more="loadMoreSnapshots"
              />

              <RecoveryScopeSelector
                v-if="createStep === 2"
                v-model:restore-scope="newRecovery.restore_scope"
                v-model:selected-paths="newRecovery.selected_paths"
                :files="recoverySnapshotFiles"
                :loading="recoverySnapshotFilesLoading"
                :error="recoverySnapshotFilesError"
                :loading-paths="loadingRecoverySnapshotPaths"
                :format-bytes="formatBytes"
                @load-files="loadRecoverySnapshotFiles"
              />

              <RecoveryTargetSelector
                v-if="createStep === 3"
                v-model:selected-node="newRecovery.node"
                v-model:recovery-type="newRecovery.recovery_type"
                v-model:target-path="newRecovery.target_path"
                :nodes="nodes"
              />

              <RecoveryOptionsSelector
                v-if="createStep === 4"
                v-model:conflict-policy="newRecovery.conflict_policy"
                v-model:priority="newRecovery.priority"
                :recovery="newRecovery"
                :selected-snapshot="selectedSnapshot"
                :selected-target-node="selectedTargetNode"
              />
            </div>

            <RecoveryWizardReviewAside
              :recovery="newRecovery"
              :selected-snapshot="selectedSnapshot"
              :selected-target-node="selectedTargetNode"
              :selected-file-stats="selectedRecoveryFileStats"
              :format-bytes="formatBytes"
            />
          </div>
          <div
            class="sticky bottom-0 modal-surface px-6 py-4 border-t border-border flex justify-between gap-3"
          >
            <button
              @click="previousCreateStep"
              :disabled="createStep === 0"
              class="px-4 py-2 text-sm text-foreground-secondary border border-border rounded-lg hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ t("common.previous") }}
            </button>
            <div class="flex justify-end gap-3">
              <button
                @click="closeCreateRecovery"
                class="px-4 py-2 text-sm text-foreground-secondary border border-border rounded-lg hover:bg-hover"
              >
                {{ t("common.cancel") }}
              </button>
              <button
                v-if="!isLastCreateStep"
                @click="nextCreateStep"
                :disabled="!canContinueRecoveryWizard"
                class="px-4 py-2 text-sm text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ t("common.next") }}
              </button>
              <button
                v-else
                @click="createRecovery"
                :disabled="!canCreateRecovery"
                class="px-4 py-2 text-sm text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ editingTaskId ? t("common.save") : t("common.create") }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <RecoveryTaskDetailModal
      v-if="showDetailModal && selectedTask"
      v-model:detail-tab="detailTab"
      :task="selectedTask"
      :runs="recoveryRuns"
      :runs-loading="runsLoading"
      :format-bytes="formatBytes"
      :format-date-time="formatDateTime"
      :get-status-color="getStatusColor"
      :get-status-icon="getStatusIcon"
      @close="showDetailModal = false"
      @refresh-runs="selectedTask && fetchRecoveryRuns(selectedTask.id)"
    />
  </div>
</template>
