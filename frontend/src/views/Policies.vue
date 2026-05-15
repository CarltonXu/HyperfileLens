<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { policiesApi } from "@/api";
import { useAppStore } from "@/stores/app";
import { getApiErrorMessage } from "@/utils/errors";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import Pagination from "@/components/Pagination.vue";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";
import {
  ArrowPathIcon,
  CalendarIcon,
  CheckCircleIcon,
  ClockIcon,
  Cog6ToothIcon,
  DocumentTextIcon,
  EyeIcon,
  MagnifyingGlassIcon,
  PauseIcon,
  PencilSquareIcon,
  PlusIcon,
  ShieldCheckIcon,
  TrashIcon,
  XCircleIcon,
} from "@heroicons/vue/24/outline";

const { t } = useI18n();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();

type PolicyScope = "global" | "host" | "user" | "path";
type ScheduleMode = "manual" | "interval" | "time" | "cron";

interface KopiaRetentionPolicy {
  keep_latest: number;
  keep_hourly: number;
  keep_daily: number;
  keep_weekly: number;
  keep_monthly: number;
  keep_annual: number;
}

interface BackupPolicy {
  id: string;
  name: string;
  description?: string;
  frequency: string;
  backup_type: string;
  schedule_time?: string | null;
  schedule_day?: number | null;
  retention_days?: number;
  retention_snapshots?: number;
  is_active: boolean;
  policy_scope: PolicyScope;
  policy_target: Record<string, any>;
  snapshot_schedule: Record<string, any>;
  retention_policy: KopiaRetentionPolicy;
  file_policy: Record<string, any>;
  compression_policy: Record<string, any>;
  advanced_policy: Record<string, any>;
  next_run_time?: string | null;
  created_at?: string;
  updated_at?: string;
}

interface PolicyForm {
  name: string;
  description: string;
  is_active: boolean;
  backup_type: string;
  policy_scope: PolicyScope;
  target_host: string;
  target_user: string;
  target_path: string;
  schedule_mode: ScheduleMode;
  interval: string;
  time_of_day: string;
  cron: string;
  run_missed: boolean;
  keep_latest: number;
  keep_hourly: number;
  keep_daily: number;
  keep_weekly: number;
  keep_monthly: number;
  keep_annual: number;
  ignore_patterns_text: string;
  dot_ignore_files_text: string;
  one_file_system: boolean;
  ignore_file_errors: boolean;
  ignore_dir_errors: boolean;
  compression: string;
  metadata_compression: boolean;
  max_parallel_file_reads: number;
  ignore_identical_snapshots: boolean;
}

const defaultRetention: KopiaRetentionPolicy = {
  keep_latest: 10,
  keep_hourly: 48,
  keep_daily: 14,
  keep_weekly: 25,
  keep_monthly: 24,
  keep_annual: 3,
};

const defaultForm = (): PolicyForm => ({
  name: "",
  description: "",
  is_active: true,
  backup_type: "incremental",
  policy_scope: "path",
  target_host: "",
  target_user: "",
  target_path: "",
  schedule_mode: "interval",
  interval: "24h",
  time_of_day: "02:00",
  cron: "",
  run_missed: true,
  keep_latest: defaultRetention.keep_latest,
  keep_hourly: defaultRetention.keep_hourly,
  keep_daily: defaultRetention.keep_daily,
  keep_weekly: defaultRetention.keep_weekly,
  keep_monthly: defaultRetention.keep_monthly,
  keep_annual: defaultRetention.keep_annual,
  ignore_patterns_text: "",
  dot_ignore_files_text: ".kopiaignore",
  one_file_system: false,
  ignore_file_errors: false,
  ignore_dir_errors: false,
  compression: "zstd",
  metadata_compression: true,
  max_parallel_file_reads: 4,
  ignore_identical_snapshots: true,
});

const retentionFields = [
  { key: "keep_latest", label: "keep_latest", description: "keep_latest_desc" },
  { key: "keep_hourly", label: "keep_hourly", description: "keep_hourly_desc" },
  { key: "keep_daily", label: "keep_daily", description: "keep_daily_desc" },
  { key: "keep_weekly", label: "keep_weekly", description: "keep_weekly_desc" },
  {
    key: "keep_monthly",
    label: "keep_monthly",
    description: "keep_monthly_desc",
  },
  { key: "keep_annual", label: "keep_annual", description: "keep_annual_desc" },
] as const;

const isLoading = ref(true);
const isSaving = ref(false);
const policies = ref<BackupPolicy[]>([]);
const searchQuery = ref("");
const showPolicyModal = ref(false);
const editingPolicy = ref<BackupPolicy | null>(null);
const showDetailsModal = ref(false);
const selectedPolicy = ref<BackupPolicy | null>(null);
const isLoadingDetails = ref(false);
const form = ref<PolicyForm>(defaultForm());

const currentPage = ref(1);
const pageSize = ref(getPageSize("policies"));
const PAGE_STORAGE_KEY = "policies";

watch(pageSize, (newSize) => {
  setPageSize(newSize, PAGE_STORAGE_KEY);
});

const filteredPolicies = computed(() => {
  if (!searchQuery.value) return policies.value;
  const query = searchQuery.value.toLowerCase();
  return policies.value.filter((policy) =>
    [policy.name, policy.description, policy.policy_scope]
      .join(" ")
      .toLowerCase()
      .includes(query),
  );
});

type PolicyColumnKey =
  | "name"
  | "target"
  | "schedule"
  | "retention"
  | "status"
  | "actions";

