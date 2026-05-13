<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { alertsApi } from "@/api";
import { useAppStore } from "@/stores/app";
import { getApiErrorMessage } from "@/utils/errors";
import MetricRuleForm from "@/components/alerts/MetricRuleForm.vue";
import AvailabilityRuleForm from "@/components/alerts/AvailabilityRuleForm.vue";
import JobRuleForm from "@/components/alerts/JobRuleForm.vue";
import EventRuleForm from "@/components/alerts/EventRuleForm.vue";
import SystemRuleForm from "@/components/alerts/SystemRuleForm.vue";
import RecoveryRuleForm from "@/components/alerts/RecoveryRuleForm.vue";
import ResourceSelector from "@/components/alerts/ResourceSelector.vue";
import NotificationChannelSelector from "@/components/alerts/NotificationChannelSelector.vue";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const appStore = useAppStore();
const saving = ref(false);
const loading = ref(false);

const form = reactive<Record<string, any>>({
  name: "",
  type: "metric",
  severity: "warning",
  enabled: true,
  description: "",
  resource_type: "",
  scope: "all",
  resource_ids: [],
  trigger_rule: {},
  recovery_rule: { enabled: false },
  notification_channel_ids: [],
});

const notificationOptions = reactive({
  notify_on_trigger: "yes",
  notify_on_recovery: "yes",
});

// Resource data
const resourceTypes = ref<Array<{ value: string; label: string }>>([]);
const targetResources = ref<
  Array<{ id: string; name: string; status?: string }>
>([]);
const targetResourcesLoading = ref(false);
const channels = ref<
  Array<{ id: string; name: string; type: string; enabled: boolean }>
>([]);

// Computed properties
const usesConcreteMonitorTarget = computed(() => {
  return form.type === "metric" || form.type === "availability";
});

const selectedChannelNames = computed(() => {
  const selected = new Set(form.notification_channel_ids || []);
  return channels.value
    .filter((channel) => selected.has(channel.id))
    .map((channel) => channel.name);
});

const metrics = computed(() => {
  if (form.resource_type === "system")
    return [
      "cpu_usage",
      "memory_usage",
      "swap_usage",
      "disk_usage",
      "disk_read_bytes",
      "disk_write_bytes",
      "network_rx",
      "network_tx",
      "load_1m",
      "load_5m",
      "load_15m",
    ];
  if (form.resource_type === "sync_proxy")
    return [
      "cpu_usage",
      "memory_usage",
      "disk_usage",
      "network_rx",
      "network_tx",
    ];
  if (form.resource_type === "gateway")
    return [
      "cpu_usage",
      "memory_usage",
      "disk_usage",
      "network_rx",
      "network_tx",
    ];
  if (form.resource_type === "agent_proxy")
    return [
      "cpu_usage",
      "memory_usage",
      "disk_usage",
      "network_rx",
      "network_tx",
    ];
  if (form.resource_type === "backup_repository")
    return ["capacity_usage", "used_size", "free_size"];
  if (form.resource_type === "target_storage")
    return ["capacity_usage", "used_size", "free_size"];
  return [];
});

const previewRuleText = computed(() => {
  const rule = form.trigger_rule || {};
  const type = form.type;

  if (type === "metric") {
    const metric = rule.metric_key || "-";
    const op = rule.operator || "-";
    const threshold = rule.threshold || "-";
    const unit = rule.unit || "";
    const duration = t("alertsCenter.duration.minutes", {
      count: (rule.duration_seconds || 300) / 60,
    });
    return t("alertsCenter.preview.metricRule", {
      metric,
      operator: op,
      threshold,
      unit,
      duration,
    });
  }
  if (type === "availability") {
    const checkType = rule.check_type || "-";
    const timeout = rule.timeout_seconds || 30;
    const duration = t("alertsCenter.duration.minutes", {
      count: (rule.duration_seconds || 300) / 60,
    });
    return t("alertsCenter.preview.availabilityRule", {
      checkType,
      timeout,
      duration,
    });
  }
  if (type === "job") {
    const jobType = rule.job_type || "-";
    const eventType = rule.event_type || "-";
    const count = rule.consecutive_failures || 1;
    return t("alertsCenter.preview.jobRule", { jobType, eventType, count });
  }
  if (type === "system") {
    const serviceName =
      rule.service_name || t("alertsCenter.preview.systemService");
    const checkType = rule.check_type || "-";
    const duration = t("alertsCenter.duration.minutes", {
      count: (rule.duration_seconds || 300) / 60,
    });
    return t("alertsCenter.preview.systemRule", {
      serviceName,
      checkType,
      duration,
    });
  }
  return "-";
});

