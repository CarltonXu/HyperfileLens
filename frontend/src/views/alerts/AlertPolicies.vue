<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  BellAlertIcon,
  DocumentDuplicateIcon,
  MagnifyingGlassIcon,
  PencilSquareIcon,
  PlusIcon,
  PowerIcon,
  TrashIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";
import { alertsApi } from "@/api";
import { useAppStore } from "@/stores/app";
import { getApiErrorMessage } from "@/utils/errors";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";
import AlertSeverityTag from "@/components/alerts/AlertSeverityTag.vue";
import AlertTypeTag from "@/components/alerts/AlertTypeTag.vue";
import AvailabilityRuleForm from "@/components/alerts/AvailabilityRuleForm.vue";
import EventRuleForm from "@/components/alerts/EventRuleForm.vue";
import JobRuleForm from "@/components/alerts/JobRuleForm.vue";
import MetricRuleForm from "@/components/alerts/MetricRuleForm.vue";
import NotificationChannelSelector from "@/components/alerts/NotificationChannelSelector.vue";
import RecoveryRuleForm from "@/components/alerts/RecoveryRuleForm.vue";
import ResourceSelector from "@/components/alerts/ResourceSelector.vue";
import SystemRuleForm from "@/components/alerts/SystemRuleForm.vue";

interface AlertPolicy {
  id: string;
  name: string;
  description?: string;
  type: string;
  severity: string;
  resource_type: string;
  scope: string;
  enabled: boolean;
  notification_channels: Array<{ id: string; name: string }>;
  created_at: string;
  updated_at: string;
}

const router = useRouter();
const { t } = useI18n();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();
const loading = ref(false);
const saving = ref(false);
const showCreate = ref(false);
const policies = ref<AlertPolicy[]>([]);
const metrics = ref<string[]>([]);
const resourceTypes = ref<Array<{ value: string; label: string }>>([]);
const targetResources = ref<
  Array<{ id: string; name: string; status?: string }>
>([]);
const targetResourcesLoading = ref(false);
const channels = ref<
  Array<{ id: string; name: string; type: string; enabled: boolean }>
>([]);
const pagination = reactive({
  page: 1,
  page_size: getPageSize("alert-policies"),
  count: 0,
});
const PAGE_STORAGE_KEY = "alert-policies";
const filters = reactive({ search: "", type: "", severity: "", enabled: "" });

watch(
  () => pagination.page_size,
  (newSize) => {
    setPageSize(newSize, PAGE_STORAGE_KEY);
  },
);

const form = reactive({
  name: "",
  description: "",
  type: "metric",
  severity: "warning",
  enabled: true,
  resource_type: "sync_proxy",
  scope: "selected",
  resource_ids: [] as string[],
  trigger_rule: {} as Record<string, any>,
  recovery_rule: { enabled: true } as Record<string, any>,
  notification_channel_ids: [] as string[],
});

const notificationOptions = reactive({
  notify_on_trigger: "yes",
  notify_on_recovery: "yes",
});

const stats = computed(() => ({
  total: pagination.count,
  enabled: policies.value.filter((item) => item.enabled).length,
  critical: policies.value.filter((item) => item.severity === "critical")
    .length,
  channels: new Set(
    policies.value.flatMap((item) =>
      (item.notification_channels || []).map((channel) => channel.id),
    ),
  ).size,
}));

const selectedChannelNames = computed(() => {
  const selected = new Set(form.notification_channel_ids);
  return channels.value
    .filter((channel) => selected.has(channel.id))
    .map((channel) => channel.name);
});

type AlertPolicyColumnKey =
  | "name"
  | "type"
  | "severity"
  | "resource_type"
  | "scope"
  | "enabled"
  | "notification_channels"
  | "actions";

const alertPolicyColumns = computed(() => [
  {
    key: "name" as const,
    label: t("alertsCenter.common.name"),
    min: 220,
    max: 520,
  },
  {
    key: "type" as const,
    label: t("alertsCenter.common.type"),
    min: 120,
    max: 240,
  },
  {
    key: "severity" as const,
    label: t("alertsCenter.common.severity"),
    min: 120,
    max: 220,
  },
  {
    key: "resource_type" as const,
    label: t("alertsCenter.policies.targetColumn"),
    min: 150,
    max: 320,
  },
  {
    key: "scope" as const,
    label: t("alertsCenter.policies.scope"),
    min: 110,
    max: 220,
  },
  {
    key: "enabled" as const,
    label: t("alertsCenter.common.status"),
    min: 120,
    max: 220,
  },
  {
    key: "notification_channels" as const,
    label: t("alertsCenter.policies.notificationColumn"),
    min: 220,
    max: 520,
  },
  {
    key: "actions" as const,
    label: t("alertsCenter.common.actions"),
    min: 150,
    max: 220,
    sortable: false,
    align: "right" as const,
  },
]);

