<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  BellIcon,
  CheckCircleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EnvelopeIcon,
  GlobeAltIcon,
  PlusIcon,
  XCircleIcon,
  XMarkIcon,
  ChatBubbleLeftRightIcon,
} from "@heroicons/vue/24/outline";
import { alertsApi } from "@/api";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import NotificationChannelTable from "@/components/alerts/NotificationChannelTable.vue";
import NotificationChannelToolbar from "@/components/alerts/NotificationChannelToolbar.vue";
import type {
  NotificationChannel,
  NotificationChannelTestResult,
} from "@/types/alerts";

const channels = ref<NotificationChannel[]>([]);
const { t, locale } = useI18n();
const { getPageSize, setPageSize } = usePagination();
const loading = ref(false);
const filters = reactive({ search: "", type: "", enabled: "" });

// Pagination
const pagination = reactive({
  page: 1,
  page_size: getPageSize("notification-channels"),
  count: 0,
});
const PAGE_STORAGE_KEY = "notification-channels";

watch(
  () => pagination.page_size,
  (newSize) => {
    setPageSize(newSize, PAGE_STORAGE_KEY);
  },
);

// Modal state
const showCreateModal = ref(false);
const editingChannel = ref<NotificationChannel | null>(null);
const saving = ref(false);
const testing = ref(false);
const testResult = ref<NotificationChannelTestResult | null>(null);
const showDetailsModal = ref(false);
const detailsLoading = ref(false);
const channelDetails = ref<any>(null);

// Form state
const form = reactive({
  name: "",
  type: "email" as string,
  enabled: true,
  notification_language: locale.value?.startsWith("zh") ? "zh-CN" : "en",
  // Email config
  email: {
    smtp_host: "",
    smtp_port: "587",
    smtp_username: "",
    smtp_password: "",
    from_email: "",
    email_subject: "",
    to_emails: "",
    use_tls: true,
  },
  // Webhook config
  webhook: {
    url: "",
    method: "POST",
    headers: "",
    timeout: 30,
  },
  // DingTalk config
  dingtalk: {
    webhook_url: "",
    secret: "",
  },
  // WeCom config
  wecom: {
    webhook_url: "",
  },
});

// Channel type icons
const channelIcons: Record<string, any> = {
  email: EnvelopeIcon,
  webhook: GlobeAltIcon,
  dingtalk: ChatBubbleLeftRightIcon,
  wecom: ChatBubbleLeftRightIcon,
};

// Channel type colors
const channelColors: Record<string, string> = {
  email: "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400",
  webhook:
    "bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400",
  dingtalk: "bg-cyan-100 text-cyan-600 dark:bg-cyan-900/30 dark:text-cyan-400",
  wecom:
    "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400",
};

// Filtered channels
const filteredChannels = computed(() => {
  let result = channels.value;

  if (filters.search) {
    const search = filters.search.toLowerCase();
    result = result.filter((c) => c.name.toLowerCase().includes(search));
  }

  if (filters.type) {
    result = result.filter((c) => c.type === filters.type);
  }

  if (filters.enabled) {
    const enabled = filters.enabled === "true";
    result = result.filter((c) => c.enabled === enabled);
  }

  return result;
});

type NotificationChannelColumnKey =
  | "name"
  | "type"
  | "enabled"
  | "target"
  | "updated_at"
  | "actions";

const notificationChannelColumns = computed(() => [
  {
    key: "name" as const,
    label: t("alertsCenter.common.name"),
    min: 220,
    max: 520,
  },
  {
    key: "type" as const,
    label: t("alertsCenter.common.type"),
    min: 130,
    max: 260,
  },
  {
    key: "enabled" as const,
    label: t("alertsCenter.common.status"),
    min: 130,
    max: 260,
  },
  {
    key: "target" as const,
    label: t("alertsCenter.common.target"),
    min: 280,
    max: 720,
  },
  {
    key: "updated_at" as const,
    label: t("alertsCenter.common.updatedAt"),
    min: 190,
    max: 320,
  },
  {
    key: "actions" as const,
    label: t("alertsCenter.common.actions"),
    min: 180,
    max: 260,
    sortable: false,
    align: "right" as const,
  },
]);

const notificationChannelTable = useResizableSortableTable<
  NotificationChannel,
  NotificationChannelColumnKey
>({
  storageKey: "hyperfilelens:notification-channels:columnWidths",
  columns: notificationChannelColumns,
  rows: filteredChannels,
  defaultSort: { key: "name" },
  minTableWidth: 900,
  getSortValue: (channel, key) => {
    if (key === "target") return getChannelTarget(channel);
    if (key === "enabled") return channel.enabled ? 1 : 0;
    if (key === "updated_at")
      return channel.updated_at ? new Date(channel.updated_at).getTime() : 0;
    if (key === "actions") return "";
    return channel[key] ?? "";
  },
  getColumnText: (channel, key) => {
    if (key === "target") return getChannelTarget(channel);
    if (key === "enabled")
      return channel.enabled
        ? t("alertsCenter.values.enabled")
        : t("alertsCenter.values.disabled");
    if (key === "updated_at")
      return new Date(
        channel.updated_at || channel.created_at,
      ).toLocaleString();
    if (key === "actions") return t("alertsCenter.common.actions");
    return String(channel[key] ?? "");
  },
});

// Get channel target display
function getChannelTarget(channel: NotificationChannel) {
  const config = channel.config || {};
  if (channel.type === "email")
    return (config.to_emails || []).join(", ") || config.from_email || "-";
  if (channel.type === "webhook") return config.url || "-";
  return config.webhook_url || "-";
}

// Open create modal
function openCreateModal() {
  editingChannel.value = null;
  testResult.value = null;
  resetForm();
  showCreateModal.value = true;
}

