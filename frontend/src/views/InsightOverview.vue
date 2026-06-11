<script setup lang="ts">
import { computed, ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import {
  MagnifyingGlassIcon,
  ShieldCheckIcon,
  DocumentChartBarIcon,
  FireIcon,
  DocumentDuplicateIcon,
  ChatBubbleLeftRightIcon,
  ArrowRightIcon,
  FolderIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  ArrowPathIcon,
  SparklesIcon,
} from "@heroicons/vue/24/outline";
import { aiInsightsApi } from "@/api";
import PageTitle from "@/components/PageTitle.vue";
import AIInsightScopeSelector from "@/components/ai-insights/AIInsightScopeSelector.vue";

const route = useRoute();
const router = useRouter();
const { t, locale } = useI18n();

// Loading state
const isLoading = ref(true);

// Overview data
const overviewData = ref<any>(null);

const scopeType = computed(() => String(route.query.scope_type || "tenant"));
const scopeId = computed(() => String(route.query.scope_id || ""));
const scopeParams = computed(() => {
  if (!scopeType.value || scopeType.value === "tenant") {
    return { scope_type: "tenant" };
  }
  return scopeId.value
    ? { scope_type: scopeType.value, scope_id: scopeId.value }
    : { scope_type: scopeType.value };
});

// Quick access cards for AI Insights features
const quickAccessCards = computed(() => [
  {
    id: "smart-search",
    title: t("aiInsights.nav.smartSearch"),
    description: t("insightOverview.smartSearchDesc"),
    icon: MagnifyingGlassIcon,
    color: "from-violet-500 to-purple-600",
    bgColor: "bg-violet-50 dark:bg-violet-900/20",
    path: "/ai-insights/smart-search",
    stats: null,
  },
  {
    id: "sensitive-data",
    title: t("aiInsights.nav.sensitiveData"),
    description: t("insightOverview.sensitiveDataDesc"),
    icon: ShieldCheckIcon,
    color: "from-red-500 to-rose-600",
    bgColor: "bg-red-50 dark:bg-red-900/20",
    path: "/ai-insights/sensitive-data",
    stats: overviewData.value?.risk_summary?.sensitive_files
      ? `${overviewData.value.risk_summary.sensitive_files} ${t("insightOverview.files")}`
      : null,
  },
  {
    id: "content-profiling",
    title: t("aiInsights.nav.contentProfile"),
    description: t("insightOverview.contentProfileDesc"),
    icon: DocumentChartBarIcon,
    color: "from-blue-500 to-cyan-600",
    bgColor: "bg-blue-50 dark:bg-blue-900/20",
    path: "/ai-insights/content-profiling",
    stats: null,
  },
  {
    id: "data-heatmap",
    title: t("aiInsights.nav.dataHeatmap"),
    description: t("insightOverview.dataHeatmapDesc"),
    icon: FireIcon,
    color: "from-orange-500 to-amber-600",
    bgColor: "bg-orange-50 dark:bg-orange-900/20",
    path: "/ai-insights/data-heatmap",
    stats: overviewData.value?.optimization_suggestions?.cold_data?.percentage
      ? `${overviewData.value.optimization_suggestions.cold_data.percentage}% ${t("insightOverview.coldData")}`
      : null,
  },
  {
    id: "redundancy",
    title: t("aiInsights.nav.redundancy"),
    description: t("insightOverview.redundancyDesc"),
    icon: DocumentDuplicateIcon,
    color: "from-emerald-500 to-teal-600",
    bgColor: "bg-emerald-50 dark:bg-emerald-900/20",
    path: "/ai-insights/redundancy",
    stats:
      overviewData.value?.optimization_suggestions?.duplicate_files?.size ||
      null,
  },
  {
    id: "ai-chat",
    title: t("aiInsights.nav.aiChat"),
    description: t("insightOverview.aiChatDesc"),
    icon: ChatBubbleLeftRightIcon,
    color: "from-indigo-500 to-violet-600",
    bgColor: "bg-indigo-50 dark:bg-indigo-900/20",
    path: "/ai-insights/ai-chat",
    stats: null,
  },
]);

// Stats summary
const statsSummary = computed(() => [
  {
    label: t("insightOverview.totalFiles"),
    value: overviewData.value?.total_files?.toLocaleString() || "-",
    icon: FolderIcon,
    color: "text-violet-500",
  },
  {
    label: t("insightOverview.totalSize"),
    value: overviewData.value?.total_size || "-",
    icon: DocumentTextIcon,
    color: "text-blue-500",
  },
  {
    label: t("insightOverview.sensitiveFiles"),
    value: overviewData.value?.risk_summary?.sensitive_files?.toString() || "0",
    icon: ExclamationTriangleIcon,
    color: "text-red-500",
  },
  {
    label: t("insightOverview.duplicateSize"),
    value:
      overviewData.value?.optimization_suggestions?.duplicate_files?.size ||
      "-",
    icon: DocumentDuplicateIcon,
    color: "text-emerald-500",
  },
]);

// Navigate to feature
function navigateTo(path: string) {
  router.push({ path, query: { ...route.query } });
}

// Fetch overview data
async function fetchOverview() {
  isLoading.value = true;
  try {
    const response = await aiInsightsApi.overview(scopeParams.value);
    overviewData.value = response.data;
  } catch (error) {
    console.error("Failed to fetch overview:", error);
    overviewData.value = {
      total_files: 0,
      total_size: "0 B",
      file_categories: [],
      risk_summary: {
        sensitive_files: 0,
        ransomware_risk: "unknown",
        permission_issues: 0,
      },
      optimization_suggestions: {
        duplicate_files: { count: 0, size: "0 B" },
        cold_data: { size: "0 B", percentage: 0 },
        fastest_growing: { path: "-", growth_rate: 0 },
      },
    };
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  fetchOverview();
});

watch(
  () => [route.query.scope_type, route.query.scope_id],
  () => {
    fetchOverview();
  },
);
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <PageTitle
        :icon="SparklesIcon"
        :title="t('insightOverview.title')"
        :subtitle="t('insightOverview.subtitle')"
        icon-class="text-amber-600 dark:text-amber-400"
      />
      <div class="flex items-center gap-2 text-sm text-foreground-secondary">
        <ClockIcon class="w-4 h-4" />
        <span
          >{{ t("insightOverview.lastSync") }}:
          {{ new Date().toLocaleString() }}</span
        >
      </div>
    </div>

    <AIInsightScopeSelector />

    <!-- Stats Summary -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <ArrowPathIcon class="w-8 h-8 text-slate-400 animate-spin" />
    </div>
    <template v-else>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          v-for="stat in statsSummary"
          :key="stat.label"
          class="bg-card rounded-xl border border-border p-5">
          <div class="flex items-center gap-3">
            <component :is="stat.icon" :class="['w-5 h-5', stat.color]" />
            <span class="text-sm text-foreground-secondary">{{
              stat.label
            }}</span>
          </div>
          <p class="text-2xl font-bold text-foreground mt-2">
            {{ stat.value }}
          </p>
        </div>
      </div>

      <!-- File Categories Overview -->
      <div class="bg-card rounded-xl border border-border p-6">
        <h2 class="text-lg font-semibold text-foreground mb-4">
          {{ t("insightOverview.fileCategories") }}
        </h2>
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div
            v-for="cat in overviewData?.file_categories"
            :key="cat.name"
            class="text-center p-4 bg-background-secondary rounded-lg">
            <p class="text-2xl font-bold text-foreground">
              {{ cat.percentage }}%
            </p>
            <p class="text-sm text-foreground-secondary mt-1">
              {{ locale === "zh-CN" ? cat.name_zh : cat.name }}
            </p>
            <p class="text-xs text-foreground-muted">{{ cat.size }}</p>
          </div>
        </div>
      </div>

      <!-- Quick Access Cards -->
      <div>
        <h2
          class="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
          <SparklesIcon class="w-5 h-5 text-violet-500" />
          {{ t("insightOverview.quickAccess") }}
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="card in quickAccessCards"
            :key="card.id"
            @click="navigateTo(card.path)"
            class="group bg-card rounded-xl border border-border p-5 cursor-pointer hover:border-violet-300 dark:hover:border-violet-700 hover:shadow-lg transition-all">
            <div class="flex items-start justify-between">
              <div
                :class="[
                  'w-12 h-12 rounded-lg flex items-center justify-center bg-gradient-to-br',
                  card.color,
                ]">
                <component :is="card.icon" class="w-6 h-6 text-white" />
              </div>
              <ArrowRightIcon
                class="w-5 h-5 text-slate-300 group-hover:text-violet-500 transition-colors" />
            </div>
            <h3 class="text-base font-semibold text-foreground mt-4">
              {{ card.title }}
            </h3>
            <p class="text-sm text-foreground-secondary mt-1">
              {{ card.description }}
            </p>
            <div
              v-if="card.stats"
              class="mt-3 px-2 py-1 rounded bg-background-tertiary inline-block">
              <span class="text-xs font-medium text-foreground-secondary">{{
                card.stats
              }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Risk & Optimization Summary -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Risk Summary -->
        <div class="bg-card rounded-xl border border-border p-6">
          <h2 class="text-lg font-semibold text-foreground mb-4">
            {{ t("insightOverview.riskSummary") }}
          </h2>
          <div class="space-y-3">
            <div
              class="flex items-center justify-between p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
              <div class="flex items-center gap-3">
                <ExclamationTriangleIcon class="w-5 h-5 text-amber-500" />
                <span class="text-sm text-amber-700 dark:text-amber-300">{{
                  t("insightOverview.sensitiveInfo")
                }}</span>
              </div>
              <span
                class="text-sm font-semibold text-amber-600 dark:text-amber-400"
                >{{ overviewData?.risk_summary?.sensitive_files || 0 }}
                {{ t("insightOverview.files") }}</span
              >
            </div>
            <div
              class="flex items-center justify-between p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
              <div class="flex items-center gap-3">
                <ShieldCheckIcon class="w-5 h-5 text-emerald-500" />
                <span class="text-sm text-emerald-700 dark:text-emerald-300">{{
                  t("insightOverview.ransomwareRisk")
                }}</span>
              </div>
              <span
                class="text-sm font-semibold text-emerald-600 dark:text-emerald-400"
                >{{ t("insightOverview.safe") }}</span
              >
            </div>
          </div>
        </div>

        <!-- Optimization Suggestions -->
        <div class="bg-card rounded-xl border border-border p-6">
          <h2 class="text-lg font-semibold text-foreground mb-4">
            {{ t("insightOverview.optimizationSuggestions") }}
          </h2>
          <div class="space-y-3">
            <div
              class="flex items-center justify-between p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <div class="flex items-center gap-3">
                <DocumentDuplicateIcon class="w-5 h-5 text-red-500" />
                <span class="text-sm text-red-700 dark:text-red-300">{{
                  t("insightOverview.duplicateFiles")
                }}</span>
              </div>
              <span
                class="text-sm font-semibold text-red-600 dark:text-red-400"
                >{{
                  overviewData?.optimization_suggestions?.duplicate_files
                    ?.size || "-"
                }}</span
              >
            </div>
            <div
              class="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <div class="flex items-center gap-3">
                <FireIcon class="w-5 h-5 text-blue-500" />
                <span class="text-sm text-blue-700 dark:text-blue-300">{{
                  t("insightOverview.coldData")
                }}</span>
              </div>
              <span
                class="text-sm font-semibold text-blue-600 dark:text-blue-400"
                >{{
                  overviewData?.optimization_suggestions?.cold_data
                    ?.percentage || 0
                }}%</span
              >
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