const policyColumns = computed(() => [
  { key: "name" as const, label: t("common.name"), min: 220, max: 420 },
  {
    key: "target" as const,
    label: t("policies.target.title"),
    min: 220,
    max: 420,
  },
  {
    key: "schedule" as const,
    label: t("policies.form.schedule"),
    min: 180,
    max: 300,
  },
  {
    key: "retention" as const,
    label: t("policies.retention.title"),
    min: 190,
    max: 320,
  },
  { key: "status" as const, label: t("common.status"), min: 140, max: 220 },
  {
    key: "actions" as const,
    label: t("common.actions"),
    min: 150,
    max: 220,
    sortable: false,
    align: "right" as const,
  },
]);

const policyTable = useResizableSortableTable<BackupPolicy, PolicyColumnKey>({
  storageKey: "hyperfilelens:policies:columns",
  columns: policyColumns,
  rows: filteredPolicies,
  defaultSort: { key: "name", direction: "asc" },
  minTableWidth: 1120,
  getSortValue: (policy, key) => {
    if (key === "name") return policy.name;
    if (key === "target") return getPolicyTarget(policy);
    if (key === "schedule") return getScheduleLabel(policy);
    if (key === "retention") return formatRetention(policy);
    if (key === "status") return policy.is_active ? 1 : 0;
    return "";
  },
  getColumnText: (policy, key) => {
    if (key === "name") return `${policy.name} ${policy.description || ""}`;
    if (key === "target")
      return `${getScopeLabel(policy.policy_scope)} ${getPolicyTarget(policy)}`;
    if (key === "schedule")
      return `${getScheduleLabel(policy)} ${formatDate(policy.next_run_time)}`;
    if (key === "retention") return formatRetention(policy);
    if (key === "status")
      return policy.is_active ? t("common.enabled") : t("common.disabled");
    return "";
  },
});

const paginatedPolicies = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return policyTable.sortedRows.value.slice(start, start + pageSize.value);
});

const enabledCount = computed(
  () => policies.value.filter((policy) => policy.is_active).length,
);

const retentionPreview = computed(() => {
  return [
    `latest ${form.value.keep_latest}`,
    `hourly ${form.value.keep_hourly}`,
    `daily ${form.value.keep_daily}`,
    `weekly ${form.value.keep_weekly}`,
    `monthly ${form.value.keep_monthly}`,
    `annual ${form.value.keep_annual}`,
  ].join(" / ");
});

const policyPreviewCommand = computed(() => {
  const target = buildKopiaTargetFromForm();
  const lines = [
    `kopia policy set ${target || "<target>"}`,
    `  --keep-latest ${form.value.keep_latest}`,
    `  --keep-hourly ${form.value.keep_hourly}`,
    `  --keep-daily ${form.value.keep_daily}`,
    `  --keep-weekly ${form.value.keep_weekly}`,
    `  --keep-monthly ${form.value.keep_monthly}`,
    `  --keep-annual ${form.value.keep_annual}`,
  ];
  if (form.value.schedule_mode === "interval") {
    lines.push(`  --snapshot-interval ${form.value.interval}`);
  } else if (form.value.schedule_mode === "time") {
    lines.push(`  --snapshot-time ${form.value.time_of_day}`);
  } else if (form.value.schedule_mode === "cron") {
    lines.push(`  --snapshot-time-crontab "${form.value.cron || "* * * * *"}"`);
  }
  return lines.join("\n");
});

watch(searchQuery, () => {
  currentPage.value = 1;
});

function normalizePolicy(raw: any): BackupPolicy {
  const retention = raw.retention_policy || {};
  return {
    ...raw,
    is_active: raw.is_active ?? raw.enabled ?? true,
    frequency: raw.frequency || raw.schedule_type || "daily",
    backup_type: raw.backup_type || "incremental",
    policy_scope: raw.policy_scope || "path",
    policy_target: raw.policy_target || {},
    snapshot_schedule: raw.snapshot_schedule || {},
    retention_policy: {
      keep_latest: retention.keep_latest ?? raw.retention_snapshots ?? 10,
      keep_hourly: retention.keep_hourly ?? 48,
      keep_daily: retention.keep_daily ?? 14,
      keep_weekly: retention.keep_weekly ?? 25,
      keep_monthly: retention.keep_monthly ?? 24,
      keep_annual: retention.keep_annual ?? 3,
    },
    file_policy: raw.file_policy || {},
    compression_policy: raw.compression_policy || {},
    advanced_policy: raw.advanced_policy || {},
  };
}

async function fetchPolicies() {
  isLoading.value = true;
  try {
    const response = await policiesApi.list({ page_size: 500 });
    policies.value = (response.data.results || response.data || []).map(
      normalizePolicy,
    );
  } catch (error) {
    console.error("Failed to fetch policies:", error);
  } finally {
    isLoading.value = false;
  }
}

function openCreateModal() {
  editingPolicy.value = null;
  form.value = defaultForm();
  showPolicyModal.value = true;
}

