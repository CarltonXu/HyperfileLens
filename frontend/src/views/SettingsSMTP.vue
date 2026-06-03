<template>
  <div class="space-y-6">
    <div class="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <div v-if="loading" class="p-8 text-center">
        <div class="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-indigo-600"></div>
      </div>

      <form v-else @submit.prevent="saveConfig">
        <div class="border-b border-border px-6 py-5">
          <div class="flex items-start gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-300">
              <EnvelopeIcon class="h-5 w-5" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-foreground">
                {{ t("settings.smtp.title") }}
              </h3>
              <p class="mt-1 text-sm text-foreground-secondary">
                {{ t("settings.smtp.description") }}
              </p>
            </div>
          </div>
        </div>

        <div class="space-y-5 px-6 py-5">
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label class="block text-sm font-semibold text-foreground-secondary">
                {{ t("settings.smtp.name") }}
              </label>
              <input
                v-model="form.name"
                type="text"
                required
                class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20" />
            </div>

            <label class="flex cursor-pointer items-end justify-between gap-3 pb-0.5">
              <div>
                <span class="block text-sm font-semibold text-foreground-secondary">
                  {{ t("common.active") }}
                </span>
                <span class="mt-2 block text-sm font-medium text-foreground">
                  {{ form.is_active ? t("common.enabled") : t("common.disabled") }}
                </span>
              </div>
              <input v-model="form.is_active" type="checkbox" class="sr-only" />
              <span
                :class="[
                  'relative inline-flex h-6 w-10 items-center rounded-full transition-colors',
                  form.is_active ? 'bg-indigo-600' : 'bg-background-tertiary border border-border',
                ]">
                <span
                  :class="[
                    'inline-block h-4 w-4 rounded-full bg-white shadow transition-transform',
                    form.is_active ? 'translate-x-5' : 'translate-x-1',
                  ]" />
              </span>
            </label>
          </div>

          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label class="block text-sm font-semibold text-foreground-secondary">
                {{ t("settings.smtp.host") }}
              </label>
              <input
                v-model="form.host"
                type="text"
                required
                class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                placeholder="smtp.example.com" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-foreground-secondary">
                {{ t("settings.smtp.port") }}
              </label>
              <input
                v-model.number="form.port"
                type="number"
                required
                class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                placeholder="587" />
            </div>
          </div>

          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label class="block text-sm font-semibold text-foreground-secondary">
                {{ t("settings.smtp.username") }}
              </label>
              <input
                v-model="form.username"
                type="text"
                :placeholder="t('settings.smtp.usernamePlaceholder')"
                class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20" />
            </div>

            <div>
              <label class="block text-sm font-semibold text-foreground-secondary">
                {{ t("settings.smtp.password") }}
              </label>
              <input
                v-model="form.password"
                type="password"
                class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                :placeholder="t('settings.smtp.passwordPlaceholder')" />
            </div>
          </div>

          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label class="block text-sm font-semibold text-foreground-secondary">
                {{ t("settings.smtp.fromEmail") }}
              </label>
              <input
                v-model="form.from_email"
                type="email"
                required
                placeholder="noreply@example.com"
                class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20" />
            </div>

            <div>
              <label class="block text-sm font-semibold text-foreground-secondary">
                {{ t("settings.smtp.fromName") }}
              </label>
              <input
                v-model="form.from_name"
                type="text"
                :placeholder="t('settings.smtp.emailSubjectPlaceholder')"
                class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20" />
            </div>
          </div>

          <div class="grid grid-cols-1 gap-4 border-t border-border pt-5 md:grid-cols-2">
            <label class="inline-flex cursor-pointer items-center gap-3">
              <input
                :checked="form.use_tls"
                type="checkbox"
                class="sr-only"
                @change="setEncryption('tls', ($event.target as HTMLInputElement).checked)" />
              <span
                :class="[
                  'relative inline-flex h-6 w-10 items-center rounded-full transition-colors',
                  form.use_tls ? 'bg-indigo-600' : 'bg-background-tertiary border border-border',
                ]">
                <span
                  :class="[
                    'inline-block h-4 w-4 rounded-full bg-white shadow transition-transform',
                    form.use_tls ? 'translate-x-5' : 'translate-x-1',
                  ]" />
              </span>
              <span class="text-sm font-semibold text-foreground">TLS</span>
            </label>

            <label class="inline-flex cursor-pointer items-center gap-3">
              <input
                :checked="form.use_ssl"
                type="checkbox"
                class="sr-only"
                @change="setEncryption('ssl', ($event.target as HTMLInputElement).checked)" />
              <span
                :class="[
                  'relative inline-flex h-6 w-10 items-center rounded-full transition-colors',
                  form.use_ssl ? 'bg-indigo-600' : 'bg-background-tertiary border border-border',
                ]">
                <span
                  :class="[
                    'inline-block h-4 w-4 rounded-full bg-white shadow transition-transform',
                    form.use_ssl ? 'translate-x-5' : 'translate-x-1',
                  ]" />
              </span>
              <span class="text-sm font-semibold text-foreground">SSL</span>
            </label>
          </div>
          <p class="text-xs leading-5 text-foreground-muted">
            {{ t("settings.smtp.encryptionHint") }}
          </p>
        </div>

        <div class="flex flex-wrap justify-end gap-3 border-t border-border bg-background/60 px-6 py-4">
          <button
            type="button"
            class="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="!smtpConfigId || isTestingConnection"
            @click="testConnection">
            <CheckCircleIcon class="h-4 w-4" />
            {{ t("settings.smtp.testConnection") }}
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="!smtpConfigId"
            @click="showTestEmailDialog = true">
            <PaperAirplaneIcon class="h-4 w-4" />
            {{ t("settings.smtp.sendTestEmail") }}
          </button>
          <button
            type="submit"
            class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isSaving">
            <CloudArrowUpIcon class="h-4 w-4" />
            {{ isSaving ? t("common.saving") : t("common.save") }}
          </button>
        </div>
      </form>
    </div>

    <div v-if="showTestEmailDialog" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-screen items-center justify-center p-4">
        <div
          class="fixed inset-0 bg-black/50 backdrop-blur-sm"
          @click="closeTestEmailDialog"></div>
        <div class="relative w-full max-w-md overflow-hidden rounded-xl border border-border bg-card shadow-2xl">
          <div class="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
            <div class="flex items-start gap-3">
              <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-300">
                <PaperAirplaneIcon class="h-5 w-5" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-foreground">
                  {{ t("settings.smtp.sendTestEmail") }}
                </h3>
                <p class="mt-1 text-sm text-foreground-secondary">
                  {{ t("settings.smtp.sendTestEmailDescription") }}
                </p>
              </div>
            </div>
            <button
              type="button"
              class="rounded-lg p-2 text-foreground-secondary hover:bg-hover hover:text-foreground"
              @click="closeTestEmailDialog">
              <XMarkIcon class="h-5 w-5" />
            </button>
          </div>

          <form @submit.prevent="sendTestEmail">
            <div class="px-6 py-5">
              <label class="block text-sm font-semibold text-foreground-secondary">
                {{ t("settings.smtp.testEmailTo") }}
              </label>
              <input
                v-model="testEmail"
                type="email"
                required
                class="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                placeholder="admin@example.com" />
            </div>

            <div class="flex justify-end gap-3 border-t border-border bg-background/60 px-6 py-4">
              <button
                type="button"
                class="rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover"
                @click="closeTestEmailDialog">
                {{ t("common.cancel") }}
              </button>
              <button
                type="submit"
                class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="isSendingTestEmail || !testEmail">
                <PaperAirplaneIcon class="h-4 w-4" />
                {{ isSendingTestEmail ? t("common.sending") : t("settings.smtp.sendTest") }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useI18n } from "vue-i18n";
