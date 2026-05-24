<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  StopIcon,
  XCircleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from "@heroicons/vue/24/outline";
import { taskManagementApi } from "@/api";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";

const { t } = useI18n();
const route = useRoute();
const { getPageSize, setPageSize } = usePagination();

interface ManagedTask {
  id: string;
  source: "proxy" | "backup" | "recovery";
  name: string;
  task_type: string;
  status: string;
  progress: number;
  message: string;
  proxy_name?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  parameters?: Record<string, unknown>;
  result?: Record<string, unknown>;
  error_message?: string;
}

interface TaskStep {
  step?: string;
  status?: string;
  message?: string;
}

const tasks = ref<ManagedTask[]>([]);
const stats = ref({
  total: 0,
  running: 0,
  completed: 0,
  failed: 0,
  cancelled: 0,
});
const loading = ref(false);
const cancellingTaskId = ref<string | null>(null);
const openingTaskId = ref<string | null>(null);
const selectedTask = ref<ManagedTask | null>(null);
const search = ref("");
const statusFilter = ref("");
const sourceFilter = ref("");

// Pagination
const pagination = ref({ page: 1, count: 0 });
const pageSize = ref(getPageSize("event-log"));
const PAGE_STORAGE_KEY = "event-log";

watch(pageSize, (newSize) => {
  setPageSize(newSize, PAGE_STORAGE_KEY);
});

const totalPages = computed(() =>
  Math.ceil(pagination.value.count / pageSize.value),
);

const startItem = computed(
  () => (pagination.value.page - 1) * pageSize.value + 1,
);
const endItem = computed(() =>
  Math.min(pagination.value.page * pageSize.value, pagination.value.count),
);

const visiblePages = computed(() => {
  const current = pagination.value.page;
  const total = totalPages.value;
  const pages: (number | string)[] = [];

  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i);
  } else {
    pages.push(1);
    if (current > 3) pages.push("...");
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    if (current < total - 2) pages.push("...");
    pages.push(total);
  }

  return pages;
});

const statCards = computed(() => [
  {
    label: t("taskManagement.stats.total"),
    value: stats.value.total,
    className: "text-foreground",
    icon: CheckCircleIcon,
  },
  {
    label: t("taskManagement.stats.running"),
    value: stats.value.running,
    className: "text-blue-600",
    icon: ArrowPathIcon,
  },
  {
    label: t("taskManagement.stats.completed"),
    value: stats.value.completed,
    className: "text-emerald-600",
    icon: CheckCircleIcon,
  },
  {
    label: t("taskManagement.stats.failed"),
    value: stats.value.failed,
    className: "text-red-600",
    icon: XCircleIcon,
  },
  {
    label: t("taskManagement.stats.cancelled"),
    value: stats.value.cancelled,
    className: "text-foreground-secondary",
    icon: ClockIcon,
  },
]);

const resultSteps = computed<TaskStep[]>(() => {
  const steps = selectedTask.value?.result?.steps;
  return Array.isArray(steps) ? (steps as TaskStep[]) : [];
});

type TaskColumnKey =
  | "name"
  | "source"
  | "status"
  | "progress"
  | "proxy_name"
  | "created_at"
  | "actions";

const taskColumns = computed(() => [
  { key: "name" as const, label: t("taskManagement.task"), min: 300, max: 720 },
  {
    key: "source" as const,
    label: t("taskManagement.sourceTitle"),
    min: 130,
    max: 260,
  },
  {
    key: "status" as const,
    label: t("taskManagement.statusTitle"),
    min: 140,
    max: 260,
  },
  {
    key: "progress" as const,
    label: t("taskManagement.progress"),
    min: 170,
    max: 320,
  },
  {
    key: "proxy_name" as const,
    label: t("taskManagement.node"),
    min: 170,
    max: 360,
  },
  {
    key: "created_at" as const,
    label: t("taskManagement.time"),
    min: 190,
    max: 320,
  },
  {
    key: "actions" as const,
    label: t("common.actions"),
    min: 110,
    max: 160,
  },
]);