function openEditModal(policy: BackupPolicy) {
  editingPolicy.value = policy;
  const target = policy.policy_target || {};
  const schedule = policy.snapshot_schedule || {};
  const retention = policy.retention_policy || defaultRetention;

  form.value = {
    name: policy.name,
    description: policy.description || "",
    is_active: policy.is_active,
    backup_type: policy.backup_type || "incremental",
    policy_scope: policy.policy_scope || "path",
    target_host: target.host || "",
    target_user: target.user || "",
    target_path: target.path || "",
    schedule_mode: schedule.mode || policy.frequency || "interval",
    interval: schedule.interval || "24h",
    time_of_day: schedule.time_of_day || policy.schedule_time || "02:00",
    cron: schedule.cron || "",
    run_missed: schedule.run_missed ?? true,
    keep_latest: retention.keep_latest ?? 10,
    keep_hourly: retention.keep_hourly ?? 48,
    keep_daily: retention.keep_daily ?? 14,
    keep_weekly: retention.keep_weekly ?? 25,
    keep_monthly: retention.keep_monthly ?? 24,
    keep_annual: retention.keep_annual ?? 3,
    ignore_patterns_text: "",
    dot_ignore_files_text: ".kopiaignore",
    one_file_system: false,
    ignore_file_errors: false,
    ignore_dir_errors: false,
    compression: "zstd",
    metadata_compression: true,
    max_parallel_file_reads: 4,
    ignore_identical_snapshots: true,
  };
  showPolicyModal.value = true;
}

async function openDetailsModal(policy: BackupPolicy) {
  selectedPolicy.value = policy;
  showDetailsModal.value = true;
  isLoadingDetails.value = true;
  try {
    const response = await policiesApi.detail(policy.id);
    selectedPolicy.value = normalizePolicy(response.data);
  } catch (error) {
    console.error("Failed to fetch policy details:", error);
    appStore.error(getApiErrorMessage(error, t("common.updateFailed")));
  } finally {
    isLoadingDetails.value = false;
  }
}

function buildKopiaTargetFromForm() {
  if (form.value.policy_scope === "global") return "global";
  if (form.value.policy_scope === "host")
    return `@${form.value.target_host || "host"}`;
  if (form.value.policy_scope === "user") {
    return `${form.value.target_user || "user"}@${form.value.target_host || "host"}`;
  }
  const userHost =
    form.value.target_user || form.value.target_host
      ? `${form.value.target_user || "user"}@${form.value.target_host || "host"}`
      : "user@host";
  return `${userHost}:${form.value.target_path || "/path"}`;
}

function buildPayload() {
  const scheduleMode = form.value.schedule_mode;
  const frequency =
    scheduleMode === "manual"
      ? "manual"
      : scheduleMode === "interval"
        ? "hourly"
        : "daily";
  return {
    name: form.value.name.trim(),
    description: form.value.description.trim(),
    is_active: form.value.is_active,
    backup_type: form.value.backup_type,
    frequency,
    schedule_time:
      scheduleMode === "time" || scheduleMode === "interval"
        ? form.value.time_of_day
        : null,
    retention_days: Math.max(1, form.value.keep_daily || 1),
    retention_snapshots: Math.max(1, form.value.keep_latest || 1),
    policy_scope: form.value.policy_scope,
    policy_target: {
      host: form.value.target_host.trim(),
      user: form.value.target_user.trim(),
      path: form.value.target_path.trim(),
      kopia_target: buildKopiaTargetFromForm(),
    },
    snapshot_schedule: {
      mode: form.value.schedule_mode,
      interval: form.value.interval,
      time_of_day: form.value.time_of_day,
      cron: form.value.cron,
      run_missed: form.value.run_missed,
    },
    retention_policy: {
      keep_latest: Number(form.value.keep_latest) || 0,
      keep_hourly: Number(form.value.keep_hourly) || 0,
      keep_daily: Number(form.value.keep_daily) || 0,
      keep_weekly: Number(form.value.keep_weekly) || 0,
      keep_monthly: Number(form.value.keep_monthly) || 0,
      keep_annual: Number(form.value.keep_annual) || 0,
    },
    file_policy: {},
    compression_policy: {},
    compression_enabled: true,
    encryption_enabled: true,
  };
}

async function savePolicy() {
  if (!form.value.name.trim()) {
    appStore.error(t("policies.validation.nameRequired"));
    return;
  }
  isSaving.value = true;
  try {
    const payload = buildPayload();
    if (editingPolicy.value) {
      await policiesApi.update(editingPolicy.value.id, payload);
    } else {
      await policiesApi.create(payload);
    }
    showPolicyModal.value = false;
    await fetchPolicies();
  } catch (error) {
    console.error("Failed to save policy:", error);
    appStore.error(getApiErrorMessage(error, t("common.saveFailed")));
  } finally {
    isSaving.value = false;
  }
}

async function togglePolicy(policy: BackupPolicy) {
  try {
    if (policy.is_active) {
      await policiesApi.disable(policy.id);
    } else {
      await policiesApi.enable(policy.id);
    }
    await fetchPolicies();
    if (selectedPolicy.value?.id === policy.id) {
      selectedPolicy.value = {
        ...selectedPolicy.value,
        is_active: !policy.is_active,
      };
    }
  } catch (error) {
    console.error("Failed to toggle policy:", error);
    appStore.error(getApiErrorMessage(error, t("common.updateFailed")));
  }
}

async function deletePolicy(policy: BackupPolicy) {
  if (!confirm(t("policies.confirmDelete"))) return;
  try {
    await policiesApi.delete(policy.id);
    await fetchPolicies();
  } catch (error) {
    console.error("Failed to delete policy:", error);
    appStore.error(getApiErrorMessage(error, t("common.deleteFailed")));
  }
}

function getScopeLabel(scope: string) {
  return t(`policies.scopes.${scope}`) || scope;
}

function getScheduleLabel(policy: BackupPolicy) {
  const mode = policy.snapshot_schedule?.mode || policy.frequency || "manual";
  if (mode === "interval") return policy.snapshot_schedule?.interval || "24h";
  if (mode === "time") return policy.snapshot_schedule?.time_of_day || "-";
  if (mode === "cron") return policy.snapshot_schedule?.cron || "-";
  return t("policies.scheduleTypes.manual");
}