import {
  CheckCircleIcon,
  CloudArrowUpIcon,
  EnvelopeIcon,
  PaperAirplaneIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";
import { smtpApi, type SMTPConfig } from "@/api";
import { useAppStore } from "@/stores/app";

const { t } = useI18n();
const appStore = useAppStore();

const loading = ref(true);
const isSaving = ref(false);
const isTestingConnection = ref(false);
const isSendingTestEmail = ref(false);
const showTestEmailDialog = ref(false);
const smtpConfigId = ref<string | null>(null);
const testEmail = ref("");

const form = reactive({
  name: "Default",
  host: "",
  port: 587,
  username: "",
  password: "",
  use_tls: true,
  use_ssl: false,
  from_email: "noreply@hyperfilelens.com",
  from_name: "HyperFileLens",
  is_active: true,
});

type SMTPConfigListResponse = SMTPConfig[] | { results?: SMTPConfig[] };

function applyConfig(config: SMTPConfig) {
  smtpConfigId.value = config.id;
  Object.assign(form, {
    name: config.name || "Default",
    host: config.host || "",
    port: config.port || 587,
    username: config.username || "",
    password: config.password || "",
    use_tls: config.use_tls,
    use_ssl: config.use_ssl,
    from_email: config.from_email || "noreply@hyperfilelens.com",
    from_name: config.from_name || "HyperFileLens",
    is_active: config.is_active,
  });
}

function normalizeConfigs(data: SMTPConfigListResponse): SMTPConfig[] {
  if (Array.isArray(data)) return data.filter(Boolean);
  return (data.results || []).filter(Boolean);
}

async function fetchConfig() {
  loading.value = true;
  try {
    const defaultResponse = await smtpApi.getDefault();
    applyConfig(defaultResponse.data);
  } catch {
    try {
      const response = await smtpApi.list();
      const configs = normalizeConfigs(response.data as SMTPConfigListResponse);
      const config = configs.find((item) => item.is_default) || configs[0];
      if (config) {
        applyConfig(config);
      }
    } catch (listError) {
      console.error("Failed to fetch SMTP config:", listError);
      appStore.showToast({ type: "error", title: t("common.error") });
    }
  } finally {
    loading.value = false;
  }
}

async function saveConfig() {
  isSaving.value = true;
  try {
    const isExistingConfig = Boolean(smtpConfigId.value);
    const data = { ...form, is_default: true };
    let response;
    if (isExistingConfig && smtpConfigId.value) {
      response = await smtpApi.update(smtpConfigId.value, data);
    } else {
      response = await smtpApi.create(data);
    }
    applyConfig(response.data);
    appStore.showToast({
      type: "success",
      title: isExistingConfig ? t("common.updateSuccess") : t("common.createSuccess"),
    });
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.error || t("common.error"),
    });
  } finally {
    isSaving.value = false;
  }
}