// Open edit modal
function openEditModal(channel: NotificationChannel) {
  editingChannel.value = channel;
  testResult.value = null;

  form.name = channel.name;
  form.type = channel.type;
  form.enabled = channel.enabled;

  const config = channel.config || {};
  form.notification_language =
    config.notification_language ||
    (locale.value?.startsWith("zh") ? "zh-CN" : "en");

  // Load type-specific config
  if (channel.type === "email") {
    form.email = {
      smtp_host: config.smtp_host || "",
      smtp_port: config.smtp_port?.toString() || "587",
      smtp_username: config.smtp_username || "",
      smtp_password: "", // Don't load password for security
      from_email: config.from_email || "",
      email_subject: config.email_subject || "",
      to_emails: (config.to_emails || []).join(", "),
      use_tls: config.use_tls !== false,
    };
  } else if (channel.type === "webhook") {
    form.webhook = {
      url: config.url || "",
      method: config.method || "POST",
      headers: config.headers ? JSON.stringify(config.headers, null, 2) : "",
      timeout: config.timeout || 30,
    };
  } else if (channel.type === "dingtalk") {
    form.dingtalk = {
      webhook_url: config.webhook_url || "",
      secret: config.secret || "",
    };
  } else if (channel.type === "wecom") {
    form.wecom = {
      webhook_url: config.webhook_url || "",
    };
  }

  showCreateModal.value = true;
}

// Reset form
function resetForm() {
  Object.assign(form, {
    name: "",
    type: "email",
    enabled: true,
    notification_language: locale.value?.startsWith("zh") ? "zh-CN" : "en",
    email: {
      smtp_host: "",
      smtp_port: "587",
      smtp_username: "",
      smtp_password: "",
      from_email: "",
      email_subject: "",
      to_emails: "",
      use_tls: true,
    },
    webhook: {
      url: "",
      method: "POST",
      headers: "",
      timeout: 30,
    },
    dingtalk: {
      webhook_url: "",
      secret: "",
    },
    wecom: {
      webhook_url: "",
    },
  });
}

// Watch type change to reset config
watch(
  () => form.type,
  () => {
    testResult.value = null;
  },
);

// Build config from form
function buildConfig(): Record<string, any> {
  const config: Record<string, any> = {
    notification_language: form.notification_language,
  };

  if (form.type === "email") {
    config.smtp_host = form.email.smtp_host;
    config.smtp_port = parseInt(form.email.smtp_port);
    config.smtp_username = form.email.smtp_username;
    config.smtp_password = form.email.smtp_password;
    config.from_email = form.email.from_email;
    config.email_subject = form.email.email_subject;
    config.to_emails = form.email.to_emails
      .split(",")
      .map((e) => e.trim())
      .filter((e) => e);
    config.use_tls = form.email.use_tls;
  } else if (form.type === "webhook") {
    config.url = form.webhook.url;
    config.method = form.webhook.method;
    try {
      config.headers = form.webhook.headers
        ? JSON.parse(form.webhook.headers)
        : {};
    } catch {
      config.headers = {};
    }
    config.timeout = parseInt(form.webhook.timeout.toString());
  } else if (form.type === "dingtalk") {
    config.webhook_url = form.dingtalk.webhook_url;
    config.secret = form.dingtalk.secret;
  } else if (form.type === "wecom") {
    config.webhook_url = form.wecom.webhook_url;
  }

  return config;
}

// Validate form
function validateForm(): string | null {
  if (!form.name.trim()) {
    return t("alertsCenter.common.name") + " " + t("common.required");
  }

  if (form.type === "email") {
    if (!form.email.smtp_host)
      return (
        t("alertsCenter.channels.email.smtpHost") + " " + t("common.required")
      );
    if (!form.email.from_email)
      return (
        t("alertsCenter.channels.email.fromEmail") + " " + t("common.required")
      );
    if (!form.email.to_emails)
      return (
        t("alertsCenter.channels.email.toEmails") + " " + t("common.required")
      );
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(form.email.from_email))
      return (
        t("alertsCenter.channels.email.fromEmail") + " " + t("common.invalid")
      );
  } else if (form.type === "webhook") {
    if (!form.webhook.url)
      return (
        t("alertsCenter.channels.webhook.url") + " " + t("common.required")
      );
    try {
      const url = new URL(form.webhook.url);
      if (!url.protocol.startsWith("http"))
        return (
          t("alertsCenter.channels.webhook.url") + " " + t("common.invalid")
        );
    } catch {
      return t("alertsCenter.channels.webhook.url") + " " + t("common.invalid");
    }
    if (form.webhook.headers) {
      try {
        JSON.parse(form.webhook.headers);
      } catch {
        return (
          t("alertsCenter.channels.webhook.headers") + " " + t("common.invalid")
        );
      }
    }
  } else if (form.type === "dingtalk") {
    if (!form.dingtalk.webhook_url)
      return (
        t("alertsCenter.channels.dingtalk.webhookUrl") +
        " " +
        t("common.required")
      );
  } else if (form.type === "wecom") {
    if (!form.wecom.webhook_url)
      return (
        t("alertsCenter.channels.wecom.webhookUrl") + " " + t("common.required")
      );
  }

  return null;
}

// Test channel connection
async function testConnection() {
  const error = validateForm();
  if (error) {
    alert(error);
    return;
  }

  testing.value = true;
  testResult.value = null;

  try {
    const payload = {
      name: form.name,
      type: form.type,
      enabled: false,
      config: buildConfig(),
    };

    const res = await alertsApi.createNotificationChannel(payload);

    // Test the channel
    await alertsApi.testNotificationChannel(res.data.id);

    // Delete the test channel
    await alertsApi.deleteNotificationChannel(res.data.id);

    testResult.value = {
      success: true,
      message: t("alertsCenter.channels.testSuccess"),
    };
  } catch (err: any) {
    testResult.value = {
      success: false,
      message:
        err.response?.data?.detail ||
        err.message ||
        t("alertsCenter.channels.testFailed"),
    };
  } finally {
    testing.value = false;
  }
}