const previewRecoveryText = computed(() => {
  const rule = form.recovery_rule || {};
  if (!rule.enabled) return t("alertsCenter.policies.manualResolveOnly");
  const condition = rule.recovery_condition || "-";
  const op = rule.operator || "-";
  const threshold = rule.threshold || "-";
  const duration = t("alertsCenter.duration.minutes", {
    count: (rule.duration_seconds || 300) / 60,
  });
  return `${condition} ${op} ${threshold} for ${duration}`;
});

// Functions
async function loadPolicy() {
  loading.value = true;
  try {
    const res = await alertsApi.getPolicy(route.params.id as string);
    Object.assign(form, res.data);
    form.notification_channel_ids = res.data.notification_channel_ids || [];
  } catch (err) {
    console.error("Failed to load policy:", err);
  } finally {
    loading.value = false;
  }
}

async function fetchResourceTypes() {
  try {
    const res = await alertsApi.metadata("resource-types");
    resourceTypes.value = res.data;
  } catch (err) {
    console.error("Failed to fetch resource types:", err);
  }
}

async function fetchTargetResources() {
  if (!form.resource_type) return;
  targetResourcesLoading.value = true;
  try {
    const res = await alertsApi.metadataResources({
      resource_type: form.resource_type,
    });
    targetResources.value = res.data || [];
  } catch (err) {
    console.error("Failed to fetch target resources:", err);
  } finally {
    targetResourcesLoading.value = false;
  }
}

async function fetchChannels() {
  try {
    const res = await alertsApi.notificationChannels({ page_size: 300 });
    channels.value = res.data.results || res.data || [];
  } catch (err) {
    console.error("Failed to fetch channels:", err);
  }
}

async function submit() {
  saving.value = true;
  try {
    const payload = {
      ...form,
      notification_options: notificationOptions,
    };
    await alertsApi.updatePolicy(route.params.id as string, payload);
    router.push("/alerts/policies");
  } catch (err) {
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(err, t("common.saveFailed")),
    });
  } finally {
    saving.value = false;
  }
}

// Watchers
watch(
  () => form.resource_type,
  () => {
    form.resource_ids = [];
    if (form.type === "metric" && form.resource_type === "system") {
      form.scope = "all";
    }
    if (usesConcreteMonitorTarget.value) {
      fetchTargetResources();
    }
  },
);

watch(
  () => form.type,
  () => {
    // Reset trigger_rule when type changes
    form.trigger_rule = {};
  },
);

// Lifecycle
onMounted(async () => {
  await Promise.all([loadPolicy(), fetchResourceTypes(), fetchChannels()]);
  if (usesConcreteMonitorTarget.value) {
    await fetchTargetResources();
  }
});
</script>

