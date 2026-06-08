<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import {
  FolderIcon,
  DocumentTextIcon,
  ShieldExclamationIcon,
  DocumentDuplicateIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  TrashIcon,
  ClockIcon,
  ArrowTrendingUpIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  TagIcon,
  FireIcon,
  ServerIcon,
} from "@heroicons/vue/24/outline";
import { aiInsightsApi } from "@/api";
import AIQueryPanel from "@/components/ai-insights/AIQueryPanel.vue";

const route = useRoute();
const { t, locale } = useI18n();

// Gateway status
const gatewayStatus = ref<"checking" | "online" | "offline">("checking");

// Loading states
const isLoadingOverview = ref(false);
const isLoadingSensitive = ref(false);
const isLoadingProfile = ref(false);
const isLoadingHeatmap = ref(false);
const isLoadingRedundancy = ref(false);
const isSearching = ref(false);

// Data
const overviewData = ref<any>(null);
const sensitiveData = ref<any>(null);
const contentProfile = ref<any>(null);
const dataHeatmap = ref<any>(null);
const redundancyData = ref<any>(null);

// Search
const searchQuery = ref("");
const searchResults = ref<any[]>([]);
const hasSearched = ref(false);

// Current tab from route
const currentTab = computed(() => {
  // Get tab from route meta
  return (route.meta?.tab as string) || "overview";
});

// Page title based on current tab
const pageTitle = computed(() => {
  const titleKeys: Record<string, string> = {
    overview: "aiInsights.pageTitles.overview",
    search: "aiInsights.pageTitles.search",
    sensitive: "aiInsights.pageTitles.sensitive",
    profile: "aiInsights.pageTitles.profile",
    heatmap: "aiInsights.pageTitles.heatmap",
    redundancy: "aiInsights.pageTitles.redundancy",
    chat: "aiInsights.pageTitles.chat",
  };
  const key = titleKeys[currentTab.value];
  return key ? t(key) : "AI Insights";
});

// Format bytes
function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

// Get severity color
function getSeverityColor(severity: string): string {
  const colors: Record<string, string> = {
    high: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    medium:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    low: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  };
  return colors[severity] || colors.low;
}

// Fetch data based on current tab
async function fetchData() {
  switch (currentTab.value) {
    case "overview":
      await fetchOverview();
      break;
    case "sensitive":
      await fetchSensitiveData();
      break;
    case "profile":
      await fetchContentProfile();
      break;
    case "heatmap":
      await fetchDataHeatmap();
      break;
    case "redundancy":
      await fetchRedundancy();
      break;
  }
}

async function fetchOverview() {
  if (overviewData.value) return;
  isLoadingOverview.value = true;
  try {
    const response = await aiInsightsApi.overview();
    overviewData.value = response.data;
    gatewayStatus.value = "online";
  } catch (error) {
    console.error("Failed to fetch overview:", error);
    gatewayStatus.value = "offline";
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
    isLoadingOverview.value = false;
  }
}

async function fetchSensitiveData() {
  if (sensitiveData.value) return;
  isLoadingSensitive.value = true;
  try {
    const response = await aiInsightsApi.sensitiveData();
    sensitiveData.value = response.data;
  } catch (error) {
    console.error("Failed to fetch sensitive data:", error);
    sensitiveData.value = {
      last_scan: "-",
      findings: [],
      summary: { high: 0, medium: 0, low: 0, total_findings: 0 },
    };
  } finally {
    isLoadingSensitive.value = false;
  }
}

async function fetchContentProfile() {
  if (contentProfile.value) return;
  isLoadingProfile.value = true;
  try {
    const response = await aiInsightsApi.contentProfiling();
    contentProfile.value = response.data;
  } catch (error) {
    console.error("Failed to fetch content profile:", error);
    contentProfile.value = {
      categories: [],
      auto_tags: [],
    };
  } finally {
    isLoadingProfile.value = false;
  }
}

async function fetchDataHeatmap() {
  if (dataHeatmap.value) return;
  isLoadingHeatmap.value = true;
  try {
    const response = await aiInsightsApi.dataHeatmap();
    dataHeatmap.value = response.data;
  } catch (error) {
    console.error("Failed to fetch data heatmap:", error);
    dataHeatmap.value = {
      heatmap: [],
      zombie_data: {
        description: "-",
        size: "0 B",
        file_count: 0,
        potential_savings: "-",
      },
    };
  } finally {
    isLoadingHeatmap.value = false;
  }
}