const alertPolicyTable = useResizableSortableTable<
  AlertPolicy,
  AlertPolicyColumnKey
>({
  storageKey: "hyperfilelens:alert-policies:columnWidths",
  columns: alertPolicyColumns,
  rows: policies,
  defaultSort: { key: "name" },
  minTableWidth: 1040,
  getSortValue: (policy, key) => {
    if (key === "notification_channels") {
      return (policy.notification_channels || [])
        .map((channel) => channel.name)
        .join(", ");
    }
    if (key === "enabled") return policy.enabled ? 1 : 0;
    if (key === "actions") return "";
    return policy[key] ?? "";
  },
  getColumnText: (policy, key) => {
    if (key === "notification_channels") {
      return (
        (policy.notification_channels || [])
          .map((channel) => channel.name)
          .join(", ") || "-"
      );
    }
    if (key === "enabled") {
      return policy.enabled
        ? t("alertsCenter.values.enabled")
        : t("alertsCenter.values.disabled");
    }
    if (key === "actions") return t("alertsCenter.common.actions");
    return String(policy[key] ?? "");
  },
});

const previewRuleText = computed(() => {
  const rule = form.trigger_rule || {};
  if (form.type === "metric") {
    return t("alertsCenter.preview.metricRule", {
      metric: rule.metric_key || "metric",
      operator: rule.operator || ">=",
      threshold: rule.threshold ?? "-",
      unit: rule.unit || "",
      duration: formatDuration(rule.duration_seconds),
    });
  }
  if (form.type === "availability") {
    return t("alertsCenter.preview.availabilityRule", {
      checkType: rule.check_type || "heartbeat",
      timeout: rule.timeout_seconds || "-",
      duration: formatDuration(rule.duration_seconds),
    });
  }
  if (form.type === "job") {
    return t("alertsCenter.preview.jobRule", {
      jobType: rule.job_type || "job",
      eventType: rule.event_type || "job_failed",
      count: rule.consecutive_failures || 1,
    });
  }
  if (form.type === "event") {
    return `${rule.event_category || "event"}: ${(rule.event_types || []).join(", ") || "-"}`;
  }
  return t("alertsCenter.preview.systemRule", {
    serviceName: rule.service_name || t("alertsCenter.preview.systemService"),
    checkType: rule.check_type || "service_health",
    duration: formatDuration(rule.duration_seconds),
  });
});

const previewRecoveryText = computed(() => {
  const rule = form.recovery_rule || {};
  if (!rule.enabled) return t("alertsCenter.policies.manualResolveOnly");
  const condition = rule.recovery_condition || "below_threshold";
  const threshold =
    rule.threshold !== undefined && rule.threshold !== ""
      ? ` ${rule.operator || "<"} ${rule.threshold}`
      : "";
  return `${condition}${threshold} for ${formatDuration(rule.duration_seconds)}`;
});

const usesConcreteMonitorTarget = computed(
  () => !["job", "event"].includes(form.type),
);

function ruleDefaults(type: string) {
  if (type === "metric")
    return {
      metric_key: metrics.value[0] || "cpu_usage",
      operator: ">=",
      threshold: 80,
      unit: "%",
      duration_seconds: 300,
      evaluation_interval_seconds: 60,
    };
  if (type === "availability")
    return {
      check_type: "heartbeat",
      timeout_seconds: 60,
      duration_seconds: 300,
    };
  if (type === "job")
    return {
      job_type: "backup",
      event_type: "job_failed",
      consecutive_failures: 1,
    };
  if (type === "event")
    return {
      event_category: "user",
      event_types: ["user_deleted", "login_failed"],
    };
  return {
    check_type: "service_health",
    service_name: "celery_worker",
    duration_seconds: 300,
  };
}

function resetForm() {
  Object.assign(form, {
    name: "",
    description: "",
    type: "metric",
    severity: "warning",
    enabled: true,
    resource_type: "sync_proxy",
    scope: "selected",
    resource_ids: [],
    trigger_rule: ruleDefaults("metric"),
    recovery_rule: {
      enabled: true,
      operator: "<",
      threshold: 70,
      duration_seconds: 180,
      recovery_condition: "below_threshold",
    },
    notification_channel_ids: [],
  });
  Object.assign(notificationOptions, {
    notify_on_trigger: "yes",
    notify_on_recovery: "yes",
  });
}

