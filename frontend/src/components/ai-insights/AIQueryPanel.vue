<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { ArrowPathIcon, ChatBubbleLeftRightIcon } from "@heroicons/vue/24/outline";
import { aiInsightsApi } from "@/api";

type QueryRecord = {
  id: string;
  query_text: string;
  status: "pending" | "processing" | "completed" | "failed";
  result?: Record<string, any>;
  error_message?: string;
};

const { t } = useI18n();

const queryText = ref("");
const isSubmitting = ref(false);
const activeQuery = ref<QueryRecord | null>(null);
const pollTimer = ref<number | null>(null);

const answer = computed(() => {
  const result = activeQuery.value?.result || {};
  return result.answer || result.summary || "";
});

const sources = computed(() => {
  const result = activeQuery.value?.result || {};
  return Array.isArray(result.sources) ? result.sources : [];
});

function clearTimer() {
  if (pollTimer.value) {
    window.clearTimeout(pollTimer.value);
    pollTimer.value = null;
  }
}

async function pollQuery(id: string) {
  clearTimer();
  try {
    const response = await aiInsightsApi.getQuery(id);
    activeQuery.value = response.data;
    if (["pending", "processing"].includes(activeQuery.value?.status || "")) {
      pollTimer.value = window.setTimeout(() => pollQuery(id), 2000);
    }
  } catch (error) {
    console.error("Failed to poll AI query:", error);
  }
}

async function submitQuery() {
  const text = queryText.value.trim();
  if (!text || isSubmitting.value) return;
  isSubmitting.value = true;
  clearTimer();
  try {
    const response = await aiInsightsApi.query({
      query_text: text,
      query_type: "search",
    });
    activeQuery.value = response.data;
    queryText.value = "";
    if (activeQuery.value?.id) {
      await pollQuery(activeQuery.value.id);
    }
  } catch (error: any) {
    activeQuery.value = {
      id: "",
      query_text: text,
      status: "failed",
      error_message: error?.response?.data?.error || error?.message || t("aiInsights.chat.failed"),
    };
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <div class="space-y-5">
    <div class="bg-card border border-border rounded-xl p-6">
      <div class="flex items-center gap-3 mb-5">
        <div class="w-10 h-10 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
          <ChatBubbleLeftRightIcon class="w-5 h-5 text-violet-600 dark:text-violet-400" />
        </div>
        <div>
          <h3 class="text-lg font-semibold text-foreground">
            {{ t("aiInsights.chat.title") }}
          </h3>
          <p class="text-sm text-foreground-secondary">
            {{ t("aiInsights.chat.description") }}
          </p>
        </div>
      </div>

      <div class="flex gap-3">
        <input
          v-model="queryText"
          type="text"
          :placeholder="t('aiInsights.chat.placeholder')"
          class="flex-1 px-4 py-3 bg-background-secondary border border-border rounded-lg text-foreground placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500"
          @keyup.enter="submitQuery" />
        <button
          class="px-5 py-3 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          :disabled="isSubmitting || !queryText.trim()"
          @click="submitQuery">
          <ArrowPathIcon v-if="isSubmitting" class="w-5 h-5 animate-spin" />
          <ChatBubbleLeftRightIcon v-else class="w-5 h-5" />
          {{ t("aiInsights.chat.ask") }}
        </button>
      </div>
    </div>

    <div v-if="activeQuery" class="bg-card border border-border rounded-xl p-6">
      <div class="flex items-center justify-between mb-4">
        <h4 class="text-sm font-semibold text-foreground">
          {{ activeQuery.query_text }}
        </h4>
        <span
          class="px-2.5 py-1 text-xs font-medium rounded-full"
          :class="{
            'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300': ['pending', 'processing'].includes(activeQuery.status),
            'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300': activeQuery.status === 'completed',
            'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300': activeQuery.status === 'failed',
          }">
          {{ t(`aiInsights.chat.status.${activeQuery.status}`) }}
        </span>
      </div>

      <div v-if="['pending', 'processing'].includes(activeQuery.status)" class="flex items-center gap-2 text-sm text-foreground-secondary">
        <ArrowPathIcon class="w-4 h-4 animate-spin" />
        {{ t("aiInsights.chat.processing") }}
      </div>
      <div v-else-if="activeQuery.status === 'failed'" class="text-sm text-red-600 dark:text-red-400">
        {{ activeQuery.error_message || t("aiInsights.chat.failed") }}
      </div>
      <div v-else class="space-y-5">
        <p class="text-sm leading-6 text-foreground-secondary whitespace-pre-wrap">
          {{ answer || t("aiInsights.chat.noAnswer") }}
        </p>

        <div v-if="sources.length" class="space-y-2">
          <h5 class="text-xs font-semibold uppercase tracking-wide text-foreground-muted">
            {{ t("aiInsights.chat.sources") }}
          </h5>
          <div
            v-for="source in sources"
            :key="`${source.snapshot_name}-${source.path}`"
            class="p-3 bg-background-secondary rounded-lg">
            <p class="text-sm font-medium text-foreground truncate">
              {{ source.path }}
            </p>
            <p class="text-xs text-foreground-muted truncate">
              {{ source.snapshot_name || "-" }} · {{ source.repository_name || "-" }} · {{ source.reason || "-" }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