<template>
  <form class="space-y-5" @submit.prevent="submit">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">
          {{ t("alertsCenter.policies.editTitle") }}
        </h1>
        <p class="mt-1 text-sm text-foreground-secondary">
          {{ t("alertsCenter.policies.editDesc") }}
        </p>
      </div>
      <div class="flex gap-2">
        <button
          type="button"
          @click="router.push('/alerts/policies')"
          class="rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-hover"
        >
          {{ $t("common.cancel") }}
        </button>
        <button
          type="submit"
          :disabled="saving"
          class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {{ saving ? t("common.saving") : $t("common.save") }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="text-sm text-foreground-secondary">
        {{ t("common.loading") }}
      </div>
    </div>

    <div v-else class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div class="space-y-5">
        <!-- Basic Info -->
        <section class="rounded-lg border border-border bg-card p-5">
          <div class="mb-4">
            <h3 class="text-base font-semibold text-foreground">
              {{ t("alertsCenter.policies.basicInfo") }}
            </h3>
            <p class="mt-1 text-sm text-foreground-secondary">
              {{ t("alertsCenter.policies.basicInfoDesc") }}
            </p>
          </div>
          <div class="mt-4 grid gap-4 md:grid-cols-2">
            <div class="space-y-2">
              <span class="text-sm font-medium text-foreground"
                >{{ t("alertsCenter.policies.alertName") }}
                <span class="text-red-500">*</span></span
              >
              <input
                v-model="form.name"
                required
                class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                :placeholder="t('alertsCenter.policies.alertNamePlaceholder')"
              />
            </div>
            <div class="space-y-2">
              <span class="text-sm font-medium text-foreground">{{
                t("alertsCenter.policies.alertType")
              }}</span>
              <select
                v-model="form.type"
                class="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              >
                <option value="metric">
                  {{ t("alertsCenter.values.metric") }}
                </option>
                <option value="availability">
                  {{ t("alertsCenter.values.availability") }}
                </option>
                <option value="job">{{ t("alertsCenter.values.job") }}</option>
                <option value="event">
                  {{ t("alertsCenter.values.event") }}
                </option>
                <option value="system">
                  {{ t("alertsCenter.values.system") }}
                </option>
              </select>
            </div>
            <div class="space-y-2">
              <span class="text-sm font-medium text-foreground">{{
                t("alertsCenter.common.severity")
              }}</span>
              <select
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
              </select>
            </div>
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
                    :class="form.enabled ? 'translate-x-5' : 'translate-x-0.5'"
                  />
                </span>
              </button>
            </div>
            <div class="space-y-2 md:col-span-2">
              <span class="text-sm font-medium text-foreground">{{
                t("alertsCenter.policies.description")
              }}</span>
              <textarea
                v-model="form.description"
                rows="3"
                class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                :placeholder="t('alertsCenter.policies.descriptionPlaceholder')"
              />
            </div>
          </div>
        </section>

        <!-- Monitor Target -->
        <section class="rounded-lg border border-border bg-card p-5">
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

        <!-- Trigger Rule -->
        <section class="rounded-lg border border-border bg-card p-5">
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

        <!-- Recovery Rule -->
        <section class="rounded-lg border border-border bg-card p-5">
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

        <!-- Notification -->
        <section class="rounded-lg border border-border bg-card p-5">
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
            <div class="space-y-2">
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
                <option value="no">{{ t("alertsCenter.policies.no") }}</option>
              </select>
            </div>
            <div class="space-y-2">
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
                <option value="no">{{ t("alertsCenter.policies.no") }}</option>
              </select>
            </div>
          </div>
        </section>
      </div>

      <!-- Preview Sidebar -->
      <aside class="sticky top-4 h-fit space-y-4">
        <div
          class="rounded-lg border border-border bg-background-secondary p-5"
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
                >
                <span class="mt-1 block text-foreground">{{
                  t(`alertsCenter.values.${form.type}`)
                }}</span>
              </div>
              <div class="rounded-lg bg-background p-3">
                <span
                  class="block text-xs font-medium uppercase text-foreground-muted"
                  >{{ t("alertsCenter.common.severity") }}</span
                >
                <span class="mt-1 block text-foreground">{{
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
                >{{ form.resource_type || "-" }} / {{ form.scope }}</span
              >
              <span
                v-if="form.resource_ids && form.resource_ids.length"
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
              <span class="mt-1 block text-xs">
                {{ t("alertsCenter.policies.trigger") }}:
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
                }}
              </span>
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
        </div>
      </aside>
    </div>
  </form>
</template>
