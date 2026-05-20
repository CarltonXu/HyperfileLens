<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ClockIcon,
  CircleStackIcon,
  ArchiveBoxIcon,
  DocumentDuplicateIcon,
  EyeIcon,
  FolderIcon,
  LinkIcon,
  ShareIcon,
  StopIcon,
  TrashIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
} from "@heroicons/vue/24/outline";
import { recoveryExportsApi } from "@/api";
import { useAppStore } from "@/stores/app";
import { getApiErrorMessage } from "@/utils/errors";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import Pagination from "@/components/Pagination.vue";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";

type ExportColumnKey =
  | "select"
  | "export"
  | "snapshot"
  | "paths"
  | "status"
  | "package"
  | "downloads"
  | "share"
  | "created"
  | "expires"
  | "actions";

const { t } = useI18n();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();

const exportsList = ref<any[]>([]);
const totalItems = ref(0);
const currentPage = ref(1);
const pageSize = ref(getPageSize("recoveryExports"));
const isLoading = ref(false);
const selectedStatus = ref("all");
const searchQuery = ref("");
const selectedIds = ref<Set<string>>(new Set());
const selectedExport = ref<any | null>(null);
const shareExport = ref<any | null>(null);
const sharePassword = ref("");
const shareExpiresInHours = ref(24);
const shareSaving = ref(false);
let refreshTimer: ReturnType<typeof setInterval> | null = null;

const columns = computed(() => [
  { key: "select" as const, label: "", width: 44, min: 44, max: 44, sortable: false },
  { key: "export" as const, label: t("recoveryExports.export"), width: 300, min: 240, max: 520 },
  { key: "snapshot" as const, label: t("recoveryExports.snapshot"), width: 280, min: 220, max: 520 },
  { key: "paths" as const, label: t("recoveryExports.paths"), width: 260, min: 180, max: 520, sortable: false },
  { key: "status" as const, label: t("common.status"), width: 260, min: 220, max: 420 },
  { key: "package" as const, label: t("recoveryExports.package"), width: 160, min: 130, max: 260 },
  { key: "downloads" as const, label: t("recoveryExports.downloads"), width: 130, min: 110, max: 200 },
  { key: "share" as const, label: t("recoveryExports.share"), width: 150, min: 130, max: 240 },
  { key: "created" as const, label: t("recoveryExports.createdAt"), width: 190, min: 160, max: 280 },
  { key: "expires" as const, label: t("recoveryExports.expires"), width: 190, min: 160, max: 280 },
  { key: "actions" as const, label: t("common.actions"), width: 190, min: 170, max: 240, sortable: false, align: "right" as const },
]);

const table = useResizableSortableTable<any, ExportColumnKey>({
  storageKey: "recovery-exports-table",
  columns,
  rows: computed(() => exportsList.value),
  defaultSort: { key: "created", direction: "desc" },
  getSortValue: (row, key) => {
    if (key === "export") return row.name || "";
    if (key === "snapshot") return row.snapshot_created_at || row.snapshot_name || "";
    if (key === "status") return row.status || "";
    if (key === "package") return row.package_size || 0;
    if (key === "downloads") return row.download_count || 0;
    if (key === "share") return row.share_enabled ? 1 : 0;
    if (key === "created") return row.created_at || "";
    if (key === "expires") return row.expires_at || "";
    return "";
  },
  getColumnText: (row, key) => {
    if (key === "export") return row.name || "";
    if (key === "snapshot") return `${row.snapshot_name || ""} ${row.snapshot_source_path || ""}`;
    if (key === "paths") return (row.selected_paths || []).join(" ");
    if (key === "package") return String(row.package_size || row.processed_size || 0);
    return String(row[key] || "");
  },
  minTableWidth: 2100,
});

const allVisibleSelected = computed(
  () => exportsList.value.length > 0 && exportsList.value.every((item) => selectedIds.value.has(item.id)),
);