// Save channel
async function saveChannel() {
  const error = validateForm();
  if (error) {
    alert(error);
    return;
  }

  saving.value = true;

  try {
    const payload = {
      name: form.name,
      type: form.type,
      enabled: form.enabled,
      config: buildConfig(),
    };

    if (editingChannel.value) {
      // Keep existing password if not provided
      if (form.type === "email" && !form.email.smtp_password) {
        payload.config.smtp_password =
          editingChannel.value.config?.smtp_password;
      }
      await alertsApi.updateNotificationChannel(
        editingChannel.value.id,
        payload,
      );
    } else {
      await alertsApi.createNotificationChannel(payload);
    }

    showCreateModal.value = false;
    await fetchChannels();
  } catch (err: any) {
    alert(err.response?.data?.detail || err.message || t("common.saveFailed"));
  } finally {
    saving.value = false;
  }
}

// Delete channel
async function deleteChannel(channel: NotificationChannel) {
  if (
    !window.confirm(
      t("alertsCenter.channels.deleteConfirm", { name: channel.name }),
    )
  )
    return;
  try {
    await alertsApi.deleteNotificationChannel(channel.id);
    await fetchChannels();
  } catch (err: any) {
    alert(
      err.response?.data?.detail || err.message || t("common.deleteFailed"),
    );
  }
}

// Toggle channel enabled
async function toggleChannel(channel: NotificationChannel) {
  try {
    if (channel.enabled) {
      await alertsApi.updateNotificationChannel(channel.id, {
        ...channel,
        enabled: false,
      });
    } else {
      await alertsApi.updateNotificationChannel(channel.id, {
        ...channel,
        enabled: true,
      });
    }
    await fetchChannels();
  } catch (err: any) {
    alert(
      err.response?.data?.detail || err.message || t("common.updateFailed"),
    );
  }
}

// Test existing channel
async function testExistingChannel(channel: NotificationChannel) {
  try {
    await alertsApi.testNotificationChannel(channel.id);
    alert(t("alertsCenter.channels.testSuccess"));
  } catch (err: any) {
    alert(
      err.response?.data?.detail ||
        err.message ||
        t("alertsCenter.channels.testFailed"),
    );
  }
}

// Fetch channels
async function fetchChannels() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {
      page: pagination.page,
      page_size: pagination.page_size,
    };
    if (filters.search) params.search = filters.search;
    if (filters.type) params.type = filters.type;
    if (filters.enabled) params.enabled = filters.enabled;
    const res = await alertsApi.notificationChannels(params);
    channels.value = res.data.results || res.data || [];
    pagination.count = res.data.count || channels.value.length;
  } catch (err) {
    console.error("Failed to fetch channels:", err);
  } finally {
    loading.value = false;
  }
}

// Pagination functions
const totalPages = computed(() =>
  Math.ceil(pagination.count / pagination.page_size),
);

const displayedPages = computed(() => {
  const pages: number[] = [];
  const start = Math.max(1, pagination.page - 2);
  const end = Math.min(totalPages.value, pagination.page + 2);
  for (let i = start; i <= end; i++) pages.push(i);
  return pages;
});

const prevPage = () => {
  if (pagination.page > 1) {
    pagination.page--;
    fetchChannels();
  }
};

const nextPage = () => {
  if (pagination.page < totalPages.value) {
    pagination.page++;
    fetchChannels();
  }
};

const goToPage = (page: number) => {
  pagination.page = page;
  fetchChannels();
};

const handlePageSizeChange = (newSize: number) => {
  pagination.page_size = newSize;
  pagination.page = 1;
  fetchChannels();
};

// View channel details
async function viewDetails(channel: NotificationChannel) {
  showDetailsModal.value = true;
  detailsLoading.value = true;
  channelDetails.value = null;

  try {
    const response = await alertsApi.getChannelDetails(channel.id);
    channelDetails.value = response.data;
  } catch (err: any) {
    alert(err.response?.data?.detail || err.message || t("common.error"));
    showDetailsModal.value = false;
  } finally {
    detailsLoading.value = false;
  }
}

