<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EnvelopeIcon,
  ListBulletIcon,
  MagnifyingGlassIcon,
  XCircleIcon,
} from "@heroicons/vue/24/outline";
import { alertsApi } from "@/api";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";
import AlertSeverityTag from "@/components/alerts/AlertSeverityTag.vue";
import AlertStatusTag from "@/components/alerts/AlertStatusTag.vue";
import AlertTypeTag from "@/components/alerts/AlertTypeTag.vue";

const { t } = useI18n();
const { getPageSize, setPageSize } = usePagination();

const logs = ref<any[]>([]);
const channels = ref<any[]>([]);
const stats = ref<any>({ total: 0, success: 0, failed: 0, success_rate: 0 });
const selected = ref<any | null>(null);
const loading = ref(false);
const filters = reactive({
  search: "",
  channel_id: "",
  notification_type: "",
  status: "",
  type: "",
  severity: "",
});
const pagination = reactive({
  page: 1,
  page_size: getPageSize("notification-logs"),
  count: 0,
});
const PAGE_STORAGE_KEY = "notification-logs";

watch(
  () => pagination.page_size,
  (newSize) => setPageSize(newSize, PAGE_STORAGE_KEY),
);

const totalPages = computed(() =>
  Math.ceil(pagination.count / pagination.page_size),
);
const startItem = computed(() =>
  pagination.count === 0 ? 0 : (pagination.page - 1) * pagination.page_size + 1,
);
const endItem = computed(() =>
  Math.min(pagination.page * pagination.page_size, pagination.count),
);
const visiblePages = computed(() => {
  const current = pagination.page;
  const total = totalPages.value;
  const pages: (number | string)[] = [];
  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i);
  } else {
    pages.push(1);
    if (current > 3) pages.push("...");
    for (
      let i = Math.max(2, current - 1);
      i <= Math.min(total - 1, current + 1);
      i++
    )
      pages.push(i);
    if (current < total - 2) pages.push("...");
    pages.push(total);
  }
  return pages;
});

type NotificationLogColumnKey =
  | "alert"
  | "channel"
  | "policy"
  | "resource"
  | "notification_type"
  | "status"
  | "sent_at"
  | "error_message";

const columns = computed(() => [
  {
    key: "alert" as const,
    label: t("alertsCenter.logs.alert"),
    min: 280,
    max: 620,
  },
  {
    key: "channel" as const,
    label: t("alertsCenter.logs.channel"),
    min: 190,
    max: 360,
  },
  {
    key: "policy" as const,
    label: t("alertsCenter.logs.policy"),
    min: 190,
    max: 420,
  },
  {
    key: "resource" as const,
    label: t("alertsCenter.common.resource"),
    min: 180,
    max: 360,
  },
  {
    key: "notification_type" as const,
    label: t("alertsCenter.logs.notificationType"),
    min: 140,
    max: 240,
  },
  {
    key: "status" as const,
    label: t("alertsCenter.logs.deliveryStatus"),
    min: 120,
    max: 220,
  },
  {
    key: "sent_at" as const,
    label: t("alertsCenter.logs.sentAt"),
    min: 190,
    max: 320,
  },
  {
    key: "error_message" as const,
    label: t("alertsCenter.logs.result"),
    min: 240,
    max: 620,
  },
]);

const table = useResizableSortableTable<any, NotificationLogColumnKey>({
  storageKey: "hyperfilelens:notification-logs:columnWidths",
  columns,
  rows: logs,
  defaultSort: { key: "sent_at", direction: "desc" },
  minTableWidth: 1400,
  getSortValue: (log, key) => {
    if (key === "channel") return log.channel?.name || "";
    if (key === "alert") return log.alert?.title || "";
    if (key === "policy") return log.policy?.name || "";
    if (key === "resource") return log.alert?.resource_name || "";
    if (key === "notification_type") return log.notification_type || "";
    if (key === "sent_at")
      return log.sent_at ? new Date(log.sent_at).getTime() : 0;
    return log[key] ?? "";
  },
  getColumnText: (log, key) => {
    if (key === "channel") return log.channel?.name || "-";
    if (key === "alert") return log.alert?.title || "-";
    if (key === "policy") return log.policy?.name || "-";
    if (key === "resource") return log.alert?.resource_name || "-";
    if (key === "notification_type") return notificationTypeLabel(log);
    if (key === "sent_at") return formatDate(log.sent_at);
    if (key === "error_message") return deliveryResult(log);
    return String(log[key] ?? "");
  },
});