function exportDisplayName(item: any) {
  const paths = item.selected_paths || [];
  if (!paths.length) return item.name || t("recoveryExports.untitled");
  const first = paths[0];
  const suffix = paths.length > 1 ? ` +${paths.length - 1}` : "";
  return `${first}${suffix}`;
}

function hasActiveExports() {
  return exportsList.value.some((item) =>
    ["pending", "dispatched", "running", "packaging"].includes(item.status),
  );
}

async function fetchExports() {
  if (!exportsList.value.length) isLoading.value = true;
  try {
    const ordering =
      table.sort.value.key === "export"
        ? `${table.sort.value.direction === "desc" ? "-" : ""}name`
        : table.sort.value.key === "downloads"
          ? `${table.sort.value.direction === "desc" ? "-" : ""}download_count`
          : table.sort.value.key === "package"
            ? `${table.sort.value.direction === "desc" ? "-" : ""}package_size`
            : table.sort.value.key === "created"
              ? `${table.sort.value.direction === "desc" ? "-" : ""}created_at`
              : table.sort.value.key === "expires"
                ? `${table.sort.value.direction === "desc" ? "-" : ""}expires_at`
              : "-created_at";
    const response = await recoveryExportsApi.list({
      page: currentPage.value,
      page_size: pageSize.value,
      status: selectedStatus.value === "all" ? undefined : selectedStatus.value,
      ordering,
    });
    const data = response.data;
    const rows = data.results || data;
    const query = searchQuery.value.trim().toLowerCase();
    exportsList.value = query
      ? rows.filter((item: any) =>
          [
            exportDisplayName(item),
            item.name,
            item.snapshot_name,
            item.snapshot_source_path,
            item.repository_name,
            item.file_name,
            ...(item.selected_paths || []),
          ].some((value) => String(value || "").toLowerCase().includes(query)),
        )
      : rows;
    totalItems.value = data.count ?? exportsList.value.length;
  } catch (error) {
    appStore.error(getApiErrorMessage(error, t("common.error")));
  } finally {
    isLoading.value = false;
  }
}

function toggleAllVisible() {
  const next = new Set(selectedIds.value);
  if (allVisibleSelected.value) {
    exportsList.value.forEach((item) => next.delete(item.id));
  } else {
    exportsList.value.forEach((item) => next.add(item.id));
  }
  selectedIds.value = next;
}

function toggleSelected(id: string) {
  const next = new Set(selectedIds.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selectedIds.value = next;
}

async function bulkDelete() {
  if (!selectedIds.value.size) return;
  if (!window.confirm(t("recoveryExports.deleteConfirm", { count: selectedIds.value.size }))) return;
  try {
    await recoveryExportsApi.bulkDelete([...selectedIds.value]);
    selectedIds.value = new Set();
    appStore.success(t("common.deleteSuccess"));
    await fetchExports();
  } catch (error) {
    appStore.error(getApiErrorMessage(error, t("common.deleteFailed")));
  }
}

async function cancelExport(item: any) {
  try {
    await recoveryExportsApi.cancel(item.id);
    appStore.success(t("recoveryExports.cancelled"));
    await fetchExports();
  } catch (error) {
    appStore.error(getApiErrorMessage(error, t("recoveryExports.cancelFailed")));
  }
}

function downloadExport(item: any) {
  if (!item.is_downloadable) return;
  window.open(recoveryExportsApi.downloadUrl(item.id), "_blank");
}

function openShare(item: any) {
  if (!item.is_downloadable) return;
  shareExport.value = item;
  sharePassword.value = "";
  shareExpiresInHours.value = 24;
}

async function saveShare(enabled = true) {
  if (!shareExport.value) return;
  shareSaving.value = true;
  try {
    const password = sharePassword.value.trim();
    if (enabled && !password && !shareExport.value.has_share_password) {
      appStore.error(t("recoveryExports.passwordRequiredForShare"));
      return;
    }
    const response = await recoveryExportsApi.share(shareExport.value.id, {
      enabled,
      password: password || undefined,
      expires_in_hours: shareExpiresInHours.value,
      clear_password: !enabled,
    });
    shareExport.value = response.data;
    await fetchExports();
    appStore.success(t("recoveryExports.shareSaved"));
  } catch (error) {
    appStore.error(getApiErrorMessage(error, t("common.updateFailed")));
  } finally {
    shareSaving.value = false;
  }
}

function shareUrlForCopy(item: any) {
  const url = item?.share_url || "";
  if (!url) return "";
  try {
    const parsed = new URL(url, window.location.origin);
    return `${window.location.origin}${parsed.pathname}${parsed.search}`;
  } catch {
    return url.startsWith("/") ? `${window.location.origin}${url}` : url;
  }
}

function shareTextForCopy(item: any) {
  const password = sharePassword.value.trim();
  return [
    "HyperFileLens Recovery Export",
    `${t("recoveryExports.copyInstruction")}:`,
    shareUrlForCopy(item),
    `${t("recoveryExports.accessPassword")}: ${password}`,
  ].join("\n");
}

async function copyShareUrl(item: any) {
  if (!shareUrlForCopy(item)) return;
  if (!sharePassword.value.trim()) {
    appStore.error(t("recoveryExports.passwordRequiredForCopy"));
    return;
  }
  const text = shareTextForCopy(item);
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "readonly");
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      textarea.style.top = "0";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      const copied = document.execCommand("copy");
      document.body.removeChild(textarea);
      if (!copied) throw new Error("copy failed");
    }
    appStore.success(t("recoveryExports.shareCopied"));
  } catch (error) {
    appStore.error(t("recoveryExports.shareCopyFailed"));
  }
}