onMounted(fetchChannels);
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-start gap-3">
        <div
          class="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-lg"
        >
          <BellIcon class="h-6 w-6" />
        </div>
        <div>
          <h1 class="text-2xl font-semibold text-foreground">
            {{ t("alertsCenter.channels.title") }}
          </h1>
          <p class="mt-1 text-sm text-foreground-secondary">
            {{ t("alertsCenter.channels.subtitle") }}
          </p>
        </div>
      </div>
      <button
        @click="openCreateModal"
        class="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-primary-hover transition-colors"
      >
        <PlusIcon class="h-4 w-4" />
        {{ t("alertsCenter.common.createChannel") }}
      </button>
    </div>

    <NotificationChannelToolbar
      v-model:search="filters.search"
      v-model:type="filters.type"
      v-model:enabled="filters.enabled"
      :loading="loading"
      @refresh="fetchChannels"
    />

    <NotificationChannelTable
      v-if="filteredChannels.length > 0"
      :channels="notificationChannelTable.sortedRows.value"
      :columns="notificationChannelColumns"
      :table="notificationChannelTable"
      :channel-icons="channelIcons"
      :channel-colors="channelColors"
      :get-channel-target="getChannelTarget"
      @test="testExistingChannel"
      @toggle="toggleChannel"
      @details="viewDetails"
      @edit="openEditModal"
      @delete="deleteChannel"
    />

    <!-- Pagination -->
    <div
      v-if="pagination.count > 0"
      class="flex flex-col sm:flex-row items-center justify-between gap-4 px-4 py-3 bg-card border border-border rounded-lg"
    >
      <div class="flex flex-1 justify-between sm:hidden">
        <button
          :disabled="pagination.page === 1"
          class="relative inline-flex items-center rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
          @click="prevPage"
        >
          {{ t("common.previous") }}
        </button>
        <button
          :disabled="pagination.page >= totalPages"
          class="relative ml-3 inline-flex items-center rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
          @click="nextPage"
        >
          {{ t("common.next") }}
        </button>
      </div>
      <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
        <div>
          <p class="text-sm text-foreground-secondary">
            {{ t("pagination.showing") }}
            {{ (pagination.page - 1) * pagination.page_size + 1 }}
            {{ t("pagination.to") }}
            {{ Math.min(pagination.page * pagination.page_size, pagination.count) }}
            {{ t("pagination.of") }} {{ pagination.count }}
            {{ t("pagination.items") }}
          </p>
        </div>
        <div class="flex items-center gap-4">
          <!-- 每页条数选择 -->
          <div class="flex items-center gap-2">
            <span class="text-sm text-foreground-secondary">{{
              t("pagination.pageSize")
            }}</span>
            <select
              :value="pagination.page_size"
              @change="handlePageSizeChange(Number(($event.target as HTMLSelectElement).value))"
              class="px-2 py-1 text-sm border border-border bg-background text-foreground rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500">
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </div>

          <nav
            class="isolate inline-flex -space-x-px rounded-md shadow-sm"
            aria-label="Pagination"
          >
            <button
              :disabled="pagination.page === 1"
              class="relative inline-flex items-center rounded-l-lg border border-border px-2 py-2 text-foreground-muted hover:bg-hover focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="prevPage"
            >
              <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
            </button>
            <button
              v-for="page in displayedPages"
              :key="page"
              :class="[
                page === pagination.page
                  ? 'bg-indigo-600 text-white'
                  : 'text-foreground ring-1 ring-inset ring-border hover:bg-hover',
                'relative inline-flex items-center px-4 py-2 text-sm font-semibold focus:z-20 focus:outline-offset-0',
              ]"
              @click="goToPage(page)"
            >
              {{ page }}
            </button>
            <button
              :disabled="pagination.page >= totalPages"
              class="relative inline-flex items-center rounded-r-lg border border-border px-2 py-2 text-foreground-muted hover:bg-hover focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="nextPage"
            >
              <ChevronRightIcon class="h-5 w-5" aria-hidden="true" />
            </button>
          </nav>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-else
      class="rounded-xl border border-border bg-card p-12 text-center"
    >
      <div
        class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-background-secondary mb-4"
      >
        <BellIcon class="h-8 w-8 text-foreground-muted" />
      </div>
      <h3 class="text-base font-semibold text-foreground mb-2">
        {{ t("alertsCenter.channels.noChannels") }}
      </h3>
      <p class="text-sm text-foreground-secondary mb-4">
        {{ t("alertsCenter.channels.noChannelsDesc") }}
      </p>
      <button
        @click="openCreateModal"
        class="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover transition-colors"
      >
        <PlusIcon class="h-4 w-4" />
        {{ t("alertsCenter.common.createChannel") }}
      </button>
    </div>

    <!-- Create/Edit Modal -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <div
        class="absolute inset-0 bg-black/55 backdrop-blur-sm"
        @click="showCreateModal = false"
      />
      <div
        class="relative w-full max-w-2xl max-h-[90vh] overflow-hidden rounded-2xl bg-background shadow-2xl flex flex-col"
      >
        <!-- Modal Header -->
        <div
          class="flex items-start justify-between gap-4 border-b border-border px-6 py-4"
        >
          <div>
            <h2 class="text-lg font-semibold text-foreground">
              {{
                editingChannel
                  ? t("alertsCenter.channels.editTitle")
                  : t("alertsCenter.channels.createTitle")
              }}
            </h2>
            <p class="mt-1 text-sm text-foreground-secondary">
              {{ t("alertsCenter.channels.configDesc") }}
            </p>
          </div>
          <button
            @click="showCreateModal = false"
            class="rounded-lg p-2 text-foreground-secondary hover:bg-hover hover:text-foreground transition-colors"
          >
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <!-- Modal Content -->
        <div class="flex-1 overflow-auto p-6 space-y-6">
          <!-- Basic Info -->
          <div class="space-y-4">
            <h3 class="text-sm font-medium text-foreground">
              {{ t("alertsCenter.policies.basicInfo") }}
            </h3>
            <div class="grid gap-4 sm:grid-cols-2">
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground"
                  >{{ t("alertsCenter.common.name") }}
                  <span class="text-red-500">*</span></label
                >
                <input
                  v-model="form.name"
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  :placeholder="t('alertsCenter.channels.namePlaceholder')"
                />
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground"
                  >{{ t("alertsCenter.common.type") }}
                  <span class="text-red-500">*</span></label
                >
                <select
                  v-model="form.type"
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                >
                  <option value="email">
                    {{ t("alertsCenter.values.email") }}
                  </option>
                  <option value="webhook">
                    {{ t("alertsCenter.values.webhook") }}
                  </option>
                  <option value="dingtalk">
                    {{ t("alertsCenter.values.dingtalk") }}
                  </option>
                  <option value="wecom">
                    {{ t("alertsCenter.values.wecom") }}
                  </option>
                </select>
              </div>
              <div
                class="flex items-center gap-3 rounded-lg border border-border bg-background px-3 py-2"
              >
                <input
                  v-model="form.enabled"
                  type="checkbox"
                  class="rounded border-border"
                />
                <span class="text-sm text-foreground">{{
                  t("alertsCenter.common.enabled")
                }}</span>
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground">
                  {{ t("alertsCenter.channels.notificationLanguage") }}
                </label>
                <select
                  v-model="form.notification_language"
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                >
                  <option value="zh-CN">
                    {{ t("alertsCenter.channels.languageChinese") }}
                  </option>
                  <option value="en">
                    {{ t("alertsCenter.channels.languageEnglish") }}
                  </option>
                </select>
              </div>
            </div>
          </div>

          <!-- Type-specific Config -->
          <div class="space-y-4">
            <h3 class="text-sm font-medium text-foreground">
              {{ t("alertsCenter.common.target") }}
            </h3>

            <!-- Email Config -->
            <div v-if="form.type === 'email'" class="space-y-4">
              <div class="grid gap-4 sm:grid-cols-2">
                <div class="space-y-2">
                  <label class="text-sm font-medium text-foreground"
                    >{{ t("alertsCenter.channels.email.smtpHost") }}
                    <span class="text-red-500">*</span></label
                  >
                  <input
                    v-model="form.email.smtp_host"
                    class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                    :placeholder="
                      t('alertsCenter.channels.email.smtpHostPlaceholder')
                    "
                  />
                </div>
                <div class="space-y-2">
                  <label class="text-sm font-medium text-foreground"
                    >{{ t("alertsCenter.channels.email.smtpPort") }}
                    <span class="text-red-500">*</span></label
                  >
                  <input
                    v-model="form.email.smtp_port"
                    type="number"
                    class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                    :placeholder="
                      t('alertsCenter.channels.email.smtpPortPlaceholder')
                    "
                  />
                </div>
                <div class="space-y-2">
                  <label class="text-sm font-medium text-foreground">{{
                    t("alertsCenter.channels.email.smtpUsername")
                  }}</label>
                  <input
                    v-model="form.email.smtp_username"
                    class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                    :placeholder="
                      t('alertsCenter.channels.email.smtpUsernamePlaceholder')
                    "
                  />
                </div>
                <div class="space-y-2">
                  <label class="text-sm font-medium text-foreground"
                    >{{ t("alertsCenter.channels.email.smtpPassword") }}
                    <span class="text-xs text-foreground-muted"
                      >({{ t("common.optional") }})</span
                    ></label
                  >
                  <input
                    v-model="form.email.smtp_password"
                    type="password"
                    class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                    :placeholder="
                      t('alertsCenter.channels.email.smtpPasswordPlaceholder')
                    "
                  />
                </div>
                <div class="space-y-2 sm:col-span-2">
                  <label class="text-sm font-medium text-foreground"
                    >{{ t("alertsCenter.channels.email.fromEmail") }}
                    <span class="text-red-500">*</span></label
                  >
                  <input
                    v-model="form.email.from_email"
                    class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                    :placeholder="
                      t('alertsCenter.channels.email.fromEmailPlaceholder')
                    "
                  />
                </div>
                <div class="space-y-2 sm:col-span-2">
                  <label class="text-sm font-medium text-foreground"
                    >{{ t("alertsCenter.channels.email.emailSubject") }}
                    <span class="text-xs text-foreground-muted"
                      >({{ t("common.optional") }})</span
                    ></label
                  >
                  <input
                    v-model="form.email.email_subject"
                    class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                    :placeholder="
                      t('alertsCenter.channels.email.emailSubjectPlaceholder')
                    "
                  />
                  <p class="text-xs text-foreground-muted">
                    {{ t("alertsCenter.channels.email.emailSubjectDesc") }}
                  </p>
                </div>
                <div class="space-y-2 sm:col-span-2">
                  <label class="text-sm font-medium text-foreground"
                    >{{ t("alertsCenter.channels.email.toEmails") }}
                    <span class="text-red-500">*</span></label
                  >
                  <input
                    v-model="form.email.to_emails"
                    class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                    :placeholder="
                      t('alertsCenter.channels.email.toEmailsPlaceholder')
                    "
                  />
                  <p class="text-xs text-foreground-muted">
                    {{ t("alertsCenter.channels.email.toEmailsDesc") }}
                  </p>
                </div>
                <div
                  class="flex items-center gap-3 rounded-lg border border-border bg-background px-3 py-2 sm:col-span-2"
                >
                  <input
                    v-model="form.email.use_tls"
                    type="checkbox"
                    class="rounded border-border"
                  />
                  <span class="text-sm text-foreground">{{
                    t("alertsCenter.channels.email.useTls")
                  }}</span>
                </div>
              </div>
            </div>

            <!-- Webhook Config -->
            <div v-else-if="form.type === 'webhook'" class="space-y-4">
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground"
                  >{{ t("alertsCenter.channels.webhook.url") }}
                  <span class="text-red-500">*</span></label
                >
                <input
                  v-model="form.webhook.url"
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  :placeholder="
                    t('alertsCenter.channels.webhook.urlPlaceholder')
                  "
                />
              </div>
              <div class="grid gap-4 sm:grid-cols-2">
                <div class="space-y-2">
                  <label class="text-sm font-medium text-foreground">{{
                    t("alertsCenter.channels.webhook.method")
                  }}</label>
                  <select
                    v-model="form.webhook.method"
                    class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="PATCH">PATCH</option>
                  </select>
                </div>
                <div class="space-y-2">
                  <label class="text-sm font-medium text-foreground">{{
                    t("alertsCenter.channels.webhook.timeout")
                  }}</label>
                  <input
                    v-model="form.webhook.timeout"
                    type="number"
                    min="1"
                    max="300"
                    class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground">{{
                  t("alertsCenter.channels.webhook.headers")
                }}</label>
                <textarea
                  v-model="form.webhook.headers"
                  rows="4"
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  :placeholder="
                    t('alertsCenter.channels.webhook.headersPlaceholder')
                  "
                />
                <p class="text-xs text-foreground-muted">
                  {{ t("alertsCenter.channels.webhook.headersDesc") }}
                </p>
              </div>
            </div>

            <!-- DingTalk Config -->
            <div v-else-if="form.type === 'dingtalk'" class="space-y-4">
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground"
                  >{{ t("alertsCenter.channels.dingtalk.webhookUrl") }}
                  <span class="text-red-500">*</span></label
                >
                <input
                  v-model="form.dingtalk.webhook_url"
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  :placeholder="
                    t('alertsCenter.channels.dingtalk.webhookUrlPlaceholder')
                  "
                />
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground">{{
                  t("alertsCenter.channels.dingtalk.secret")
                }}</label>
                <input
                  v-model="form.dingtalk.secret"
                  type="password"
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  :placeholder="
                    t('alertsCenter.channels.dingtalk.secretPlaceholder')
                  "
                />
                <p class="text-xs text-foreground-muted">
                  {{ t("alertsCenter.channels.dingtalk.secretDesc") }}
                </p>
              </div>
            </div>

            <!-- WeCom Config -->
            <div v-else-if="form.type === 'wecom'" class="space-y-4">
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground"
                  >{{ t("alertsCenter.channels.wecom.webhookUrl") }}
                  <span class="text-red-500">*</span></label
                >
                <input
                  v-model="form.wecom.webhook_url"
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                  :placeholder="
                    t('alertsCenter.channels.wecom.webhookUrlPlaceholder')
                  "
                />
              </div>
            </div>
          </div>

          <!-- Test Result -->
          <div
            v-if="testResult"
            class="rounded-lg p-4"
            :class="
              testResult.success
                ? 'bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800'
                : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
            "
          >
            <div class="flex items-center gap-2">
              <component
                :is="testResult.success ? CheckCircleIcon : XCircleIcon"
                class="h-5 w-5"
                :class="
                  testResult.success
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-red-600 dark:text-red-400'
                "
              />
              <span
                class="text-sm font-medium"
                :class="
                  testResult.success
                    ? 'text-emerald-900 dark:text-emerald-100'
                    : 'text-red-900 dark:text-red-100'
                "
              >
                {{ testResult.message }}
              </span>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="flex items-center gap-3 border-t border-border px-6 py-4">
          <button
            @click="testConnection"
            :disabled="testing"
            class="flex items-center gap-2 rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <BeakerIcon :class="['h-4 w-4', testing && 'animate-spin']" />
            {{
              testing
                ? t("alertsCenter.channels.testSending")
                : t("alertsCenter.channels.testButton")
            }}
          </button>
          <div class="flex-1" />
          <button
            @click="showCreateModal = false"
            class="rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-hover transition-colors"
          >
            {{ $t("common.cancel") }}
          </button>
          <button
            @click="saveChannel"
            :disabled="saving || testing"
            class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ saving ? t("common.saving") : $t("common.save") }}
          </button>
        </div>
      </div>
    </div>

    <!-- Details Modal -->
    <div
      v-if="showDetailsModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <div
        class="absolute inset-0 bg-black/55 backdrop-blur-sm"
        @click="showDetailsModal = false"
      />
      <div
        class="relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-2xl bg-background shadow-2xl flex flex-col"
      >
        <!-- Modal Header -->
        <div
          class="flex items-start justify-between gap-4 border-b border-border px-6 py-4"
        >
          <div>
            <h2 class="text-lg font-semibold text-foreground">
              {{ t("alertsCenter.channels.channelDetails") }}
            </h2>
            <p class="mt-1 text-sm text-foreground-secondary">
              {{ channelDetails?.channel?.name }}
            </p>
          </div>
          <button
            @click="showDetailsModal = false"
            class="rounded-lg p-2 text-foreground-secondary hover:bg-hover hover:text-foreground transition-colors"
          >
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <div v-if="detailsLoading" class="flex justify-center py-12">
          <div
            class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"
          ></div>
        </div>

        <div
          v-else-if="channelDetails"
          class="flex-1 overflow-auto p-6 space-y-6"
        >
          <!-- Basic Info -->
          <div class="bg-background-secondary rounded-lg p-6">
            <h4
              class="text-sm font-medium text-foreground-secondary mb-4 flex items-center gap-2"
            >
              <BellIcon class="h-4 w-4" />
              {{ t("alertsCenter.channels.basicInfo") }}
            </h4>
            <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div>
                <p class="text-xs text-foreground-secondary mb-1">
                  {{ t("alertsCenter.channels.channelName") }}
                </p>
                <p class="text-sm font-medium text-foreground">
                  {{ channelDetails.channel.name }}
                </p>
              </div>
              <div>
                <p class="text-xs text-foreground-secondary mb-1">
                  {{ t("alertsCenter.channels.channelType") }}
                </p>
                <div class="flex items-center gap-2">
                  <component
                    :is="channelIcons[channelDetails.channel.type]"
                    class="h-4 w-4 text-foreground-secondary"
                  />
                  <span class="text-sm font-medium text-foreground">
                    {{
                      t(`alertsCenter.values.${channelDetails.channel.type}`)
                    }}
                  </span>
                </div>
              </div>
              <div>
                <p class="text-xs text-foreground-secondary mb-1">
                  {{ t("alertsCenter.channels.enabled") }}
                </p>
                <div class="flex items-center gap-2">
                  <component
                    :is="
                      channelDetails.channel.enabled
                        ? CheckCircleIcon
                        : XCircleIcon
                    "
                    :class="[
                      'h-4 w-4',
                      channelDetails.channel.enabled
                        ? 'text-emerald-500'
                        : 'text-gray-500',
                    ]"
                  />
                  <span
                    :class="[
                      'text-sm font-medium',
                      channelDetails.channel.enabled
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-gray-600 dark:text-gray-400',
                    ]"
                  >
                    {{
                      channelDetails.channel.enabled
                        ? t("common.enabled")
                        : t("common.disabled")
                    }}
                  </span>
                </div>
              </div>
              <div>
                <p class="text-xs text-foreground-secondary mb-1">
                  {{ t("common.created") }}
                </p>
                <p class="text-sm text-foreground">
                  {{
                    new Date(channelDetails.channel.created_at).toLocaleString()
                  }}
                </p>
              </div>
              <div>
                <p class="text-xs text-foreground-secondary mb-1">
                  {{ t("common.updated") }}
                </p>
                <p class="text-sm text-foreground">
                  {{
                    new Date(channelDetails.channel.updated_at).toLocaleString()
                  }}
                </p>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div
              class="bg-background-secondary rounded-lg border border-border p-4"
            >
              <p class="text-xs text-foreground-secondary">
                {{ t("alertsCenter.channels.associatedPolicies") }}
              </p>
              <p class="mt-2 text-2xl font-semibold text-foreground">
                {{ channelDetails.stats.policies_count }}
              </p>
            </div>
            <div
              class="bg-background-secondary rounded-lg border border-border p-4"
            >
              <p class="text-xs text-foreground-secondary">
                {{ t("alertsCenter.channels.successRate") }}
              </p>
              <p class="mt-2 text-2xl font-semibold text-foreground">
                {{ channelDetails.stats.success_rate }}%
              </p>
            </div>
            <div
              class="bg-background-secondary rounded-lg border border-border p-4"
            >
              <p class="text-xs text-foreground-secondary">
                {{ t("alertsCenter.channels.successfulSends") }}
              </p>
              <p
                class="mt-2 text-2xl font-semibold text-emerald-600 dark:text-emerald-400"
              >
                {{ channelDetails.stats.logs_success }}
              </p>
            </div>
            <div
              class="bg-background-secondary rounded-lg border border-border p-4"
            >
              <p class="text-xs text-foreground-secondary">
                {{ t("alertsCenter.channels.failedSends") }}
              </p>
              <p
                class="mt-2 text-2xl font-semibold text-red-600 dark:text-red-400"
              >
                {{ channelDetails.stats.logs_failed }}
              </p>
            </div>
          </div>

          <!-- Channel Configuration Details -->
          <div class="bg-background-secondary rounded-lg p-6">
            <h4
              class="text-sm font-medium text-foreground-secondary mb-4 flex items-center gap-2"
            >
              <GlobeAltIcon class="h-4 w-4" />
              {{ t("alertsCenter.channels.channelConfig") || "渠道配置" }}
            </h4>
            <div
              class="mb-4 rounded-lg border border-border bg-background px-4 py-3"
            >
              <p class="text-xs text-foreground-secondary mb-1">
                {{ t("alertsCenter.channels.notificationLanguage") }}
              </p>
              <p class="text-sm text-foreground">
                {{
                  channelDetails.channel.config.notification_language === "en"
                    ? t("alertsCenter.channels.languageEnglish")
                    : t("alertsCenter.channels.languageChinese")
                }}
              </p>
            </div>

            <!-- Email Configuration -->
            <div
              v-if="channelDetails.channel.type === 'email'"
              class="space-y-4"
            >
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="bg-card rounded-lg border border-border p-4">
                  <p class="text-xs text-foreground-secondary mb-1">
                    {{ t("alertsCenter.channels.email.smtpHost") }}
                  </p>
                  <p class="text-sm font-medium text-foreground break-all">
                    {{ channelDetails.channel.config.smtp_host || "-" }}
                  </p>
                </div>
                <div class="bg-card rounded-lg border border-border p-4">
                  <p class="text-xs text-foreground-secondary mb-1">
                    {{ t("alertsCenter.channels.email.smtpPort") }}
                  </p>
                  <p class="text-sm font-medium text-foreground">
                    {{ channelDetails.channel.config.smtp_port || "-" }}
                  </p>
                </div>
                <div class="bg-card rounded-lg border border-border p-4">
                  <p class="text-xs text-foreground-secondary mb-1">
                    {{ t("alertsCenter.channels.email.smtpUsername") }}
                  </p>
                  <p class="text-sm font-medium text-foreground">
                    {{ channelDetails.channel.config.smtp_username || "-" }}
                  </p>
                </div>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-card rounded-lg border border-border p-4">
                  <p class="text-xs text-foreground-secondary mb-1">
                    {{ t("alertsCenter.channels.email.fromEmail") }}
                  </p>
                  <p class="text-sm font-medium text-foreground break-all">
                    {{ channelDetails.channel.config.from_email || "-" }}
                  </p>
                </div>
                <div class="bg-card rounded-lg border border-border p-4">
                  <p class="text-xs text-foreground-secondary mb-1">
                    {{ t("alertsCenter.channels.email.toEmails") }}
                  </p>
                  <p class="text-sm font-medium text-foreground break-all">
                    {{
                      (channelDetails.channel.config.to_emails || []).join(
                        ", ",
                      ) || "-"
                    }}
                  </p>
                </div>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-card rounded-lg border border-border p-4">
                  <p class="text-xs text-foreground-secondary mb-1">
                    {{ t("alertsCenter.channels.email.emailSubject") }}
                  </p>
                  <p class="text-sm font-medium text-foreground break-all">
                    {{ channelDetails.channel.config.email_subject || "-" }}
                  </p>
                </div>
                <div class="bg-card rounded-lg border border-border p-4">
                  <p class="text-xs text-foreground-secondary mb-1">
                    {{ t("alertsCenter.channels.email.useTls") }}
                  </p>
                  <div class="flex items-center gap-2">
                    <component
                      :is="
                        channelDetails.channel.config.use_tls
                          ? CheckCircleIcon
                          : XCircleIcon
                      "
                      :class="[
                        'h-4 w-4',
                        channelDetails.channel.config.use_tls
                          ? 'text-emerald-500'
                          : 'text-gray-500',
                      ]"
                    />
                    <span
                      :class="[
                        'text-sm font-medium',
                        channelDetails.channel.config.use_tls
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-gray-600 dark:text-gray-400',
                      ]"
                    >
                      {{
                        channelDetails.channel.config.use_tls
                          ? t("common.enabled")
                          : t("common.disabled")
                      }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Webhook Configuration -->
            <div
              v-else-if="channelDetails.channel.type === 'webhook'"
              class="space-y-4"
            >
              <div class="bg-card rounded-lg border border-border p-4">
                <p class="text-xs text-foreground-secondary mb-1">
                  {{ t("alertsCenter.channels.webhook.url") }}
                </p>
                <p
                  class="text-sm font-medium text-foreground break-all font-mono"
                >
                  {{ channelDetails.channel.config.url || "-" }}
                </p>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="bg-card rounded-lg border border-border p-4">
                  <p class="text-xs text-foreground-secondary mb-1">
                    {{ t("alertsCenter.channels.webhook.method") }}
                  </p>
                  <p class="text-sm font-medium text-foreground">
                    {{ channelDetails.channel.config.method || "-" }}
                  </p>
                </div>
                <div class="bg-card rounded-lg border border-border p-4">
                  <p class="text-xs text-foreground-secondary mb-1">
                    {{ t("alertsCenter.channels.webhook.timeout") }}
                  </p>
                  <p class="text-sm font-medium text-foreground">
                    {{ channelDetails.channel.config.timeout }}s
                  </p>
                </div>
              </div>
              <div
                v-if="channelDetails.channel.config.headers"
                class="bg-card rounded-lg border border-border p-4"
              >
                <p class="text-xs text-foreground-secondary mb-1">
                  {{ t("alertsCenter.channels.webhook.headers") }}
                </p>
                <pre
                  class="text-sm text-foreground break-all whitespace-pre-wrap mt-2 font-mono"
                  >{{
                    JSON.stringify(
                      channelDetails.channel.config.headers,
                      null,
                      2,
                    )
                  }}</pre
                >
              </div>
            </div>

            <!-- DingTalk Configuration -->
            <div
              v-else-if="channelDetails.channel.type === 'dingtalk'"
              class="space-y-4"
            >
              <div class="bg-card rounded-lg border border-border p-4">
                <p class="text-xs text-foreground-secondary mb-1">
                  {{ t("alertsCenter.channels.dingtalk.webhookUrl") }}
                </p>
                <p
                  class="text-sm font-medium text-foreground break-all font-mono"
                >
                  {{ channelDetails.channel.config.webhook_url || "-" }}
                </p>
              </div>
              <div
                v-if="channelDetails.channel.config.secret"
                class="bg-card rounded-lg border border-border p-4"
              >
                <p class="text-xs text-foreground-secondary mb-1">
                  {{ t("alertsCenter.channels.dingtalk.secret") }}
                </p>
                <p class="text-sm font-medium text-foreground">******</p>
              </div>
            </div>

            <!-- WeCom Configuration -->
            <div
              v-else-if="channelDetails.channel.type === 'wecom'"
              class="space-y-4"
            >
              <div class="bg-card rounded-lg border border-border p-4">
                <p class="text-xs text-foreground-secondary mb-1">
                  {{ t("alertsCenter.channels.wecom.webhookUrl") }}
                </p>
                <p
                  class="text-sm font-medium text-foreground break-all font-mono"
                >
                  {{ channelDetails.channel.config.webhook_url || "-" }}
                </p>
              </div>
            </div>
          </div>

          <!-- Associated Policies -->
          <div v-if="channelDetails.associated_policies.length > 0">
            <h4 class="text-sm font-medium text-foreground-secondary mb-3">
              {{ t("alertsCenter.channels.associatedPolicies") }}
              ({{ channelDetails.associated_policies.length }})
            </h4>
            <div
              class="bg-card rounded-lg border border-border overflow-hidden"
            >
              <table class="min-w-full divide-y divide-border">
                <thead class="bg-background/50">
                  <tr>
                    <th
                      class="px-4 py-3 text-left text-xs font-medium text-foreground-secondary uppercase tracking-wider"
                    >
                      {{ t("alertsCenter.channels.policyName") }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-medium text-foreground-secondary uppercase tracking-wider"
                    >
                      {{ t("alertsCenter.channels.status") }}
                    </th>
                    <th
                      class="px-4 py-3 text-left text-xs font-medium text-foreground-secondary uppercase tracking-wider"
                    >
                      {{ t("common.created") }}
                    </th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border">
                  <tr
                    v-for="policy in channelDetails.associated_policies"
                    :key="policy.id"
                    class="hover:bg-hover/50"
                  >
                    <td class="px-4 py-3">
                      <p class="text-sm font-medium text-foreground">
                        {{ policy.name }}
                      </p>
                      <p class="text-xs text-foreground-secondary mt-1">
                        {{ policy.description }}
                      </p>
                    </td>
                    <td class="px-4 py-3">
                      <span
                        :class="[
                          'px-2 py-1 text-xs font-medium rounded',
                          policy.enabled
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300'
                            : 'bg-gray-100 text-gray-800 dark:text-gray-300',
                        ]"
                      >
                        {{
                          policy.enabled
                            ? t("common.enabled")
                            : t("common.disabled")
                        }}
                      </span>
                    </td>
                    <td class="px-4 py-3 text-sm text-foreground-secondary">
                      {{ new Date(policy.created_at).toLocaleString() }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div
            v-else
            class="bg-card rounded-lg border border-border p-8 text-center"
          >
            <BellIcon class="mx-auto h-12 w-12 text-gray-400" />
            <p class="mt-2 text-sm text-foreground-secondary">
              {{ t("alertsCenter.channels.noPolicies") }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