async function testConnection() {
  if (!smtpConfigId.value) return;
  isTestingConnection.value = true;
  try {
    const response = await smtpApi.testConnection(smtpConfigId.value);
    appStore.showToast({
      type: response.data.success ? "success" : "error",
      title: response.data.message,
    });
  } catch (error: unknown) {
    const err = error as { response?: { data?: { message?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.message || t("common.error"),
    });
  } finally {
    isTestingConnection.value = false;
  }
}

function closeTestEmailDialog() {
  showTestEmailDialog.value = false;
  testEmail.value = "";
}

async function sendTestEmail() {
  if (!smtpConfigId.value || !testEmail.value) return;
  isSendingTestEmail.value = true;
  try {
    const response = await smtpApi.sendTestEmail(smtpConfigId.value, testEmail.value);
    appStore.showToast({
      type: response.data.success ? "success" : "error",
      title: response.data.message,
    });
    if (response.data.success) {
      closeTestEmailDialog();
    }
  } catch (error: unknown) {
    const err = error as { response?: { data?: { message?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.message || t("common.error"),
    });
  } finally {
    isSendingTestEmail.value = false;
  }
}

function setEncryption(type: "tls" | "ssl", enabled: boolean) {
  if (type === "tls") {
    form.use_tls = enabled;
    if (enabled) form.use_ssl = false;
    return;
  }

  form.use_ssl = enabled;
  if (enabled) form.use_tls = false;
}

onMounted(() => {
  fetchConfig();
});
</script>
