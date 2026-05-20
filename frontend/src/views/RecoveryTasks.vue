<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  recoveryTasksApi,
  backupTasksApi,
  nodesApi,
  repositoriesApi,
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
import RecoveryWizardReviewAside from "@/components/recovery-tasks/RecoveryWizardReviewAside.vue";
import RecoveryWizardStepper from "@/components/recovery-tasks/RecoveryWizardStepper.vue";
import {
  PlusIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  BoltIcon,
  PauseIcon,
  XCircleIcon,
  ServerIcon,
  CircleStackIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  DocumentIcon,
  FolderIcon,
  FolderOpenIcon,
  ShieldCheckIcon,
} from "@heroicons/vue/24/outline";

const { t } = useI18n();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();

const vIndeterminate = {
  mounted(el: HTMLInputElement, binding: { value: boolean }) {
    el.indeterminate = Boolean(binding.value);
  },
  updated(el: HTMLInputElement, binding: { value: boolean }) {
    el.indeterminate = Boolean(binding.value);
  },
};

const isLoading = ref(true);
const tasks = ref<RecoveryTask[]>([]);
const stats = ref<RecoveryTaskStatsBackend | null>(null);
const nodes = ref<ProxyNode[]>([]);
const repositories = ref<Repository[]>([]);
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
const recoverySnapshotFiles = ref<any[]>([]);
const recoverySnapshotFilesLoading = ref(false);
const recoverySnapshotFilesError = ref("");
const expandedRecoverySnapshotPaths = ref<Set<string>>(new Set());
const loadingRecoverySnapshotPaths = ref<Set<string>>(new Set());

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
  | "progress"
  | "date"
  | "actions";