function formatRetention(policy: BackupPolicy) {
  const retention = policy.retention_policy || defaultRetention;
  return `L${retention.keep_latest} H${retention.keep_hourly} D${retention.keep_daily} W${retention.keep_weekly} M${retention.keep_monthly} A${retention.keep_annual}`;
}

function getPolicyTarget(policy: BackupPolicy | null) {
  if (!policy) return "-";
  return policy.policy_target?.kopia_target || "-";
}

function getPolicyPreviewCommand(policy: BackupPolicy | null) {
  if (!policy) return "";
  const retention = policy.retention_policy || defaultRetention;
  const schedule = policy.snapshot_schedule || {};
  const lines = [
    `kopia policy set ${getPolicyTarget(policy) || "<target>"}`,
    `  --keep-latest ${retention.keep_latest}`,
    `  --keep-hourly ${retention.keep_hourly}`,
    `  --keep-daily ${retention.keep_daily}`,
    `  --keep-weekly ${retention.keep_weekly}`,
    `  --keep-monthly ${retention.keep_monthly}`,
    `  --keep-annual ${retention.keep_annual}`,
  ];
  if (schedule.mode === "interval") {
    lines.push(`  --snapshot-interval ${schedule.interval || "24h"}`);
  } else if (schedule.mode === "time") {
    lines.push(`  --snapshot-time ${schedule.time_of_day || "02:00"}`);
  } else if (schedule.mode === "cron") {
    lines.push(`  --snapshot-time-crontab "${schedule.cron || "* * * * *"}"`);
  } else {
    lines.push("  --manual");
  }
  return lines.join("\n");
}

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString() : "-";
}