async function copyShareLinkOnly(item: any) {
  const url = shareUrlForCopy(item);
  if (!url) return;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url);
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = url;
      textarea.setAttribute("readonly", "readonly");
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      textarea.style.top = "0";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      const copied = document.execCommand("copy");
      document.body.removeChild(textarea);
      if (!copied) throw new Error("copy failed");
    }
    appStore.success(t("recoveryExports.shareLinkCopied"));
  } catch {
    appStore.error(t("recoveryExports.shareCopyFailed"));
  }
}

function formatBytes(bytes?: number) {
  const value = Number(bytes || 0);
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / Math.pow(1024, index)).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatSpeed(speed?: number) {
  const value = Number(speed || 0);
  if (!value) return "-";
  return `${value.toFixed(value >= 10 ? 1 : 2)} MB/s`;
}

function formatDate(value?: string) {
  return value ? new Date(value).toLocaleString() : "-";
}

function progressPercent(item: any) {
  return Math.max(0, Math.min(100, Number(item.progress || 0)));
}

function statusClass(status: string) {
  const classes: Record<string, string> = {
    pending: "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
    dispatched: "bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300",
    running: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300",
    packaging: "bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300",
    ready: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300",
    failed: "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300",
    cancelled: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    expired: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  };
  return classes[status] || classes.pending;
}

function statusIcon(status: string) {
  if (status === "ready") return CheckCircleIcon;
  if (status === "failed") return ExclamationTriangleIcon;
  return ClockIcon;
}

watch([currentPage, pageSize, selectedStatus, () => table.sort.value.key, () => table.sort.value.direction], fetchExports);
watch(searchQuery, () => {
  currentPage.value = 1;
  fetchExports();
});