const recoveryTaskColumns = computed(() => [
  { key: "name" as const, label: t("common.name"), min: 240, max: 460 },
  {
    key: "type" as const,
    label: t("recoveryTasks.form.type"),
    min: 180,
    max: 280,
  },
  { key: "status" as const, label: t("common.status"), min: 140, max: 220 },
  {
    key: "progress" as const,
    label: t("recoveryTasks.progress.progress"),
    min: 150,
    max: 240,
  },
  { key: "date" as const, label: t("common.date"), min: 150, max: 260 },
  {
    key: "actions" as const,
    label: t("common.actions"),
    min: 130,
    max: 200,
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
  minTableWidth: 1020,
  getSortValue: (task, key) => {
    if (key === "name") return task.name;
    if (key === "type") return task.recovery_type || "";
    if (key === "status") return task.status || "";
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
    const [nodesRes, reposRes] = await Promise.all([
      nodesApi.list({ page_size: 100 }),
      repositoriesApi.list({ page_size: 100 }),
    ]);
    nodes.value = nodesRes.data.results || nodesRes.data;
    repositories.value = reposRes.data.results || reposRes.data;
  } catch (error) {
    console.error("Failed to fetch nodes/repos:", error);
  }
}

async function fetchSnapshots() {
  if (!newRecovery.value.repository) {
    snapshots.value = [];
    newRecovery.value.snapshot_id = "";
    return;
  }
  try {
    const response = await backupTasksApi.listSnapshots({
      repository: newRecovery.value.repository,
      page_size: 50,
    });
    snapshots.value = response.data.results || response.data;
  } catch (error) {
    console.error("Failed to fetch snapshots:", error);
  }
}

watch(() => newRecovery.value.repository, fetchSnapshots);

watch(
  () => newRecovery.value.snapshot_id,
  () => {
    recoverySnapshotFiles.value = [];
    recoverySnapshotFilesError.value = "";
    expandedRecoverySnapshotPaths.value = new Set();
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
  const query = snapshotSearchQuery.value.trim().toLowerCase();
  if (!query) return snapshots.value;
  return snapshots.value.filter((snap) => {
    const fields = [
      snap.id,
      snap.name,
      snap.source_path,
      snap.description,
      snap.snapshot_time,
    ];
    return fields.some((field) =>
      String(field || "").toLowerCase().includes(query),
    );
  });
});

const selectedTargetNode = computed(() =>
  nodes.value.find((node) => String(node.id) === String(newRecovery.value.node)),
);

const selectedRecoveryPaths = computed(
  () => new Set(newRecovery.value.selected_paths || []),
);

const selectedRecoveryFileStats = computed(() => {
  const paths = newRecovery.value.selected_paths || [];
  const selected = new Set(paths);
  let knownFiles = 0;
  let knownBytes = 0;
  for (const file of recoverySnapshotFiles.value) {
    if (
      selected.has(file.relative_path) ||
      Array.from(selected).some((path) => file.relative_path?.startsWith(`${path}/`))
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
    return Boolean(newRecovery.value.repository && newRecovery.value.snapshot_id);
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
  createStep.value = 0;
  showCreateModal.value = true;
}

function openEditRecovery(task: RecoveryTask) {
  const repositoryId = task.repository_id || "";
  const snapshotId = task.snapshot || task.snapshot_id || "";
  editingTaskId.value = task.id;
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
      message: getApiErrorMessage(error, t("recoveryTasks.messages.executeFailed")),
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
      message: getApiErrorMessage(error, t("recoveryTasks.messages.fetchRunsFailed")),
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
      expandedRecoverySnapshotPaths.value = new Set();
      loadingRecoverySnapshotPaths.value = new Set();
    } else {
      mergeRecoverySnapshotChildren(path, files);
      expandedRecoverySnapshotPaths.value = new Set([
        ...expandedRecoverySnapshotPaths.value,
        path,
      ]);
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

function visibleRecoverySnapshotFiles() {
  return recoverySnapshotFiles.value.filter((file) => {
    if (!file.parent_path) return true;
    const ancestors = file.parent_path.split("/").filter(Boolean);
    let current = "";
    for (const part of ancestors) {
      current = current ? `${current}/${part}` : part;
      if (!expandedRecoverySnapshotPaths.value.has(current)) return false;
    }
    return true;
  });
}

async function toggleRecoverySnapshotDirectory(file: any) {
  if (!file.is_dir) return;
  const path = file.relative_path;
  const next = new Set(expandedRecoverySnapshotPaths.value);
  if (next.has(path)) {
    next.delete(path);
    expandedRecoverySnapshotPaths.value = next;
    return;
  }
  if (!file.children_loaded) {
    await loadRecoverySnapshotFiles(path);
    return;
  }
  next.add(path);
  expandedRecoverySnapshotPaths.value = next;
}

function toggleRecoveryPathSelection(file: any) {
  const path = file.relative_path;
  const next = new Set(newRecovery.value.selected_paths || []);
  const currentlySelected = getRecoverySelectionState(file) === "checked";
  if (currentlySelected) {
    removeRecoveryPathAndDescendants(next, path);
  } else {
    removeRecoveryDescendants(next, path);
    next.add(path);
  }
  newRecovery.value.selected_paths = [...next];
}

function removeRecoveryPathAndDescendants(selected: Set<string>, path: string) {
  selected.delete(path);
  for (const item of [...selected]) {
    if (item.startsWith(`${path}/`)) selected.delete(item);
  }
  const ancestor = findSelectedAncestor(path, selected);
  if (ancestor) {
    selected.delete(ancestor);
    const descendants = recoverySnapshotFiles.value.filter((file) =>
      file.relative_path?.startsWith(`${ancestor}/`),
    );
    for (const file of descendants) {
      if (
        file.relative_path !== path &&
        !file.relative_path.startsWith(`${path}/`)
      ) {
        selected.add(file.relative_path);
      }
    }
  }
}

function removeRecoveryDescendants(selected: Set<string>, path: string) {
  for (const item of [...selected]) {
    if (item.startsWith(`${path}/`)) selected.delete(item);
  }
}

function findSelectedAncestor(path: string, selected: Set<string>) {
  const parts = path.split("/").filter(Boolean);
  while (parts.length > 1) {
    parts.pop();
    const ancestor = parts.join("/");
    if (selected.has(ancestor)) return ancestor;
  }
  return "";
}

function hasSelectedAncestor(path: string) {
  return Boolean(findSelectedAncestor(path, selectedRecoveryPaths.value));
}

function getRecoverySelectionState(file: any): "checked" | "partial" | "none" {
  const path = file.relative_path;
  const selected = selectedRecoveryPaths.value;
  if (selected.has(path) || hasSelectedAncestor(path)) return "checked";
  if (!file.is_dir) return "none";
  const descendants = recoverySnapshotFiles.value.filter((item) =>
    item.relative_path?.startsWith(`${path}/`),
  );
  if (
    descendants.some(
      (item) => selected.has(item.relative_path) || hasSelectedAncestor(item.relative_path),
    )
  ) {
    return "partial";
  }
  return "none";
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
      message: getApiErrorMessage(error, t("recoveryTasks.messages.pauseFailed")),
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
      <div>
        <h1 class="text-2xl font-bold text-foreground">
          {{ t("recoveryTasks.title") }}
        </h1>
        <p class="text-slate-500 mt-1">{{ t("recoveryTasks.subtitle") }}</p>
      </div>
      <button
        @click="openCreateRecovery"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-emerald-500 to-teal-600 rounded-lg hover:from-emerald-600 hover:to-teal-700 transition-all shadow-md hover:shadow-lg"
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
              <section
                v-if="createStep === 0"
                class="rounded-lg border border-border bg-background-secondary/40 p-4"
              >
                <div class="flex items-start gap-3 mb-4">
                  <FolderOpenIcon class="w-5 h-5 text-emerald-600 mt-0.5" />
                  <div>
                    <h3 class="text-sm font-semibold text-foreground">
                      {{ t("recoveryTasks.wizard.basic") }}
                    </h3>
                    <p class="text-xs text-foreground-secondary mt-1">
                      {{ t("recoveryTasks.wizard.basicHelp") }}
                    </p>
                  </div>
                </div>
                <div class="space-y-4">
                  <div>
                    <label class="block text-sm font-medium text-foreground-secondary mb-1">
                      {{ t("common.name") }}
                    </label>
                    <input
                      v-model="newRecovery.name"
                      type="text"
                      :placeholder="t('recoveryTasks.form.namePlaceholder')"
                      class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-foreground-secondary mb-1">
                      {{ t("common.description") }}
                    </label>
                    <textarea
                      v-model="newRecovery.description"
                      rows="4"
                      :placeholder="t('recoveryTasks.form.descriptionPlaceholder')"
                      class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                </div>
              </section>

              <section
                v-if="createStep === 1"
                class="rounded-lg border border-border bg-background-secondary/40 p-4"
              >
                <div class="flex items-start gap-3 mb-4">
                  <CircleStackIcon class="w-5 h-5 text-emerald-600 mt-0.5" />
                  <div>
                    <h3 class="text-sm font-semibold text-foreground">
                      {{ t("recoveryTasks.sections.source") }}
                    </h3>
                    <p class="text-xs text-foreground-secondary mt-1">
                      {{ t("recoveryTasks.sections.sourceHelp") }}
                    </p>
                  </div>
                </div>
                <div>
                  <label class="block text-sm font-medium text-foreground-secondary mb-1">
                    {{ t("recoveryTasks.form.repository") }}
                  </label>
                  <select
                    v-model="newRecovery.repository"
                    class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option class="bg-background" value="">
                      {{ t("common.select") || "Select" }}
                    </option>
                    <option
                      class="bg-background"
                      v-for="repo in repositories"
                      :key="repo.id"
                      :value="repo.id"
                    >
                      {{ repo.name }}
                    </option>
                  </select>
                </div>
                <div class="mt-4">
                  <div class="flex items-center justify-between gap-3 mb-2">
                    <label class="block text-sm font-medium text-foreground-secondary">
                      {{ t("recoveryTasks.form.snapshot") }}
                    </label>
                    <span class="text-xs text-foreground-secondary">
                      {{ filteredSnapshots.length }} / {{ snapshots.length }}
                    </span>
                  </div>
                  <div class="relative mb-3">
                    <MagnifyingGlassIcon
                      class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
                    />
                    <input
                      v-model="snapshotSearchQuery"
                      type="text"
                      :placeholder="t('recoveryTasks.form.snapshotSearchPlaceholder')"
                      class="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-lg bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>

                  <div
                    v-if="!newRecovery.repository"
                    class="rounded-lg border border-dashed border-border p-8 text-center"
                  >
                    <CircleStackIcon class="w-8 h-8 text-slate-400 mx-auto mb-3" />
                    <p class="text-sm font-medium text-foreground">
                      {{ t("recoveryTasks.empty.selectRepositoryTitle") }}
                    </p>
                    <p class="text-xs text-foreground-secondary mt-1">
                      {{ t("recoveryTasks.empty.selectRepositoryDescription") }}
                    </p>
                  </div>
                  <div
                    v-else-if="filteredSnapshots.length === 0"
                    class="rounded-lg border border-dashed border-border p-8 text-center"
                  >
                    <ClockIcon class="w-8 h-8 text-slate-400 mx-auto mb-3" />
                    <p class="text-sm font-medium text-foreground">
                      {{ t("recoveryTasks.empty.noSnapshotsTitle") }}
                    </p>
                    <p class="text-xs text-foreground-secondary mt-1">
                      {{ t("recoveryTasks.empty.noSnapshotsDescription") }}
                    </p>
                  </div>
                  <div
                    v-else
                    class="max-h-[360px] overflow-y-auto pr-1 space-y-2"
                  >
                    <button
                      v-for="snap in filteredSnapshots"
                      :key="snap.id"
                      type="button"
                      @click="newRecovery.snapshot_id = snap.id"
                      :class="[
                        'w-full text-left rounded-lg border p-4 transition-colors',
                        newRecovery.snapshot_id === snap.id
                          ? 'border-emerald-500 bg-emerald-50/70 dark:bg-emerald-950/20'
                          : 'border-border bg-card hover:bg-hover',
                      ]"
                    >
                      <div class="flex items-start justify-between gap-4">
                        <div class="min-w-0">
                          <div class="flex items-center gap-2">
                            <span
                              v-if="newRecovery.snapshot_id === snap.id"
                              class="w-2 h-2 rounded-full bg-emerald-500"
                            />
                            <p class="text-sm font-semibold text-foreground truncate">
                              {{ snap.name || snap.id }}
                            </p>
                          </div>
                          <p class="text-xs text-foreground-secondary mt-1 font-mono truncate">
                            {{ snap.source_path || snap.id }}
                          </p>
                        </div>
                        <div class="text-right shrink-0">
                          <p class="text-sm font-medium text-foreground">
                            {{ formatBytes(snap.total_size || snap.size_bytes || 0) }}
                          </p>
                          <p class="text-xs text-foreground-secondary mt-1">
                            {{ snap.file_count || snap.files_total || 0 }}
                            {{ t("recoveryTasks.progress.files") }}
                          </p>
                        </div>
                      </div>
                      <div class="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs text-foreground-secondary">
                        <span>{{ formatDateTime(snap.snapshot_time) }}</span>
                        <span class="truncate">{{ snap.description || "-" }}</span>
                        <span class="font-mono truncate">{{ snap.id }}</span>
                      </div>
                    </button>
                  </div>
                </div>
              </section>

              <section
                v-if="createStep === 2"
                class="rounded-lg border border-border bg-background-secondary/40 p-4"
              >
                <div class="flex items-start gap-3 mb-4">
                  <FolderOpenIcon class="w-5 h-5 text-emerald-600 mt-0.5" />
                  <div>
                    <h3 class="text-sm font-semibold text-foreground">
                      {{ t("recoveryTasks.scope.title") }}
                    </h3>
                    <p class="text-xs text-foreground-secondary mt-1">
                      {{ t("recoveryTasks.wizard.scopeHelp") }}
                    </p>
                  </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <label class="flex items-start gap-3 rounded-lg border border-emerald-500/40 bg-emerald-50/60 dark:bg-emerald-950/20 p-3">
                    <input
                      v-model="newRecovery.restore_scope"
                      type="radio"
                      value="entire_snapshot"
                      class="mt-1 text-emerald-600"
                    />
                    <span>
                      <span class="block text-sm font-medium text-foreground">
                        {{ t("recoveryTasks.scope.entire") }}
                      </span>
                      <span class="block text-xs text-foreground-secondary mt-1">
                        {{ t("recoveryTasks.scope.entireHelp") }}
                      </span>
                    </span>
                  </label>
                  <label
                    :class="[
                      'flex items-start gap-3 rounded-lg border p-3 cursor-pointer',
                      newRecovery.restore_scope === 'selected_paths'
                        ? 'border-emerald-500 bg-emerald-50/60 dark:bg-emerald-950/20'
                        : 'border-border bg-card hover:bg-hover',
                    ]"
                  >
                    <input
                      v-model="newRecovery.restore_scope"
                      type="radio"
                      value="selected_paths"
                      class="mt-1 text-emerald-600"
                    />
                    <span>
                      <span class="block text-sm font-medium text-foreground">
                        {{ t("recoveryTasks.scope.selected") }}
                      </span>
                      <span class="block text-xs text-foreground-secondary mt-1">
                        {{ t("recoveryTasks.scope.selectedHelp") }}
                      </span>
                    </span>
                  </label>
                </div>
                <div
                  v-if="newRecovery.restore_scope === 'selected_paths'"
                  class="mt-5 rounded-lg border border-border bg-card overflow-hidden"
                >
                  <div class="px-4 py-3 border-b border-border flex items-center justify-between gap-3">
                    <div>
                      <h4 class="text-sm font-semibold text-foreground">
                        {{ t("recoveryTasks.scope.fileTreeTitle") }}
                      </h4>
                      <p class="text-xs text-foreground-secondary mt-1">
                        {{ t("recoveryTasks.scope.fileTreeHelp") }}
                      </p>
                    </div>
                    <button
                      type="button"
                      @click="loadRecoverySnapshotFiles()"
                      class="inline-flex items-center gap-2 px-3 py-2 text-sm border border-border rounded-lg hover:bg-hover"
                    >
                      <ArrowPathIcon
                        :class="[
                          'w-4 h-4',
                          recoverySnapshotFilesLoading ? 'animate-spin' : '',
                        ]"
                      />
                      {{ t("common.refresh") }}
                    </button>
                  </div>
                  <div class="px-4 py-2 border-b border-border bg-background-secondary/40 flex items-center justify-between text-xs text-foreground-secondary">
                    <span>
                      {{ (newRecovery.selected_paths || []).length }}
                      {{ t("recoveryTasks.scope.selectedCount") }}
                    </span>
                    <button
                      v-if="(newRecovery.selected_paths || []).length"
                      type="button"
                      class="text-emerald-600 hover:text-emerald-700"
                      @click="newRecovery.selected_paths = []"
                    >
                      {{ t("common.clear") || "Clear" }}
                    </button>
                  </div>
                  <div
                    v-if="recoverySnapshotFilesLoading"
                    class="p-8 flex justify-center"
                  >
                    <div class="w-7 h-7 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin" />
                  </div>
                  <div
                    v-else-if="recoverySnapshotFilesError"
                    class="p-6 text-center"
                  >
                    <ExclamationTriangleIcon class="w-8 h-8 text-red-500 mx-auto mb-3" />
                    <p class="text-sm font-medium text-foreground">
                      {{ t("recoveryTasks.messages.snapshotFilesLoadFailed") }}
                    </p>
                    <p class="text-xs text-foreground-secondary mt-1">
                      {{ recoverySnapshotFilesError }}
                    </p>
                  </div>
                  <div
                    v-else-if="recoverySnapshotFiles.length === 0"
                    class="p-8 text-center"
                  >
                    <FolderIcon class="w-8 h-8 text-slate-400 mx-auto mb-3" />
                    <p class="text-sm font-medium text-foreground">
                      {{ t("recoveryTasks.scope.noFilesTitle") }}
                    </p>
                    <p class="text-xs text-foreground-secondary mt-1">
                      {{ t("recoveryTasks.scope.noFilesDescription") }}
                    </p>
                    <button
                      type="button"
                      @click="loadRecoverySnapshotFiles()"
                      class="mt-4 inline-flex items-center gap-2 px-3 py-2 text-sm border border-border rounded-lg hover:bg-hover"
                    >
                      <ArrowPathIcon class="w-4 h-4" />
                      {{ t("recoveryTasks.scope.loadFiles") }}
                    </button>
                  </div>
                  <div v-else class="max-h-[360px] overflow-y-auto py-1">
                    <div
                      v-for="file in visibleRecoverySnapshotFiles()"
                      :key="file.relative_path || file.id"
                      class="grid grid-cols-[minmax(0,1fr)_120px] gap-4 px-4 py-1.5 hover:bg-hover"
                    >
                      <div
                        class="flex items-center gap-1.5 min-w-0"
                        :style="{ paddingLeft: `${(file.depth || 0) * 20}px` }"
                      >
                        <button
                          type="button"
                          class="w-5 h-5 inline-flex items-center justify-center rounded hover:bg-background-tertiary shrink-0"
                          :class="file.is_dir ? 'visible' : 'invisible'"
                          @click="toggleRecoverySnapshotDirectory(file)"
                        >
                          <ChevronDownIcon
                            v-if="
                              file.is_dir &&
                              expandedRecoverySnapshotPaths.has(file.relative_path)
                            "
                            class="w-4 h-4 text-foreground-secondary"
                          />
                          <ChevronRightIcon
                            v-else
                            class="w-4 h-4 text-foreground-secondary"
                          />
                        </button>
                        <ArrowPathIcon
                          v-if="loadingRecoverySnapshotPaths.has(file.relative_path)"
                          class="w-4 h-4 animate-spin text-emerald-600 shrink-0"
                        />
                        <input
                          type="checkbox"
                          v-indeterminate="getRecoverySelectionState(file) === 'partial'"
                          class="h-4 w-4 rounded border-border text-emerald-600 focus:ring-emerald-500 shrink-0"
                          :checked="getRecoverySelectionState(file) === 'checked'"
                          @change="toggleRecoveryPathSelection(file)"
                        />
                        <FolderIcon
                          v-if="file.is_dir"
                          class="w-4 h-4 text-amber-500 shrink-0"
                        />
                        <DocumentIcon
                          v-else
                          class="w-4 h-4 text-foreground-secondary shrink-0"
                        />
                        <button
                          type="button"
                          class="text-left text-sm text-foreground truncate hover:text-emerald-600"
                          @click="
                            file.is_dir
                              ? toggleRecoverySnapshotDirectory(file)
                              : undefined
                          "
                        >
                          {{ file.file_name || file.relative_path }}
                        </button>
                      </div>
                      <span class="text-sm text-foreground-secondary text-right tabular-nums">
                        {{ file.is_dir ? "-" : formatBytes(file.size || 0) }}
                      </span>
                    </div>
                  </div>
                </div>
              </section>

              <section
                v-if="createStep === 3"
                class="rounded-lg border border-border bg-background-secondary/40 p-4"
              >
                <div class="flex items-start gap-3 mb-4">
                  <ServerIcon class="w-5 h-5 text-emerald-600 mt-0.5" />
                  <div>
                    <h3 class="text-sm font-semibold text-foreground">
                      {{ t("recoveryTasks.sections.target") }}
                    </h3>
                    <p class="text-xs text-foreground-secondary mt-1">
                      {{ t("recoveryTasks.sections.targetHelp") }}
                    </p>
                  </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-medium text-foreground-secondary mb-1">
                      {{ t("recoveryTasks.form.targetNode") }}
                    </label>
                    <select
                      v-model="newRecovery.node"
                      class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option class="bg-background" value="">
                        {{ t("common.select") || "Select" }}
                      </option>
                      <option
                        class="bg-background"
                        v-for="node in nodes"
                        :key="node.id"
                        :value="node.id"
                      >
                        {{ node.name }} · {{ node.status }}
                      </option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-foreground-secondary mb-1">
                      {{ t("recoveryTasks.form.type") }}
                    </label>
                    <select
                      v-model="newRecovery.recovery_type"
                      class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option class="bg-background" value="new_location">
                        {{ t("recoveryTasks.types.new_location") }}
                      </option>
                      <option class="bg-background" value="original">
                        {{ t("recoveryTasks.types.original") }}
                      </option>
                    </select>
                  </div>
                </div>
                <div class="mt-4">
                  <label class="block text-sm font-medium text-foreground-secondary mb-1">
                    {{ t("recoveryTasks.form.targetPath") }}
                  </label>
                  <input
                    v-model="newRecovery.target_path"
                    type="text"
                    :placeholder="t('recoveryTasks.form.targetPathPlaceholder')"
                    class="w-full px-3 py-2 font-mono text-sm border border-border rounded-lg bg-background text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <p class="text-xs text-foreground-secondary mt-1">
                    {{ t("recoveryTasks.form.targetPathHelp") }}
                  </p>
                </div>
              </section>

              <section
                v-if="createStep === 4"
                class="rounded-lg border border-border bg-background-secondary/40 p-4"
              >
                <div class="flex items-start gap-3 mb-4">
                  <ShieldCheckIcon class="w-5 h-5 text-emerald-600 mt-0.5" />
                  <div>
                    <h3 class="text-sm font-semibold text-foreground">
                      {{ t("recoveryTasks.sections.options") }}
                    </h3>
                    <p class="text-xs text-foreground-secondary mt-1">
                      {{ t("recoveryTasks.sections.optionsHelp") }}
                    </p>
                  </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-medium text-foreground-secondary mb-1">
                      {{ t("recoveryTasks.form.conflictPolicy") }}
                    </label>
                    <select
                      v-model="newRecovery.conflict_policy"
                      class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option class="bg-background" value="skip">
                        {{ t("recoveryTasks.conflict.skip") }}
                      </option>
                      <option class="bg-background" value="overwrite">
                        {{ t("recoveryTasks.conflict.overwrite") }}
                      </option>
                    </select>
                    <p class="text-xs text-foreground-secondary mt-1">
                      {{ t("recoveryTasks.form.conflictHelp") }}
                    </p>
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-foreground-secondary mb-1">
                      {{ t("recoveryTasks.form.priority") }}
                    </label>
                    <select
                      v-model="newRecovery.priority"
                      class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option class="bg-background" value="low">Low</option>
                      <option class="bg-background" value="normal">Normal</option>
                      <option class="bg-background" value="high">High</option>
                      <option class="bg-background" value="critical">Critical</option>
                    </select>
                  </div>
                </div>
                <div class="mt-5 rounded-lg border border-border bg-card p-4">
                  <h4 class="text-sm font-semibold text-foreground mb-3">
                    {{ t("recoveryTasks.review.title") }}
                  </h4>
                  <dl class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <dt class="text-xs text-foreground-secondary">
                        {{ t("common.name") }}
                      </dt>
                      <dd class="font-medium text-foreground mt-1">
                        {{ newRecovery.name || "-" }}
                      </dd>
                    </div>
                    <div>
                      <dt class="text-xs text-foreground-secondary">
                        {{ t("recoveryTasks.form.snapshot") }}
                      </dt>
                      <dd class="font-medium text-foreground mt-1 break-all">
                        {{ selectedSnapshot?.name || selectedSnapshot?.id || "-" }}
                      </dd>
                    </div>
                    <div>
                      <dt class="text-xs text-foreground-secondary">
                        {{ t("recoveryTasks.form.targetNode") }}
                      </dt>
                      <dd class="font-medium text-foreground mt-1">
                        {{ selectedTargetNode?.name || "-" }}
                      </dd>
                    </div>
                    <div>
                      <dt class="text-xs text-foreground-secondary">
                        {{ t("recoveryTasks.form.targetPath") }}
                      </dt>
                      <dd class="font-mono text-xs text-foreground mt-1 break-all">
                        {{ newRecovery.target_path || "-" }}
                      </dd>
                    </div>
                  </dl>
                </div>
              </section>
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
