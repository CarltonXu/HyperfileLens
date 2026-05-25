<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowTopRightOnSquareIcon,
  ChevronDownIcon,
  ClipboardDocumentIcon,
  ExclamationTriangleIcon,
  ListBulletIcon,
  ArrowsUpDownIcon,
} from "@heroicons/vue/24/outline";

const props = defineProps<{
  runs: any[];
  loading: boolean;
  totalCount: number;
  getStatusColor: (status: string) => string;
  formatDateTime: (value?: string | null) => string;
  runDuration: (run: any) => string;
  currentPage: number;
  pageSize: number;
  statusFilter: string;
  triggerFilter: string;
  ordering: string;
}>();

const emit = defineEmits<{
  "update:currentPage": [page: number];
  "update:pageSize": [size: number];
  "update:statusFilter": [filter: string];
  "update:triggerFilter": [filter: string];
  "update:ordering": [order: string];
  openManagement: [run: any];
  copyError: [text: string];
  reload: [];
}>();

const { t } = useI18n();
const expandedErrorIds = ref<Set<string>>(new Set());

const statusOptions = [
  { value: "all", label: "common.all" },
  { value: "pending", label: "backupTasks.status.pending" },
  { value: "dispatched", label: "backupTasks.status.dispatched" },
  { value: "running", label: "backupTasks.status.running" },
  { value: "completed", label: "backupTasks.status.completed" },
  { value: "partial", label: "backupTasks.status.partial" },
  { value: "failed", label: "backupTasks.status.failed" },
  { value: "cancelled", label: "backupTasks.status.cancelled" },
  { value: "timeout", label: "backupTasks.status.timeout" },
];

const triggerOptions = [
  { value: "all", label: "common.all" },
  { value: "manual", label: "backupTasks.runs.triggerManual" },
  { value: "scheduled", label: "backupTasks.runs.triggerScheduled" },
  { value: "retry", label: "backupTasks.runs.triggerRetry" },
];

const orderingOptions = [
  { value: "-created_at", label: "common.newestFirst" },
  { value: "created_at", label: "common.oldestFirst" },
  { value: "-status", label: "common.statusDesc" },
  { value: "status", label: "common.statusAsc" },
  { value: "-progress", label: "common.progressDesc" },
  { value: "progress", label: "common.progressAsc" },
];

const totalPages = computed(() => Math.ceil(props.totalCount / props.pageSize) || 1);

const showPagination = computed(() => props.totalCount > props.pageSize);

function errorText(run: any) {
  const statusHasError = ["failed", "timeout", "partial"].includes(run.status);
  const text = run.error_message || (statusHasError ? run.message : "");
  return String(text || "").trim();
}

function hasErrorDetails(run: any) {
  return Boolean(errorText(run));
}

function isLongError(run: any) {
  return errorText(run).length > 260;
}

function isErrorExpanded(run: any) {
  return expandedErrorIds.value.has(String(run.id));
}

function displayedError(run: any) {
  const text = errorText(run);
  if (!isLongError(run) || isErrorExpanded(run)) return text;
  return `${text.slice(0, 260)}...`;
}

function toggleError(run: any) {
  const next = new Set(expandedErrorIds.value);
  const id = String(run.id);
  if (next.has(id)) {
    next.delete(id);
  } else {
    next.add(id);
  }
  expandedErrorIds.value = next;
}

function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return;
  emit("update:currentPage", page);
}

function handlePageSizeChange(size: number) {
  emit("update:pageSize", size);
}

function handleStatusFilterChange(filter: string) {
  emit("update:statusFilter", filter);
}

function handleTriggerFilterChange(filter: string) {
  emit("update:triggerFilter", filter);
}

function handleOrderingChange(order: string) {
  emit("update:ordering", order);
}

// Reload when page changes
watch(() => props.currentPage, () => {
  emit("reload");
});
</script>

