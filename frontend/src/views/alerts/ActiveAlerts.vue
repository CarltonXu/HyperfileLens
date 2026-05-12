<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  BellAlertIcon,
  CheckIcon,
  ClockIcon,
  EyeIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";
import { alertsApi } from "@/api";
import { usePagination } from "@/composables/usePagination";
import AlertSeverityTag from "@/components/alerts/AlertSeverityTag.vue";
import AlertStatusTag from "@/components/alerts/AlertStatusTag.vue";
import AlertTypeTag from "@/components/alerts/AlertTypeTag.vue";

const alerts = ref<any[]>([]);
const { t } = useI18n();
const { getPageSize, setPageSize } = usePagination();
const selected = ref<any | null>(null);
const loading = ref(false);
const filters = reactive({ search: "", severity: "", type: "", status: "" });
const pagination = reactive({
  page: 1,
  page_size: getPageSize("active-alerts"),
  count: 0,
});
const PAGE_STORAGE_KEY = "active-alerts";

watch(
  () => pagination.page_size,
  (newSize) => {
    setPageSize(newSize, PAGE_STORAGE_KEY);
  },
);

const stats = computed(() => ({
  critical: alerts.value.filter((item) => item.severity === "critical").length,
  warning: alerts.value.filter((item) => item.severity === "warning").length,
  firing: alerts.value.filter((item) => item.status === "firing").length,
  acknowledged: alerts.value.filter((item) => item.status === "acknowledged")
    .length,
}));

async function fetchAlerts() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {
      page: pagination.page,
      page_size: pagination.page_size,
    };
    if (filters.search) params.search = filters.search;
    if (filters.severity) params.severity = filters.severity;
    if (filters.type) params.type = filters.type;
    params.status = filters.status || "firing";
    const res = await alertsApi.records(params);
    alerts.value = res.data.results || res.data;
    pagination.count = res.data.count ?? alerts.value.length;
  } finally {
    loading.value = false;
  }
}

async function acknowledge(alert: any) {
  await alertsApi.acknowledgeRecord(alert.id);
  await fetchAlerts();
}

async function resolve(alert: any) {
  await alertsApi.resolveRecord(alert.id);
  await fetchAlerts();
}

function applyFilters() {
  pagination.page = 1;
  fetchAlerts();
}

function formatDate(value?: string) {
  return value ? new Date(value).toLocaleString() : "-";
}

function duration(alert: any) {
  if (alert.duration_seconds == null) return "-";
  const minutes = Math.floor(alert.duration_seconds / 60);
  const seconds = alert.duration_seconds % 60;
  return `${minutes}m ${seconds}s`;
}