function openCreate() {
  resetForm();
  showCreate.value = true;
}

async function fetchPolicies() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {
      page: pagination.page,
      page_size: pagination.page_size,
    };
    if (filters.search) params.search = filters.search;
    if (filters.type) params.type = filters.type;
    if (filters.severity) params.severity = filters.severity;
    if (filters.enabled) params.enabled = filters.enabled;
    const res = await alertsApi.policies(params);
    policies.value = res.data.results || res.data;
    pagination.count = res.data.count ?? policies.value.length;
  } finally {
    loading.value = false;
  }
}

async function loadOptions() {
  const [resourceRes, channelRes] = await Promise.all([
    alertsApi.metadata("resource-types"),
    alertsApi.notificationChannels({ page_size: 300 }),
  ]);
  resourceTypes.value = resourceRes.data || [];
  channels.value = channelRes.data.results || channelRes.data || [];
}

async function fetchTargetResources() {
  if (!usesConcreteMonitorTarget.value) {
    targetResources.value = [];
    return;
  }
  targetResourcesLoading.value = true;
  try {
    const res = await alertsApi.metadataResources({
      resource_type: form.resource_type,
    });
    targetResources.value = res.data || [];
    const validIds = new Set(targetResources.value.map((item) => item.id));
    form.resource_ids = form.resource_ids.filter((id) => validIds.has(id));
  } finally {
    targetResourcesLoading.value = false;
  }
}

async function remove(policy: AlertPolicy) {
  if (
    !window.confirm(
      t("alertsCenter.policies.deleteConfirm", { name: policy.name }),
    )
  )
    return;
  await alertsApi.deletePolicy(policy.id);
  await fetchPolicies();
}

async function toggle(policy: AlertPolicy) {
  if (policy.enabled) await alertsApi.disablePolicy(policy.id);
  else await alertsApi.enablePolicy(policy.id);
  await fetchPolicies();
}

async function duplicate(policy: AlertPolicy) {
  try {
    await alertsApi.duplicatePolicy(policy.id);
    await fetchPolicies();
  } catch (err) {
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(err, t("common.createFailed")),
    });
  }
}

async function submitCreate() {
  saving.value = true;
  try {
    await alertsApi.createPolicy({
      name: form.name,
      description: form.description,
      type: form.type,
      severity: form.severity,
      enabled: form.enabled,
      resource_type: form.resource_type,
      scope: form.scope,
      resource_ids: form.resource_ids,
      trigger_rule: form.trigger_rule,
      recovery_rule: form.recovery_rule,
      notification_channel_ids: form.notification_channel_ids,
    });
    showCreate.value = false;
    await fetchPolicies();
  } catch (err) {
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(err, t("common.createFailed")),
    });
  } finally {
    saving.value = false;
  }
}

function formatDuration(seconds?: number) {
  if (!seconds) return "-";
  if (seconds % 60 !== 0)
    return t("alertsCenter.duration.seconds", { count: seconds });
  const minutes = seconds / 60;
  return t("alertsCenter.duration.minutes", { count: minutes });
}

function applyFilters() {
  pagination.page = 1;
  fetchPolicies();
}

watch(
  () => form.type,
  (type) => {
    form.trigger_rule = ruleDefaults(type);
    form.recovery_rule =
      type === "event"
        ? { enabled: false }
        : {
            enabled: true,
            operator: "<",
            threshold: 70,
            duration_seconds: 180,
            recovery_condition:
              type === "job" ? "next_success" : "below_threshold",
          };
    if (type === "job") {
      form.resource_type = "job";
      form.scope = "all";
      form.resource_ids = [];
    } else if (type === "event") {
      form.resource_type = "license";
      form.scope = "all";
      form.resource_ids = [];
    } else if (type === "system") {
      form.resource_type = "system_service";
      form.scope = "all";
      form.resource_ids = [];
    } else if (
      type === "availability" &&
      ![
        "sync_proxy",
        "agent_proxy",
        "gateway",
        "backup_repository",
        "source_resource",
        "target_storage",
      ].includes(form.resource_type)
    ) {
      form.resource_type = "sync_proxy";
      form.scope = "selected";
    } else if (
      type === "metric" &&
      ![
        "sync_proxy",
        "gateway",
        "agent_proxy",
        "backup_repository",
        "source_resource",
        "target_storage",
      ].includes(form.resource_type)
    ) {
      form.resource_type = "sync_proxy";
      form.scope = "selected";
    }
  },
);

