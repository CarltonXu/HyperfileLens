<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  StopIcon,
} from "@heroicons/vue/24/outline";
import { recoveryExportsApi } from "@/api";
import { useAppStore } from "@/stores/app";
import { getApiErrorMessage } from "@/utils/errors";

const { t } = useI18n();
const appStore = useAppStore();

const exportsList = ref<any[]>([]);
const isLoading = ref(false);
const selectedStatus = ref("all");
const searchQuery = ref("");

const filteredExports = computed(() => {
  let rows = exportsList.value;
  if (selectedStatus.value !== "all") {
    rows = rows.filter((item) => item.status === selectedStatus.value);
  }
  const query = searchQuery.value.trim().toLowerCase();
  if (query) {
    rows = rows.filter((item) =>
      [item.name, item.snapshot_name, item.repository_name, item.file_name]
        .some((value) => String(value || "").toLowerCase().includes(query)),
    );
  }
  return rows;
});

async function fetchExports() {
  isLoading.value = true;
  try {
    const response = await recoveryExportsApi.list({ page_size: 200 });
    exportsList.value = response.data.results || response.data;
  } catch (error) {
    appStore.error(getApiErrorMessage(error, t("common.error")));
  } finally {
    isLoading.value = false;
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
  window.open(recoveryExportsApi.downloadUrl(item.id), "_blank");
}

function formatBytes(bytes?: number) {
  const value = Number(bytes || 0);
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / Math.pow(1024, index)).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDate(value?: string) {
  return value ? new Date(value).toLocaleString() : "-";
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

onMounted(fetchExports);
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">{{ t("nav.recoveryExports") }}</h1>
        <p class="mt-1 text-sm text-foreground-secondary">
          {{ t("recoveryExports.subtitle") }}
        </p>
      </div>
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium text-foreground hover:bg-hover"
        @click="fetchExports"
      >
        <ArrowPathIcon :class="['h-4 w-4', isLoading ? 'animate-spin' : '']" />
        {{ t("common.refresh") }}
      </button>
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
      <div
        class="grid grid-cols-[minmax(240px,1.6fr)_minmax(220px,1fr)_140px_130px_180px] gap-4 border-b border-border bg-background-secondary px-4 py-3 text-xs font-medium uppercase tracking-wide text-foreground-secondary"
      >
        <span>{{ t("recoveryExports.export") }}</span>
        <span>{{ t("recoveryExports.snapshot") }}</span>
        <span>{{ t("common.status") }}</span>
        <span>{{ t("recoveryExports.package") }}</span>
        <span class="text-right">{{ t("common.actions") }}</span>
      </div>
      <div v-if="isLoading" class="p-10 text-center text-foreground-secondary">
        {{ t("common.loading") }}
      </div>
      <div v-else-if="filteredExports.length === 0" class="p-10 text-center">
        <ArrowDownTrayIcon class="mx-auto mb-3 h-10 w-10 text-foreground-muted" />
        <p class="text-sm font-medium text-foreground">{{ t("recoveryExports.noExportsTitle") }}</p>
        <p class="mt-1 text-sm text-foreground-secondary">
          {{ t("recoveryExports.noExportsDesc") }}
        </p>
      </div>
      <div
        v-for="item in filteredExports"
        v-else
        :key="item.id"
        class="grid grid-cols-[minmax(240px,1.6fr)_minmax(220px,1fr)_140px_130px_180px] gap-4 border-b border-border px-4 py-3 text-sm last:border-b-0 hover:bg-hover"
      >
        <div class="min-w-0">
          <p class="font-medium text-foreground truncate">{{ item.name }}</p>
          <p class="mt-1 text-xs text-foreground-secondary">
            {{ t("recoveryExports.selectedItems", { count: item.selected_paths?.length || 0 }) }} · {{ t("recoveryExports.expires") }} {{ formatDate(item.expires_at) }}
          </p>
        </div>
        <div class="min-w-0">
          <p class="truncate text-foreground">{{ item.snapshot_name || item.snapshot }}</p>
          <p class="mt-1 truncate text-xs text-foreground-secondary">{{ item.repository_name || "-" }}</p>
        </div>
        <div>
          <span :class="['inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium', statusClass(item.status)]">
            <component :is="statusIcon(item.status)" class="h-3.5 w-3.5" />
            {{ t(`recoveryExports.statuses.${item.status}`) }}
          </span>
          <div v-if="['running', 'packaging', 'dispatched'].includes(item.status)" class="mt-2 h-1.5 rounded-full bg-background-tertiary">
            <div class="h-full rounded-full bg-emerald-500" :style="{ width: `${item.progress || 0}%` }" />
          </div>
        </div>
        <div>
          <p class="text-foreground">{{ formatBytes(item.package_size || item.processed_size) }}</p>
          <p class="mt-1 text-xs text-foreground-secondary">{{ item.package_format?.toUpperCase() }}</p>
        </div>
        <div class="flex justify-end gap-2">
          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-hover disabled:opacity-50"
            :disabled="!item.is_downloadable"
            @click="downloadExport(item)"
          >
            <ArrowDownTrayIcon class="h-4 w-4" />
            {{ t("common.download") || "Download" }}
          </button>
          <button
            v-if="['pending', 'dispatched', 'running', 'packaging'].includes(item.status)"
            type="button"
            class="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-hover"
            @click="cancelExport(item)"
          >
            <StopIcon class="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