const taskTable = useResizableSortableTable<ManagedTask, TaskColumnKey>({
  storageKey: "hyperfilelens:task-management:columnWidths",
  columns: taskColumns,
  rows: tasks,
  defaultSort: { key: "created_at", direction: "desc" },
  minTableWidth: 900,
  getSortValue: (task, key) => {
    if (key === "created_at")
      return task.created_at ? new Date(task.created_at).getTime() : 0;
    if (key === "progress") return task.progress || 0;
    if (key === "actions") return "";
    return task[key] ?? "";
  },
  getColumnText: (task, key) => {
    if (key === "source") return sourceLabel(task.source);
    if (key === "status") return t(`taskManagement.status.${task.status}`);
    if (key === "progress") return `${task.progress || 0}%`;
    if (key === "created_at") return formatDate(task.created_at);
    if (key === "actions") return "";
    return String(task[key] ?? "");
  },
});

async function fetchTasks() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {
      page: pagination.value.page,
      page_size: pageSize.value,
      search: search.value || undefined,
      status: statusFilter.value || undefined,
      source: sourceFilter.value || undefined,
    };
    const [listRes, statsRes] = await Promise.all([
      taskManagementApi.list(params),
      taskManagementApi.stats(),
    ]);
    tasks.value = listRes.data.results || listRes.data;
    pagination.value.count = listRes.data.count || tasks.value.length;
    stats.value = statsRes.data;
    await openTaskFromRoute();
  } finally {
    loading.value = false;
  }
}

async function openTaskFromRoute() {
  const taskId = typeof route.query.task === "string" ? route.query.task : "";
  if (!taskId || openingTaskId.value === taskId) return;

  const visibleTask = tasks.value.find((task) => task.id === taskId);
  if (visibleTask) {
    selectedTask.value = visibleTask;
    return;
  }

  openingTaskId.value = taskId;
  try {
    const response = await taskManagementApi.detail(taskId);
    selectedTask.value = response.data;
  } catch (error) {
    console.error("Failed to open task from route:", error);
  } finally {
    openingTaskId.value = null;
  }
}

function refetchFromFirstPage() {
  pagination.value.page = 1;
  fetchTasks();
}

function changePage(page: number) {
  pagination.value.page = page;
  fetchTasks();
}

function handlePageSizeChange() {
  pagination.value.page = 1;
  fetchTasks();
}

function isCancellable(task: ManagedTask) {
  return ["pending", "dispatched", "accepted", "running"].includes(task.status);
}

async function cancelTask(task: ManagedTask) {
  if (!isCancellable(task)) return;
  if (!window.confirm(t("taskManagement.confirmCancel"))) return;

  cancellingTaskId.value = task.id;
  try {
    await taskManagementApi.cancelTask(task.id, {
      reason: t("taskManagement.cancelReason"),
    });
    if (selectedTask.value?.id === task.id) {
      selectedTask.value = null;
    }
    await fetchTasks();
  } finally {
    cancellingTaskId.value = null;
  }
}

function statusClass(status: string) {
  if (["completed", "success"].includes(status))
    return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400";
  if (["failed", "error"].includes(status))
    return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
  if (["running", "accepted", "dispatched"].includes(status))
    return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
  if (status === "cancelled")
    return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300";
  return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
}

function statusIcon(status: string) {
  if (status === "completed") return CheckCircleIcon;
  if (status === "failed") return XCircleIcon;
  if (status === "running") return ArrowPathIcon;
  if (status === "cancelled") return ClockIcon;
  return InformationCircleIcon;
}

function sourceLabel(source: string) {
  const labels: Record<string, string> = {
    backup: t("taskManagement.source.backup"),
    recovery: t("taskManagement.source.recovery"),
    proxy: t("taskManagement.source.proxy"),
  };
  return labels[source] || source;
}

function sourceClass(source: string) {
  if (source === "backup")
    return "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400";
  if (source === "recovery")
    return "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400";
  return "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300";
}

function formatDate(value?: string) {
  return value ? new Date(value).toLocaleString() : "-";
}

function formatDuration(seconds?: number) {
  if (!seconds) return "-";
  const minutes = Math.floor(seconds / 60);
  const rest = Math.floor(seconds % 60);
  return minutes > 0 ? `${minutes}m ${rest}s` : `${rest}s`;
}

watch(
  () => route.query.task,
  () => {
    openTaskFromRoute();
  },
);