onMounted(fetchAlerts);
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-start gap-3">
        <div
          class="flex h-11 w-11 items-center justify-center rounded-lg bg-red-600 text-white shadow-sm">
          <BellAlertIcon class="h-6 w-6" />
        </div>
        <div>
          <h1 class="text-2xl font-semibold text-foreground">
            {{ $t("alertsCenter.active.title") }}
          </h1>
          <p class="mt-1 max-w-3xl text-sm text-foreground-secondary">
            {{ $t("alertsCenter.active.subtitle") }}
          </p>
        </div>
      </div>
      <div class="flex gap-2">
        <button
          class="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium text-foreground shadow-sm hover:bg-hover">
          <CheckIcon class="h-4 w-4" />
          {{ t("alertsCenter.active.batchAcknowledge") }}
        </button>
        <button
          @click="fetchAlerts"
          class="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-hover">
          <ArrowPathIcon class="h-4 w-4" />
          {{ $t("common.refresh") }}
        </button>
      </div>
    </div>

    <div class="grid gap-3 md:grid-cols-4">
      <div class="rounded-lg border border-border p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="rounded-lg bg-red-500/10 p-2 text-red-600">
            <BellAlertIcon class="h-5 w-5" />
          </div>
          <div>
            <p class="text-2xl font-semibold text-foreground">
              {{ stats.critical }}
            </p>
            <p class="text-sm text-foreground-secondary">
              {{ t("alertsCenter.common.critical") }}
            </p>
          </div>
        </div>
      </div>
      <div class="rounded-lg border border-border p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="rounded-lg bg-amber-500/10 p-2 text-amber-600">
            <ClockIcon class="h-5 w-5" />
          </div>
          <div>
            <p class="text-2xl font-semibold text-foreground">
              {{ stats.warning }}
            </p>
            <p class="text-sm text-foreground-secondary">
              {{ t("alertsCenter.common.warning") }}
            </p>
          </div>
        </div>
      </div>
      <div class="rounded-lg border border-border p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="rounded-lg bg-red-500/10 p-2 text-red-600">
            <XMarkIcon class="h-5 w-5" />
          </div>
          <div>
            <p class="text-2xl font-semibold text-foreground">
              {{ stats.firing }}
            </p>
            <p class="text-sm text-foreground-secondary">
              {{ t("alertsCenter.active.firing") }}
            </p>
          </div>
        </div>
      </div>
      <div class="rounded-lg border border-border p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="rounded-lg bg-blue-500/10 p-2 text-blue-600">
            <CheckIcon class="h-5 w-5" />
          </div>
          <div>
            <p class="text-2xl font-semibold text-foreground">
              {{ stats.acknowledged }}
            </p>
            <p class="text-sm text-foreground-secondary">
              {{ t("alertsCenter.active.acknowledged") }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <div
      class="grid gap-3 rounded-lg border border-border p-4 shadow-sm md:grid-cols-5">
      <div class="relative md:col-span-2">
        <MagnifyingGlassIcon
          class="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-foreground-muted" />
        <input
          v-model="filters.search"
          @keyup.enter="applyFilters"
          :placeholder="t('alertsCenter.active.searchPlaceholder')"
          class="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
      </div>
      <select
        v-model="filters.severity"
        @change="applyFilters"
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20">
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
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20">
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
        v-model="filters.status"
        @change="applyFilters"
        class="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20">
        <option value="">{{ t("alertsCenter.active.firing") }}</option>
        <option value="pending">{{ t("alertsCenter.values.pending") }}</option>
        <option value="firing">{{ t("alertsCenter.values.firing") }}</option>
        <option value="acknowledged">
          {{ t("alertsCenter.values.acknowledged") }}
        </option>
      </select>
    </div>

    <div class="overflow-hidden rounded-lg border border-border shadow-sm">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[1120px] text-left text-sm">
          <thead
            class="border-b border-border bg-background bg-background-secondary text-xs uppercase text-foreground-secondary">
            <tr>
              <th class="px-4 py-3 font-medium">
                {{ t("alertsCenter.common.severity") }}
              </th>
              <th class="px-4 py-3 font-medium">
                {{ t("alertsCenter.common.title") }}
              </th>
              <th class="px-4 py-3 font-medium">
                {{ t("alertsCenter.common.type") }}
              </th>
              <th class="px-4 py-3 font-medium">
                {{ t("alertsCenter.common.resource") }}
              </th>
              <th class="px-4 py-3 font-medium">
                {{ t("alertsCenter.common.current") }}
              </th>
              <th class="px-4 py-3 font-medium">
                {{ t("alertsCenter.common.threshold") }}
              </th>
              <th class="px-4 py-3 font-medium">
                {{ t("alertsCenter.common.status") }}
              </th>
              <th class="px-4 py-3 font-medium">
                {{ t("alertsCenter.common.duration") }}
              </th>
              <th class="px-4 py-3 text-right font-medium">
                {{ t("alertsCenter.common.actions") }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr v-for="alert in alerts" :key="alert.id" class="hover:bg-hover">
              <td class="px-4 py-4">
                <AlertSeverityTag :severity="alert.severity" />
              </td>
              <td class="px-4 py-4">
                <div class="font-medium text-foreground">{{ alert.title }}</div>
                <div class="mt-0.5 text-xs text-foreground-secondary">
                  {{ t("alertsCenter.active.firstTriggered") }}
                  {{ formatDate(alert.first_triggered_at) }}
                </div>
              </td>
              <td class="px-4 py-4"><AlertTypeTag :type="alert.type" /></td>
              <td class="px-4 py-4 text-foreground-secondary">
                {{ alert.resource_name || alert.resource_type || "-" }}
              </td>
              <td class="px-4 py-4 text-foreground-secondary">
                {{ alert.current_value ?? "-" }}{{ alert.unit || "" }}
              </td>
              <td class="px-4 py-4 text-foreground-secondary">
                {{ alert.threshold_value ?? "-" }}{{ alert.unit || "" }}
              </td>
              <td class="px-4 py-4">
                <AlertStatusTag :status="alert.status" />
              </td>
              <td class="px-4 py-4 text-foreground-secondary">
                {{ duration(alert) }}
              </td>
              <td class="px-4 py-4">
                <div class="flex justify-end gap-1">
                  <button
                    :title="t('alertsCenter.common.detail')"
                    @click="selected = alert"
                    class="rounded-lg p-2 text-foreground-secondary hover:bg-hover hover:text-foreground">
                    <EyeIcon class="h-4 w-4" />
                  </button>
                  <button
                    :title="t('alertsCenter.common.acknowledge')"
                    @click="acknowledge(alert)"
                    class="rounded-lg p-2 text-foreground-secondary hover:bg-hover hover:text-foreground">
                    <CheckIcon class="h-4 w-4" />
                  </button>
                  <button
                    :title="t('alertsCenter.common.resolve')"
                    @click="resolve(alert)"
                    class="rounded-lg p-2 text-foreground-secondary hover:bg-hover hover:text-foreground">
                    <XMarkIcon class="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="!loading && alerts.length === 0">
              <td
                colspan="9"
                class="px-4 py-12 text-center text-sm text-foreground-secondary">
                {{ $t("common.noData") }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="selected" class="fixed inset-0 z-50 flex justify-end">
      <div class="absolute inset-0 bg-black/55" @click="selected = null" />
      <aside
        class="relative h-full w-full max-w-xl overflow-auto border-l border-border bg-background p-5 shadow-xl">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold text-foreground">
              {{ selected.title }}
            </h2>
            <p class="mt-1 text-sm text-foreground-secondary">
              {{ selected.resource_name || selected.resource_type || "-" }}
            </p>
          </div>
          <button
            @click="selected = null"
            class="rounded-lg p-2 text-foreground-secondary hover:bg-hover hover:text-foreground">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>
        <pre
          class="mt-4 overflow-auto rounded-lg border border-border bg-background-secondary p-3 text-xs text-foreground"
          >{{ JSON.stringify(selected, null, 2) }}</pre
        >
      </aside>
    </div>
  </div>
</template>
