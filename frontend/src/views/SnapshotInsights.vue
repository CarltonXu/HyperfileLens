<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  ChartBarIcon,
  CircleStackIcon,
  DocumentMagnifyingGlassIcon,
  ExclamationTriangleIcon,
  FolderIcon,
  MagnifyingGlassIcon,
  SparklesIcon,
} from "@heroicons/vue/24/outline";
import { backupTasksApi, insightsApi } from "@/api";
import PageTitle from "@/components/PageTitle.vue";
import { useAppStore } from "@/stores/app";
import { getApiErrorMessage } from "@/utils/errors";

const route = useRoute();
const router = useRouter();
const { t, locale } = useI18n();
const appStore = useAppStore();

const snapshotId = computed(() => String(route.params.snapshotId || ""));
const loading = ref(true);
const indexing = ref(false);
const analyzing = ref(false);
const aiSummarizing = ref(false);
const snapshot = ref<any>(null);
const indexJob = ref<any>(null);
const aiJobs = ref<any[]>([]);
const insights = ref<any[]>([]);
const searchQuery = ref("");
const searchResults = ref<any[]>([]);
const indexPollTimer = ref<ReturnType<typeof setInterval> | null>(null);

function formatBytes(value?: number | string | null) {
  const bytes = Number(value || 0);
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const size = bytes / 1024 ** index;
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function insightByType(type: string) {
  return insights.value.find((item) => item.insight_type === type);
}

const categoryInsight = computed(() => insightByType("file_categories"));
const largeFilesInsight = computed(() => insightByType("large_files"));
const duplicateInsight = computed(() => insightByType("duplicates"));
const coldDataInsight = computed(() => insightByType("cold_data"));
const growthInsight = computed(() => insightByType("growth"));
const aiSummaryInsight = computed(() => insightByType("ai_summary"));
const latestAiJob = computed(() => aiJobs.value[0] || null);
const activeIndexStatuses = new Set(["pending", "dispatched", "running"]);
const indexJobActive = computed(() =>
  activeIndexStatuses.has(indexJob.value?.status || ""),
);

function stopIndexPolling() {
  if (indexPollTimer.value) {
    clearInterval(indexPollTimer.value);
    indexPollTimer.value = null;
  }
}

function startIndexPolling() {
  if (indexPollTimer.value) return;
  indexPollTimer.value = setInterval(fetchIndexStatus, 3000);
}

async function fetchIndexStatus() {
  try {
    const response = await insightsApi.indexStatus(snapshotId.value);
    indexJob.value = response.data?.status === "not_indexed" ? null : response.data;
    if (!indexJobActive.value) {
      stopIndexPolling();
      const [insightsResponse, aiJobsResponse] = await Promise.all([
        insightsApi.insights(snapshotId.value),
        insightsApi.aiJobs(snapshotId.value),
      ]);
      insights.value = insightsResponse.data || [];
      aiJobs.value = aiJobsResponse.data || [];
    }
  } catch (error) {
    stopIndexPolling();
    appStore.error(getApiErrorMessage(error, t("snapshotInsights.loadFailed")));
  }
}

async function fetchAll() {
  loading.value = true;
  try {
    const [snapshotResponse, statusResponse, insightsResponse, aiJobsResponse] = await Promise.all([
      backupTasksApi.snapshotDetail(snapshotId.value),
      insightsApi.indexStatus(snapshotId.value),
      insightsApi.insights(snapshotId.value),
      insightsApi.aiJobs(snapshotId.value),
    ]);
    snapshot.value = snapshotResponse.data;
    indexJob.value = statusResponse.data?.status === "not_indexed" ? null : statusResponse.data;
    insights.value = insightsResponse.data || [];
    aiJobs.value = aiJobsResponse.data || [];
    if (indexJobActive.value) {
      startIndexPolling();
    } else {
      stopIndexPolling();
    }
  } catch (error) {
    appStore.error(getApiErrorMessage(error, t("snapshotInsights.loadFailed")));
  } finally {
    loading.value = false;
  }
}

async function startIndex(force = false) {
  indexing.value = true;
  try {
    const response = await insightsApi.indexSnapshot(snapshotId.value, { force });
    indexJob.value = response.data;
    startIndexPolling();
    appStore.success(t("snapshotInsights.indexStarted"));
  } catch (error) {
    appStore.error(getApiErrorMessage(error, t("snapshotInsights.indexFailed")));
  } finally {
    indexing.value = false;
  }
}

async function runAnalyze() {
  analyzing.value = true;
  try {
    const response = await insightsApi.analyze(snapshotId.value);
    insights.value = response.data || [];
    appStore.success(t("snapshotInsights.analyzeCompleted"));
  } catch (error) {
    appStore.error(getApiErrorMessage(error, t("snapshotInsights.analyzeFailed")));
  } finally {
    analyzing.value = false;
  }
}

async function generateAiSummary() {
  aiSummarizing.value = true;
  try {
    const response = await insightsApi.aiSummary(snapshotId.value, { language: locale.value });
    aiJobs.value = [response.data, ...aiJobs.value];
    appStore.success(t("snapshotInsights.aiSummaryStarted"));
  } catch (error) {
    appStore.error(getApiErrorMessage(error, t("snapshotInsights.aiSummaryFailed")));
  } finally {
    aiSummarizing.value = false;
  }
}

async function search() {
  if (!searchQuery.value.trim()) {
    searchResults.value = [];
    return;
  }
  try {
    const response = await insightsApi.search(snapshotId.value, { q: searchQuery.value, limit: 50 });
    searchResults.value = response.data.results || [];
  } catch (error) {
    appStore.error(getApiErrorMessage(error, t("snapshotInsights.searchFailed")));
  }
}

function openAIInsightsForSnapshot() {
  router.push({
    path: "/ai-insights/overview",
    query: {
      scope_type: "snapshot",
      scope_id: snapshotId.value,
      scope_name: snapshot.value?.name || snapshot.value?.version || snapshotId.value,
    },
  });
}

onMounted(fetchAll);
onUnmounted(stopIndexPolling);
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <PageTitle
        :icon="DocumentMagnifyingGlassIcon"
        :title="t('snapshotInsights.title')"
        :subtitle="snapshot?.name || snapshot?.version || snapshotId"
        icon-class="text-amber-600 dark:text-amber-400"
      />
      <div class="flex flex-wrap gap-2">
        <button class="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:bg-hover" @click="fetchAll">
          <ArrowPathIcon class="h-4 w-4" />
          {{ t("common.refresh") }}
        </button>
        <button class="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:bg-hover disabled:opacity-50" :disabled="indexing" @click="startIndex(true)">
          <CircleStackIcon class="h-4 w-4" />
          {{ t("snapshotInsights.indexSnapshot") }}
        </button>
        <button class="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary/90 disabled:opacity-50" :disabled="analyzing || !indexJob" @click="runAnalyze">
          <ChartBarIcon class="h-4 w-4" />
          {{ t("snapshotInsights.analyze") }}
        </button>
        <button class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50" :disabled="aiSummarizing || !indexJob" @click="generateAiSummary">
          <SparklesIcon class="h-4 w-4" />
          {{ t("snapshotInsights.generateAiSummary") }}
        </button>
        <button class="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium hover:bg-hover" @click="openAIInsightsForSnapshot">
          <DocumentMagnifyingGlassIcon class="h-4 w-4" />
          AI Insights
        </button>
      </div>
    </div>

    <div v-if="loading" class="rounded-lg border border-border bg-card p-8 text-center text-sm text-foreground-secondary">
      {{ t("common.loading") }}
    </div>

    <template v-else>
      <section class="grid gap-4 md:grid-cols-4">
        <div class="rounded-lg border border-border bg-card p-4">
          <p class="text-xs text-foreground-muted">{{ t("snapshotInsights.indexStatus") }}</p>
          <p class="mt-2 text-lg font-semibold text-foreground">{{ indexJob?.status || t("snapshotInsights.notIndexed") }}</p>
          <div v-if="indexJob" class="mt-3 h-2 rounded-full bg-background-tertiary">
            <div class="h-full rounded-full bg-primary" :style="{ width: `${indexJob.progress || 0}%` }" />
          </div>
        </div>
        <div class="rounded-lg border border-border bg-card p-4">
          <p class="text-xs text-foreground-muted">{{ t("snapshotInsights.indexedFiles") }}</p>
          <p class="mt-2 text-lg font-semibold text-foreground">{{ indexJob?.indexed_files || 0 }}</p>
        </div>
        <div class="rounded-lg border border-border bg-card p-4">
          <p class="text-xs text-foreground-muted">{{ t("snapshotInsights.indexedBytes") }}</p>
          <p class="mt-2 text-lg font-semibold text-foreground">{{ formatBytes(indexJob?.indexed_bytes) }}</p>
        </div>
        <div class="rounded-lg border border-border bg-card p-4">
          <p class="text-xs text-foreground-muted">{{ t("snapshotInsights.lastUpdated") }}</p>
          <p class="mt-2 text-sm font-medium text-foreground">{{ formatDate(indexJob?.updated_at) }}</p>
        </div>
      </section>

      <section v-if="indexJob?.error_message" class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/20 dark:text-red-300">
        <div class="flex gap-2">
          <ExclamationTriangleIcon class="h-5 w-5" />
          <span>{{ indexJob.error_message }}</span>
        </div>
      </section>

      <section class="rounded-lg border border-border bg-card p-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <h2 class="inline-flex items-center gap-2 text-base font-semibold text-foreground">
            <SparklesIcon class="h-5 w-5 text-indigo-500" />
            {{ t("snapshotInsights.aiSummary") }}
          </h2>
          <div v-if="latestAiJob" class="min-w-48 text-right text-xs text-foreground-secondary">
            <p>{{ t("snapshotInsights.latestAiJob") }}: <span class="font-medium text-foreground">{{ latestAiJob.status }}</span></p>
            <div class="mt-2 h-1.5 rounded-full bg-background-tertiary">
              <div class="h-full rounded-full bg-indigo-500" :style="{ width: `${latestAiJob.progress || 0}%` }" />
            </div>
          </div>
        </div>

        <div v-if="aiSummaryInsight" class="mt-4 space-y-4">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <p class="text-sm font-semibold text-foreground">{{ aiSummaryInsight.title }}</p>
              <span class="rounded-full border border-border px-2 py-0.5 text-xs uppercase text-foreground-secondary">
                {{ aiSummaryInsight.severity }}
              </span>
              <span class="rounded-full bg-background-tertiary px-2 py-0.5 text-xs text-foreground-secondary">
                {{ aiSummaryInsight.evidence?.provider || latestAiJob?.provider || "-" }} / {{ aiSummaryInsight.evidence?.model || latestAiJob?.model || "-" }}
              </span>
            </div>
            <p class="mt-2 text-sm leading-6 text-foreground-secondary">{{ aiSummaryInsight.summary || "-" }}</p>
          </div>

          <div v-if="aiSummaryInsight.evidence?.findings?.length" class="grid gap-3 lg:grid-cols-2">
            <div v-for="finding in aiSummaryInsight.evidence.findings" :key="finding.title" class="rounded-lg border border-border bg-background/40 p-3">
              <p class="text-sm font-medium text-foreground">{{ finding.title }}</p>
              <p class="mt-1 text-xs leading-5 text-foreground-secondary">{{ finding.description }}</p>
            </div>
          </div>

          <div v-if="aiSummaryInsight.recommended_actions?.length" class="border-t border-border pt-3">
            <p class="text-xs font-medium uppercase text-foreground-muted">{{ t("snapshotInsights.recommendedActions") }}</p>
            <div class="mt-2 space-y-2">
              <div v-for="action in aiSummaryInsight.recommended_actions" :key="action.type || action.label" class="text-sm">
                <p class="font-medium text-foreground">{{ action.label || action.type }}</p>
                <p class="text-xs text-foreground-secondary">{{ action.description }}</p>
              </div>
            </div>
          </div>

          <div v-if="aiSummaryInsight.related_paths?.length" class="border-t border-border pt-3">
            <p class="text-xs font-medium uppercase text-foreground-muted">{{ t("snapshotInsights.relatedPaths") }}</p>
            <div class="mt-2 max-h-28 overflow-auto rounded-lg border border-border">
              <p v-for="path in aiSummaryInsight.related_paths" :key="path" class="truncate border-b border-border px-3 py-2 text-xs text-foreground-secondary last:border-b-0">
                {{ path }}
              </p>
            </div>
          </div>
        </div>

        <div v-else class="mt-4 rounded-lg border border-dashed border-border p-5 text-sm text-foreground-secondary">
          {{ t("snapshotInsights.noAiSummary") }}
        </div>

        <p v-if="latestAiJob?.error_message" class="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/20 dark:text-red-300">
          {{ latestAiJob.error_message }}
        </p>
      </section>

      <section class="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div class="rounded-lg border border-border bg-card p-4">
          <h2 class="inline-flex items-center gap-2 text-base font-semibold text-foreground">
            <FolderIcon class="h-5 w-5 text-primary" />
            {{ t("snapshotInsights.fileCategories") }}
          </h2>
          <div class="mt-4 space-y-2">
            <div v-for="item in categoryInsight?.evidence?.categories || []" :key="item.category" class="flex items-center justify-between text-sm">
              <span class="capitalize text-foreground-secondary">{{ item.category }}</span>
              <span class="font-medium text-foreground">{{ item.count }} · {{ formatBytes(item.size) }}</span>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-border bg-card p-4">
          <h2 class="inline-flex items-center gap-2 text-base font-semibold text-foreground">
            <ChartBarIcon class="h-5 w-5 text-primary" />
            {{ t("snapshotInsights.growthTrend") }}
          </h2>
          <dl class="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt class="text-foreground-muted">{{ t("snapshotInsights.fileDelta") }}</dt>
              <dd class="mt-1 font-semibold text-foreground">{{ growthInsight?.evidence?.file_delta ?? "-" }}</dd>
            </div>
            <div>
              <dt class="text-foreground-muted">{{ t("snapshotInsights.sizeDelta") }}</dt>
              <dd class="mt-1 font-semibold text-foreground">{{ formatBytes(growthInsight?.evidence?.size_delta) }}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section class="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div class="rounded-lg border border-border bg-card p-4">
          <h2 class="text-base font-semibold text-foreground">{{ t("snapshotInsights.largeFiles") }}</h2>
          <div class="mt-4 max-h-72 overflow-auto rounded-lg border border-border">
            <div v-for="file in largeFilesInsight?.evidence?.files || []" :key="file.path" class="border-b border-border px-3 py-2 text-sm last:border-b-0">
              <p class="truncate font-medium text-foreground">{{ file.name }}</p>
              <p class="mt-1 truncate text-xs text-foreground-secondary">{{ file.path }} · {{ formatBytes(file.size) }}</p>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-border bg-card p-4">
          <h2 class="text-base font-semibold text-foreground">{{ t("snapshotInsights.duplicates") }}</h2>
          <div class="mt-4 max-h-72 overflow-auto rounded-lg border border-border">
            <div v-for="group in duplicateInsight?.evidence?.groups || []" :key="group.paths?.[0]" class="border-b border-border px-3 py-2 text-sm last:border-b-0">
              <p class="font-medium text-foreground">{{ group.count }} {{ t("snapshotInsights.candidates") }} · {{ formatBytes(group.size) }}</p>
              <p class="mt-1 truncate text-xs text-foreground-secondary">{{ group.paths?.[0] }}</p>
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-border bg-card p-4">
        <h2 class="inline-flex items-center gap-2 text-base font-semibold text-foreground">
          <DocumentMagnifyingGlassIcon class="h-5 w-5 text-primary" />
          {{ t("snapshotInsights.smartSearch") }}
        </h2>
        <div class="mt-4 flex gap-2">
          <div class="relative flex-1">
            <MagnifyingGlassIcon class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted" />
            <input v-model="searchQuery" class="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm" :placeholder="t('snapshotInsights.searchPlaceholder')" @keydown.enter="search" />
          </div>
          <button class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90" @click="search">
            {{ t("common.search") }}
          </button>
        </div>
        <div class="mt-4 rounded-lg border border-border">
          <div v-for="file in searchResults" :key="file.id" class="border-b border-border px-3 py-2 text-sm last:border-b-0">
            <p class="font-medium text-foreground">{{ file.name }}</p>
            <p class="mt-1 truncate text-xs text-foreground-secondary">{{ file.path }} · {{ file.category }} · {{ formatBytes(file.size) }}</p>
          </div>
          <p v-if="searchResults.length === 0" class="px-3 py-8 text-center text-sm text-foreground-secondary">
            {{ t("snapshotInsights.noSearchResults") }}
          </p>
        </div>
      </section>

      <section class="rounded-lg border border-border bg-card p-4">
        <h2 class="text-base font-semibold text-foreground">{{ t("snapshotInsights.coldData") }}</h2>
        <p class="mt-2 text-sm text-foreground-secondary">{{ coldDataInsight?.summary || "-" }}</p>
        <p class="mt-3 text-lg font-semibold text-foreground">{{ formatBytes(coldDataInsight?.evidence?.size) }}</p>
      </section>
    </template>
  </div>
</template>
