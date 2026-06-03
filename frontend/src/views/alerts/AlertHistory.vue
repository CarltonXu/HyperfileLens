<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ClockIcon,
  EyeIcon,
  MagnifyingGlassIcon,
} from "@heroicons/vue/24/outline";
import { alertsApi } from "@/api";
import { useAuthStore } from "@/stores/auth";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";
import AlertSeverityTag from "@/components/alerts/AlertSeverityTag.vue";
import AlertStatusTag from "@/components/alerts/AlertStatusTag.vue";
import AlertTypeTag from "@/components/alerts/AlertTypeTag.vue";

const alerts = ref<any[]>([]);
const { t } = useI18n();
const authStore = useAuthStore();
const { getPageSize, setPageSize } = usePagination();
const selected = ref<any | null>(null);
const loading = ref(false);
const exporting = ref(false);
const filters = reactive({
  search: "",
  severity: "",
  type: "",
  status: "",
  resource_type: "",
});
const isSystemAdmin = computed(() => !!authStore.user?.is_superuser);
const pagination = reactive({
  page: 1,
  page_size: getPageSize("alert-history"),
  count: 0,
});
const PAGE_STORAGE_KEY = "alert-history";

watch(
  () => pagination.page_size,
  (newSize) => {
    setPageSize(newSize, PAGE_STORAGE_KEY);
  },
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
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    if (current < total - 2) pages.push("...");
    pages.push(total);
  }

  return pages;
});

async function fetchAlerts() {
  loading.value = true;
  try {
    const params = Object.fromEntries(
      Object.entries({
        ...filters,
        page: pagination.page,
        page_size: pagination.page_size,
      }).filter(([, value]) => value !== ""),
    );
    const res = await alertsApi.records(params);
    alerts.value = res.data.results || res.data;
    pagination.count = res.data.count ?? alerts.value.length;
  } finally {
    loading.value = false;
  }
}

function applyFilters() {
  pagination.page = 1;
  fetchAlerts();
}

function changePage(page: number) {
  pagination.page = page;
  fetchAlerts();
}

function handlePageSizeChange() {
  pagination.page = 1;
  fetchAlerts();
}

function csvValue(value: unknown) {
  const text = String(value ?? "");
  return `"${text.replace(/"/g, '""')}"`;
}

function currentFilterParams() {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== ""),
  );
}

