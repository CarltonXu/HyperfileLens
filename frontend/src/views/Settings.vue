<script setup lang="ts">
import { ref, computed, nextTick, onMounted, watch } from "vue";
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
  XMarkIcon,
} from "@heroicons/vue/24/outline";
import PageTitle from "@/components/PageTitle.vue";
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
const aiTestMessagesContainer = ref<HTMLElement | null>(null);
const aiTestMessageInput = ref<HTMLTextAreaElement | null>(null);
type AiTestMessage = {
  role: "user" | "assistant";
  content: string;
  isTyping?: boolean;
  status?: "error";
  meta?: {
    model?: string;
    latency_ms?: number;
    url?: string;
  };
};
const aiTestMessages = ref<AiTestMessage[]>([]);
const hasTypingAiTestMessage = computed(() => aiTestMessages.value.some((message) => message.isTyping));
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

async function typeAssistantMessage(
  fullText: string,
  meta?: {
    model?: string;
    latency_ms?: number;
    url?: string;
  },
) {
  const message = {
    role: "assistant" as const,
    content: "",
    isTyping: true,
    meta,
  };
  aiTestMessages.value.push(message);
  const messageIndex = aiTestMessages.value.length - 1;

  for (const char of fullText) {
    aiTestMessages.value[messageIndex].content += char;
    await new Promise((resolve) => setTimeout(resolve, char.trim() ? 18 : 8));
  }

  aiTestMessages.value[messageIndex].isTyping = false;
}

function getCsrfToken(): string | null {
  const name = "csrftoken=";
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(name));
  return cookie ? decodeURIComponent(cookie.slice(name.length)) : null;
}

function getStreamErrorMessage(error: unknown) {
  if (error && typeof error === "object" && "message" in error) {
    return String((error as { message?: unknown }).message || "");
  }
  return String(error || "");
}

function scrollAiTestMessagesToBottom() {
  void nextTick(() => {
    const container = aiTestMessagesContainer.value;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  });
}

function waitForAiStreamPaint() {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, 12);
  });
}