async function fetchRedundancy() {
  if (redundancyData.value) return;
  isLoadingRedundancy.value = true;
  try {
    const response = await aiInsightsApi.redundancy();
    redundancyData.value = response.data;
  } catch (error) {
    console.error("Failed to fetch redundancy:", error);
    redundancyData.value = {
      total_duplicates: 0,
      duplicate_size: "0 B",
      potential_savings: "0 B",
      duplicate_groups: [],
    };
  } finally {
    isLoadingRedundancy.value = false;
  }
}

async function handleSearch() {
  if (!searchQuery.value.trim()) return;
  isSearching.value = true;
  hasSearched.value = true;
  try {
    const response = await aiInsightsApi.smartSearch({
      query: searchQuery.value,
    });
    searchResults.value = response.data?.results || [];
  } catch (error) {
    console.error("Search failed:", error);
    searchResults.value = [];
  } finally {
    isSearching.value = false;
  }
}

// Watch route changes
watch(
  () => route.meta?.tab,
  () => {
    fetchData();
  },
);

onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div
      data-tour="ai-insights-entry"
      class="flex items-center justify-between"
    >
      <div>
        <h1 class="text-2xl font-bold text-foreground">{{ pageTitle }}</h1>
        <p class="text-foreground-secondary mt-1">
          {{ t("aiInsights.subtitle") }}
        </p>
      </div>
      <div class="flex items-center gap-4">
        <!-- Gateway Status -->
        <div
          class="flex items-center gap-2 px-3 py-1.5 bg-background-secondary border border-border rounded-lg"
        >
          <ServerIcon class="w-4 h-4 text-slate-400" />
          <span class="text-sm text-foreground-secondary">Gateway:</span>
          <span
            :class="[
              'text-sm font-medium',
              gatewayStatus === 'online'
                ? 'text-emerald-600 dark:text-emerald-400'
                : gatewayStatus === 'offline'
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-slate-400',
            ]"
          >
            {{
              gatewayStatus === "online"
                ? t("common.online")
                : gatewayStatus === "offline"
                  ? t("common.offline")
                  : t("common.checking")
            }}
          </span>
          <div
            :class="[
              'w-2 h-2 rounded-full',
              gatewayStatus === 'online'
                ? 'bg-emerald-500'
                : gatewayStatus === 'offline'
                  ? 'bg-red-500'
                  : 'bg-slate-300 animate-pulse',
            ]"
          />
        </div>
      </div>
    </div>

    <!-- Content based on current route -->
    <div class="min-h-[500px]">
      <!-- Overview -->
      <div v-if="currentTab === 'overview'" class="space-y-6">
        <div
          v-if="isLoadingOverview"
          class="flex items-center justify-center py-12"
        >
          <ArrowPathIcon class="w-8 h-8 text-slate-400 animate-spin" />
        </div>
        <template v-else-if="overviewData">
          <!-- Stats Cards -->
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="bg-card rounded-xl border border-border p-5">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm text-foreground-secondary">
                    {{ t("aiInsights.overview.totalFiles") }}
                  </p>
                  <p class="text-2xl font-bold text-foreground mt-1">
                    {{ overviewData.total_files?.toLocaleString() }}
                  </p>
                </div>
                <div
                  class="w-12 h-12 bg-violet-100 dark:bg-violet-900/30 rounded-lg flex items-center justify-center"
                >
                  <FolderIcon
                    class="w-6 h-6 text-violet-600 dark:text-violet-400"
                  />
                </div>
              </div>
            </div>
            <div class="bg-card rounded-xl border border-border p-5">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm text-foreground-secondary">
                    {{ t("aiInsights.overview.totalSize") }}
                  </p>
                  <p class="text-2xl font-bold text-foreground mt-1">
                    {{ overviewData.total_size }}
                  </p>
                </div>
                <div
                  class="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center"
                >
                  <DocumentTextIcon
                    class="w-6 h-6 text-blue-600 dark:text-blue-400"
                  />
                </div>
              </div>
            </div>
            <div class="bg-card rounded-xl border border-border p-5">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm text-foreground-secondary">
                    {{ t("aiInsights.overview.sensitiveFiles") }}
                  </p>
                  <p
                    class="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1"
                  >
                    {{ overviewData.risk_summary?.sensitive_files }}
                  </p>
                </div>
                <div
                  class="w-12 h-12 bg-amber-100 dark:bg-amber-900/30 rounded-lg flex items-center justify-center"
                >
                  <ShieldExclamationIcon
                    class="w-6 h-6 text-amber-600 dark:text-amber-400"
                  />
                </div>
              </div>
            </div>
            <div class="bg-card rounded-xl border border-border p-5">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm text-foreground-secondary">
                    {{ t("aiInsights.overview.duplicateSize") }}
                  </p>
                  <p
                    class="text-2xl font-bold text-red-600 dark:text-red-400 mt-1"
                  >
                    {{
                      overviewData.optimization_suggestions?.duplicate_files
                        ?.size
                    }}
                  </p>
                </div>
                <div
                  class="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center"
                >
                  <DocumentDuplicateIcon
                    class="w-6 h-6 text-red-600 dark:text-red-400"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- File Categories & Risk -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- File Categories -->
            <div class="bg-card rounded-xl border border-border p-6">
              <h3 class="text-lg font-semibold text-foreground mb-4">
                {{ t("aiInsights.overview.fileCategories") }}
              </h3>
              <div class="space-y-4">
                <div
                  v-for="cat in overviewData.file_categories"
                  :key="cat.name"
                  class="flex items-center gap-4"
                >
                  <div class="flex-1">
                    <div class="flex items-center justify-between mb-1">
                      <span
                        class="text-sm font-medium text-foreground-secondary"
                        >{{ locale === "zh-CN" ? cat.name_zh : cat.name }}</span
                      >
                      <span class="text-sm text-slate-500"
                        >{{ cat.percentage }}%</span
                      >
                    </div>
                    <div
                      class="h-2 bg-background-tertiary rounded-full overflow-hidden"
                    >
                      <div
                        class="h-full bg-gradient-to-r from-violet-500 to-purple-500 rounded-full transition-all"
                        :style="{ width: `${cat.percentage}%` }"
                      />
                    </div>
                  </div>
                  <span class="text-sm text-slate-500 w-16 text-right">{{
                    cat.size
                  }}</span>
                </div>
              </div>
            </div>

            <!-- Risk Summary -->
            <div class="bg-card rounded-xl border border-border p-6">
              <h3 class="text-lg font-semibold text-foreground mb-4">
                {{ t("aiInsights.overview.riskMonitoring") }}
              </h3>
              <div class="space-y-4">
                <div
                  class="flex items-center justify-between p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg"
                >
                  <div class="flex items-center gap-3">
                    <ExclamationTriangleIcon class="w-5 h-5 text-amber-500" />
                    <span class="text-sm text-amber-700 dark:text-amber-300">{{
                      t("aiInsights.overview.sensitiveInfo")
                    }}</span>
                  </div>
                  <span
                    class="text-sm font-semibold text-amber-600 dark:text-amber-400"
                    >{{ overviewData.risk_summary?.sensitive_files }}
                    {{ t("aiInsights.overview.files") }}</span
                  >
                </div>
                <div
                  class="flex items-center justify-between p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg"
                >
                  <div class="flex items-center gap-3">
                    <CheckCircleIcon class="w-5 h-5 text-emerald-500" />
                    <span
                      class="text-sm text-emerald-700 dark:text-emerald-300"
                      >{{ t("aiInsights.overview.ransomwareRisk") }}</span
                    >
                  </div>
                  <span
                    class="text-sm font-semibold text-emerald-600 dark:text-emerald-400"
                    >{{ t("aiInsights.overview.safe") }}</span
                  >
                </div>
                <div
                  class="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg"
                >
                  <div class="flex items-center gap-3">
                    <ShieldExclamationIcon class="w-5 h-5 text-blue-500" />
                    <span class="text-sm text-blue-700 dark:text-blue-300">{{
                      t("aiInsights.overview.permissionIssues")
                    }}</span>
                  </div>
                  <span
                    class="text-sm font-semibold text-blue-600 dark:text-blue-400"
                    >{{ overviewData.risk_summary?.permission_issues }}
                    {{ t("aiInsights.overview.places") }}</span
                  >
                </div>
              </div>
            </div>
          </div>

          <!-- Optimization Suggestions -->
          <div class="bg-card rounded-xl border border-border p-6">
            <h3 class="text-lg font-semibold text-foreground mb-4">
              {{ t("aiInsights.overview.optimizationSuggestions") }}
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="p-4 border border-border rounded-lg">
                <div class="flex items-center gap-2 mb-2">
                  <TrashIcon class="w-5 h-5 text-red-500" />
                  <span class="font-medium text-foreground-secondary">{{
                    t("aiInsights.overview.duplicateFiles")
                  }}</span>
                </div>
                <p class="text-2xl font-bold text-foreground">
                  {{
                    overviewData.optimization_suggestions?.duplicate_files?.size
                  }}
                </p>
                <p class="text-sm text-slate-500 mt-1">
                  {{ t("aiInsights.overview.suggestClean") }}
                </p>
              </div>
              <div class="p-4 border border-border rounded-lg">
                <div class="flex items-center gap-2 mb-2">
                  <ClockIcon class="w-5 h-5 text-blue-500" />
                  <span class="font-medium text-foreground-secondary">{{
                    t("aiInsights.overview.coldData")
                  }}</span>
                </div>
                <p class="text-2xl font-bold text-foreground">
                  {{ overviewData.optimization_suggestions?.cold_data?.size }}
                </p>
                <p class="text-sm text-slate-500 mt-1">
                  {{ t("aiInsights.overview.suggestArchive") }}
                </p>
              </div>
              <div class="p-4 border border-border rounded-lg">
                <div class="flex items-center gap-2 mb-2">
                  <ArrowTrendingUpIcon class="w-5 h-5 text-amber-500" />
                  <span class="font-medium text-foreground-secondary">{{
                    t("aiInsights.overview.fastestGrowing")
                  }}</span>
                </div>
                <p class="text-lg font-bold text-foreground">
                  {{
                    overviewData.optimization_suggestions?.fastest_growing?.path
                  }}
                </p>
                <p class="text-sm text-slate-500 mt-1">
                  {{ t("aiInsights.overview.weeklyGrowth") }}:
                  {{
                    overviewData.optimization_suggestions?.fastest_growing
                      ?.growth_rate
                  }}
                </p>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Smart Search -->
      <div v-if="currentTab === 'search'" class="space-y-6">
        <div class="bg-card rounded-xl border border-border p-6">
          <h3 class="text-lg font-semibold text-foreground mb-4">
            {{ t("aiInsights.search.title") }}
          </h3>
          <div class="flex gap-4">
            <div class="flex-1 relative">
              <MagnifyingGlassIcon
                class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400"
              />
              <input
                v-model="searchQuery"
                type="text"
                :placeholder="t('aiInsights.search.placeholder')"
                class="w-full pl-12 pr-4 py-3 bg-background-secondary border border-border rounded-lg text-foreground placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500"
                @keyup.enter="handleSearch"
              />
            </div>
            <button
              @click="handleSearch"
              :disabled="isSearching || !searchQuery.trim()"
              class="px-6 py-3 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              <ArrowPathIcon v-if="isSearching" class="w-5 h-5 animate-spin" />
              <MagnifyingGlassIcon v-else class="w-5 h-5" />
              {{ t("aiInsights.search.search") }}
            </button>
          </div>

          <!-- Search Results -->
          <div v-if="hasSearched" class="mt-6">
            <h4 class="text-sm font-medium text-foreground-secondary mb-3">
              {{ t("aiInsights.search.results") }}
            </h4>
            <div
              v-if="searchResults.length === 0"
              class="text-center py-8 text-slate-500"
            >
              {{ t("aiInsights.search.noResults") }}
            </div>
            <div v-else class="space-y-2">
              <div
                v-for="result in searchResults"
                :key="result.path"
                class="flex items-center gap-4 p-3 bg-background-secondary rounded-lg"
              >
                <DocumentTextIcon class="w-5 h-5 text-slate-400" />
                <div class="flex-1 min-w-0">
                  <p
                    class="text-sm font-medium text-foreground-secondary truncate"
                  >
                    {{ result.name || result.path?.split("/").pop() }}
                  </p>
                  <p class="text-xs text-slate-500 truncate">
                    {{ result.path }}
                  </p>
                  <p class="mt-1 text-[11px] text-foreground-muted truncate">
                    {{ result.snapshot_name || result.snapshot_id }} ·
                    {{ result.backup_task_name || "-" }} ·
                    {{ result.repository_name || "-" }} ·
                    {{ result.category || "-" }}
                  </p>
                </div>
                <span class="text-sm text-slate-500">{{
                  formatBytes(result.size || 0)
                }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Sensitive Data -->
      <div v-if="currentTab === 'sensitive'" class="space-y-6">
        <div
          v-if="isLoadingSensitive"
          class="flex items-center justify-center py-12"
        >
          <ArrowPathIcon class="w-8 h-8 text-slate-400 animate-spin" />
        </div>
        <template v-else-if="sensitiveData">
          <div class="bg-card rounded-xl border border-border p-6">
            <div class="flex items-center justify-between mb-6">
              <h3 class="text-lg font-semibold text-foreground">
                {{ t("aiInsights.sensitive.title") }}
              </h3>
              <div class="flex items-center gap-2 text-sm text-slate-500">
                <ClockIcon class="w-4 h-4" />
                {{ t("aiInsights.sensitive.lastScan") }}:
                {{ sensitiveData.last_scan }}
              </div>
            </div>
            <div class="space-y-4">
              <div
                v-for="finding in sensitiveData.findings"
                :key="finding.type"
                class="p-4 border border-border rounded-lg"
              >
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center gap-3">
                    <span
                      :class="[
                        'px-2 py-1 text-xs font-medium rounded',
                        getSeverityColor(finding.severity),
                      ]"
                    >
                      {{ finding.severity.toUpperCase() }}
                    </span>
                    <span class="font-medium text-foreground-secondary">{{
                      locale === "zh-CN" ? finding.type_zh : finding.type
                    }}</span>
                  </div>
                  <span class="text-sm text-slate-500"
                    >{{ finding.count }}
                    {{ t("aiInsights.sensitive.matches") }}</span
                  >
                </div>
                <p class="text-sm text-foreground-secondary mb-2">
                  {{ finding.recommendation }}
                </p>
                <div class="text-xs text-slate-500">
                  {{ t("aiInsights.sensitive.files") }}:
                  {{
                    finding.files
                      .map((f: any) => f.path?.split("/").pop())
                      .join(", ")
                  }}
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Content Profile -->
      <div v-if="currentTab === 'profile'" class="space-y-6">
        <div
          v-if="isLoadingProfile"
          class="flex items-center justify-center py-12"
        >
          <ArrowPathIcon class="w-8 h-8 text-slate-400 animate-spin" />
        </div>
        <template v-else-if="contentProfile">
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div
              v-for="cat in contentProfile.categories"
              :key="cat.name"
              class="bg-card rounded-xl border border-border p-5"
            >
              <div class="flex items-center gap-3 mb-3">
                <TagIcon class="w-5 h-5 text-violet-500" />
                <span class="font-medium text-foreground-secondary">{{
                  locale === "zh-CN" ? cat.name_zh : cat.name
                }}</span>
              </div>
              <p class="text-2xl font-bold text-foreground">{{ cat.count }}</p>
              <p class="text-sm text-slate-500">{{ cat.size }}</p>
              <div class="flex flex-wrap gap-1 mt-3">
                <span
                  v-for="tag in cat.tags"
                  :key="tag"
                  class="px-2 py-0.5 text-xs bg-background-tertiary text-foreground-secondary rounded"
                >
                  {{ tag }}
                </span>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Data Heatmap -->
      <div v-if="currentTab === 'heatmap'" class="space-y-6">
        <div
          v-if="isLoadingHeatmap"
          class="flex items-center justify-center py-12"
        >
          <ArrowPathIcon class="w-8 h-8 text-slate-400 animate-spin" />
        </div>
        <template v-else-if="dataHeatmap">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div
              v-for="item in dataHeatmap.heatmap"
              :key="item.category"
              class="bg-card rounded-xl border border-border p-6"
            >
              <div class="flex items-center gap-3 mb-4">
                <div
                  :class="[
                    'w-10 h-10 rounded-lg flex items-center justify-center',
                    item.category === 'hot'
                      ? 'bg-red-100 dark:bg-red-900/30'
                      : item.category === 'warm'
                        ? 'bg-amber-100 dark:bg-amber-900/30'
                        : 'bg-blue-100 dark:bg-blue-900/30',
                  ]"
                >
                  <FireIcon
                    :class="[
                      'w-5 h-5',
                      item.category === 'hot'
                        ? 'text-red-500'
                        : item.category === 'warm'
                          ? 'text-amber-500'
                          : 'text-blue-500',
                    ]"
                  />
                </div>
                <div>
                  <p class="font-medium text-foreground-secondary">
                    {{ locale === "zh-CN" ? item.category_zh : item.category }}
                  </p>
                  <p class="text-xs text-slate-500">{{ item.description }}</p>
                </div>
              </div>
              <p class="text-2xl font-bold text-foreground">{{ item.size }}</p>
              <div
                class="flex items-center justify-between mt-2 text-sm text-slate-500"
              >
                <span>{{ item.percentage }}%</span>
                <span
                  >{{ item.file_count?.toLocaleString() }}
                  {{ t("aiInsights.heatmap.files") }}</span
                >
              </div>
            </div>
          </div>

          <!-- Zombie Data -->
          <div
            v-if="dataHeatmap.zombie_data"
            class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-6"
          >
            <div class="flex items-center gap-3 mb-3">
              <ExclamationTriangleIcon class="w-5 h-5 text-amber-500" />
              <span class="font-medium text-amber-700 dark:text-amber-300">{{
                t("aiInsights.heatmap.zombieData")
              }}</span>
            </div>
            <p class="text-amber-600 dark:text-amber-400">
              {{ dataHeatmap.zombie_data.description }}
            </p>
            <p
              class="text-lg font-bold text-amber-700 dark:text-amber-300 mt-2"
            >
              {{ dataHeatmap.zombie_data.size }} ({{
                dataHeatmap.zombie_data.file_count?.toLocaleString()
              }}
              {{ t("aiInsights.heatmap.files") }})
            </p>
            <p class="text-sm text-amber-600 dark:text-amber-400 mt-1">
              {{ dataHeatmap.zombie_data.potential_savings }}
            </p>
          </div>
        </template>
      </div>

      <!-- Redundancy -->
      <div v-if="currentTab === 'redundancy'" class="space-y-6">
        <div
          v-if="isLoadingRedundancy"
          class="flex items-center justify-center py-12"
        >
          <ArrowPathIcon class="w-8 h-8 text-slate-400 animate-spin" />
        </div>
        <template v-else-if="redundancyData">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="bg-card rounded-xl border border-border p-5">
              <p class="text-sm text-slate-500">
                {{ t("aiInsights.redundancy.duplicateFiles") }}
              </p>
              <p class="text-2xl font-bold text-foreground mt-1">
                {{ redundancyData.total_duplicates?.toLocaleString() }}
              </p>
            </div>
            <div class="bg-card rounded-xl border border-border p-5">
              <p class="text-sm text-slate-500">
                {{ t("aiInsights.redundancy.duplicateSize") }}
              </p>
              <p class="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">
                {{ redundancyData.duplicate_size }}
              </p>
            </div>
            <div class="bg-card rounded-xl border border-border p-5">
              <p class="text-sm text-slate-500">
                {{ t("aiInsights.redundancy.potentialSavings") }}
              </p>
              <p
                class="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1"
              >
                {{ redundancyData.potential_savings }}
              </p>
            </div>
          </div>

          <div class="bg-card rounded-xl border border-border p-6">
            <h3 class="text-lg font-semibold text-foreground mb-4">
              {{ t("aiInsights.redundancy.duplicateGroups") }}
            </h3>
            <div class="space-y-3">
              <div
                v-for="group in redundancyData.duplicate_groups"
                :key="group.file_name"
                class="p-4 bg-background-secondary rounded-lg"
              >
                <div class="flex items-center justify-between mb-2">
                  <span class="font-medium text-foreground-secondary">{{
                    group.file_name
                  }}</span>
                  <span class="text-sm text-slate-500"
                    >{{ group.count }}
                    {{ t("aiInsights.redundancy.copies") }}</span
                  >
                </div>
                <div class="text-xs text-slate-500">
                  {{ t("aiInsights.redundancy.locations") }}:
                  {{ group.locations.join(", ") }}
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- AI Chat (Placeholder) -->
      <div v-if="currentTab === 'chat'" class="space-y-6">
        <AIQueryPanel />
      </div>
    </div>
  </div>
</template>
