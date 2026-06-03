<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { aiInsightsApi } from "@/api";
import {
  UserCircleIcon,
  KeyIcon,
  Cog6ToothIcon,
  SparklesIcon,
  CodeBracketSquareIcon,
  InformationCircleIcon,
  ServerStackIcon,
  EnvelopeIcon,
  PaperAirplaneIcon,
} from "@heroicons/vue/24/outline";
import ThemeSwitcher from "@/components/ThemeSwitcher.vue";
import { usePagination } from "@/composables/usePagination";
import SettingsSMTP from "@/views/SettingsSMTP.vue";

const { t, locale } = useI18n();
const route = useRoute();
const authStore = useAuthStore();
const {
  globalPageSize,
  getGlobalPageSize,
  setGlobalPageSizeRef,
  resetAllPageSizes,
  DEFAULT_PAGE_SIZE,
} = usePagination();

const activeTab = ref(String(route.query.tab || "profile"));

// Preferences form
const preferences = ref({
  defaultPageSize: getGlobalPageSize(),
});

// Profile form
const profile = ref({
  first_name: authStore.user?.first_name || "",
  last_name: authStore.user?.last_name || "",
  email: authStore.user?.email || "",
  phone: authStore.user?.phone || "",
});

// Password form
const passwordForm = ref({
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const isSaving = ref(false);
const isChangingPassword = ref(false);
const isSavingProvider = ref(false);
const passwordError = ref("");
const passwordSuccess = ref("");
const aiProvider = ref<any>(null);
const aiProviderError = ref("");
const aiProviderSuccess = ref("");
const aiProviderJsonError = ref("");
const providerJson = ref("");
const selectedProviderPreset = ref("openai");
const aiInsightsEnabled = ref(false);
const aiTestMessage = ref("Hello, please reply with one short sentence.");
const aiTestResult = ref<any>(null);
const aiTestError = ref("");
const isTestingProvider = ref(false);
const showAiTestPanel = ref(false);
const providerForm = ref({
  name: "Default AI Provider",
  provider_type: "openai_compatible",
  base_url: "https://api.openai.com/v1",
  api_key: "",
  default_model: "gpt-4.1-mini",
  timeout_seconds: 60,
  is_enabled: true,
  is_default: true,
  config: {} as Record<string, unknown>,
});

const aiProviderPresets = computed(() => [
  {
    id: "openai",
    label: "OpenAI",
    name: "OpenAI",
    provider_type: "openai",
    base_url: "https://api.openai.com/v1",
    default_model: "gpt-4.1-mini",
    config: {},
  },
  {
    id: "agione_hyperone",
    label: "Agione HyperOne",
    name: "Agione HyperOne",
    provider_type: "openai_compatible",
    base_url: "https://agione.cc/hyperone/xapi/api",
    default_model: "z-ai/glm-4.7/57f69",
    config: {},
  },
  {
    id: "openrouter",
    label: "OpenRouter",
    name: "OpenRouter",
    provider_type: "openai_compatible",
    base_url: "https://openrouter.ai/api/v1",
    default_model: "openai/gpt-4.1-mini",
    config: {
      headers: {
        "HTTP-Referer": "https://hyperfilelens.local",
        "X-Title": "HyperFileLens",
      },
    },
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    name: "DeepSeek",
    provider_type: "openai_compatible",
    base_url: "https://api.deepseek.com/v1",
    default_model: "deepseek-chat",
    config: {},
  },
  {
    id: "local",
    label: "Local Fallback",
    name: "Local Fallback",
    provider_type: "local",
    base_url: "",
    default_model: "rule-summary",
    config: {},
  },
  {
    id: "custom",
    label: t("settings.aiInsights.customPreset"),
    name: "Custom AI Provider",
    provider_type: "openai_compatible",
    base_url: "",
    default_model: "",
    config: {},
  },
]);

// Get user initials for avatar
const userInitials = computed(() => {
  const firstName = authStore.user?.first_name || "";
  const lastName = authStore.user?.last_name || "";
  if (firstName || lastName) {
    return (firstName.charAt(0) + lastName.charAt(0)).toUpperCase();
  }
  return authStore.user?.username?.charAt(0).toUpperCase() || "U";
});

// Format date
const formattedCreatedAt = computed(() => {
  if (!authStore.user?.date_joined) return "";
  const date = new Date(authStore.user.date_joined);
  return date.toLocaleDateString(locale.value === "zh-CN" ? "zh-CN" : "en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
});

// Get role display name
const roleDisplayName = computed(() => {
  const roleCode = authStore.user?.role?.code;
  if (roleCode === "admin") return t("settings.profile.roles.admin");
  if (roleCode === "operator") return t("settings.profile.roles.operator");
  return t("settings.profile.roles.viewer");
});

const tabs = computed(() => [
  {
    id: "profile",
    icon: UserCircleIcon,
    label: t("settings.sections.profile"),
  },
  { id: "security", icon: KeyIcon, label: t("settings.sections.security") },
  {
    id: "preferences",
    icon: Cog6ToothIcon,
    label: t("settings.sections.preferences"),
  },
  {
    id: "aiInsights",
    icon: SparklesIcon,
    label: t("settings.sections.aiInsights"),
  },
  ...(authStore.user?.is_superuser
    ? [
        {
          id: "email",
          icon: EnvelopeIcon,
          label: t("settings.sections.email"),
        },
      ]
    : []),
]);

function ensureActiveTab() {
  if (!tabs.value.some((tab) => tab.id === activeTab.value)) {
    activeTab.value = "profile";
  }
}

function setLocale(newLocale: string) {
  locale.value = newLocale;
  localStorage.setItem("locale", newLocale);
}

function savePreferences() {
  setGlobalPageSizeRef(preferences.value.defaultPageSize);
  // Show success message (toast)
  alert(t("settings.preferences.saved"));
}

function resetPreferences() {
  resetAllPageSizes();
  preferences.value.defaultPageSize = DEFAULT_PAGE_SIZE;
  // Show success message (toast)
  alert(t("settings.preferences.reset"));
}

async function saveProfile() {
  isSaving.value = true;
  try {
    // TODO: Call API to save profile
    await new Promise((resolve) => setTimeout(resolve, 500));
    // Show success message
  } finally {
    isSaving.value = false;
  }
}

async function changePassword() {
  passwordError.value = "";
  passwordSuccess.value = "";

  // Validation
  if (!passwordForm.value.currentPassword) {
    passwordError.value = t("settings.security.errors.currentRequired");
    return;
  }
  if (passwordForm.value.newPassword.length < 8) {
    passwordError.value = t("settings.security.errors.minLength");
    return;
  }
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    passwordError.value = t("settings.security.errors.mismatch");
    return;
  }

  isChangingPassword.value = true;
  try {
    // TODO: Call API to change password
    await new Promise((resolve) => setTimeout(resolve, 500));
    passwordSuccess.value = t("settings.security.success");
    passwordForm.value = {
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    };
  } finally {
    isChangingPassword.value = false;
  }
}

async function fetchAiProvider() {
  try {
    const response = await aiInsightsApi.defaultProvider();
    aiProvider.value = response.data;
    aiInsightsEnabled.value = response.data.is_enabled === true;
    providerForm.value = {
      name: response.data.name || "Default AI Provider",
      provider_type: response.data.provider_type || "openai_compatible",
      base_url: response.data.base_url || "https://api.openai.com/v1",
      api_key: "",
      default_model: response.data.default_model || "gpt-4.1-mini",
      timeout_seconds: response.data.timeout_seconds || 60,
      is_enabled: response.data.is_enabled !== false,
      is_default: response.data.is_default !== false,
      config: response.data.config || {},
    };
    selectedProviderPreset.value = inferProviderPreset(providerForm.value.base_url, providerForm.value.provider_type);
    syncProviderJson();
  } catch (error: any) {
    aiProvider.value = null;
    aiInsightsEnabled.value = false;
    if (error?.response?.status !== 404) {
      aiProviderError.value = t("settings.aiInsights.loadFailed");
    }
    syncProviderJson();
  }
}

function inferProviderPreset(baseUrl: string, providerType: string) {
  if (providerType === "local") return "local";
  if (baseUrl.includes("agione.cc/hyperone/xapi/api")) return "agione_hyperone";
  if (baseUrl.includes("openrouter.ai")) return "openrouter";
  if (baseUrl.includes("deepseek.com")) return "deepseek";
  if (baseUrl.includes("api.openai.com")) return "openai";
  return "custom";
}

function applyProviderPreset() {
  const preset = aiProviderPresets.value.find((item) => item.id === selectedProviderPreset.value);
  if (!preset || preset.id === "custom") return;
  providerForm.value.name = preset.name || preset.label || providerForm.value.name;
  providerForm.value.provider_type = preset.provider_type;
  providerForm.value.base_url = preset.base_url;
  providerForm.value.default_model = preset.default_model;
  providerForm.value.config = { ...preset.config };
  syncProviderJson();
}

function syncProviderJson() {
  aiProviderJsonError.value = "";
  providerJson.value = JSON.stringify(
    {
      provider_type: providerForm.value.provider_type,
      base_url: providerForm.value.base_url,
      default_model: providerForm.value.default_model,
      timeout_seconds: providerForm.value.timeout_seconds,
      is_enabled: providerForm.value.is_enabled,
      config: providerForm.value.config || {},
    },
    null,
    2,
  );
}

function applyProviderJson(showSuccess = true) {
  aiProviderJsonError.value = "";
  try {
    const parsed = JSON.parse(providerJson.value || "{}");
    providerForm.value.provider_type = parsed.provider_type || providerForm.value.provider_type;
    providerForm.value.base_url = parsed.base_url ?? providerForm.value.base_url;
    providerForm.value.default_model = parsed.default_model ?? providerForm.value.default_model;
    providerForm.value.timeout_seconds = Number(parsed.timeout_seconds || providerForm.value.timeout_seconds || 60);
    providerForm.value.is_enabled = parsed.is_enabled !== false;
    aiInsightsEnabled.value = providerForm.value.is_enabled;
    providerForm.value.config = parsed.config || {};
    selectedProviderPreset.value = inferProviderPreset(providerForm.value.base_url, providerForm.value.provider_type);
    if (showSuccess) {
      aiProviderSuccess.value = t("settings.aiInsights.jsonApplied");
    }
    return true;
  } catch (error) {
    aiProviderJsonError.value = t("settings.aiInsights.invalidJson");
    return false;
  }
}

async function saveAiProvider() {
  aiProviderError.value = "";
  aiProviderSuccess.value = "";
  if (!applyProviderJson(false)) return;
  isSavingProvider.value = true;
  try {
    const payload = { ...providerForm.value };
    if (!payload.api_key) {
      delete (payload as any).api_key;
    }
    const response = aiProvider.value?.id
      ? await aiInsightsApi.updateProvider(aiProvider.value.id, payload)
      : await aiInsightsApi.createProvider(payload);
    aiProvider.value = response.data;
    aiInsightsEnabled.value = response.data.is_enabled === true;
    providerForm.value.is_enabled = aiInsightsEnabled.value;
    providerForm.value.api_key = "";
    aiTestResult.value = null;
    aiTestError.value = "";
    aiProviderSuccess.value = t("settings.aiInsights.saved");
  } catch (error: any) {
    aiProviderError.value = error?.response?.data?.error || error?.response?.data?.api_key || t("settings.aiInsights.saveFailed");
  } finally {
    isSavingProvider.value = false;
  }
}

async function testAiProviderChat() {
  aiProviderError.value = "";
  aiProviderSuccess.value = "";
  aiTestError.value = "";
  aiTestResult.value = null;

  if (!aiProvider.value?.id) {
    aiTestError.value = t("settings.aiInsights.testSaveFirst");
    return;
  }

  const message = aiTestMessage.value.trim();
  if (!message) {
    aiTestError.value = t("settings.aiInsights.testPromptRequired");
    return;
  }

  isTestingProvider.value = true;
  try {
    const response = await aiInsightsApi.testProviderChat(aiProvider.value.id, {
      message,
    });
    aiTestResult.value = response.data;
  } catch (error: any) {
    aiTestError.value =
      error?.response?.data?.error ||
      error?.response?.data?.detail ||
      t("settings.aiInsights.testFailed");
    if (error?.response?.data?.url) {
      aiTestResult.value = { url: error.response.data.url };
    }
  } finally {
    isTestingProvider.value = false;
  }
}

async function toggleAiInsights() {
  aiProviderError.value = "";
  aiProviderSuccess.value = "";
  providerForm.value.is_enabled = aiInsightsEnabled.value;
  syncProviderJson();
  if (!aiInsightsEnabled.value && aiProvider.value?.id) {
    isSavingProvider.value = true;
    try {
      const response = await aiInsightsApi.updateProvider(aiProvider.value.id, { is_enabled: false });
      aiProvider.value = response.data;
      aiProviderSuccess.value = t("settings.aiInsights.disabled");
    } catch (error: any) {
      aiProviderError.value = error?.response?.data?.error || t("settings.aiInsights.saveFailed");
      aiInsightsEnabled.value = true;
      providerForm.value.is_enabled = true;
    } finally {
      isSavingProvider.value = false;
    }
  }
}

onMounted(() => {
  ensureActiveTab();
  fetchAiProvider();
});

watch(tabs, ensureActiveTab);
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold text-foreground">
        {{ t("settings.title") }}
      </h1>
      <p class="text-foreground-secondary mt-1">{{ t("settings.subtitle") }}</p>
    </div>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-[240px_1fr]">
      <aside class="rounded-xl border border-border bg-card p-2 shadow-sm lg:self-start">
        <nav class="space-y-1">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            :class="[
              'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300'
                : 'text-foreground-secondary hover:bg-hover hover:text-foreground',
            ]"
            @click="activeTab = tab.id">
            <component :is="tab.icon" class="h-5 w-5 flex-shrink-0" />
            <span class="truncate">{{ tab.label }}</span>
          </button>
        </nav>
      </aside>

    <!-- Content -->
      <div class="min-w-0 max-w-5xl">
      <!-- Profile -->
      <div
        v-if="activeTab === 'profile'"
        class="bg-card rounded-xl border border-border shadow-sm">
        <div class="px-6 py-4 border-b border-border">
          <div class="flex items-start gap-3">
            <div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-300">
              <UserCircleIcon class="h-5 w-5" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-foreground">
                {{ t("settings.profile.title") }}
              </h3>
              <p class="mt-1 text-sm text-foreground-secondary">
                {{ t("settings.profile.description") }}
              </p>
            </div>
          </div>
        </div>
        <div class="p-6 space-y-6">
          <!-- Avatar Section -->
          <div class="flex items-center gap-4">
            <div
              class="w-16 h-16 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold shadow-lg">
              {{ userInitials }}
            </div>
            <div>
              <p class="font-medium text-foreground">
                {{ authStore.user?.username }}
              </p>
              <p class="text-sm text-foreground-secondary">
                {{ roleDisplayName }}
              </p>
            </div>
          </div>

          <!-- Form -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label
                class="block text-sm font-medium text-foreground-secondary mb-1"
                >{{ t("settings.profile.firstName") }}</label
              >
              <input
                v-model="profile.first_name"
                type="text"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div>
              <label
                class="block text-sm font-medium text-foreground-secondary mb-1"
                >{{ t("settings.profile.lastName") }}</label
              >
              <input
                v-model="profile.last_name"
                type="text"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div>
              <label
                class="block text-sm font-medium text-foreground-secondary mb-1"
                >{{ t("settings.profile.email") }}</label
              >
              <input
                v-model="profile.email"
                type="email"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background-secondary text-foreground-secondary cursor-not-allowed"
                disabled />
            </div>
            <div>
              <label
                class="block text-sm font-medium text-foreground-secondary mb-1"
                >{{ t("settings.profile.phone") }}</label
              >
              <input
                v-model="profile.phone"
                type="tel"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
          </div>

          <!-- Account Info -->
          <div class="pt-4 border-t border-border">
            <h4 class="text-sm font-medium text-foreground-secondary mb-3">
              {{ t("settings.profile.accountInfo") }}
            </h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span class="text-foreground-secondary"
                  >{{ t("settings.profile.username") }}:</span
                >
                <span class="ml-2 text-foreground">{{
                  authStore.user?.username
                }}</span>
              </div>
              <div>
                <span class="text-foreground-secondary"
                  >{{ t("settings.profile.role") }}:</span
                >
                <span class="ml-2 text-foreground">{{ roleDisplayName }}</span>
              </div>
              <div>
                <span class="text-foreground-secondary"
                  >{{ t("settings.profile.createdAt") }}:</span
                >
                <span class="ml-2 text-foreground">{{
                  formattedCreatedAt
                }}</span>
              </div>
            </div>
          </div>

          <div class="flex justify-end">
            <button
              class="px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg font-medium hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md"
              :disabled="isSaving"
              @click="saveProfile">
              {{ isSaving ? t("common.saving") : t("common.save") }}
            </button>
          </div>
        </div>
      </div>

      <!-- Security -->
      <div
        v-if="activeTab === 'security'"
        class="bg-card rounded-xl border border-border shadow-sm">
        <div class="px-6 py-4 border-b border-border">
          <div class="flex items-start gap-3">
            <div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-300">
              <KeyIcon class="h-5 w-5" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-foreground">
                {{ t("settings.security.title") }}
              </h3>
              <p class="mt-1 text-sm text-foreground-secondary">
                {{ t("settings.security.description") }}
              </p>
            </div>
          </div>
        </div>
        <div class="p-6 space-y-4">
          <!-- Error/Success Messages -->
          <div
            v-if="passwordError"
            class="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm">
            {{ passwordError }}
          </div>
          <div
            v-if="passwordSuccess"
            class="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 text-sm">
            {{ passwordSuccess }}
          </div>

          <div>
            <label
              class="block text-sm font-medium text-foreground-secondary mb-1"
              >{{ t("settings.security.currentPassword") }}</label
            >
            <input
              v-model="passwordForm.currentPassword"
              type="password"
              class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
          </div>
          <div>
            <label
              class="block text-sm font-medium text-foreground-secondary mb-1"
              >{{ t("settings.security.newPassword") }}</label
            >
            <input
              v-model="passwordForm.newPassword"
              type="password"
              class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            <p class="text-xs text-foreground-secondary mt-1">
              {{ t("settings.security.passwordHint") }}
            </p>
          </div>
          <div>
            <label
              class="block text-sm font-medium text-foreground-secondary mb-1"
              >{{ t("settings.security.confirmPassword") }}</label
            >
            <input
              v-model="passwordForm.confirmPassword"
              type="password"
              class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
          </div>
          <div class="flex justify-end">
            <button
              class="px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg font-medium hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md"
              :disabled="isChangingPassword"
              @click="changePassword">
              {{
                isChangingPassword
                  ? t("common.saving")
                  : t("settings.security.changePassword")
              }}
            </button>
          </div>
        </div>
      </div>

      <!-- Preferences -->
      <div
        v-if="activeTab === 'preferences'"
        class="bg-card rounded-xl border border-border shadow-sm">
        <div class="px-6 py-4 border-b border-border">
          <div class="flex items-start gap-3">
            <div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-300">
              <Cog6ToothIcon class="h-5 w-5" />
            </div>
            <div>
              <h3 class="text-lg font-semibold text-foreground">
                {{ t("settings.preferences.title") }}
              </h3>
              <p class="mt-1 text-sm text-foreground-secondary">
                {{ t("settings.preferences.description") }}
              </p>
            </div>
          </div>
        </div>
        <div class="divide-y divide-border">
          <section class="grid grid-cols-1 gap-4 px-6 py-5 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div>
              <h4 class="text-sm font-semibold text-foreground">
                {{ t("settings.preferences.defaultPageSize") }}
              </h4>
              <p class="mt-1 text-sm text-foreground-secondary">
                {{ t("settings.preferences.defaultPageSizeDesc") }}
              </p>
              <p class="mt-2 text-xs text-foreground-muted">
                {{ t("settings.preferences.currentValue") }}:
                <span class="font-medium text-foreground">{{ globalPageSize }}</span>
              </p>
            </div>
            <div class="flex items-start lg:justify-end">
              <input
                v-model.number="preferences.defaultPageSize"
                type="number"
                min="5"
                max="100"
                step="5"
                class="w-full max-w-[180px] px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
          </section>

          <section class="grid grid-cols-1 gap-4 px-6 py-5 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div>
              <h4 class="text-sm font-semibold text-foreground">
                {{ t("settings.appearance.theme") }}
              </h4>
              <p class="mt-1 text-sm text-foreground-secondary">
                {{ t("settings.appearance.description") }}
              </p>
            </div>
            <div class="flex items-start lg:justify-end">
              <ThemeSwitcher />
            </div>
          </section>

          <section class="grid grid-cols-1 gap-4 px-6 py-5 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div>
              <h4 class="text-sm font-semibold text-foreground">
                {{ t("settings.language.title") }}
              </h4>
              <p class="mt-1 text-sm text-foreground-secondary">
                {{ t("settings.language.description") }}
              </p>
            </div>
            <div class="grid grid-cols-2 rounded-lg border border-border bg-background p-1">
              <button
                :class="[
                  'rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  locale === 'en'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-foreground-secondary hover:bg-hover hover:text-foreground',
                ]"
                @click="setLocale('en')">
                {{ t("settings.language.english") }}
              </button>
              <button
                :class="[
                  'rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  locale === 'zh-CN'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-foreground-secondary hover:bg-hover hover:text-foreground',
                ]"
                @click="setLocale('zh-CN')">
                {{ t("settings.language.chinese") }}
              </button>
            </div>
          </section>

          <div class="flex flex-wrap justify-end gap-3 bg-background/60 px-6 py-4">
            <button
              @click="savePreferences"
              class="px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg font-medium hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md">
              {{ t("common.save") }}
            </button>
            <button
              @click="resetPreferences"
              class="px-4 py-2 rounded-lg border border-border bg-background text-foreground hover:bg-hover transition-colors">
              {{ t("settings.preferences.reset") }}
            </button>
          </div>
        </div>
      </div>

      <!-- AI Insights -->
      <div
        v-if="activeTab === 'aiInsights'"
        class="bg-card rounded-xl border border-border shadow-sm">
        <div class="px-6 py-4 border-b border-border">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div class="flex items-start gap-3">
              <div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-300">
                <SparklesIcon class="h-5 w-5" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-foreground">
                  {{ t("settings.aiInsights.title") }}
                </h3>
                <p class="mt-1 text-sm text-foreground-secondary">
                  {{ t("settings.aiInsights.description") }}
                </p>
              </div>
            </div>
            <label class="inline-flex cursor-pointer items-center gap-3">
              <span class="text-sm text-foreground-secondary">
                {{ aiInsightsEnabled ? t("common.enabled") : t("common.disabled") }}
              </span>
              <input
                v-model="aiInsightsEnabled"
                type="checkbox"
                class="sr-only"
                @change="toggleAiInsights" />
              <span
                :class="[
                  'relative inline-flex h-7 w-12 items-center rounded-full transition-colors',
                  aiInsightsEnabled ? 'bg-indigo-600' : 'bg-background-tertiary border border-border',
                ]">
                <span
                  :class="[
                    'inline-block h-5 w-5 rounded-full bg-white shadow transition-transform',
                    aiInsightsEnabled ? 'translate-x-6' : 'translate-x-1',
                  ]" />
              </span>
            </label>
          </div>
        </div>
        <div class="p-6 space-y-5">
          <div
            v-if="aiProviderError"
            class="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm">
            {{ aiProviderError }}
          </div>
          <div
            v-if="aiProviderSuccess"
            class="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 text-sm">
            {{ aiProviderSuccess }}
          </div>
          <div
            v-if="aiProviderJsonError"
            class="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm">
            {{ aiProviderJsonError }}
          </div>

          <div
            v-if="!aiInsightsEnabled"
            class="rounded-lg border border-dashed border-border bg-background/40 p-5">
            <div class="flex gap-3">
              <SparklesIcon class="mt-0.5 h-5 w-5 text-foreground-muted" />
              <div>
                <p class="text-sm font-medium text-foreground">
                  {{ t("settings.aiInsights.disabledTitle") }}
                </p>
                <p class="mt-1 text-sm leading-6 text-foreground-secondary">
                  {{ t("settings.aiInsights.disabledDescription") }}
                </p>
              </div>
            </div>
          </div>

          <template v-else>
          <div
            :class="[
              showAiTestPanel
                ? 'grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_360px]'
                : 'block',
            ]">
          <div class="space-y-5">
          <div class="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-4">
            <div class="rounded-lg border border-border bg-background/40 p-4">
              <h4 class="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                <ServerStackIcon class="h-4 w-4 text-indigo-500" />
                {{ t("settings.aiInsights.quickPreset") }}
              </h4>
              <p class="mt-2 text-xs leading-5 text-foreground-secondary">
                {{ t("settings.aiInsights.quickPresetHint") }}
              </p>
              <select
                v-model="selectedProviderPreset"
                class="mt-3 w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                @change="applyProviderPreset()">
                <option
                  v-for="preset in aiProviderPresets"
                  :key="preset.id"
                  :value="preset.id">
                  {{ preset.label }}
                </option>
              </select>
            </div>

            <div class="rounded-lg border border-border bg-background/40 p-4">
              <h4 class="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                <InformationCircleIcon class="h-4 w-4 text-indigo-500" />
                {{ t("settings.aiInsights.howItWorks") }}
              </h4>
              <p class="mt-2 text-xs leading-5 text-foreground-secondary">
                {{ t("settings.aiInsights.howItWorksDesc") }}
              </p>
              <p class="mt-2 text-xs leading-5 text-foreground-muted">
                {{ t("settings.aiInsights.providerExamples") }}
              </p>
            </div>
          </div>

          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-foreground-secondary mb-1">
                {{ t("settings.aiInsights.providerName") }}
              </label>
              <input
                v-model="providerForm.name"
                type="text"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div>
              <label class="block text-sm font-medium text-foreground-secondary mb-1">
                {{ t("settings.aiInsights.providerType") }}
              </label>
              <select
                v-model="providerForm.provider_type"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                @change="syncProviderJson()">
                <option value="openai_compatible">OpenAI Compatible</option>
                <option value="openai">OpenAI</option>
                <option value="local">Local Fallback</option>
              </select>
            </div>
            <div class="lg:col-span-2">
              <label class="block text-sm font-medium text-foreground-secondary mb-1">
                {{ t("settings.aiInsights.baseUrl") }}
              </label>
              <input
                v-model="providerForm.base_url"
                type="text"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                @input="syncProviderJson()" />
              <p class="mt-1 text-xs text-foreground-muted">
                {{ t("settings.aiInsights.baseUrlHint") }}
              </p>
            </div>
            <div>
              <label class="block text-sm font-medium text-foreground-secondary mb-1">
                {{ t("settings.aiInsights.model") }}
              </label>
              <input
                v-model="providerForm.default_model"
                type="text"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                @input="syncProviderJson()" />
            </div>
            <div>
              <label class="block text-sm font-medium text-foreground-secondary mb-1">
                {{ t("settings.aiInsights.timeout") }}
              </label>
              <input
                v-model.number="providerForm.timeout_seconds"
                type="number"
                min="5"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                @input="syncProviderJson()" />
            </div>
            <div class="lg:col-span-2">
              <label class="block text-sm font-medium text-foreground-secondary mb-1">
                {{ t("settings.aiInsights.apiKey") }}
              </label>
              <input
                v-model="providerForm.api_key"
                type="password"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                :placeholder="aiProvider?.api_key_masked || t('settings.aiInsights.apiKeyPlaceholder')" />
              <p class="mt-1 text-xs text-foreground-muted">
                {{ t("settings.aiInsights.apiKeyHint") }}
              </p>
            </div>
          </div>

          <div class="rounded-lg border border-border bg-background/40">
            <div class="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
              <div>
                <h4 class="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                  <CodeBracketSquareIcon class="h-4 w-4 text-indigo-500" />
                  {{ t("settings.aiInsights.jsonConfig") }}
                </h4>
                <p class="mt-1 text-xs text-foreground-muted">
                  {{ t("settings.aiInsights.jsonConfigHint") }}
                </p>
              </div>
              <div class="flex gap-2">
                <button
                  class="rounded-lg border border-border px-3 py-1.5 text-xs text-foreground-secondary hover:bg-hover"
                  @click="syncProviderJson()">
                  {{ t("settings.aiInsights.refreshJson") }}
                </button>
                <button
                  class="rounded-lg border border-border px-3 py-1.5 text-xs text-foreground-secondary hover:bg-hover"
                  @click="applyProviderJson()">
                  {{ t("settings.aiInsights.applyJson") }}
                </button>
              </div>
            </div>
            <textarea
              v-model="providerJson"
              class="min-h-64 w-full resize-y border-0 bg-transparent p-4 font-mono text-xs leading-5 text-foreground outline-none focus:ring-0"
              spellcheck="false" />
          </div>

          <div class="flex flex-wrap items-center justify-between gap-4 border-t border-border pt-4">
            <p class="text-xs leading-5 text-foreground-muted">
              {{ t("settings.aiInsights.saveHint") }}
            </p>
            <div class="flex flex-wrap items-center justify-end gap-2">
              <button
                class="px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg font-medium hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md disabled:opacity-50"
                :disabled="isSavingProvider"
                @click="saveAiProvider">
                {{ isSavingProvider ? t("common.saving") : t("common.save") }}
              </button>
              <button
                class="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-4 py-2 font-medium text-foreground-secondary transition-colors hover:bg-hover hover:text-foreground"
                @click="showAiTestPanel = !showAiTestPanel">
                <SparklesIcon class="h-4 w-4 text-indigo-500" />
                {{
                  showAiTestPanel
                    ? t("common.close")
                    : t("settings.aiInsights.testChat")
                }}
              </button>
            </div>
          </div>
          </div>

          <aside
            v-if="showAiTestPanel"
            class="rounded-lg border border-border bg-background/40 xl:sticky xl:top-4 xl:self-start">
            <div class="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
              <div>
                <h4 class="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                  <SparklesIcon class="h-4 w-4 text-indigo-500" />
                  {{ t("settings.aiInsights.testChat") }}
                </h4>
                <p class="mt-1 text-xs text-foreground-muted">
                  {{ t("settings.aiInsights.testChatHint") }}
                </p>
              </div>
              <span
                v-if="aiProvider?.id"
                class="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                {{ t("settings.aiInsights.savedProvider") }}
              </span>
              <span
                v-else
                class="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                {{ t("settings.aiInsights.unsavedProvider") }}
              </span>
            </div>
            <div class="space-y-3 p-4">
              <textarea
                v-model="aiTestMessage"
                rows="3"
                class="w-full resize-y rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-foreground-muted focus:border-transparent focus:ring-2 focus:ring-indigo-500"
                :placeholder="t('settings.aiInsights.testPromptPlaceholder')" />
              <div class="flex flex-wrap items-center justify-between gap-3">
                <p class="text-xs leading-5 text-foreground-muted">
                  {{ t("settings.aiInsights.testChatSaveHint") }}
                </p>
                <button
                  class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="isTestingProvider || !aiProvider?.id"
                  @click="testAiProviderChat">
                  <PaperAirplaneIcon class="h-4 w-4" />
                  {{
                    isTestingProvider
                      ? t("settings.aiInsights.testing")
                      : t("settings.aiInsights.sendTest")
                  }}
                </button>
              </div>

              <div
                v-if="aiTestError"
                class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">
                {{ aiTestError }}
              </div>
              <div
                v-if="aiTestResult"
                class="rounded-lg border border-border bg-card p-3">
                <div class="flex flex-wrap items-center gap-2 text-xs text-foreground-muted">
                  <span v-if="aiTestResult.model">
                    {{ t("settings.aiInsights.model") }}:
                    <span class="font-medium text-foreground">{{ aiTestResult.model }}</span>
                  </span>
                  <span v-if="aiTestResult.latency_ms">
                    {{ t("settings.aiInsights.latency") }}:
                    <span class="font-medium text-foreground">{{ aiTestResult.latency_ms }}ms</span>
                  </span>
                </div>
                <p
                  v-if="aiTestResult.url"
                  class="mt-2 break-all font-mono text-xs text-foreground-muted">
                  {{ aiTestResult.url }}
                </p>
                <p
                  v-if="aiTestResult.answer"
                  class="mt-3 whitespace-pre-wrap rounded-md bg-background px-3 py-2 text-sm leading-6 text-foreground">
                  {{ aiTestResult.answer }}
                </p>
              </div>
            </div>
          </aside>
          </div>
          </template>
        </div>
      </div>

      <!-- Email Settings -->
      <SettingsSMTP v-if="activeTab === 'email' && authStore.user?.is_superuser" />
      </div>
    </div>
  </div>
</template>