function resizeAiTestMessageInput() {
  void nextTick(() => {
    const input = aiTestMessageInput.value;
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 112)}px`;
  });
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderInlineMarkdown(value: string) {
  const codeSpans: string[] = [];
  let html = escapeHtml(value).replace(/`([^`]+)`/g, (_match, code) => {
    const token = `@@CODE_SPAN_${codeSpans.length}@@`;
    codeSpans.push(`<code class="rounded bg-black/5 px-1 py-0.5 font-mono text-[0.92em] dark:bg-white/10">${code}</code>`);
    return token;
  });

  html = html
    .replace(/\*\*([^*]+)\*\*/g, "<strong class=\"font-semibold\">$1</strong>")
    .replace(/__([^_]+)__/g, "<strong class=\"font-semibold\">$1</strong>")
    .replace(/\*([^*\n]+)\*/g, "<em>$1</em>");

  codeSpans.forEach((code, index) => {
    html = html.replace(`@@CODE_SPAN_${index}@@`, code);
  });
  return html;
}

function renderMarkdown(content: string) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: string[] = [];
  let paragraph: string[] = [];
  let listItems: string[] = [];
  let orderedListItems: string[] = [];
  let quoteLines: string[] = [];
  let codeLines: string[] = [];
  let inCodeBlock = false;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push(`<p>${paragraph.map(renderInlineMarkdown).join("<br>")}</p>`);
    paragraph = [];
  };
  const flushList = () => {
    if (listItems.length) {
      blocks.push(`<ul>${listItems.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</ul>`);
      listItems = [];
    }
    if (orderedListItems.length) {
      blocks.push(`<ol>${orderedListItems.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</ol>`);
      orderedListItems = [];
    }
  };
  const flushQuote = () => {
    if (!quoteLines.length) return;
    blocks.push(`<blockquote>${quoteLines.map(renderInlineMarkdown).join("<br>")}</blockquote>`);
    quoteLines = [];
  };
  const flushAll = () => {
    flushParagraph();
    flushList();
    flushQuote();
  };

  for (const line of lines) {
    const codeFence = line.match(/^```([\w-]*)\s*$/);
    if (codeFence) {
      if (inCodeBlock) {
        blocks.push(
          `<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`,
        );
        codeLines = [];
        inCodeBlock = false;
      } else {
        flushAll();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    if (!line.trim()) {
      flushAll();
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushAll();
      const level = heading[1].length;
      blocks.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }

    const quote = line.match(/^>\s?(.*)$/);
    if (quote) {
      flushParagraph();
      flushList();
      quoteLines.push(quote[1]);
      continue;
    }

    const unordered = line.match(/^\s*[-*]\s+(.+)$/);
    if (unordered) {
      flushParagraph();
      flushQuote();
      listItems.push(unordered[1]);
      continue;
    }

    const ordered = line.match(/^\s*\d+\.\s+(.+)$/);
    if (ordered) {
      flushParagraph();
      flushQuote();
      orderedListItems.push(ordered[1]);
      continue;
    }

    flushList();
    flushQuote();
    paragraph.push(line);
  }

  if (inCodeBlock) {
    blocks.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  }
  flushAll();

  return blocks.join("");
}

async function testAiProviderChatStream(providerId: string | number, message: string) {
  if (!window.ReadableStream) return false;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = localStorage.getItem("token");
  if (token) {
    headers.Authorization = `Token ${token}`;
  }
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(`/api/v1/system/ai-providers/${providerId}/test-chat/`, {
    method: "POST",
    headers,
    body: JSON.stringify({ message, stream: true, max_tokens: 4096 }),
  });

  const contentType = response.headers.get("content-type") || "";
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.error || data?.detail || response.statusText);
  }
  if (!response.body || !contentType.includes("text/event-stream")) {
    return false;
  }

  const assistantMessage: AiTestMessage = {
    role: "assistant",
    content: "",
    isTyping: true,
    meta: {},
  };
  aiTestMessages.value.push(assistantMessage);
  const assistantMessageIndex = aiTestMessages.value.length - 1;
  scrollAiTestMessagesToBottom();

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const handleEvent = async (eventText: string) => {
    const dataLines = eventText
      .replace(/\r\n/g, "\n")
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart());
    if (dataLines.length === 0) return;
    const event = JSON.parse(dataLines.join("\n"));
    const currentMessage = aiTestMessages.value[assistantMessageIndex];
    if (!currentMessage) return;
    if (event.type === "meta") {
      currentMessage.meta = {
        model: event.model,
        latency_ms: event.latency_ms,
        url: event.url,
      };
    } else if (event.type === "delta") {
      currentMessage.content += event.content || "";
      scrollAiTestMessagesToBottom();
      await waitForAiStreamPaint();
    } else if (event.type === "done") {
      currentMessage.isTyping = false;
      if (event.model) {
        currentMessage.meta = {
          ...currentMessage.meta,
          model: event.model,
        };
      }
      if (!currentMessage.content && event.answer) {
        currentMessage.content = event.answer;
      }
      aiTestResult.value = {
        success: true,
        answer: currentMessage.content,
        model: currentMessage.meta?.model,
        latency_ms: currentMessage.meta?.latency_ms,
        url: currentMessage.meta?.url,
      };
      scrollAiTestMessagesToBottom();
    } else if (event.type === "error") {
      throw new Error(event.error || t("settings.aiInsights.testFailed"));
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, "\n");
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";
      for (const eventText of events) {
        await handleEvent(eventText);
      }
    }
    buffer += decoder.decode();
    if (buffer.trim()) {
      await handleEvent(buffer);
    }
    if (aiTestMessages.value[assistantMessageIndex]) {
      aiTestMessages.value[assistantMessageIndex].isTyping = false;
    }
    scrollAiTestMessagesToBottom();
    return true;
  } catch (error) {
    const currentMessage = aiTestMessages.value[assistantMessageIndex];
    if (currentMessage) {
      currentMessage.isTyping = false;
      currentMessage.status = "error";
      currentMessage.content = getStreamErrorMessage(error) || t("settings.aiInsights.testFailed");
    }
    scrollAiTestMessagesToBottom();
    return true;
  }
}

async function testAiProviderChat() {
  if (isTestingProvider.value) return;

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

  aiTestMessages.value.push({
    role: "user",
    content: message,
  });
  scrollAiTestMessagesToBottom();
  aiTestMessage.value = "";
  resizeAiTestMessageInput();
  isTestingProvider.value = true;
  try {
    const streamed = await testAiProviderChatStream(aiProvider.value.id, message);
    if (streamed) return;

    const response = await aiInsightsApi.testProviderChat(aiProvider.value.id, {
      message,
    });
    aiTestResult.value = response.data;
    await typeAssistantMessage(
      response.data.answer || t("settings.aiInsights.testNoAnswer"),
      {
        model: response.data.model,
        latency_ms: response.data.latency_ms,
        url: response.data.url,
      },
    );
  } catch (error: any) {
    aiTestError.value =
      error?.response?.data?.error ||
      error?.response?.data?.detail ||
      error?.message ||
      t("settings.aiInsights.testFailed");
    if (error?.response?.data?.url) {
      aiTestResult.value = { url: error.response.data.url };
    }
    aiTestMessages.value.push({
      role: "assistant",
      content: aiTestError.value,
      status: "error",
      meta: {
        url: error?.response?.data?.url,
      },
    });
  } finally {
    isTestingProvider.value = false;
  }
}

function handleAiTestMessageKeydown(event: KeyboardEvent) {
  if (event.key !== "Enter" || event.shiftKey) return;
  event.preventDefault();
  void testAiProviderChat();
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
watch(aiTestMessage, resizeAiTestMessageInput);
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <PageTitle
      :icon="Cog6ToothIcon"
      :title="t('settings.title')"
      :subtitle="t('settings.subtitle')"
      icon-class="text-slate-600 dark:text-slate-300"
    />

    <div class="space-y-6">
      <div class="rounded-xl border border-border bg-card px-2 shadow-sm">
        <nav class="flex gap-1 overflow-x-auto">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            :class="[
              'relative flex shrink-0 items-center gap-2 px-4 py-3 text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'text-indigo-700 dark:text-indigo-300'
                : 'text-foreground-secondary hover:text-foreground',
            ]"
            @click="activeTab = tab.id">
            <component :is="tab.icon" class="h-5 w-5 flex-shrink-0" />
            <span class="truncate">{{ tab.label }}</span>
            <span
              v-if="activeTab === tab.id"
              class="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-indigo-600 dark:bg-indigo-400" />
          </button>
        </nav>
      </div>

    <!-- Content -->
      <div class="min-w-0">
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
                @click="showAiTestPanel = true">
                <SparklesIcon class="h-4 w-4 text-indigo-500" />
                {{ t("settings.aiInsights.testChat") }}
              </button>
            </div>
          </div>
          </div>

          <div
            v-if="showAiTestPanel"
            class="fixed inset-0 z-[10000] bg-black/50"
            @click.self="showAiTestPanel = false">
            <aside
              class="ml-auto flex h-full w-full flex-col border-l border-border bg-card shadow-2xl sm:w-[60vw] sm:max-w-[60vw]">
              <div class="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
                <div>
                  <h4 class="inline-flex items-center gap-2 text-base font-semibold text-foreground">
                    <SparklesIcon class="h-5 w-5 text-indigo-500" />
                    {{ t("settings.aiInsights.testChat") }}
                  </h4>
                  <p class="mt-1 text-sm leading-5 text-foreground-secondary">
                    {{ t("settings.aiInsights.testChatHint") }}
                  </p>
                  <span
                    v-if="aiProvider?.id"
                    class="mt-3 inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                    {{ t("settings.aiInsights.savedProvider") }}
                  </span>
                  <span
                    v-else
                    class="mt-3 inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                    {{ t("settings.aiInsights.unsavedProvider") }}
                  </span>
                </div>
                <button
                  class="rounded-lg p-2 text-foreground-muted transition-colors hover:bg-hover hover:text-foreground"
                  :aria-label="t('common.close')"
                  @click="showAiTestPanel = false">
                  <XMarkIcon class="h-5 w-5" />
                </button>
              </div>

              <div
                ref="aiTestMessagesContainer"
                class="min-h-0 flex-1 space-y-4 overflow-y-auto bg-background/50 px-5 py-5">
                <div
                  v-if="aiTestMessages.length === 0"
                  class="rounded-lg border border-dashed border-border bg-card px-4 py-5 text-sm leading-6 text-foreground-secondary">
                  {{ t("settings.aiInsights.testEmptyState") }}
                </div>
                <div
                  v-for="(message, index) in aiTestMessages"
                  :key="index"
                  :class="[
                    'flex',
                    message.role === 'user' ? 'justify-end' : 'justify-start',
                  ]">
                  <div
                    :class="[
                      'max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm',
                      message.role === 'user'
                        ? 'rounded-br-md bg-indigo-600 text-white'
                        : message.status === 'error'
                          ? 'rounded-bl-md border border-red-200 bg-red-50 text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300'
                          : 'rounded-bl-md border border-border bg-card text-foreground',
                    ]">
                    <div
                      v-if="message.role === 'assistant' && message.isTyping && !message.content"
                      class="flex items-center gap-3 text-foreground-secondary">
                      <span class="inline-flex h-7 w-7 items-center justify-center rounded-full bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-300">
                        <SparklesIcon class="h-4 w-4 animate-pulse" />
                      </span>
                      <span class="text-sm">{{ t("settings.aiInsights.waitingForProvider") }}</span>
                      <span class="inline-flex items-center gap-1">
                        <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.24s]" />
                        <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:-0.12s]" />
                        <span class="h-1.5 w-1.5 animate-bounce rounded-full bg-current" />
                      </span>
                    </div>
                    <div
                      v-else-if="message.role === 'assistant' && message.status !== 'error'"
                      class="ai-test-markdown"
                      v-html="renderMarkdown(message.content)" />
                    <p
                      v-else
                      class="whitespace-pre-wrap">
                      {{ message.content }}<span
                        v-if="message.isTyping"
                        class="ml-0.5 inline-block h-4 w-1 translate-y-0.5 animate-pulse rounded-full bg-current" />
                    </p>
                    <span
                      v-if="message.role === 'assistant' && message.status !== 'error' && message.isTyping && message.content"
                      class="ml-0.5 inline-block h-4 w-1 translate-y-0.5 animate-pulse rounded-full bg-current" />
                    <div
                      v-if="message.role === 'assistant' && message.isTyping && message.content"
                      class="mt-2 flex items-center gap-2 border-t border-current/10 pt-2 text-[11px] leading-4 text-foreground-muted">
                      <span class="relative flex h-2 w-2">
                        <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-75" />
                        <span class="relative inline-flex h-2 w-2 rounded-full bg-indigo-500" />
                      </span>
                      <span>{{ t("settings.aiInsights.receivingStream") }}</span>
                      <span class="inline-flex items-center gap-0.5 opacity-70">
                        <span class="h-1 w-1 animate-bounce rounded-full bg-current [animation-delay:-0.24s]" />
                        <span class="h-1 w-1 animate-bounce rounded-full bg-current [animation-delay:-0.12s]" />
                        <span class="h-1 w-1 animate-bounce rounded-full bg-current" />
                      </span>
                    </div>
                    <div
                      v-if="message.meta?.model || message.meta?.latency_ms || message.meta?.url"
                      class="mt-2 space-y-1 border-t border-current/10 pt-2 text-[11px] leading-4 opacity-75">
                      <p v-if="message.meta?.model">
                        {{ t("settings.aiInsights.model") }}: {{ message.meta.model }}
                      </p>
                      <p v-if="message.meta?.latency_ms">
                        {{ t("settings.aiInsights.latency") }}: {{ message.meta.latency_ms }}ms
                      </p>
                      <p
                        v-if="message.meta?.url"
                        class="break-all font-mono">
                        {{ message.meta.url }}
                      </p>
                    </div>
                  </div>
                </div>
                <div
                  v-if="isTestingProvider && !hasTypingAiTestMessage"
                  class="flex justify-start">
                  <div class="rounded-2xl rounded-bl-md border border-border bg-card px-4 py-3 text-sm text-foreground-secondary shadow-sm">
                    {{ t("settings.aiInsights.testing") }}
                  </div>
                </div>
              </div>

              <div class="border-t border-border bg-card p-4">
                <p
                  v-if="!aiProvider?.id"
                  class="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-300">
                  {{ t("settings.aiInsights.testChatSaveHint") }}
                </p>
                <div class="flex items-end gap-2">
                  <textarea
                    ref="aiTestMessageInput"
                    v-model="aiTestMessage"
                    rows="1"
                    class="max-h-28 min-h-10 flex-1 resize-none rounded-lg border border-border bg-background px-3 py-2 text-sm leading-6 text-foreground placeholder:text-foreground-muted focus:border-transparent focus:ring-2 focus:ring-indigo-500"
                    :placeholder="t('settings.aiInsights.testPromptPlaceholder')"
                    @input="resizeAiTestMessageInput"
                    @keydown="handleAiTestMessageKeydown" />
                  <button
                    class="inline-flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                    :disabled="isTestingProvider || !aiProvider?.id || !aiTestMessage.trim()"
                    :title="isTestingProvider ? t('settings.aiInsights.testing') : t('settings.aiInsights.sendTest')"
                    @click="testAiProviderChat">
                    <PaperAirplaneIcon class="h-5 w-5" />
                  </button>
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

<style scoped>
.ai-test-markdown {
  white-space: normal;
}

.ai-test-markdown :deep(p) {
  margin: 0.35rem 0;
  white-space: pre-wrap;
}

.ai-test-markdown :deep(p:first-child),
.ai-test-markdown :deep(ul:first-child),
.ai-test-markdown :deep(ol:first-child),
.ai-test-markdown :deep(pre:first-child),
.ai-test-markdown :deep(blockquote:first-child),
.ai-test-markdown :deep(h1:first-child),
.ai-test-markdown :deep(h2:first-child),
.ai-test-markdown :deep(h3:first-child) {
  margin-top: 0;
}

.ai-test-markdown :deep(p:last-child),
.ai-test-markdown :deep(ul:last-child),
.ai-test-markdown :deep(ol:last-child),
.ai-test-markdown :deep(pre:last-child),
.ai-test-markdown :deep(blockquote:last-child) {
  margin-bottom: 0;
}

.ai-test-markdown :deep(h1),
.ai-test-markdown :deep(h2),
.ai-test-markdown :deep(h3) {
  margin: 0.8rem 0 0.35rem;
  font-weight: 700;
  line-height: 1.35;
}

.ai-test-markdown :deep(h1) {
  font-size: 1rem;
}

.ai-test-markdown :deep(h2) {
  font-size: 0.96rem;
}

.ai-test-markdown :deep(h3) {
  font-size: 0.92rem;
}

.ai-test-markdown :deep(ul),
.ai-test-markdown :deep(ol) {
  margin: 0.4rem 0;
  padding-left: 1.25rem;
}

.ai-test-markdown :deep(ul) {
  list-style: disc;
}

.ai-test-markdown :deep(ol) {
  list-style: decimal;
}

.ai-test-markdown :deep(li) {
  margin: 0.2rem 0;
}

.ai-test-markdown :deep(blockquote) {
  margin: 0.5rem 0;
  border-left: 3px solid rgb(99 102 241 / 0.45);
  padding-left: 0.75rem;
  opacity: 0.82;
}

.ai-test-markdown :deep(pre) {
  margin: 0.6rem 0;
  max-width: 100%;
  overflow-x: auto;
  border-radius: 0.5rem;
  background: rgb(15 23 42);
  padding: 0.75rem;
  color: rgb(226 232 240);
  font-size: 0.78rem;
  line-height: 1.55;
}

.ai-test-markdown :deep(pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}
</style>
