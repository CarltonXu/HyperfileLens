<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  PaperAirplaneIcon,
} from "@heroicons/vue/24/outline";
import { aiInsightsApi } from "@/api";

type Source = {
  path?: string;
  snapshot_name?: string;
  repository_name?: string;
  reason?: string;
};

const props = defineProps<{
  scope?: { scope_type?: string; scope_id?: string };
  scopeLabel?: string;
}>();

const { t } = useI18n();

const queryText = ref("");
const isStreaming = ref(false);
const answer = ref("");
const errorMessage = ref("");
const activeQueryId = ref("");
const providerMeta = ref<Record<string, any> | null>(null);
const candidateCount = ref<number | null>(null);
const sources = ref<Source[]>([]);

const canSubmit = computed(() => queryText.value.trim().length > 0 && !isStreaming.value);

function getCsrfToken(): string | null {
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith("csrftoken="));
  return cookie ? decodeURIComponent(cookie.substring("csrftoken=".length)) : null;
}

function parseSsePayload(raw: string) {
  return raw
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim())
    .filter(Boolean);
}

async function submitQuery() {
  const text = queryText.value.trim();
  if (!text || isStreaming.value) return;

  isStreaming.value = true;
  answer.value = "";
  errorMessage.value = "";
  activeQueryId.value = "";
  providerMeta.value = null;
  candidateCount.value = null;
  sources.value = [];

  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    };
    const token = localStorage.getItem("token");
    if (token) headers.Authorization = `Token ${token}`;
    const csrf = getCsrfToken();
    if (csrf) headers["X-CSRFToken"] = csrf;

    const response = await fetch(aiInsightsApi.queryStreamUrl(), {
      method: "POST",
      headers,
      body: JSON.stringify({
        query_text: text,
        query_type: "search",
        ...(props.scope || {}),
      }),
    });

    if (!response.ok || !response.body) {
      const body = await response.text();
      throw new Error(body || `Request failed: ${response.status}`);
    }

    queryText.value = "";
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";

      for (const event of events) {
        for (const payload of parseSsePayload(event)) {
          const data = JSON.parse(payload);
          if (data.type === "query") {
            activeQueryId.value = data.query_id || "";
            candidateCount.value = Number(data.candidate_count || 0);
          } else if (data.type === "meta") {
            providerMeta.value = data;
          } else if (data.type === "delta") {
            answer.value += data.content || "";
          } else if (data.type === "done") {
            if (data.query_id) activeQueryId.value = data.query_id;
            if (!answer.value && data.answer) answer.value = data.answer;
          } else if (data.type === "error") {
            errorMessage.value = data.error || "AI query failed";
          }
        }
      }
    }

    if (activeQueryId.value) {
      try {
        const saved = await aiInsightsApi.getQuery(activeQueryId.value);
        const result = saved.data?.result || {};
        sources.value = Array.isArray(result.sources) ? result.sources : [];
        if (!answer.value) answer.value = result.answer || result.summary || "";
        providerMeta.value = providerMeta.value || {
          provider: result.provider,
          model: result.model || saved.data?.model_used,
        };
      } catch (error) {
        console.error("Failed to load saved AI query:", error);
      }
    }
  } catch (error: any) {
    errorMessage.value = error?.message || t("aiInsights.chat.failed");
  } finally {
    isStreaming.value = false;
  }
}
</script>

<template>
  <div class="space-y-5">
    <div class="rounded-lg border border-border bg-card p-5">
      <div class="mb-4 flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <ChatBubbleLeftRightIcon class="h-6 w-6 text-primary" />
          <div>
            <h3 class="text-base font-semibold text-foreground">
              {{ t("aiInsights.chat.title") }}
            </h3>
            <p class="text-sm text-foreground-secondary">
              {{ t("aiInsights.chat.description") }}
            </p>
          </div>
        </div>
        <div v-if="providerMeta || candidateCount !== null" class="text-right text-xs text-foreground-muted">
          <p v-if="scopeLabel">{{ scopeLabel }}</p>
          <p v-if="providerMeta">
            {{ providerMeta.provider || "local" }} / {{ providerMeta.model || "-" }}
          </p>
          <p v-if="candidateCount !== null">{{ candidateCount }} candidate files</p>
        </div>
      </div>

      <div class="flex items-end gap-3">
        <textarea
          v-model="queryText"
          rows="2"
          :placeholder="t('aiInsights.chat.placeholder')"
          class="min-h-[44px] flex-1 resize-y rounded-lg border border-border bg-background px-3 py-2 text-sm leading-6 text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-primary/40"
          @keydown.enter.exact.prevent="submitQuery"
        />
        <button
          class="inline-flex h-11 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="!canSubmit"
          @click="submitQuery"
        >
          <ArrowPathIcon v-if="isStreaming" class="h-4 w-4 animate-spin" />
          <PaperAirplaneIcon v-else class="h-4 w-4" />
          {{ t("aiInsights.chat.ask") }}
        </button>
      </div>
    </div>

    <div v-if="isStreaming || answer || errorMessage" class="rounded-lg border border-border bg-card p-5">
      <div v-if="isStreaming && !answer" class="flex items-center gap-2 text-sm text-foreground-secondary">
        <span class="inline-flex h-2 w-2 animate-pulse rounded-full bg-primary" />
        {{ t("aiInsights.chat.processing") }}
      </div>

      <div v-if="errorMessage" class="flex items-start gap-2 text-sm text-red-600 dark:text-red-400">
        <ExclamationTriangleIcon class="mt-0.5 h-4 w-4 shrink-0" />
        <span>{{ errorMessage }}</span>
      </div>

      <div v-if="answer" class="space-y-5">
        <p class="whitespace-pre-wrap text-sm leading-7 text-foreground-secondary">
          {{ answer }}<span v-if="isStreaming" class="ml-1 inline-block h-4 w-1 animate-pulse bg-primary align-[-2px]" />
        </p>

        <div v-if="sources.length" class="space-y-2">
          <h5 class="text-xs font-semibold uppercase text-foreground-muted">
            {{ t("aiInsights.chat.sources") }}
          </h5>
          <div
            v-for="source in sources"
            :key="`${source.snapshot_name}-${source.path}`"
            class="rounded-lg bg-background-secondary p-3"
          >
            <div class="flex items-start gap-2">
              <DocumentTextIcon class="mt-0.5 h-4 w-4 shrink-0 text-foreground-muted" />
              <div class="min-w-0">
                <p class="truncate text-sm font-medium text-foreground">{{ source.path }}</p>
                <p class="truncate text-xs text-foreground-muted">
                  {{ source.snapshot_name || "-" }} · {{ source.repository_name || "-" }} · {{ source.reason || "-" }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