onMounted(() => {
  fetchExports();
  refreshTimer = setInterval(() => {
    if (hasActiveExports()) fetchExports();
  }, 3000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">{{ t("nav.recoveryExports") }}</h1>
        <p class="mt-1 text-sm text-foreground-secondary">{{ t("recoveryExports.subtitle") }}</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="selectedIds.size"
          type="button"
          class="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300"
          @click="bulkDelete"
        >
          <TrashIcon class="h-4 w-4" />
          {{ t("recoveryExports.cleanSelected", { count: selectedIds.size }) }}
        </button>
        <button
          v-if="exportsList.length"
          type="button"
          class="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium text-foreground hover:bg-hover"
          @click="toggleAllVisible"
        >
          {{ allVisibleSelected ? t("recoveryExports.clearSelection") : t("recoveryExports.selectPage") }}
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium text-foreground hover:bg-hover"
          @click="fetchExports"
        >
          <ArrowPathIcon :class="['h-4 w-4', isLoading ? 'animate-spin' : '']" />
          {{ t("common.refresh") }}
        </button>
      </div>
    </div>

    <div class="rounded-lg border border-border bg-card p-4">
      <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <input
          v-model="searchQuery"
          type="text"
          class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-foreground-muted md:max-w-sm"
          :placeholder="t('recoveryExports.searchPlaceholder')"
        />
        <select
          v-model="selectedStatus"
          class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
        >
          <option value="all">{{ t("recoveryExports.statuses.all") }}</option>
          <option value="running">{{ t("recoveryExports.statuses.running") }}</option>
          <option value="packaging">{{ t("recoveryExports.statuses.packaging") }}</option>
          <option value="ready">{{ t("recoveryExports.statuses.ready") }}</option>
          <option value="failed">{{ t("recoveryExports.statuses.failed") }}</option>
          <option value="cancelled">{{ t("recoveryExports.statuses.cancelled") }}</option>
        </select>
      </div>
    </div>

    <div class="overflow-hidden rounded-lg border border-border bg-card">
      <div class="overflow-x-auto">
        <table class="w-full table-fixed" :style="{ minWidth: table.tableMinWidth.value }">
          <thead>
            <tr>
              <ResizableSortableTh
                v-for="column in columns"
                :key="column.key"
                :column-key="column.key"
                :label="column.label"
                :style-value="table.columnStyle(column.key)"
                :sortable="column.sortable !== false"
                :active="table.sort.value.key === column.key"
                :sort-icon="table.getSortIcon(column.key)"
                :align="column.align"
                :resizing="table.resizingColumn.value === column.key"
                @sort="table.toggleSort($event as ExportColumnKey)"
                @resize-start="
                  (key, event) =>
                    table.startResize(key as ExportColumnKey, event)
                "
                @resize-reset="table.resetColumnWidth($event as ExportColumnKey)"
              >
                <template v-if="column.key === 'select'" />
              </ResizableSortableTh>
            </tr>
          </thead>
          <tbody>
            <tr v-if="isLoading">
              <td :colspan="columns.length" class="p-10 text-center text-foreground-secondary">
                {{ t("common.loading") }}
              </td>
            </tr>
            <tr v-else-if="exportsList.length === 0">
              <td :colspan="columns.length" class="p-10 text-center">
                <ArrowDownTrayIcon class="mx-auto mb-3 h-10 w-10 text-foreground-muted" />
                <p class="text-sm font-medium text-foreground">{{ t("recoveryExports.noExportsTitle") }}</p>
                <p class="mt-1 text-sm text-foreground-secondary">{{ t("recoveryExports.noExportsDesc") }}</p>
              </td>
            </tr>
            <tr
              v-for="item in table.sortedRows.value"
              v-else
              :key="item.id"
              class="border-b border-border last:border-b-0 hover:bg-hover"
            >
              <td :style="table.columnStyle('select')" class="px-4 py-3">
                <input
                  type="checkbox"
                  class="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  :checked="selectedIds.has(item.id)"
                  @change="toggleSelected(item.id)"
                />
              </td>
              <td :style="table.columnStyle('export')" class="px-4 py-3 align-top">
                <p class="truncate text-sm font-medium text-foreground">{{ exportDisplayName(item) }}</p>
                <p class="mt-1 truncate text-xs text-foreground-secondary">{{ item.name }}</p>
                <p class="mt-1 text-xs text-foreground-muted">{{ t("recoveryExports.createdAt") }} {{ formatDate(item.created_at) }}</p>
              </td>
              <td :style="table.columnStyle('snapshot')" class="px-4 py-3 align-top">
                <p class="truncate text-sm text-foreground">{{ item.snapshot_name || item.snapshot }}</p>
                <p class="mt-1 truncate text-xs text-foreground-secondary">{{ item.snapshot_source_path || "-" }}</p>
                <p class="mt-1 truncate text-xs text-foreground-muted">{{ item.repository_name || "-" }} · {{ formatDate(item.snapshot_created_at) }}</p>
              </td>
              <td :style="table.columnStyle('paths')" class="px-4 py-3 align-top">
                <p class="text-sm text-foreground">{{ t("recoveryExports.selectedItems", { count: item.selected_paths?.length || 0 }) }}</p>
                <p class="mt-1 truncate text-xs text-foreground-secondary">{{ (item.selected_paths || []).slice(0, 2).join(", ") || "-" }}</p>
              </td>
              <td :style="table.columnStyle('status')" class="px-4 py-3 align-top">
                <span :class="['inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium', statusClass(item.status)]">
                  <component :is="statusIcon(item.status)" class="h-3.5 w-3.5" />
                  {{ t(`recoveryExports.statuses.${item.status}`) }}
                </span>
                <div v-if="['running', 'packaging', 'dispatched'].includes(item.status)" class="mt-2">
                  <div class="flex items-center justify-between text-[11px] text-foreground-secondary">
                    <span class="truncate">{{ item.status_message || t("recoveryExports.working") }}</span>
                    <span class="ml-2 tabular-nums">{{ progressPercent(item) }}%</span>
                  </div>
                  <div class="mt-1 h-1.5 rounded-full bg-background-tertiary">
                    <div class="h-full rounded-full bg-emerald-500" :style="{ width: `${progressPercent(item)}%` }" />
                  </div>
                  <p class="mt-1 truncate text-[11px] text-foreground-muted">
                    {{ formatBytes(item.processed_size) }} / {{ formatBytes(item.total_size) }} · {{ formatSpeed(item.speed_mbps) }} · {{ item.eta || "-" }}
                  </p>
                </div>
                <p v-else-if="item.error_message" class="mt-1 line-clamp-2 text-xs text-red-600">{{ item.error_message }}</p>
              </td>
              <td :style="table.columnStyle('package')" class="px-4 py-3 align-top">
                <p class="text-sm text-foreground">{{ formatBytes(item.package_size || item.processed_size) }}</p>
                <p class="mt-1 text-xs text-foreground-secondary">{{ item.package_format?.toUpperCase() }} · {{ item.file_name || "-" }}</p>
              </td>
              <td :style="table.columnStyle('downloads')" class="px-4 py-3 align-top">
                <p class="text-sm tabular-nums text-foreground">{{ item.download_count || 0 }}</p>
                <p class="mt-1 text-xs text-foreground-secondary">{{ formatDate(item.last_downloaded_at) }}</p>
              </td>
              <td :style="table.columnStyle('share')" class="px-4 py-3 align-top">
                <span :class="['inline-flex rounded-full px-2 py-1 text-xs font-medium', item.share_enabled ? 'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300' : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300']">
                  {{ item.share_enabled ? t("recoveryExports.shared") : t("recoveryExports.notShared") }}
                </span>
                <p class="mt-1 text-xs text-foreground-secondary">{{ formatDate(item.share_expires_at) }}</p>
              </td>
              <td :style="table.columnStyle('created')" class="px-4 py-3 align-top text-sm text-foreground-secondary">
                {{ formatDate(item.created_at) }}
              </td>
              <td :style="table.columnStyle('expires')" class="px-4 py-3 align-top text-sm text-foreground-secondary">
                {{ formatDate(item.expires_at) }}
              </td>
              <td :style="table.columnStyle('actions')" class="px-4 py-3 align-top">
                <div class="flex justify-end gap-1.5">
                  <button class="rounded-lg border border-border p-1.5 hover:bg-hover" :title="t('common.details')" @click="selectedExport = item">
                    <EyeIcon class="h-4 w-4" />
                  </button>
                  <button
                    class="rounded-lg border border-border p-1.5 hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
                    :disabled="!item.is_downloadable"
                    :title="t('recoveryExports.share')"
                    @click="openShare(item)"
                  >
                    <ShareIcon class="h-4 w-4" />
                  </button>
                  <button
                    class="rounded-lg border border-border p-1.5 hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
                    :disabled="!item.is_downloadable"
                    :title="t('common.download')"
                    @click="downloadExport(item)"
                  >
                    <ArrowDownTrayIcon class="h-4 w-4" />
                  </button>
                  <button v-if="['pending', 'dispatched', 'running', 'packaging'].includes(item.status)" class="rounded-lg border border-border p-1.5 hover:bg-hover" @click="cancelExport(item)">
                    <StopIcon class="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <Pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total-items="totalItems"
        @update:page-size="setPageSize($event, 'recoveryExports')"
      />
    </div>

    <div
      v-if="selectedExport"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="selectedExport = null"
    >
      <div class="max-h-[92vh] w-full max-w-4xl overflow-hidden rounded-lg border border-border bg-card shadow-xl">
        <div class="border-b border-border bg-card px-5 py-4">
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <h2 class="truncate text-lg font-semibold text-foreground">
                  {{ exportDisplayName(selectedExport) }}
                </h2>
                <span :class="['inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium', statusClass(selectedExport.status)]">
                  <component :is="statusIcon(selectedExport.status)" class="h-3.5 w-3.5" />
                  {{ t(`recoveryExports.statuses.${selectedExport.status}`) }}
                </span>
              </div>
              <p class="mt-1 truncate text-sm text-foreground-secondary">
                {{ selectedExport.name }}
              </p>
            </div>
            <button class="rounded-lg p-1 text-foreground-secondary hover:bg-hover hover:text-foreground" @click="selectedExport = null">
              <XMarkIcon class="h-5 w-5" />
            </button>
          </div>
          <dl class="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs">
            <div class="inline-flex items-center gap-1.5">
              <dt class="text-foreground-muted">{{ t("recoveryExports.packageSize") }}</dt>
              <dd class="font-medium text-foreground">{{ formatBytes(selectedExport.package_size || selectedExport.processed_size) }}</dd>
            </div>
            <div class="inline-flex items-center gap-1.5">
              <dt class="text-foreground-muted">{{ t("recoveryExports.selectedPaths") }}</dt>
              <dd class="font-medium text-foreground">{{ selectedExport.selected_paths?.length || 0 }}</dd>
            </div>
            <div class="inline-flex items-center gap-1.5">
              <dt class="text-foreground-muted">{{ t("recoveryExports.downloads") }}</dt>
              <dd class="font-medium text-foreground">{{ selectedExport.download_count || 0 }}</dd>
            </div>
            <div class="inline-flex min-w-0 items-center gap-1.5">
              <dt class="text-foreground-muted">{{ t("recoveryExports.expires") }}</dt>
              <dd class="truncate font-medium text-foreground">{{ formatDate(selectedExport.expires_at) }}</dd>
            </div>
          </dl>
        </div>

        <div class="max-h-[calc(92vh-150px)] overflow-auto bg-card p-4">
          <div
            v-if="['running', 'packaging', 'dispatched'].includes(selectedExport.status)"
            class="mb-3 rounded-lg border border-border bg-background-secondary/60 px-3 py-2.5"
          >
            <div class="flex items-center justify-between text-sm">
              <span class="font-medium text-foreground">{{ selectedExport.status_message || t("recoveryExports.working") }}</span>
              <span class="tabular-nums text-foreground-secondary">{{ progressPercent(selectedExport) }}%</span>
            </div>
            <div class="mt-2 h-2 rounded-full bg-background-tertiary">
              <div class="h-full rounded-full bg-primary" :style="{ width: `${progressPercent(selectedExport)}%` }" />
            </div>
            <div class="mt-2 grid gap-2 text-xs text-foreground-secondary sm:grid-cols-4">
              <span>{{ formatBytes(selectedExport.processed_size) }} / {{ formatBytes(selectedExport.total_size) }}</span>
              <span>{{ formatSpeed(selectedExport.speed_mbps) }}</span>
              <span>{{ t("recoveryExports.eta") }} {{ selectedExport.eta || "-" }}</span>
              <span class="truncate">{{ selectedExport.current_file || "-" }}</span>
            </div>
          </div>

          <div class="grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
            <section class="rounded-lg border border-border bg-card p-3">
              <div class="mb-3 flex items-center justify-between">
                <h3 class="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                  <CircleStackIcon class="h-4 w-4 text-primary" />
                  {{ t("recoveryExports.snapshot") }}
                </h3>
                <span class="rounded-full bg-background-secondary px-2 py-1 text-xs text-foreground-secondary">{{ selectedExport.snapshot_status || "-" }}</span>
              </div>
              <dl class="space-y-2.5 text-sm">
                <div>
                  <dt class="text-xs text-foreground-muted">{{ t("recoveryExports.snapshot") }}</dt>
                  <dd class="mt-1 break-all text-foreground">{{ selectedExport.snapshot_name || selectedExport.snapshot }}</dd>
                </div>
                <div>
                  <dt class="text-xs text-foreground-muted">{{ t("recoveryExports.sourcePath") }}</dt>
                  <dd class="mt-1 break-all text-foreground-secondary">{{ selectedExport.snapshot_source_path || "-" }}</dd>
                </div>
                <div class="grid gap-3 sm:grid-cols-2">
                  <div>
                    <dt class="text-xs text-foreground-muted">{{ t("repository.title") }}</dt>
                    <dd class="mt-1 text-foreground-secondary">{{ selectedExport.repository_name || "-" }}</dd>
                  </div>
                  <div>
                    <dt class="text-xs text-foreground-muted">{{ t("recoveryExports.snapshotTime") }}</dt>
                    <dd class="mt-1 text-foreground-secondary">{{ formatDate(selectedExport.snapshot_created_at) }}</dd>
                  </div>
                </div>
              </dl>
            </section>

            <section class="rounded-lg border border-border bg-card p-3">
              <h3 class="mb-3 inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                <ArchiveBoxIcon class="h-4 w-4 text-primary" />
                {{ t("recoveryExports.package") }}
              </h3>
              <dl class="space-y-2.5 text-sm">
                <div>
                  <dt class="text-xs text-foreground-muted">{{ t("recoveryExports.package") }}</dt>
                  <dd class="mt-1 break-all text-foreground">{{ selectedExport.file_name || "-" }}</dd>
                </div>
                <div class="grid gap-3 sm:grid-cols-2">
                  <div>
                    <dt class="text-xs text-foreground-muted">{{ t("recoveryExports.package") }}</dt>
                    <dd class="mt-1 text-foreground-secondary">{{ selectedExport.package_format?.toUpperCase() || "-" }}</dd>
                  </div>
                  <div>
                    <dt class="text-xs text-foreground-muted">{{ t("recoveryExports.downloads") }}</dt>
                    <dd class="mt-1 text-foreground-secondary">{{ selectedExport.download_count || 0 }} · {{ formatDate(selectedExport.last_downloaded_at) }}</dd>
                  </div>
                </div>
                <div>
                  <dt class="text-xs text-foreground-muted">SHA256</dt>
                  <dd class="mt-1 break-all rounded border border-border bg-background px-2 py-1 font-mono text-xs text-foreground-secondary">{{ selectedExport.checksum || "-" }}</dd>
                </div>
              </dl>
            </section>
          </div>

          <section class="mt-3 rounded-lg border border-border bg-card p-3">
            <div class="mb-3 flex items-center justify-between">
              <h3 class="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                <FolderIcon class="h-4 w-4 text-primary" />
                {{ t("recoveryExports.paths") }}
              </h3>
              <span class="text-xs text-foreground-secondary">{{ t("recoveryExports.selectedItems", { count: selectedExport.selected_paths?.length || 0 }) }}</span>
            </div>
            <div class="max-h-56 overflow-auto rounded-lg border border-border bg-background">
              <div
                v-for="path in selectedExport.selected_paths || []"
                :key="path"
                class="border-b border-border px-3 py-2 font-mono text-xs text-foreground-secondary last:border-b-0"
              >
                {{ path }}
              </div>
            </div>
          </section>

          <section v-if="selectedExport.error_message" class="mt-3">
            <div class="rounded-lg border border-red-200 bg-red-50 p-3 dark:border-red-900 dark:bg-red-950/20">
              <h3 class="inline-flex items-center gap-2 text-sm font-semibold text-red-700 dark:text-red-300">
                <ExclamationTriangleIcon class="h-4 w-4" />
                {{ t("common.error") }}
              </h3>
              <p class="mt-2 whitespace-pre-wrap text-sm text-red-700 dark:text-red-300">{{ selectedExport.error_message }}</p>
            </div>
          </section>
          <section v-if="selectedExport.share_enabled" class="mt-3 rounded-lg border border-border bg-card p-3">
            <div class="flex items-center justify-between gap-3">
              <h3 class="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                <ShareIcon class="h-4 w-4 text-primary" />
                {{ t("recoveryExports.share") }}
              </h3>
              <button
                class="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs text-foreground hover:bg-hover"
                @click="copyShareLinkOnly(selectedExport)"
              >
                <DocumentDuplicateIcon class="h-4 w-4" />
                {{ t("recoveryExports.copyShareLink") }}
              </button>
            </div>
            <p class="mt-2 truncate text-xs text-foreground-secondary">{{ shareUrlForCopy(selectedExport) }}</p>
            <p class="mt-1 text-xs text-foreground-muted">{{ t("recoveryExports.shareExpiresHours") }}: {{ formatDate(selectedExport.share_expires_at) }}</p>
          </section>
        </div>
      </div>
    </div>

    <div v-if="shareExport" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="shareExport = null">
      <div class="w-full max-w-xl rounded-lg border border-border bg-card p-5 shadow-xl">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="text-lg font-semibold text-foreground">{{ t("recoveryExports.shareSettings") }}</h2>
            <p class="mt-1 text-sm text-foreground-secondary">{{ exportDisplayName(shareExport) }}</p>
          </div>
          <button class="rounded-lg p-1 hover:bg-hover" @click="shareExport = null"><XMarkIcon class="h-5 w-5" /></button>
        </div>
        <div class="mt-4 space-y-4">
          <label class="block">
            <span class="text-sm font-medium text-foreground">{{ t("recoveryExports.sharePassword") }}</span>
            <input v-model="sharePassword" type="password" class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground" :placeholder="t('recoveryExports.optionalPassword')" />
          </label>
          <label class="block">
            <span class="text-sm font-medium text-foreground">{{ t("recoveryExports.shareExpiresHours") }}</span>
            <input v-model.number="shareExpiresInHours" type="number" min="1" max="168" class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground" />
          </label>
          <div v-if="shareExport.share_url" class="rounded-lg border border-border bg-background p-3">
            <p class="truncate text-xs text-foreground-secondary">{{ shareUrlForCopy(shareExport) }}</p>
            <p v-if="shareExport.has_share_password" class="mt-1 text-xs text-amber-600 dark:text-amber-300">
              {{ t("recoveryExports.passwordRequired") }}
            </p>
            <p class="mt-1 text-xs text-foreground-muted">
              {{ t("recoveryExports.copyWillIncludePassword") }}
            </p>
            <button class="mt-2 inline-flex items-center gap-2 rounded-lg border border-border px-2.5 py-1.5 text-xs hover:bg-hover" @click="copyShareUrl(shareExport)">
              <DocumentDuplicateIcon class="h-4 w-4" />
              {{ t("common.copy") }}
            </button>
          </div>
          <div class="flex justify-end gap-2">
            <button class="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:bg-hover" @click="saveShare(false)">
              <LinkIcon class="h-4 w-4" />
              {{ t("recoveryExports.disableShare") }}
            </button>
            <button class="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-50" :disabled="shareSaving" @click="saveShare(true)">
              <ShareIcon class="h-4 w-4" />
              {{ t("recoveryExports.enableShare") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