onMounted(fetchTasks);
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div
      class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"
    >
      <div>
        <h1 class="text-2xl font-semibold text-foreground">
          {{ t("taskManagement.title") }}
        </h1>
        <p class="mt-1 text-sm text-foreground-secondary">
          {{ t("taskManagement.subtitle") }}
        </p>
      </div>
      <button
        @click="fetchTasks"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-foreground bg-card border border-border rounded-lg hover:border-indigo-500 transition-colors"
      >
        <ArrowPathIcon :class="['w-4 h-4', loading && 'animate-spin']" />
        {{ t("common.refresh") }}
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-5 gap-4">
      <div
        v-for="card in statCards"
        :key="card.label"
        class="bg-card border border-border rounded-xl p-4"
      >
        <div class="flex items-center gap-3">
          <div
            class="w-10 h-10 rounded-lg bg-background-secondary flex items-center justify-center"
          >
            <component
              :is="card.icon"
              class="w-5 h-5"
              :class="card.className"
            />
          </div>
          <div>
            <p class="text-xs text-foreground-secondary">{{ card.label }}</p>
            <p :class="['mt-1 text-2xl font-semibold', card.className]">
              {{ card.value }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Task List -->
    <div class="bg-card border border-border rounded-xl overflow-hidden">
      <!-- Filters -->
      <div
        class="p-4 border-b border-border flex flex-wrap items-center justify-between gap-3"
      >
        <div class="flex flex-wrap items-center gap-2 flex-1">
          <input
            v-model="search"
            @keyup.enter="refetchFromFirstPage"
            :placeholder="t('taskManagement.searchPlaceholder')"
            class="flex-1 min-w-[200px] px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <select
            v-model="statusFilter"
            @change="refetchFromFirstPage"
            class="px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground"
          >
            <option value="">{{ t("taskManagement.allStatus") }}</option>
            <option value="pending">
              {{ t("taskManagement.status.pending") }}
            </option>
            <option value="running">
              {{ t("taskManagement.status.running") }}
            </option>
            <option value="completed">
              {{ t("taskManagement.status.completed") }}
            </option>
            <option value="failed">
              {{ t("taskManagement.status.failed") }}
            </option>
            <option value="cancelled">
              {{ t("taskManagement.status.cancelled") }}
            </option>
          </select>
          <select
            v-model="sourceFilter"
            @change="refetchFromFirstPage"
            class="px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground"
          >
            <option value="">{{ t("taskManagement.allSource") }}</option>
            <option value="backup">
              {{ t("taskManagement.source.backup") }}
            </option>
            <option value="recovery">
              {{ t("taskManagement.source.recovery") }}
            </option>
            <option value="proxy">
              {{ t("taskManagement.source.proxy") }}
            </option>
          </select>
        </div>
      </div>

      <!-- Table -->
      <div class="overflow-x-auto">
        <table
          class="w-full table-fixed divide-y divide-border"
          :style="{ minWidth: taskTable.tableMinWidth.value }"
        >
          <colgroup>
            <col
              v-for="column in taskColumns"
              :key="column.key"
              :style="taskTable.columnStyle(column.key)"
            />
          </colgroup>
          <thead class="bg-background-secondary">
            <tr>
              <ResizableSortableTh
                v-for="column in taskColumns"
                :key="column.key"
                :column-key="column.key"
                :label="column.label"
                :style-value="taskTable.columnStyle(column.key)"
                :active="taskTable.sort.value.key === column.key"
                :sort-icon="taskTable.getSortIcon(column.key)"
                :resizing="taskTable.resizingColumn.value === column.key"
                @sort="taskTable.toggleSort($event as TaskColumnKey)"
                @resize-start="
                  (key, event) =>
                    taskTable.startResize(key as TaskColumnKey, event)
                "
                @resize-reset="
                  taskTable.resetColumnWidth($event as TaskColumnKey)
                "
              />
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr v-if="loading">
              <td
                colspan="7"
                class="px-4 py-10 text-center text-foreground-secondary"
              >
                {{ t("common.loading") }}
              </td>
            </tr>
            <tr
              v-for="task in taskTable.sortedRows.value"
              :key="`${task.source}-${task.id}`"
              :class="[
                'hover:bg-hover cursor-pointer transition-colors',
                selectedTask?.id === task.id && 'bg-primary/5',
              ]"
              @click="selectedTask = task"
            >
              <td class="px-4 py-3" :style="taskTable.columnStyle('name')">
                <p class="font-medium text-sm">{{ task.name }}</p>
                <p class="text-xs text-foreground-muted">
                  {{ task.task_type }} ·
                  {{ task.message || task.error_message || "-" }}
                </p>
              </td>
              <td class="px-4 py-3" :style="taskTable.columnStyle('source')">
                <span
                  :class="[
                    'px-2 py-1 text-xs rounded-full',
                    sourceClass(task.source),
                  ]"
                  >{{ sourceLabel(task.source) }}</span
                >
              </td>
              <td class="px-4 py-3" :style="taskTable.columnStyle('status')">
                <span
                  :class="[
                    'inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full',
                    statusClass(task.status),
                  ]"
                >
                  <component :is="statusIcon(task.status)" class="w-3 h-3" />
                  {{ t(`taskManagement.status.${task.status}`) }}
                </span>
              </td>
              <td
                class="px-4 py-3 min-w-36"
                :style="taskTable.columnStyle('progress')"
              >
                <div class="flex items-center gap-2">
                  <div
                    class="h-2 flex-1 rounded-full bg-background-tertiary overflow-hidden"
                  >
                    <div
                      class="h-full bg-primary"
                      :style="{ width: `${task.progress || 0}%` }"
                    />
                  </div>
                  <span class="text-xs text-foreground-secondary"
                    >{{ task.progress || 0 }}%</span
                  >
                </div>
              </td>
              <td
                class="px-4 py-3 text-sm text-foreground-secondary"
                :style="taskTable.columnStyle('proxy_name')"
              >
                {{ task.proxy_name || "-" }}
              </td>
              <td
                class="px-4 py-3 text-sm text-foreground-secondary"
                :style="taskTable.columnStyle('created_at')"
              >
                {{ formatDate(task.created_at) }}
              </td>
              <td
                class="px-4 py-3 text-right"
                :style="taskTable.columnStyle('actions')"
              >
                <button
                  v-if="isCancellable(task)"
                  type="button"
                  @click.stop="cancelTask(task)"
                  :disabled="cancellingTaskId === task.id"
                  class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-foreground-muted hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 disabled:opacity-50 disabled:cursor-not-allowed"
                  :title="t('taskManagement.cancel')"
                  :aria-label="t('taskManagement.cancel')"
                >
                  <ArrowPathIcon
                    v-if="cancellingTaskId === task.id"
                    class="w-4 h-4 animate-spin"
                  />
                  <StopIcon v-else class="w-4 h-4" />
                </button>
                <span v-else class="text-xs text-foreground-muted">-</span>
              </td>
            </tr>
            <tr v-if="!loading && tasks.length === 0">
              <td
                colspan="7"
                class="px-4 py-10 text-center text-foreground-secondary"
              >
                {{ t("common.noData") }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div
        v-if="pagination.count > 0"
        class="p-4 border-t border-border flex flex-wrap items-center justify-between gap-4"
      >
        <div class="flex items-center gap-2">
          <span class="text-sm text-foreground-secondary">{{
            t("common.rowsPerPage")
          }}</span>
          <select
            v-model="pageSize"
            @change="handlePageSizeChange"
            class="px-2 py-1 text-sm rounded border border-border bg-background text-foreground"
          >
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </div>
        <div class="flex items-center gap-4">
          <span class="text-sm text-foreground-secondary">
            {{ t("common.showing") }} {{ startItem }}-{{ endItem }}
            {{ t("common.of") }} {{ pagination.count }}
          </span>
          <nav class="flex items-center gap-1">
            <button
              :disabled="pagination.page <= 1"
              @click="changePage(pagination.page - 1)"
              class="h-8 w-8 flex items-center justify-center rounded border border-border bg-background text-foreground-secondary hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeftIcon class="w-4 h-4" />
            </button>
            <template v-for="page in visiblePages" :key="page">
              <button
                v-if="page === '...'"
                class="h-8 w-8 flex items-center justify-center text-slate-400"
              >
                ...
              </button>
              <button
                v-else
                @click="changePage(page as number)"
                :class="[
                  'h-8 w-8 flex items-center justify-center rounded text-sm font-medium',
                  page === pagination.page
                    ? 'bg-indigo-600 text-white'
                    : 'border border-border bg-background text-foreground-secondary hover:bg-hover',
                ]"
              >
                {{ page }}
              </button>
            </template>
            <button
              :disabled="pagination.page >= totalPages"
              @click="changePage(pagination.page + 1)"
              class="h-8 w-8 flex items-center justify-center rounded border border-border bg-background text-foreground-secondary hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRightIcon class="w-4 h-4" />
            </button>
          </nav>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="selectedTask" class="fixed inset-0 z-50 flex justify-end">
        <div
          class="absolute inset-0 bg-black/50"
          @click="selectedTask = null"
        />
        <aside
          class="relative drawer-panel w-full max-w-[60%] h-full overflow-y-auto border-l border-border p-6"
        >
          <div class="flex items-start justify-between gap-4">
            <div>
              <h2 class="text-lg font-semibold text-foreground">
                {{ selectedTask.name }}
              </h2>
              <p class="text-sm text-foreground-secondary">
                {{ selectedTask.source }} · {{ selectedTask.task_type }}
              </p>
            </div>
            <button
              @click="selectedTask = null"
              class="p-2 rounded-lg hover:bg-background-tertiary text-foreground-muted"
            >
              ×
            </button>
          </div>
          <div v-if="isCancellable(selectedTask)" class="mt-4 flex justify-end">
            <button
              type="button"
              @click="cancelTask(selectedTask)"
              :disabled="cancellingTaskId === selectedTask.id"
              class="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300 dark:hover:bg-red-900/30 disabled:opacity-50"
            >
              <ArrowPathIcon
                v-if="cancellingTaskId === selectedTask.id"
                class="w-4 h-4 animate-spin"
              />
              <StopIcon v-else class="w-4 h-4" />
              {{ t("taskManagement.cancel") }}
            </button>
          </div>

          <div class="mt-6 grid grid-cols-2 gap-3">
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-xs text-foreground-secondary">状态</p>
              <p class="mt-1 font-medium text-foreground">
                {{ selectedTask.status }}
              </p>
            </div>
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-xs text-foreground-secondary">耗时</p>
              <p class="mt-1 font-medium text-foreground">
                {{ formatDuration(selectedTask.duration_seconds) }}
              </p>
            </div>
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-xs text-foreground-secondary">开始</p>
              <p class="mt-1 text-sm text-foreground">
                {{ formatDate(selectedTask.started_at) }}
              </p>
            </div>
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-xs text-foreground-secondary">完成</p>
              <p class="mt-1 text-sm text-foreground">
                {{ formatDate(selectedTask.completed_at) }}
              </p>
            </div>
          </div>

          <div
            v-if="selectedTask.error_message"
            class="mt-4 flex gap-2 rounded-lg border border-red-300 bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-700 dark:text-red-300"
          >
            <ExclamationCircleIcon class="w-5 h-5 flex-shrink-0" />
            {{ selectedTask.error_message }}
          </div>

          <div class="mt-6 space-y-4">
            <div>
              <h3 class="text-sm font-medium text-foreground mb-2">参数</h3>
              <pre
                class="bg-background-secondary border border-border rounded-lg p-3 text-xs text-foreground overflow-auto"
                >{{
                  JSON.stringify(selectedTask.parameters || {}, null, 2)
                }}</pre
              >
            </div>
            <div>
              <h3 class="text-sm font-medium text-foreground mb-2">结果</h3>
              <pre
                class="bg-background-secondary border border-border rounded-lg p-3 text-xs text-foreground overflow-auto"
                >{{ JSON.stringify(selectedTask.result || {}, null, 2) }}</pre
              >
            </div>
            <div v-if="resultSteps.length > 0">
              <h3 class="text-sm font-medium text-foreground mb-2">执行步骤</h3>
              <div class="space-y-2">
                <div
                  v-for="(step, index) in resultSteps"
                  :key="index"
                  class="flex gap-3 rounded-lg bg-background-secondary p-3"
                >
                  <InformationCircleIcon
                    class="w-4 h-4 text-foreground-muted mt-0.5"
                  />
                  <div>
                    <p class="text-sm text-foreground">
                      {{ step.step }} · {{ step.status }}
                    </p>
                    <p class="text-xs text-foreground-secondary">
                      {{ step.message }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </Teleport>
  </div>
</template>