watch(
  () => form.resource_type,
  async () => {
    const res = await alertsApi.metadata("metrics", {
      resource_type: form.resource_type,
    });
    metrics.value = res.data || [];
    if (
      form.type === "metric" &&
      metrics.value.length &&
      !metrics.value.includes(form.trigger_rule.metric_key)
    ) {
      form.trigger_rule.metric_key = metrics.value[0];
    }
    await fetchTargetResources();
  },
  { immediate: true },
);

watch(
  () => form.scope,
  (scope) => {
    if (scope === "all") {
      form.resource_ids = [];
    }
  },
);

onMounted(async () => {
  resetForm();
  await Promise.all([loadOptions(), fetchPolicies()]);
});
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-start gap-3">
        <div
          class="flex h-11 w-11 items-center justify-center rounded-lg bg-primary text-white shadow-sm"
        >
          <BellAlertIcon class="h-6 w-6" />
        </div>
        <div>
          <h1 class="text-2xl font-semibold text-foreground">
            {{ $t("alertsCenter.policies.title") }}
          </h1>
          <p class="mt-1 max-w-3xl text-sm text-foreground-secondary">
            {{ $t("alertsCenter.policies.subtitle") }}
          </p>
        </div>
      </div>
      <div class="flex gap-2">
        <button
          @click="fetchPolicies"
          class="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground shadow-sm hover:bg-hover"
        >
          <ArrowPathIcon class="h-4 w-4" />
          {{ $t("common.refresh") }}
        </button>
        <button
          @click="openCreate"
          class="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-hover"
        >
          <PlusIcon class="h-4 w-4" />
          {{ t("alertsCenter.common.createAlertPolicy") }}
        </button>
      </div>
    </div>

    <div class="grid gap-3 md:grid-cols-4">
      <div class="rounded-lg border border-border p-4 shadow-sm">
        <p class="text-xs font-medium uppercase text-foreground-secondary">
          {{ t("alertsCenter.common.policies") }}
        </p>
        <p class="mt-2 text-2xl font-semibold text-foreground">
          {{ stats.total }}
        </p>
      </div>
      <div class="rounded-lg border border-border p-4 shadow-sm">
        <p class="text-xs font-medium uppercase text-foreground-secondary">
          {{ t("alertsCenter.common.enabled") }}
        </p>
        <p class="mt-2 text-2xl font-semibold text-emerald-600">
          {{ stats.enabled }}
        </p>
      </div>
      <div class="rounded-lg border border-border p-4 shadow-sm">
        <p class="text-xs font-medium uppercase text-foreground-secondary">
          {{ t("alertsCenter.common.critical") }}
        </p>
        <p class="mt-2 text-2xl font-semibold text-red-600">
          {{ stats.critical }}
        </p>
      </div>
      <div class="rounded-lg border border-border p-4 shadow-sm">
        <p class="text-xs font-medium uppercase text-foreground-secondary">
          {{ t("alertsCenter.common.linkedChannels") }}
        </p>
        <p class="mt-2 text-2xl font-semibold text-foreground">
          {{ stats.channels }}
        </p>
      </div>
    </div>

    <div
      class="grid gap-3 rounded-lg border border-border p-4 shadow-sm md:grid-cols-5"
    >
      <div class="relative md:col-span-2">
        <MagnifyingGlassIcon
          class="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-foreground-muted"
        />
        <input
          v-model="filters.search"
          @keyup.enter="applyFilters"
          class="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          :placeholder="t('alertsCenter.policies.searchPlaceholder')"
        />
      </div>
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
      <select
        v-model="filters.enabled"
        @change="applyFilters"
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
      >
        <option value="">{{ t("alertsCenter.common.allStatus") }}</option>
        <option value="true">{{ t("alertsCenter.values.enabled") }}</option>
        <option value="false">{{ t("alertsCenter.values.disabled") }}</option>
      </select>
    </div>

    <div class="overflow-hidden rounded-lg border border-border shadow-sm">
      <div class="overflow-x-auto">
        <table
          class="w-full table-fixed text-left text-sm"
          :style="{ minWidth: alertPolicyTable.tableMinWidth.value }"
        >
          <colgroup>
            <col
              v-for="column in alertPolicyColumns"
              :key="column.key"
              :style="alertPolicyTable.columnStyle(column.key)"
            />
          </colgroup>
          <thead
            class="border-b border-border bg-background bg-background-secondary text-xs uppercase text-foreground-secondary"
          >
            <tr>
              <ResizableSortableTh
                v-for="column in alertPolicyColumns"
                :key="column.key"
                :column-key="column.key"
                :label="column.label"
                :style-value="alertPolicyTable.columnStyle(column.key)"
                :sortable="column.sortable !== false"
                :active="alertPolicyTable.sort.value.key === column.key"
                :align="column.align"
                :sort-icon="alertPolicyTable.getSortIcon(column.key)"
                :resizing="alertPolicyTable.resizingColumn.value === column.key"
                @sort="
                  alertPolicyTable.toggleSort($event as AlertPolicyColumnKey)
                "
                @resize-start="
                  (key, event) =>
                    alertPolicyTable.startResize(
                      key as AlertPolicyColumnKey,
                      event,
                    )
                "
                @resize-reset="
                  alertPolicyTable.resetColumnWidth(
                    $event as AlertPolicyColumnKey,
                  )
                "
              />
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr
              v-for="policy in alertPolicyTable.sortedRows.value"
              :key="policy.id"
              class="hover:bg-hover"
            >
              <td
                class="px-4 py-4"
                :style="alertPolicyTable.columnStyle('name')"
              >
                <div class="font-medium text-foreground">{{ policy.name }}</div>
                <div class="mt-0.5 text-xs text-foreground-secondary">
                  {{ t("alertsCenter.policies.updated") }}
                  {{
                    new Date(
                      policy.updated_at || policy.created_at,
                    ).toLocaleString()
                  }}
                </div>
              </td>
              <td
                class="px-4 py-4"
                :style="alertPolicyTable.columnStyle('type')"
              >
                <AlertTypeTag :type="policy.type" />
              </td>
              <td
                class="px-4 py-4"
                :style="alertPolicyTable.columnStyle('severity')"
              >
                <AlertSeverityTag :severity="policy.severity" />
              </td>
              <td
                class="px-4 py-4 text-foreground-secondary"
                :style="alertPolicyTable.columnStyle('resource_type')"
              >
                {{ policy.resource_type }}
              </td>
              <td
                class="px-4 py-4 text-foreground-secondary"
                :style="alertPolicyTable.columnStyle('scope')"
              >
                {{ policy.scope }}
              </td>
              <td
                class="px-4 py-4"
                :style="alertPolicyTable.columnStyle('enabled')"
              >
                <span
                  class="inline-flex rounded-full border px-2 py-0.5 text-xs font-medium"
                  :class="
                    policy.enabled
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300'
                      : 'border-border bg-background text-foreground-secondary'
                  "
                >
                  {{
                    policy.enabled
                      ? t("alertsCenter.values.enabled")
                      : t("alertsCenter.values.disabled")
                  }}
                </span>
              </td>
              <td
                :style="alertPolicyTable.columnStyle('notification_channels')"
                class="max-w-[220px] truncate px-4 py-4 text-foreground-secondary"
              >
                {{
                  (policy.notification_channels || [])
                    .map((c) => c.name)
                    .join(", ") || "-"
                }}
              </td>
              <td
                class="px-4 py-4"
                :style="alertPolicyTable.columnStyle('actions')"
              >
                <div class="flex justify-end gap-1">
                  <button
                    :title="$t('common.edit')"
                    @click="router.push(`/alerts/policies/${policy.id}/edit`)"
                    class="rounded-lg p-2 text-foreground-secondary hover:bg-hover hover:text-foreground"
                  >
                    <PencilSquareIcon class="h-4 w-4" />
                  </button>
                  <button
                    :title="t('alertsCenter.common.duplicate')"
                    @click="duplicate(policy)"
                    class="rounded-lg p-2 text-foreground-secondary hover:bg-hover hover:text-foreground"
                  >
                    <DocumentDuplicateIcon class="h-4 w-4" />
                  </button>
                  <button
                    :title="t('alertsCenter.common.enableDisable')"
                    @click="toggle(policy)"
                    class="rounded-lg p-2 text-foreground-secondary hover:bg-hover hover:text-foreground"
                  >
                    <PowerIcon class="h-4 w-4" />
                  </button>
                  <button
                    :title="$t('common.delete')"
                    @click="remove(policy)"
                    class="rounded-lg p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10"
                  >
                    <TrashIcon class="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="!loading && policies.length === 0">
              <td
                colspan="8"
                class="px-4 py-12 text-center text-sm text-foreground-secondary"
              >
                {{ $t("common.noData") }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div
      v-if="showCreate"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <div class="absolute inset-0 bg-black/55" @click="showCreate = false" />
      <form
        class="relative flex max-h-[92vh] w-full max-w-7xl flex-col overflow-hidden rounded-lg border border-border bg-background shadow-2xl"
        @submit.prevent="submitCreate"
      >
        <div
          class="flex items-start justify-between gap-4 border-b border-border px-5 py-4"
        >
          <div>
            <h2 class="text-lg font-semibold text-foreground">
              {{ t("alertsCenter.common.createAlertPolicy") }}
            </h2>
            <p class="mt-1 text-sm text-foreground-secondary">
              {{ t("alertsCenter.policies.createDesc") }}
            </p>
          </div>
          <button
            type="button"
            @click="showCreate = false"
            class="rounded-lg p-2 text-foreground-secondary hover:bg-hover hover:text-foreground"
          >
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <div
          class="grid flex-1 gap-5 overflow-auto p-5 lg:grid-cols-[minmax(0,1fr)_340px]"
        >
          <div class="space-y-5">
            <section class="rounded-lg border border-border p-5">
              <div class="mb-4">
                <h3 class="text-base font-semibold text-foreground">
                  {{ t("alertsCenter.policies.basicInfo") }}
                </h3>
                <p class="mt-1 text-sm text-foreground-secondary">
                  {{ t("alertsCenter.policies.basicInfoDesc") }}
                </p>
              </div>
              <div class="mt-4 grid gap-4 md:grid-cols-2">
                <label class="space-y-2"
                  ><span class="text-sm font-medium text-foreground">{{
                    t("alertsCenter.policies.alertName")
                  }}</span
                  ><input
                    v-model="form.name"
                    required
                    class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                    :placeholder="
                      t('alertsCenter.policies.alertNamePlaceholder')
                    "
                /></label>
                <label class="space-y-2"
                  ><span class="text-sm font-medium text-foreground">{{
                    t("alertsCenter.policies.alertType")
                  }}</span
                  ><select
                    v-model="form.type"
                    class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="metric">
                      {{ t("alertsCenter.values.metric") }}
                    </option>
                    <option value="availability">
                      {{ t("alertsCenter.values.availability") }}
                    </option>
                    <option value="job">
                      {{ t("alertsCenter.values.job") }}
                    </option>
                    <option value="event">
                      {{ t("alertsCenter.values.event") }}
                    </option>
                    <option value="system">
                      {{ t("alertsCenter.values.system") }}
                    </option>
                  </select></label
                >
                <label class="space-y-2"
                  ><span class="text-sm font-medium text-foreground">{{
                    t("alertsCenter.common.severity")
                  }}</span
                  ><select
                    v-model="form.severity"
                    class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="critical">
                      {{ t("alertsCenter.values.critical") }}
                    </option>
                    <option value="warning">
                      {{ t("alertsCenter.values.warning") }}
                    </option>
                    <option value="info">
                      {{ t("alertsCenter.values.info") }}
                    </option>
                  </select></label
                >
                <div class="space-y-2">
                  <span class="text-sm font-medium text-foreground">{{
                    t("alertsCenter.common.status")
                  }}</span>
                  <button
                    type="button"
                    role="switch"
                    :aria-checked="form.enabled"
                    @click="form.enabled = !form.enabled"
                    class="flex h-10 w-full items-center justify-between rounded-lg border border-border bg-background px-3 text-sm text-foreground"
                  >
                    <span>{{
                      form.enabled
                        ? t("alertsCenter.values.enabled")
                        : t("alertsCenter.values.disabled")
                    }}</span>
                    <span
                      class="relative h-6 w-11 rounded-full transition-colors"
                      :class="
                        form.enabled
                          ? 'bg-primary'
                          : 'bg-background-tertiary border border-border'
                      "
                    >
                      <span
                        class="absolute left-0 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform"
                        :class="
                          form.enabled ? 'translate-x-5' : 'translate-x-0.5'
                        "
                      />
                    </span>
                  </button>
                </div>
                <label class="space-y-2 md:col-span-2"
                  ><span class="text-sm font-medium text-foreground">{{
                    t("alertsCenter.policies.description")
                  }}</span
                  ><textarea
                    v-model="form.description"
                    rows="3"
                    class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                    :placeholder="
                      t('alertsCenter.policies.descriptionPlaceholder')
                    "
                  />
                </label>
              </div>
            </section>

            <section class="rounded-lg border border-border p-5">
              <div class="mb-4">
                <h3 class="text-base font-semibold text-foreground">
                  {{ t("alertsCenter.policies.monitorTarget") }}
                </h3>
                <p class="mt-1 text-sm text-foreground-secondary">
                  <span v-if="usesConcreteMonitorTarget">{{
                    t("alertsCenter.policies.monitorTargetDesc")
                  }}</span>
                  <span v-else>{{
                    t("alertsCenter.policies.monitorTargetEventDesc")
                  }}</span>
                </p>
              </div>
              <div class="mt-4">
                <ResourceSelector
                  v-model:resource-type="form.resource_type"
                  v-model:scope="form.scope"
                  v-model:resource-ids="form.resource_ids"
                  :resource-types="resourceTypes"
                  :resources="targetResources"
                  :loading="targetResourcesLoading"
                  :disabled="!usesConcreteMonitorTarget"
                  @refresh="fetchTargetResources"
                />
              </div>
              <div
                v-if="!usesConcreteMonitorTarget"
                class="mt-3 rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground-secondary"
              >
                {{
                  form.type === "job"
                    ? t("alertsCenter.policies.jobTargetHint")
                    : t("alertsCenter.policies.eventTargetHint")
                }}
              </div>
            </section>

            <section class="rounded-lg border border-border p-5">
              <div class="mb-4">
                <h3 class="text-base font-semibold text-foreground">
                  {{ t("alertsCenter.policies.triggerRule") }}
                </h3>
                <p class="mt-1 text-sm text-foreground-secondary">
                  {{ t("alertsCenter.policies.triggerRuleDesc") }}
                </p>
              </div>
              <div class="mt-4">
                <MetricRuleForm
                  v-if="form.type === 'metric'"
                  v-model="form.trigger_rule"
                  :metrics="metrics"
                />
                <AvailabilityRuleForm
                  v-else-if="form.type === 'availability'"
                  v-model="form.trigger_rule"
                />
                <JobRuleForm
                  v-else-if="form.type === 'job'"
                  v-model="form.trigger_rule"
                />
                <EventRuleForm
                  v-else-if="form.type === 'event'"
                  v-model="form.trigger_rule"
                />
                <SystemRuleForm v-else v-model="form.trigger_rule" />
              </div>
            </section>

            <section class="rounded-lg border border-border p-5">
              <div class="mb-4">
                <h3 class="text-base font-semibold text-foreground">
                  {{ t("alertsCenter.policies.recoveryRule") }}
                </h3>
                <p class="mt-1 text-sm text-foreground-secondary">
                  {{ t("alertsCenter.policies.recoveryRuleDesc") }}
                </p>
              </div>
              <div class="mt-4">
                <RecoveryRuleForm v-model="form.recovery_rule" />
              </div>
            </section>

            <section class="rounded-lg border border-border p-5">
              <div class="mb-4">
                <h3 class="text-base font-semibold text-foreground">
                  {{ t("alertsCenter.policies.notification") }}
                </h3>
                <p class="mt-1 text-sm text-foreground-secondary">
                  {{ t("alertsCenter.policies.notificationDesc") }}
                </p>
              </div>
              <div class="mt-4 grid gap-4 lg:grid-cols-3">
                <div class="space-y-2">
                  <p class="mb-2 text-sm font-medium text-foreground">
                    {{ t("alertsCenter.policies.notificationChannels") }}
                  </p>
                  <NotificationChannelSelector
                    v-model="form.notification_channel_ids"
                    :channels="channels"
                  />
                </div>
                <label class="space-y-2">
                  <span class="text-sm font-medium text-foreground">{{
                    t("alertsCenter.policies.notifyOnTrigger")
                  }}</span>
                  <select
                    v-model="notificationOptions.notify_on_trigger"
                    class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="yes">
                      {{ t("alertsCenter.policies.yes") }}
                    </option>
                    <option value="no">
                      {{ t("alertsCenter.policies.no") }}
                    </option>
                  </select>
                </label>
                <label class="space-y-2">
                  <span class="text-sm font-medium text-foreground">{{
                    t("alertsCenter.policies.notifyOnRecovery")
                  }}</span>
                  <select
                    v-model="notificationOptions.notify_on_recovery"
                    class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="yes">
                      {{ t("alertsCenter.policies.yes") }}
                    </option>
                    <option value="no">
                      {{ t("alertsCenter.policies.no") }}
                    </option>
                  </select>
                </label>
              </div>
            </section>
          </div>

          <aside
            class="sticky top-0 h-fit rounded-lg border border-border bg-background-secondary p-5"
          >
            <h3 class="font-semibold text-foreground">
              {{ t("alertsCenter.policies.policyPreview") }}
            </h3>
            <p class="mt-1 text-sm text-foreground-secondary">
              {{ t("alertsCenter.policies.policyPreviewDesc") }}
            </p>
            <div class="mt-4 space-y-3 text-sm text-foreground-secondary">
              <div class="rounded-lg bg-background p-3">
                <span
                  class="block text-xs font-medium uppercase text-foreground-muted"
                  >{{ t("alertsCenter.common.name") }}</span
                >
                <span class="mt-1 block font-medium text-foreground">{{
                  form.name || t("alertsCenter.policies.untitledPolicy")
                }}</span>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div class="rounded-lg bg-background p-3">
                  <span
                    class="block text-xs font-medium uppercase text-foreground-muted"
                    >{{ t("alertsCenter.common.type") }}</span
                  ><span class="mt-1 block text-foreground">{{
                    t(`alertsCenter.values.${form.type}`)
                  }}</span>
                </div>
                <div class="rounded-lg bg-background p-3">
                  <span
                    class="block text-xs font-medium uppercase text-foreground-muted"
                    >{{ t("alertsCenter.common.severity") }}</span
                  ><span class="mt-1 block text-foreground">{{
                    t(`alertsCenter.values.${form.severity}`)
                  }}</span>
                </div>
              </div>
              <div class="rounded-lg bg-background p-3">
                <span
                  class="block text-xs font-medium uppercase text-foreground-muted"
                  >{{ t("alertsCenter.common.target") }}</span
                >
                <span class="mt-1 block text-foreground"
                  >{{ form.resource_type }} / {{ form.scope }}</span
                >
                <span
                  v-if="form.resource_ids.length"
                  class="mt-1 block truncate text-xs"
                  >{{ form.resource_ids.join(", ") }}</span
                >
              </div>
              <div class="rounded-lg bg-background p-3">
                <span
                  class="block text-xs font-medium uppercase text-foreground-muted"
                  >{{ t("alertsCenter.policies.triggerRule") }}</span
                >
                <span class="mt-1 block text-foreground">{{
                  previewRuleText
                }}</span>
              </div>
              <div class="rounded-lg bg-background p-3">
                <span
                  class="block text-xs font-medium uppercase text-foreground-muted"
                  >{{ t("alertsCenter.policies.recovery") }}</span
                >
                <span class="mt-1 block text-foreground">{{
                  previewRecoveryText
                }}</span>
              </div>
              <div class="rounded-lg bg-background p-3">
                <span
                  class="block text-xs font-medium uppercase text-foreground-muted"
                  >{{ t("alertsCenter.policies.notification") }}</span
                >
                <span class="mt-1 block text-foreground">{{
                  selectedChannelNames.length
                    ? selectedChannelNames.join(", ")
                    : t("alertsCenter.common.noChannelSelected")
                }}</span>
                <span class="mt-1 block text-xs"
                  >{{ t("alertsCenter.policies.trigger") }}:
                  {{
                    t(
                      `alertsCenter.policies.${notificationOptions.notify_on_trigger}`,
                    )
                  }}
                  · {{ t("alertsCenter.policies.recovery") }}:
                  {{
                    t(
                      `alertsCenter.policies.${notificationOptions.notify_on_recovery}`,
                    )
                  }}</span
                >
              </div>
              <div class="rounded-lg bg-background p-3">
                <span
                  class="block text-xs font-medium uppercase text-foreground-muted"
                  >{{ t("alertsCenter.common.status") }}</span
                >
                <span class="mt-1 block text-foreground">{{
                  form.enabled
                    ? t("alertsCenter.policies.saveAsEnabled")
                    : t("alertsCenter.policies.saveAsDisabled")
                }}</span>
              </div>
            </div>
          </aside>
        </div>

        <div class="flex justify-end gap-2 border-t border-border px-5 py-4">
          <button
            type="button"
            @click="showCreate = false"
            class="rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-hover"
          >
            {{ $t("common.cancel") }}
          </button>
          <button
            type="submit"
            :disabled="saving"
            class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
          >
            {{ t("alertsCenter.common.saveAndEnable") }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