<template>
  <div class="space-y-3">
    <!-- Filters Toolbar -->
    <div class="flex flex-wrap items-center gap-3">
      <!-- Status Filter -->
      <div class="flex items-center gap-2">
        <label class="text-xs text-foreground-secondary">{{ t("common.status") }}:</label>
        <select
          :value="statusFilter"
          @change="handleStatusFilterChange(($event.target as HTMLSelectElement).value)"
          class="h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
            {{ t(opt.label) }}
          </option>
        </select>
      </div>

      <!-- Trigger Type Filter -->
      <div class="flex items-center gap-2">
        <label class="text-xs text-foreground-secondary">{{ t("backupTasks.runs.triggerType") }}:</label>
        <select
          :value="triggerFilter"
          @change="handleTriggerFilterChange(($event.target as HTMLSelectElement).value)"
          class="h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option v-for="opt in triggerOptions" :key="opt.value" :value="opt.value">
            {{ t(opt.label) }}
          </option>
        </select>
      </div>

      <!-- Sort Order -->
      <div class="flex items-center gap-2">
        <ArrowsUpDownIcon class="h-3.5 w-3.5 text-foreground-muted" />
        <select
          :value="ordering"
          @change="handleOrderingChange(($event.target as HTMLSelectElement).value)"
          class="h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option v-for="opt in orderingOptions" :key="opt.value" :value="opt.value">
            {{ t(opt.label) }}
          </option>
        </select>
      </div>

      <!-- Results count -->
      <div class="ml-auto text-xs text-foreground-muted">
        {{ t("common.showing") }} {{ runs.length }} / {{ totalCount }} {{ t("common.results") }}
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="py-10 text-center text-foreground-secondary">
      {{ t("common.loading") }}
    </div>

    <!-- Empty State -->
    <div
      v-else-if="runs.length === 0"
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

    <!-- Runs List -->
    <div v-else class="space-y-2">
      <div
        v-for="run in runs"
        :key="run.id"
        class="cursor-pointer rounded-lg border border-border bg-card px-3 py-2.5 transition-colors hover:border-primary hover:bg-hover"
        role="button"
        tabindex="0"
        :title="t('taskManagement.openTask')"
        @click="emit('openManagement', run)"
        @keydown.enter.prevent="emit('openManagement', run)"
        @keydown.space.prevent="emit('openManagement', run)"
      >
        <div class="flex flex-col gap-2">
          <div class="flex items-start justify-between gap-3">
            <div class="flex min-w-0 items-start gap-2.5">
              <span
                class="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-background-secondary text-foreground-muted"
              >
                <ListBulletIcon class="h-4 w-4" />
              </span>
              <div class="min-w-0">
                <p
                  class="inline-flex max-w-full items-center gap-1.5 truncate text-sm font-medium text-foreground"
                >
                  {{ run.name }}
                  <ArrowTopRightOnSquareIcon
                    class="h-3.5 w-3.5 shrink-0 text-foreground-muted"
                  />
                </p>
                <p class="mt-0.5 truncate text-xs text-foreground-secondary">
                  {{ formatDateTime(run.created_at) }}
                  <span v-if="run.proxy_name"> · {{ run.proxy_name }}</span>
                  <span v-if="run.trigger_type"> · {{ t(`backupTasks.runs.trigger${run.trigger_type.charAt(0).toUpperCase() + run.trigger_type.slice(1)}`) }}</span>
                </p>
                <p
                  v-if="run.message && !hasErrorDetails(run)"
                  class="mt-1 truncate text-xs text-foreground-secondary"
                >
                  {{ run.message }}
                </p>
              </div>
            </div>
            <span
              :class="[
                'inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[11px] font-medium',
                getStatusColor(run.status),
              ]"
            >
              {{ t(`backupTasks.status.${run.status}`) }}
            </span>
          </div>

          <div
            v-if="hasErrorDetails(run)"
            class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-red-800 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200"
            @click.stop
          >
            <div class="flex items-start justify-between gap-3">
              <div class="flex min-w-0 items-start gap-2">
                <ExclamationTriangleIcon class="mt-0.5 h-4 w-4 shrink-0" />
                <div class="min-w-0">
                  <p class="text-xs font-semibold">
                    {{ t("backupTasks.runs.errorDetails") }}
                  </p>
                  <p
                    class="mt-1 whitespace-pre-wrap break-words font-mono text-[11px] leading-5"
                  >
                    {{ displayedError(run) }}
                  </p>
                </div>
              </div>
              <div class="flex shrink-0 items-center gap-1">
                <button
                  v-if="isLongError(run)"
                  type="button"
                  class="inline-flex h-7 w-7 items-center justify-center rounded-md text-red-700 transition-colors hover:bg-red-100 dark:text-red-200 dark:hover:bg-red-900/50 border border-transparent hover:border-red-200"
                  :title="
                    isErrorExpanded(run)
                      ? t('backupTasks.runs.hideError')
                      : t('backupTasks.runs.showError')
                  "
                  @click.stop="toggleError(run)"
                >
                  <ChevronDownIcon
                    :class="[
                      'h-4 w-4 transition-transform',
                      isErrorExpanded(run) && 'rotate-180',
                    ]"
                  />
                </button>
                <button
                  type="button"
                  class="inline-flex h-7 w-7 items-center justify-center rounded-md text-red-700 transition-colors hover:bg-red-100 dark:text-red-200 dark:hover:bg-red-900/50 border border-transparent hover:border-red-200"
                  :title="t('backupTasks.runs.copyError')"
                  @click.stop="emit('copyError', errorText(run))"
                >
                  <ClipboardDocumentIcon class="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          <div
            class="grid grid-cols-2 gap-2 text-xs md:grid-cols-[65px_80px_70px_1fr_85px]"
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
                {{ t("backupTasks.progress.eta") }}
              </p>
              <p class="font-medium text-foreground">
                {{ run.eta || "-" }}
              </p>
            </div>
            <div>
              <p class="text-[11px] text-foreground-muted">
                {{ t("backupTasks.progress.files") }}
              </p>
              <p class="font-medium text-foreground">
                {{ run.processed_files || 0 }} / {{ run.total_files || 0 }}
              </p>
            </div>
            <div>
              <p class="text-[11px] text-foreground-muted">
                {{ t("backupTasks.progress.speed") }}
              </p>
              <p class="font-medium text-foreground">
                {{ run.speed_mbps ? `${run.speed_mbps.toFixed(2)} MB/s` : "-" }}
              </p>
            </div>
          </div>

          <div
            class="h-1.5 overflow-hidden rounded-full bg-background-tertiary"
          >
            <div
              class="h-full bg-primary transition-all"
              :style="{ width: `${Math.min(run.progress || 0, 100)}%` }"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="showPagination" class="flex items-center justify-between pt-2">
      <div class="flex items-center gap-2">
        <label class="text-xs text-foreground-secondary">{{ t("common.rowsPerPage") }}:</label>
        <select
          :value="pageSize"
          @change="handlePageSizeChange(Number(($event.target as HTMLSelectElement).value))"
          class="h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </div>

      <div class="flex items-center gap-1">
        <button
          @click="goToPage(1)"
          :disabled="currentPage === 1"
          class="h-8 w-8 rounded-md border border-border bg-background text-xs text-foreground hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
        >
          «
        </button>
        <button
          @click="goToPage(currentPage - 1)"
          :disabled="currentPage === 1"
          class="h-8 w-8 rounded-md border border-border bg-background text-xs text-foreground hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
        >
          ‹
        </button>

        <span class="px-2 text-xs text-foreground-secondary">
          {{ currentPage }} / {{ totalPages }}
        </span>

        <button
          @click="goToPage(currentPage + 1)"
          :disabled="currentPage >= totalPages"
          class="h-8 w-8 rounded-md border border-border bg-background text-xs text-foreground hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
        >
          ›
        </button>
        <button
          @click="goToPage(totalPages)"
          :disabled="currentPage >= totalPages"
          class="h-8 w-8 rounded-md border border-border bg-background text-xs text-foreground hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
        >
          »
        </button>
      </div>
    </div>
  </div>
</template>