onMounted(fetchPolicies);
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">
          {{ t("policies.title") }}
        </h1>
        <p class="mt-1 text-slate-500">{{ t("policies.subtitle") }}</p>
      </div>
      <button
        @click="openCreateModal"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-violet-500 to-purple-600 rounded-lg hover:from-violet-600 hover:to-purple-700 transition-all shadow-md hover:shadow-lg">
        <PlusIcon class="w-4 h-4" />
        {{ t("policies.form.addPolicy") }}
      </button>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
        <p class="text-xs text-foreground-secondary">
          {{ t("policies.stats.total") }}
        </p>
        <p class="mt-1 text-xl font-bold text-foreground">
          {{ policies.length }}
        </p>
      </div>
      <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
        <p class="text-xs text-foreground-secondary">
          {{ t("policies.stats.enabled") }}
        </p>
        <p class="mt-1 text-xl font-bold text-emerald-600">
          {{ enabledCount }}
        </p>
      </div>
      <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
        <p class="text-xs text-foreground-secondary">
          {{ t("policies.retention.kopiaRetention") }}
        </p>
        <p class="mt-1 text-xl font-bold text-violet-600">Kopia</p>
      </div>
    </div>

    <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div class="flex flex-wrap items-center gap-3">
        <div class="relative min-w-[220px] flex-1">
          <MagnifyingGlassIcon
            class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('common.search')"
            class="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-4 text-sm text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
        </div>
        <button
          @click="fetchPolicies"
          class="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-foreground-secondary hover:bg-hover">
          <ArrowPathIcon class="h-4 w-4" />
          {{ t("common.refresh") }}
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <div
        class="h-8 w-8 animate-spin rounded-full border-4 border-violet-200 border-t-violet-600" />
    </div>

    <div
      v-else-if="filteredPolicies.length === 0"
      class="rounded-xl border border-border bg-card p-12 text-center">
      <div
        class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-background-tertiary">
        <DocumentTextIcon class="h-8 w-8 text-slate-400" />
      </div>
      <h3 class="mb-1 text-lg font-medium text-foreground">
        {{ t("policies.empty.title") }}
      </h3>
      <p class="text-foreground-secondary">
        {{ t("policies.empty.description") }}
      </p>
    </div>

    <div
      v-else
      class="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <div class="overflow-x-auto">
        <table
          class="w-full table-fixed"
          :style="{ minWidth: policyTable.tableMinWidth.value }">
          <colgroup>
            <col
              v-for="column in policyColumns"
              :key="column.key"
              :style="policyTable.columnStyle(column.key)" />
          </colgroup>
          <thead class="border-b border-border bg-background-secondary">
            <tr>
              <ResizableSortableTh
                v-for="column in policyColumns"
                :key="column.key"
                :column-key="column.key"
                :label="column.label"
                :style-value="policyTable.columnStyle(column.key)"
                :sortable="column.sortable !== false"
                :active="policyTable.sort.value.key === column.key"
                :align="column.align"
                :sort-icon="policyTable.getSortIcon(column.key)"
                :resizing="policyTable.resizingColumn.value === column.key"
                @sort="policyTable.toggleSort($event as PolicyColumnKey)"
                @resize-start="
                  (key, event) =>
                    policyTable.startResize(key as PolicyColumnKey, event)
                "
                @resize-reset="
                  policyTable.resetColumnWidth($event as PolicyColumnKey)
                " />
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 dark:divide-slate-700">
            <tr
              v-for="policy in paginatedPolicies"
              :key="policy.id"
              class="hover:bg-hover transition-colors">
              <td class="px-4 py-4" :style="policyTable.columnStyle('name')">
                <div class="flex items-center gap-3">
                  <div
                    class="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-100 text-violet-600 dark:bg-violet-900/30 dark:text-violet-400">
                    <ShieldCheckIcon class="h-5 w-5" />
                  </div>
                  <div class="min-w-0">
                    <p class="truncate text-sm font-medium text-foreground">
                      {{ policy.name }}
                    </p>
                    <p class="truncate text-xs text-foreground-secondary">
                      {{ policy.description || policy.backup_type }}
                    </p>
                  </div>
                </div>
              </td>
              <td class="px-4 py-4" :style="policyTable.columnStyle('target')">
                <span
                  class="inline-flex rounded-full bg-background-tertiary px-2.5 py-0.5 text-xs font-medium text-foreground">
                  {{ getScopeLabel(policy.policy_scope) }}
                </span>
                <p
                  class="mt-1 max-w-[240px] truncate text-xs text-foreground-secondary">
                  {{ policy.policy_target?.kopia_target || "-" }}
                </p>
              </td>
              <td
                class="px-4 py-4 text-sm text-foreground-secondary"
                :style="policyTable.columnStyle('schedule')">
                <div class="flex items-center gap-2">
                  <ClockIcon class="h-4 w-4 text-foreground-muted" />
                  {{ getScheduleLabel(policy) }}
                </div>
                <p class="mt-1 text-xs text-foreground-muted">
                  {{ t("policies.form.nextRun") }}:
                  {{ formatDate(policy.next_run_time) }}
                </p>
              </td>
              <td class="px-4 py-4" :style="policyTable.columnStyle('retention')">
                <p class="font-mono text-xs text-foreground">
                  {{ formatRetention(policy) }}
                </p>
              </td>
              <td class="px-4 py-4" :style="policyTable.columnStyle('status')">
                <span
                  :class="[
                    'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors',
                    policy.is_active
                      ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                      : 'bg-background-tertiary text-slate-500',
                  ]">
                  <CheckCircleIcon
                    v-if="policy.is_active"
                    class="h-3.5 w-3.5" />
                  <PauseIcon v-else class="h-3.5 w-3.5" />
                  {{
                    policy.is_active
                      ? t("common.enabled")
                      : t("common.disabled")
                  }}
                </span>
              </td>
              <td
                class="px-4 py-4 text-right"
                :style="policyTable.columnStyle('actions')">
                <div class="flex items-center justify-end gap-2">
                  <button
                    @click="openDetailsModal(policy)"
                    class="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-background-tertiary hover:text-violet-600"
                    :title="t('common.viewDetails')">
                    <EyeIcon class="h-4 w-4" />
                  </button>
                  <button
                    @click="togglePolicy(policy)"
                    :class="[
                      'rounded-lg p-1.5 transition-colors',
                      policy.is_active
                        ? 'text-slate-500 hover:bg-amber-50 hover:text-amber-600 dark:hover:bg-amber-900/20'
                        : 'text-slate-500 hover:bg-emerald-50 hover:text-emerald-600 dark:hover:bg-emerald-900/20',
                    ]"
                    :title="
                      policy.is_active
                        ? t('policies.actions.disable')
                        : t('policies.actions.enable')
                    ">
                    <PauseIcon v-if="policy.is_active" class="h-4 w-4" />
                    <CheckCircleIcon v-else class="h-4 w-4" />
                  </button>
                  <button
                    @click="openEditModal(policy)"
                    class="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-background-tertiary hover:text-violet-600"
                    :title="t('common.edit')">
                    <PencilSquareIcon class="h-4 w-4" />
                  </button>
                  <button
                    @click="deletePolicy(policy)"
                    class="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
                    :title="t('common.delete')">
                    <TrashIcon class="h-4 w-4" />
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
        :total-items="filteredPolicies.length" />
    </div>

    <Teleport to="body">
      <div
        v-if="showDetailsModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        @click.self="showDetailsModal = false">
        <div
          class="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-border modal-surface shadow-xl">
          <div
            class="flex items-start justify-between gap-4 border-b border-border px-6 py-4">
            <div>
              <h2 class="text-lg font-semibold text-foreground">
                {{ selectedPolicy?.name || t("common.details") }}
              </h2>
              <p class="mt-1 text-sm text-foreground-secondary">
                {{ t("policies.details.subtitle") }}
              </p>
            </div>
            <button
              @click="showDetailsModal = false"
              class="rounded-lg p-2 hover:bg-background-tertiary">
              <XCircleIcon class="h-5 w-5 text-slate-400" />
            </button>
          </div>

          <div v-if="isLoadingDetails" class="flex justify-center py-16">
            <div
              class="h-8 w-8 animate-spin rounded-full border-4 border-violet-200 border-t-violet-600" />
          </div>

          <div v-else-if="selectedPolicy" class="flex-1 overflow-y-auto p-6">
            <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <section class="rounded-lg border border-border bg-card p-4">
                <div class="mb-3 flex items-center gap-2">
                  <DocumentTextIcon class="h-5 w-5 text-violet-600" />
                  <h3 class="font-semibold text-foreground">
                    {{ t("policies.sections.basic") }}
                  </h3>
                </div>
                <dl class="space-y-3 text-sm">
                  <div>
                    <dt class="text-xs text-foreground-muted">
                      {{ t("common.status") }}
                    </dt>
                    <dd class="mt-1">
                      <span
                        :class="[
                          'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium',
                          selectedPolicy.is_active
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                            : 'bg-background-tertiary text-slate-500',
                        ]">
                        <CheckCircleIcon
                          v-if="selectedPolicy.is_active"
                          class="h-3.5 w-3.5" />
                        <PauseIcon v-else class="h-3.5 w-3.5" />
                        {{
                          selectedPolicy.is_active
                            ? t("common.enabled")
                            : t("common.disabled")
                        }}
                      </span>
                    </dd>
                  </div>
                  <div>
                    <dt class="text-xs text-foreground-muted">
                      {{ t("policies.form.backupType") }}
                    </dt>
                    <dd class="mt-1 text-foreground">
                      {{ selectedPolicy.backup_type || "-" }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-xs text-foreground-muted">
                      {{ t("common.description") }}
                    </dt>
                    <dd class="mt-1 text-foreground-secondary">
                      {{ selectedPolicy.description || "-" }}
                    </dd>
                  </div>
                </dl>
              </section>

              <section class="rounded-lg border border-border bg-card p-4">
                <div class="mb-3 flex items-center gap-2">
                  <Cog6ToothIcon class="h-5 w-5 text-violet-600" />
                  <h3 class="font-semibold text-foreground">
                    {{ t("policies.target.title") }}
                  </h3>
                </div>
                <dl class="space-y-3 text-sm">
                  <div>
                    <dt class="text-xs text-foreground-muted">
                      {{ t("policies.target.title") }}
                    </dt>
                    <dd class="mt-1 text-foreground">
                      {{ getScopeLabel(selectedPolicy.policy_scope) }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-xs text-foreground-muted">
                      Kopia Target
                    </dt>
                    <dd class="mt-1 break-all font-mono text-foreground">
                      {{ getPolicyTarget(selectedPolicy) }}
                    </dd>
                  </div>
                </dl>
              </section>

              <section class="rounded-lg border border-border bg-card p-4">
                <div class="mb-3 flex items-center gap-2">
                  <CalendarIcon class="h-5 w-5 text-violet-600" />
                  <h3 class="font-semibold text-foreground">
                    {{ t("policies.schedule.title") }}
                  </h3>
                </div>
                <dl class="space-y-3 text-sm">
                  <div>
                    <dt class="text-xs text-foreground-muted">
                      {{ t("policies.form.schedule") }}
                    </dt>
                    <dd class="mt-1 text-foreground">
                      {{ getScheduleLabel(selectedPolicy) }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-xs text-foreground-muted">
                      {{ t("policies.form.nextRun") }}
                    </dt>
                    <dd class="mt-1 text-foreground-secondary">
                      {{ formatDate(selectedPolicy.next_run_time) }}
                    </dd>
                  </div>
                </dl>
              </section>
            </div>

            <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
              <section class="rounded-lg border border-border bg-card p-4">
                <div class="mb-3 flex items-center gap-2">
                  <ShieldCheckIcon class="h-5 w-5 text-violet-600" />
                  <h3 class="font-semibold text-foreground">
                    {{ t("policies.retention.title") }}
                  </h3>
                </div>
                <div class="grid grid-cols-2 gap-3">
                  <div
                    v-for="field in retentionFields"
                    :key="field.key"
                    class="rounded-lg border border-border bg-background/50 p-3">
                    <p class="text-xs text-foreground-muted">
                      {{ t(`policies.retention.${field.label}`) }}
                    </p>
                    <p class="mt-1 text-lg font-semibold text-foreground">
                      {{ selectedPolicy.retention_policy[field.key] }}
                    </p>
                  </div>
                </div>
              </section>

              <section class="rounded-lg border border-border bg-card p-4">
                <div class="mb-3 flex items-center gap-2">
                  <ShieldCheckIcon class="h-5 w-5 text-violet-600" />
                  <h3 class="font-semibold text-foreground">
                    {{ t("policies.preview.title") }}
                  </h3>
                </div>
                <pre
                  class="max-h-[360px] overflow-auto rounded-lg border border-border bg-slate-950 p-3 text-xs text-slate-100"
                  >{{ getPolicyPreviewCommand(selectedPolicy) }}</pre
                >
              </section>
            </div>
          </div>

          <div
            v-if="selectedPolicy"
            class="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
            <button
              @click="togglePolicy(selectedPolicy)"
              class="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover">
              <PauseIcon v-if="selectedPolicy.is_active" class="h-4 w-4" />
              <CheckCircleIcon v-else class="h-4 w-4" />
              {{
                selectedPolicy.is_active
                  ? t("policies.actions.disable")
                  : t("policies.actions.enable")
              }}
            </button>
            <button
              @click="
                showDetailsModal = false;
                openEditModal(selectedPolicy);
              "
              class="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700">
              <PencilSquareIcon class="h-4 w-4" />
              {{ t("common.edit") }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="showPolicyModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          class="absolute inset-0 bg-black/50"
          @click="showPolicyModal = false" />
        <div
          class="relative flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-xl border border-border modal-surface shadow-xl">
          <div
            class="flex items-start justify-between gap-4 border-b border-border px-6 py-4">
            <div>
              <h2 class="text-lg font-semibold text-foreground">
                {{
                  editingPolicy
                    ? t("policies.form.editPolicy")
                    : t("policies.form.addPolicy")
                }}
              </h2>
              <p class="mt-1 text-sm text-foreground-secondary">
                {{ t("policies.kopiaSubtitle") }}
              </p>
            </div>
            <button
              @click="showPolicyModal = false"
              class="rounded-lg p-2 hover:bg-background-tertiary">
              <XCircleIcon class="h-5 w-5 text-slate-400" />
            </button>
          </div>

          <div
            class="grid min-h-0 flex-1 grid-cols-1 overflow-y-auto xl:grid-cols-[minmax(0,1fr)_360px]">
            <div class="space-y-5 p-6">
              <section class="rounded-lg border border-border bg-card p-4">
                <div class="mb-2 flex items-center gap-2">
                  <DocumentTextIcon class="h-5 w-5 text-violet-600" />
                  <h3 class="font-semibold text-foreground">
                    {{ t("policies.sections.basic") }}
                  </h3>
                </div>
                <p class="mb-4 text-xs text-foreground-secondary">
                  {{ t("policies.basic.description") }}
                </p>
                <div class="space-y-4">
                  <div>
                    <label
                      class="mb-1 block text-sm font-medium text-foreground">
                      {{ t("policies.form.policyName") }}
                    </label>
                    <input
                      v-model="form.name"
                      type="text"
                      :placeholder="t('policies.basic.namePlaceholder')"
                      class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
                    <p class="mt-1 text-xs text-foreground-muted">
                      {{ t("policies.basic.nameDesc") }}
                    </p>
                  </div>
                  <div>
                    <label
                      class="mb-1 block text-sm font-medium text-foreground">
                      {{ t("policies.form.backupType") }}
                    </label>
                    <select
                      v-model="form.backup_type"
                      class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-violet-500">
                      <option value="incremental">Incremental</option>
                      <option value="full">Full</option>
                      <option value="differential">Differential</option>
                    </select>
                    <p class="mt-1 text-xs text-foreground-muted">
                      {{ t("policies.basic.backupTypeDesc") }}
                    </p>
                  </div>
                  <div>
                    <label
                      class="mb-1 block text-sm font-medium text-foreground">
                      {{ t("common.description") }}
                    </label>
                    <textarea
                      v-model="form.description"
                      rows="2"
                      :placeholder="t('policies.basic.descriptionPlaceholder')"
                      class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
                    <p class="mt-1 text-xs text-foreground-muted">
                      {{ t("policies.basic.descriptionDesc") }}
                    </p>
                  </div>
                  <label
                    class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground">
                    <input
                      v-model="form.is_active"
                      type="checkbox"
                      class="mt-1 h-4 w-4 rounded border-border text-violet-600 focus:ring-violet-500" />
                    <span>
                      <span class="font-medium">{{ t("common.enabled") }}</span>
                      <span
                        class="mt-1 block text-xs leading-5 text-foreground-muted">
                        {{ t("policies.basic.enabledDesc") }}
                      </span>
                    </span>
                  </label>
                </div>
              </section>

              <section class="rounded-lg border border-border bg-card p-4">
                <div class="mb-2 flex items-center gap-2">
                  <Cog6ToothIcon class="h-5 w-5 text-violet-600" />
                  <h3 class="font-semibold text-foreground">
                    {{ t("policies.target.title") }}
                  </h3>
                </div>
                <p class="mb-4 text-xs text-foreground-secondary">
                  {{ t("policies.target.description") }}
                </p>
                <div class="space-y-4">
                  <div>
                    <label
                      class="mb-1 block text-sm font-medium text-foreground">
                      {{ t("policies.target.title") }}
                    </label>
                    <select
                      v-model="form.policy_scope"
                      class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-violet-500">
                      <option value="global">
                        {{ t("policies.scopes.global") }}
                      </option>
                      <option value="host">
                        {{ t("policies.scopes.host") }}
                      </option>
                      <option value="user">
                        {{ t("policies.scopes.user") }}
                      </option>
                      <option value="path">
                        {{ t("policies.scopes.path") }}
                      </option>
                    </select>
                    <p class="mt-1 text-xs text-foreground-muted">
                      {{
                        t(
                          `policies.target.scopeDescriptions.${form.policy_scope}`,
                        )
                      }}
                    </p>
                  </div>
                </div>
                <div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
                  <div v-if="form.policy_scope !== 'global'">
                    <label
                      class="mb-1 block text-sm font-medium text-foreground">
                      {{ t("policies.target.host") }}
                    </label>
                    <input
                      v-model="form.target_host"
                      type="text"
                      class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500" />
                    <p class="mt-1 text-xs text-foreground-muted">
                      {{ t("policies.target.hostDesc") }}
                    </p>
                  </div>
                  <div v-if="['user', 'path'].includes(form.policy_scope)">
                    <label
                      class="mb-1 block text-sm font-medium text-foreground">
                      {{ t("policies.target.user") }}
                    </label>
                    <input
                      v-model="form.target_user"
                      type="text"
                      class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500" />
                    <p class="mt-1 text-xs text-foreground-muted">
                      {{ t("policies.target.userDesc") }}
                    </p>
                  </div>
                  <div v-if="form.policy_scope === 'path'">
                    <label
                      class="mb-1 block text-sm font-medium text-foreground">
                      {{ t("policies.target.path") }}
                    </label>
                    <input
                      v-model="form.target_path"
                      type="text"
                      placeholder="/data"
                      class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500" />
                    <p class="mt-1 text-xs text-foreground-muted">
                      {{ t("policies.target.pathDesc") }}
                    </p>
                  </div>
                </div>
              </section>

              <section class="rounded-lg border border-border bg-card p-4">
                <div class="mb-2 flex items-center gap-2">
                  <CalendarIcon class="h-5 w-5 text-violet-600" />
                  <h3 class="font-semibold text-foreground">
                    {{ t("policies.schedule.title") }}
                  </h3>
                </div>
                <p class="mb-4 text-xs text-foreground-secondary">
                  {{ t("policies.schedule.description") }}
                </p>
                <div class="space-y-4">
                  <div>
                    <label
                      class="mb-1 block text-sm font-medium text-foreground">
                      {{ t("policies.schedule.title") }}
                    </label>
                    <select
                      v-model="form.schedule_mode"
                      class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500">
                      <option value="manual">
                        {{ t("policies.scheduleModes.manual") }}
                      </option>
                      <option value="interval">
                        {{ t("policies.scheduleModes.interval") }}
                      </option>
                      <option value="time">
                        {{ t("policies.scheduleModes.time") }}
                      </option>
                      <option value="cron">
                        {{ t("policies.scheduleModes.cron") }}
                      </option>
                    </select>
                    <p class="mt-1 text-xs text-foreground-muted">
                      {{
                        t(
                          `policies.schedule.modeDescriptions.${form.schedule_mode}`,
                        )
                      }}
                    </p>
                  </div>
                  <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <div v-if="form.schedule_mode === 'interval'">
                      <label
                        class="mb-1 block text-sm font-medium text-foreground">
                        {{ t("policies.schedule.interval") }}
                      </label>
                      <input
                        v-model="form.interval"
                        type="text"
                        placeholder="24h"
                        class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500" />
                      <p class="mt-1 text-xs text-foreground-muted">
                        {{ t("policies.schedule.intervalDesc") }}
                      </p>
                    </div>
                    <div
                      v-if="['interval', 'time'].includes(form.schedule_mode)">
                      <label
                        class="mb-1 block text-sm font-medium text-foreground">
                        {{ t("policies.schedule.timeOfDay") }}
                      </label>
                      <input
                        v-model="form.time_of_day"
                        type="time"
                        class="w-full rounded-lg border border-border bg-background px-3 py-2 text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500" />
                      <p class="mt-1 text-xs text-foreground-muted">
                        {{ t("policies.schedule.timeOfDayDesc") }}
                      </p>
                    </div>
                    <div
                      v-if="form.schedule_mode === 'cron'"
                      class="md:col-span-2">
                      <label
                        class="mb-1 block text-sm font-medium text-foreground">
                        {{ t("policies.schedule.cron") }}
                      </label>
                      <input
                        v-model="form.cron"
                        type="text"
                        placeholder="0 2 * * *"
                        class="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-foreground placeholder:text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
                      <p class="mt-1 text-xs text-foreground-muted">
                        {{ t("policies.schedule.cronDesc") }}
                      </p>
                    </div>
                  </div>
                  <label
                    class="flex items-start gap-3 rounded-lg border border-border bg-background/50 p-3 text-sm text-foreground">
                    <input
                      v-model="form.run_missed"
                      type="checkbox"
                      class="mt-1 h-4 w-4 rounded border-border text-violet-600 focus:ring-violet-500" />
                    <span>
                      <span class="font-medium">
                        {{ t("policies.schedule.runMissed") }}
                      </span>
                      <span
                        class="mt-1 block text-xs leading-5 text-foreground-muted">
                        {{ t("policies.schedule.runMissedDesc") }}
                      </span>
                    </span>
                  </label>
                </div>
              </section>

              <section class="rounded-lg border border-border bg-card p-4">
                <div class="mb-2 flex items-center gap-2">
                  <ShieldCheckIcon class="h-5 w-5 text-violet-600" />
                  <h3 class="font-semibold text-foreground">
                    {{ t("policies.retention.title") }}
                  </h3>
                </div>
                <p class="mb-4 text-xs text-foreground-secondary">
                  {{ t("policies.retention.description") }}
                </p>
                <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div
                    v-for="field in retentionFields"
                    :key="field.key"
                    class="rounded-lg border border-border bg-background/50 p-3">
                    <label
                      class="mb-2 block text-sm font-medium text-foreground">
                      {{ t(`policies.retention.${field.label}`) }}
                    </label>
                    <input
                      v-model.number="form[field.key]"
                      type="number"
                      min="0"
                      class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
                    <p class="mt-2 text-xs leading-5 text-foreground-muted">
                      {{ t(`policies.retention.${field.description}`) }}
                    </p>
                  </div>
                </div>
              </section>
            </div>

            <aside
              class="border-t border-border bg-background-secondary p-6 xl:sticky xl:top-0 xl:max-h-full xl:self-start xl:overflow-y-auto xl:border-l xl:border-t-0">
              <h3 class="font-semibold text-foreground">
                {{ t("policies.preview.title") }}
              </h3>
              <p class="mt-1 text-sm text-foreground-secondary">
                {{ t("policies.preview.description") }}
              </p>
              <div class="mt-4 space-y-3 text-sm">
                <div class="rounded-lg border border-border bg-card p-3">
                  <p class="text-xs text-foreground-muted">
                    {{ t("policies.target.title") }}
                  </p>
                  <p class="mt-1 break-all font-mono text-foreground">
                    {{ buildKopiaTargetFromForm() }}
                  </p>
                </div>
                <div class="rounded-lg border border-border bg-card p-3">
                  <p class="text-xs text-foreground-muted">
                    {{ t("policies.retention.title") }}
                  </p>
                  <p class="mt-1 text-foreground">{{ retentionPreview }}</p>
                </div>
                <pre
                  class="max-h-[420px] overflow-auto rounded-lg border border-border bg-slate-950 p-3 text-xs text-slate-100"
                  >{{ policyPreviewCommand }}</pre
                >
              </div>
            </aside>
          </div>

          <div
            class="flex items-center justify-end gap-3 border-t border-border px-6 py-4">
            <button
              @click="showPolicyModal = false"
              class="rounded-lg border border-border px-4 py-2 text-sm text-foreground-secondary hover:bg-hover">
              {{ t("common.cancel") }}
            </button>
            <button
              @click="savePolicy"
              :disabled="isSaving"
              class="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50">
              <ArrowPathIcon v-if="isSaving" class="h-4 w-4 animate-spin" />
              {{ t("common.save") }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