function cleanParams() {
  return Object.fromEntries(
    Object.entries({
      ...filters,
      page: pagination.page,
      page_size: pagination.page_size,
    }).filter(([, value]) => value !== ""),
  );
}

async function fetchLogs() {
  loading.value = true;
  try {
    const params = cleanParams();
    const [logsRes, statsRes] = await Promise.all([
      alertsApi.notificationLogs(params),
      alertsApi.notificationLogStats(params),
    ]);
    logs.value = logsRes.data.results || logsRes.data;
    pagination.count = logsRes.data.count ?? logs.value.length;
    stats.value = statsRes.data;
  } finally {
    loading.value = false;
  }
}

async function fetchChannels() {
  const res = await alertsApi.notificationChannels({ limit: 300 });
  channels.value = res.data.results || res.data;
}

function applyFilters() {
  pagination.page = 1;
  fetchLogs();
}

function changePage(page: number) {
  pagination.page = page;
  fetchLogs();
}

function handlePageSizeChange() {
  pagination.page = 1;
  fetchLogs();
}

function formatDate(value?: string) {
  return value ? new Date(value).toLocaleString() : "-";
}

function deliveryResult(log: any) {
  return log.status === "success"
    ? t("alertsCenter.logs.deliverySucceeded")
    : log.error_message || "-";
}

function notificationTypeLabel(log: any) {
  return log.notification_type === "resolved"
    ? t("alertsCenter.values.resolved")
    : t("alertsCenter.values.firing");
}

function notificationTypeClass(log: any) {
  return log.notification_type === "resolved"
    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
    : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
}

function statusClass(status: string) {
  return status === "success"
    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
    : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300";
}