async function exportAlerts() {
  if (exporting.value) return;
  exporting.value = true;
  try {
    const pageSize = 300;
    let page = 1;
    let total = 0;
    const rows: any[] = [];

    do {
      const res = await alertsApi.records({
        ...currentFilterParams(),
        page,
        page_size: pageSize,
      });
      const data = res.data.results || res.data || [];
      rows.push(...data);
      total = res.data.count ?? rows.length;
      page += 1;
    } while (rows.length < total);

    const headers = [
      t("alertsCenter.common.severity"),
      t("alertsCenter.common.title"),
      t("alertsCenter.common.type"),
      t("alertsCenter.common.resource"),
      t("alertsCenter.common.status"),
      t("alertsCenter.history.firstTriggered"),
      t("alertsCenter.history.resolvedAt"),
      t("alertsCenter.common.duration"),
    ];
    const csvRows = rows.map((alert) =>
      [
        alert.severity,
        alert.title,
        alert.type,
        alert.resource_name || alert.resource_type || "-",
        alert.status,
        formatDate(alert.first_triggered_at),
        formatDate(alert.resolved_at),
        duration(alert),
      ]
        .map(csvValue)
        .join(","),
    );
    const csv = [headers.map(csvValue).join(","), ...csvRows].join("\n");
    const blob = new Blob([`\ufeff${csv}`], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `alert-history-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } finally {
    exporting.value = false;
  }
}

function duration(alert: any) {
  if (alert.duration_seconds == null) return "-";
  const minutes = Math.floor(alert.duration_seconds / 60);
  const seconds = alert.duration_seconds % 60;
  return `${minutes}m ${seconds}s`;
}

function formatDate(value?: string) {
  return value ? new Date(value).toLocaleString() : "-";
}

type AlertHistoryColumnKey =
  | "severity"
  | "title"
  | "type"
  | "resource"
  | "status"
  | "first_triggered_at"
  | "resolved_at"
  | "duration"
  | "actions";

const alertHistoryColumns = computed(() => [
  {
    key: "severity" as const,
    label: t("alertsCenter.common.severity"),
    min: 120,
    max: 240,
  },
  {
    key: "title" as const,
    label: t("alertsCenter.common.title"),
    min: 260,
    max: 620,
  },
  {
    key: "type" as const,
    label: t("alertsCenter.common.type"),
    min: 120,
    max: 240,
  },
  {
    key: "resource" as const,
    label: t("alertsCenter.common.resource"),
    min: 180,
    max: 420,
  },
  {
    key: "status" as const,
    label: t("alertsCenter.common.status"),
    min: 120,
    max: 240,
  },
  {
    key: "first_triggered_at" as const,
    label: t("alertsCenter.history.firstTriggered"),
    min: 190,
    max: 320,
  },
  {
    key: "resolved_at" as const,
    label: t("alertsCenter.history.resolvedAt"),
    min: 190,
    max: 320,
  },
  {
    key: "duration" as const,
    label: t("alertsCenter.common.duration"),
    min: 130,
    max: 260,
  },
  {
    key: "actions" as const,
    label: t("alertsCenter.common.actions"),
    min: 100,
    max: 180,
    sortable: false,
    align: "right" as const,
  },
]);

const alertHistoryTable = useResizableSortableTable<any, AlertHistoryColumnKey>(
  {
    storageKey: "hyperfilelens:alert-history:columnWidths",
    columns: alertHistoryColumns,
    rows: alerts,
    defaultSort: { key: "first_triggered_at", direction: "desc" },
    minTableWidth: 1040,
    getSortValue: (alert, key) => {
      if (key === "resource")
        return alert.resource_name || alert.resource_type || "";
      if (key === "duration") return Number(alert.duration_seconds ?? -1);
      if (key === "first_triggered_at" || key === "resolved_at") {
        return alert[key] ? new Date(alert[key]).getTime() : 0;
      }
      if (key === "actions") return "";
      return alert[key] ?? "";
    },
    getColumnText: (alert, key) => {
      if (key === "resource")
        return alert.resource_name || alert.resource_type || "-";
      if (key === "duration") return duration(alert);
      if (key === "first_triggered_at" || key === "resolved_at")
        return formatDate(alert[key]);
      if (key === "actions") return t("alertsCenter.common.actions");
      return String(alert[key] ?? "");
    },
  },
);

onMounted(fetchAlerts);
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-start gap-3">
        <div
          class="flex h-11 w-11 items-center justify-center rounded-lg bg-background-secondary text-foreground shadow-sm ring-1 ring-border"
        >
          <ClockIcon class="h-6 w-6" />
        </div>
        <div>
          <h1 class="text-2xl font-semibold text-foreground">
            {{ $t("alertsCenter.history.title") }}
          </h1>
          <p class="mt-1 max-w-3xl text-sm text-foreground-secondary">
            {{ $t("alertsCenter.history.subtitle") }}
          </p>
        </div>
      </div>
      <button
        :disabled="exporting"
        @click="exportAlerts"
        class="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-hover"
      >
        <ArrowDownTrayIcon class="h-4 w-4" />
        {{ t("alertsCenter.common.export") }}
      </button>
    </div>

    <div
      class="flex max-h-[calc(100vh-13rem)] min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-card shadow-sm"
    >
    <div
      class="flex flex-shrink-0 flex-wrap items-center gap-3 border-b border-border p-4"
    >
      <div class="relative min-w-[240px] flex-1">
        <MagnifyingGlassIcon
          class="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-foreground-muted"
        />
        <input
          v-model="filters.search"
          @keyup.enter="applyFilters"
          :placeholder="t('alertsCenter.history.searchPlaceholder')"
          class="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
      </div>
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
        <option v-if="isSystemAdmin" value="system">
          {{ t("alertsCenter.values.system") }}
        </option>
      </select>
      <select
        v-model="filters.status"
        @change="applyFilters"
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
      >
        <option value="">{{ t("alertsCenter.common.allStatus") }}</option>
        <option value="pending">{{ t("alertsCenter.values.pending") }}</option>
        <option value="firing">{{ t("alertsCenter.values.firing") }}</option>
        <option value="acknowledged">
          {{ t("alertsCenter.values.acknowledged") }}
        </option>
        <option value="resolved">
          {{ t("alertsCenter.values.resolved") }}
        </option>
      </select>
      <button
        class="ml-auto inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground shadow-sm hover:bg-hover"
        @click="fetchAlerts"
      >
        <ArrowPathIcon class="h-4 w-4" />
        {{ $t("common.refresh") }}
      </button>
    </div>

      <div class="relative min-h-0 flex-1 overflow-auto bg-card">
        <table
          class="w-full table-fixed border-separate border-spacing-0 text-left text-sm"
          :style="{ minWidth: alertHistoryTable.tableMinWidth.value }"
        >
          <colgroup>
            <col
              v-for="column in alertHistoryColumns"
              :key="column.key"
              :style="alertHistoryTable.columnStyle(column.key)"
            />
          </colgroup>
          <thead
            class="sticky top-0 z-30 bg-background-secondary text-xs uppercase text-foreground-secondary shadow-sm"
          >
            <tr>
              <ResizableSortableTh
                v-for="column in alertHistoryColumns"
                :key="column.key"
                :column-key="column.key"
                :label="column.label"
                :style-value="alertHistoryTable.columnStyle(column.key)"
                :sortable="column.sortable !== false"
                :active="alertHistoryTable.sort.value.key === column.key"
                :align="column.align"
                :sort-icon="alertHistoryTable.getSortIcon(column.key)"
                :resizing="
                  alertHistoryTable.resizingColumn.value === column.key
                "
                header-class="border-b border-border"
                @sort="
                  alertHistoryTable.toggleSort($event as AlertHistoryColumnKey)
                "
                @resize-start="
                  (key, event) =>
                    alertHistoryTable.startResize(
                      key as AlertHistoryColumnKey,
                      event,
                    )
                "
                @resize-reset="
                  alertHistoryTable.resetColumnWidth(
                    $event as AlertHistoryColumnKey,
                  )
                "
              />
            </tr>
          </thead>
          <tbody class="[&>tr>td]:border-b [&>tr>td]:border-border">
            <tr
              v-for="alert in alertHistoryTable.sortedRows.value"
              :key="alert.id"
              class="hover:bg-hover"
            >
              <td
                class="px-4 py-4"
                :style="alertHistoryTable.columnStyle('severity')"
              >
                <AlertSeverityTag :severity="alert.severity" />
              </td>
              <td
                class="px-4 py-4 font-medium text-foreground"
                :style="alertHistoryTable.columnStyle('title')"
              >
                {{ alert.title }}
              </td>
              <td
                class="px-4 py-4"
                :style="alertHistoryTable.columnStyle('type')"
              >
                <AlertTypeTag :type="alert.type" />
              </td>
              <td
                class="px-4 py-4 text-foreground-secondary"
                :style="alertHistoryTable.columnStyle('resource')"
              >
                {{ alert.resource_name || alert.resource_type || "-" }}
              </td>
              <td
                class="px-4 py-4"
                :style="alertHistoryTable.columnStyle('status')"
              >
                <AlertStatusTag :status="alert.status" />
              </td>
              <td
                class="px-4 py-4 text-foreground-secondary"
                :style="alertHistoryTable.columnStyle('first_triggered_at')"
              >
                {{ formatDate(alert.first_triggered_at) }}
              </td>
              <td
                class="px-4 py-4 text-foreground-secondary"
                :style="alertHistoryTable.columnStyle('resolved_at')"
              >
                {{ formatDate(alert.resolved_at) }}
              </td>
              <td
                class="px-4 py-4 text-foreground-secondary"
                :style="alertHistoryTable.columnStyle('duration')"
              >
                {{ duration(alert) }}
              </td>
              <td
                class="px-4 py-4 text-right"
                :style="alertHistoryTable.columnStyle('actions')"
              >
                <button
                  :title="t('alertsCenter.common.detail')"
                  @click="selected = alert"
                  class="rounded-lg p-2 text-foreground-secondary hover:bg-hover hover:text-foreground"
                >
                  <EyeIcon class="h-4 w-4" />
                </button>
              </td>
            </tr>
            <tr v-if="!loading && alerts.length === 0">
              <td
                colspan="9"
                class="px-4 py-12 text-center text-sm text-foreground-secondary"
              >
                {{ $t("common.noData") }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div
        v-if="pagination.count > 0"
        class="flex flex-shrink-0 flex-wrap items-center justify-between gap-4 border-t border-border bg-card p-4"
      >
        <div class="flex items-center gap-2">
          <span class="text-sm text-foreground-secondary">{{
            t("common.rowsPerPage")
          }}</span>
          <select
            v-model="pagination.page_size"
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

    <div v-if="selected" class="fixed inset-0 z-50 flex justify-end">
      <div class="absolute inset-0 bg-black/55" @click="selected = null" />
      <aside
        class="relative h-full w-full max-w-4xl overflow-auto border-l border-border bg-background p-5 shadow-xl"
      >
        <h2 class="text-lg font-semibold text-foreground">
          {{ selected.title }}
        </h2>
        <pre
          class="mt-4 overflow-auto rounded-lg border border-border bg-background-secondary p-3 text-xs text-foreground"
          >{{ JSON.stringify(selected, null, 2) }}</pre
        >
      </aside>
    </div>
  </div>
</template>