onMounted(() => {
  fetchChannels();
  fetchLogs();
});
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-start gap-3">
        <div
          class="flex h-11 w-11 items-center justify-center rounded-lg bg-background-secondary text-foreground shadow-sm ring-1 ring-border"
        >
          <EnvelopeIcon class="h-6 w-6" />
        </div>
        <div>
          <h1 class="text-2xl font-semibold text-foreground">
            {{ t("alertsCenter.logs.title") }}
          </h1>
          <p class="mt-1 max-w-3xl text-sm text-foreground-secondary">
            {{ t("alertsCenter.logs.subtitle") }}
          </p>
        </div>
      </div>
      <button
        @click="fetchLogs"
        class="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground shadow-sm hover:bg-hover"
      >
        <ArrowPathIcon class="h-4 w-4" :class="{ 'animate-spin': loading }" />
        {{ t("alertsCenter.common.refresh") }}
      </button>
    </div>

    <div class="grid gap-3 md:grid-cols-4">
      <div class="rounded-lg border border-border bg-background p-4 shadow-sm">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
            <ListBulletIcon class="w-4 h-4 text-slate-600 dark:text-slate-400" />
          </div>
          <div>
            <p class="text-xs text-foreground-secondary">
              {{ t("alertsCenter.logs.totalDeliveries") }}
            </p>
            <p class="mt-0.5 text-2xl font-semibold text-foreground">
              {{ stats.total }}
            </p>
          </div>
        </div>
      </div>
      <div class="rounded-lg border border-border bg-background p-4 shadow-sm">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
            <CheckCircleIcon class="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <p class="text-xs text-foreground-secondary">
              {{ t("alertsCenter.logs.successfulDeliveries") }}
            </p>
            <p class="mt-0.5 text-2xl font-semibold text-emerald-600 dark:text-emerald-400">
              {{ stats.success }}
            </p>
          </div>
        </div>
      </div>
      <div class="rounded-lg border border-border bg-background p-4 shadow-sm">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
            <XCircleIcon class="w-4 h-4 text-red-600 dark:text-red-400" />
          </div>
          <div>
            <p class="text-xs text-foreground-secondary">
              {{ t("alertsCenter.logs.failedDeliveries") }}
            </p>
            <p class="mt-0.5 text-2xl font-semibold text-red-600 dark:text-red-400">
              {{ stats.failed }}
            </p>
          </div>
        </div>
      </div>
      <div class="rounded-lg border border-border bg-background p-4 shadow-sm">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
            <EnvelopeIcon class="w-4 h-4 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <p class="text-xs text-foreground-secondary">
              {{ t("alertsCenter.channels.successRate") }}
            </p>
            <p class="mt-0.5 text-2xl font-semibold text-foreground">
              {{ stats.success_rate }}%
            </p>
          </div>
        </div>
      </div>
    </div>

    <div
      class="grid gap-3 rounded-lg border border-border p-4 shadow-sm md:grid-cols-7"
    >
      <div class="relative md:col-span-2">
        <MagnifyingGlassIcon
          class="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-foreground-muted"
        />
        <input
          v-model="filters.search"
          @keyup.enter="applyFilters"
          :placeholder="t('alertsCenter.logs.searchPlaceholder')"
          class="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
      </div>
      <select
        v-model="filters.channel_id"
        @change="applyFilters"
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
      >
        <option value="">{{ t("alertsCenter.logs.allChannels") }}</option>
        <option
          v-for="channel in channels"
          :key="channel.id"
          :value="channel.id"
        >
          {{ channel.name }}
        </option>
      </select>
      <select
        v-model="filters.status"
        @change="applyFilters"
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
      >
        <option value="">{{ t("alertsCenter.common.allStatus") }}</option>
        <option value="success">{{ t("alertsCenter.logs.success") }}</option>
        <option value="failed">{{ t("alertsCenter.logs.failed") }}</option>
      </select>
      <select
        v-model="filters.notification_type"
        @change="applyFilters"
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
      >
        <option value="">{{ t("alertsCenter.logs.allNotificationTypes") }}</option>
        <option value="firing">{{ t("alertsCenter.values.firing") }}</option>
        <option value="resolved">{{ t("alertsCenter.values.resolved") }}</option>
      </select>
      <select
        v-model="filters.type"
        @change="applyFilters"
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
      >
        <option value="">{{ t("alertsCenter.common.allTypes") }}</option>
        <option value="metric">{{ t("alertsCenter.values.metric") }}</option>
        <option value="availability">
          {{ t("alertsCenter.values.availability") }}
        </option>
        <option value="job">{{ t("alertsCenter.values.job") }}</option>
        <option value="event">{{ t("alertsCenter.values.event") }}</option>
        <option value="system">{{ t("alertsCenter.values.system") }}</option>
      </select>
      <select
        v-model="filters.severity"
        @change="applyFilters"
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
      >
        <option value="">{{ t("alertsCenter.common.allSeverity") }}</option>
        <option value="critical">
          {{ t("alertsCenter.values.critical") }}
        </option>
        <option value="warning">{{ t("alertsCenter.values.warning") }}</option>
        <option value="info">{{ t("alertsCenter.values.info") }}</option>
      </select>
    </div>

    <div class="overflow-hidden rounded-lg border border-border shadow-sm">
      <div class="overflow-x-auto">
        <table
          class="w-full table-fixed text-left text-sm"
          :style="{ minWidth: table.tableMinWidth.value }"
        >
          <colgroup>
            <col
              v-for="column in columns"
              :key="column.key"
              :style="table.columnStyle(column.key)"
            />
          </colgroup>
          <thead
            class="border-b border-border bg-background-secondary text-xs uppercase text-foreground-secondary"
          >
            <tr>
              <ResizableSortableTh
                v-for="column in columns"
                :key="column.key"
                :column-key="column.key"
                :label="column.label"
                :style-value="table.columnStyle(column.key)"
                :sortable="true"
                :active="table.sort.value.key === column.key"
                :sort-icon="table.getSortIcon(column.key)"
                :resizing="table.resizingColumn.value === column.key"
                @sort="table.toggleSort($event as NotificationLogColumnKey)"
                @resize-start="
                  (key, event) =>
                    table.startResize(key as NotificationLogColumnKey, event)
                "
                @resize-reset="
                  table.resetColumnWidth($event as NotificationLogColumnKey)
                "
              />
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr
              v-for="log in table.sortedRows.value"
              :key="log.id"
              class="hover:bg-hover"
            >
              <td class="px-4 py-4" :style="table.columnStyle('alert')">
                <button
                  class="text-left font-medium text-foreground hover:text-primary"
                  @click="selected = log"
                >
                  {{ log.alert?.title || "-" }}
                </button>
                <div v-if="log.alert" class="mt-2 flex flex-wrap gap-2">
                  <AlertSeverityTag :severity="log.alert.severity" />
                  <AlertTypeTag :type="log.alert.type" />
                  <AlertStatusTag :status="log.alert.status" />
                </div>
              </td>
              <td class="px-4 py-4" :style="table.columnStyle('channel')">
                <p class="font-medium text-foreground">
                  {{ log.channel?.name || "-" }}
                </p>
                <p class="mt-1 text-xs text-foreground-secondary">
                  {{ log.channel?.type || "-" }}
                </p>
              </td>
              <td
                class="px-4 py-4 text-foreground-secondary"
                :style="table.columnStyle('policy')"
              >
                {{ log.policy?.name || "-" }}
              </td>
              <td
                class="px-4 py-4 text-foreground-secondary"
                :style="table.columnStyle('resource')"
              >
                <p class="text-foreground">
                  {{ log.alert?.resource_name || "-" }}
                </p>
                <p class="mt-1 text-xs">
                  {{ log.alert?.resource_type || "-" }}
                </p>
              </td>
              <td
                class="px-4 py-4"
                :style="table.columnStyle('notification_type')"
              >
                <span
                  :class="notificationTypeClass(log)"
                  class="inline-flex rounded px-2 py-1 text-xs font-medium"
                >
                  {{ notificationTypeLabel(log) }}
                </span>
              </td>
              <td class="px-4 py-4" :style="table.columnStyle('status')">
                <span
                  :class="statusClass(log.status)"
                  class="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium"
                >
                  <CheckCircleIcon
                    v-if="log.status === 'success'"
                    class="h-3.5 w-3.5"
                  />
                  <XCircleIcon v-else class="h-3.5 w-3.5" />
                  {{
                    log.status === "success"
                      ? t("alertsCenter.logs.success")
                      : t("alertsCenter.logs.failed")
                  }}
                </span>
              </td>
              <td
                class="px-4 py-4 text-foreground-secondary"
                :style="table.columnStyle('sent_at')"
              >
                {{ formatDate(log.sent_at) }}
              </td>
              <td
                class="px-4 py-4 text-foreground-secondary"
                :style="table.columnStyle('error_message')"
              >
                <span
                  :class="
                    log.status === 'success'
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  "
                >
                  {{ deliveryResult(log) }}
                </span>
              </td>
            </tr>
            <tr v-if="!loading && logs.length === 0">
              <td
                colspan="8"
                class="px-4 py-12 text-center text-sm text-foreground-secondary"
              >
                {{ t("alertsCenter.logs.noLogs") }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div
        v-if="pagination.count > 0"
        class="flex flex-wrap items-center justify-between gap-4 border-t border-border p-4"
      >
        <div class="flex items-center gap-2">
          <span class="text-sm text-foreground-secondary">{{
            t("common.rowsPerPage")
          }}</span>
          <select
            v-model="pagination.page_size"
            @change="handlePageSizeChange"
            class="rounded border border-border bg-background px-2 py-1 text-sm text-foreground"
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
              class="flex h-8 w-8 items-center justify-center rounded border border-border bg-background text-foreground-secondary hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ChevronLeftIcon class="h-4 w-4" />
            </button>
            <template v-for="page in visiblePages" :key="page">
              <button
                v-if="page === '...'"
                class="flex h-8 w-8 items-center justify-center text-slate-400"
              >
                ...
              </button>
              <button
                v-else
                @click="changePage(page as number)"
                :class="[
                  'flex h-8 w-8 items-center justify-center rounded text-sm font-medium',
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
              class="flex h-8 w-8 items-center justify-center rounded border border-border bg-background text-foreground-secondary hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ChevronRightIcon class="h-4 w-4" />
            </button>
          </nav>
        </div>
      </div>
    </div>

    <div v-if="selected" class="fixed inset-0 z-50 flex justify-end">
      <div class="absolute inset-0 bg-black/55" @click="selected = null" />
      <aside
        class="relative h-full w-full max-w-4xl overflow-auto border-l border-border bg-background p-5 shadow-xl"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold text-foreground">
              {{ selected.alert?.title || t("alertsCenter.logs.logDetails") }}
            </h2>
            <p class="mt-1 text-sm text-foreground-secondary">
              {{ selected.channel?.name || "-" }} /
              {{ formatDate(selected.sent_at) }}
            </p>
          </div>
          <button
            @click="selected = null"
            class="rounded-lg p-2 text-foreground-secondary hover:bg-hover hover:text-foreground"
          >
            <XCircleIcon class="h-5 w-5" />
          </button>
        </div>
        <div class="mt-5 grid gap-4 md:grid-cols-2">
          <div
            class="rounded-lg border border-border bg-background-secondary p-4"
          >
            <h3 class="text-sm font-medium text-foreground">
              {{ t("alertsCenter.logs.delivery") }}
            </h3>
            <dl class="mt-3 space-y-2 text-sm">
              <div class="flex justify-between gap-4">
                <dt class="text-foreground-secondary">
                  {{ t("alertsCenter.logs.deliveryStatus") }}
                </dt>
                <dd class="text-foreground">{{ selected.status }}</dd>
              </div>
              <div class="flex justify-between gap-4">
                <dt class="text-foreground-secondary">
                  {{ t("alertsCenter.logs.notificationType") }}
                </dt>
                <dd class="text-foreground">
                  {{ notificationTypeLabel(selected) }}
                </dd>
              </div>
              <div class="flex justify-between gap-4">
                <dt class="text-foreground-secondary">
                  {{ t("alertsCenter.logs.channel") }}
                </dt>
                <dd class="text-foreground">
                  {{ selected.channel?.name || "-" }}
                </dd>
              </div>
              <div class="flex justify-between gap-4">
                <dt class="text-foreground-secondary">
                  {{ t("alertsCenter.logs.sentAt") }}
                </dt>
                <dd class="text-foreground">
                  {{ formatDate(selected.sent_at) }}
                </dd>
              </div>
            </dl>
          </div>
          <div
            class="rounded-lg border border-border bg-background-secondary p-4"
          >
            <h3 class="text-sm font-medium text-foreground">
              {{ t("alertsCenter.logs.alert") }}
            </h3>
            <dl class="mt-3 space-y-2 text-sm">
              <div class="flex justify-between gap-4">
                <dt class="text-foreground-secondary">
                  {{ t("alertsCenter.logs.policy") }}
                </dt>
                <dd class="text-foreground">
                  {{ selected.policy?.name || "-" }}
                </dd>
              </div>
              <div class="flex justify-between gap-4">
                <dt class="text-foreground-secondary">
                  {{ t("alertsCenter.common.resource") }}
                </dt>
                <dd class="text-foreground">
                  {{ selected.alert?.resource_name || "-" }}
                </dd>
              </div>
              <div class="flex justify-between gap-4">
                <dt class="text-foreground-secondary">
                  {{ t("alertsCenter.common.severity") }}
                </dt>
                <dd class="text-foreground">
                  {{ selected.alert?.severity || "-" }}
                </dd>
              </div>
            </dl>
          </div>
        </div>
        <pre
          class="mt-4 overflow-auto rounded-lg border border-border bg-background-secondary p-3 text-xs text-foreground"
          >{{ JSON.stringify(selected, null, 2) }}</pre
        >
      </aside>
    </div>
  </div>
</template>
