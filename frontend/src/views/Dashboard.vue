<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { backupTasksApi, proxiesApi } from "@/api";
import {
  ServerIcon,
  BoltIcon,
  CircleStackIcon,
  ChartBarIcon,
  CloudArrowUpIcon,
  ArrowUturnLeftIcon,
  ArrowTrendingUpIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  SparklesIcon,
  ShieldExclamationIcon,
  FolderIcon,
  DocumentDuplicateIcon,
  FireIcon,
  ArrowRightIcon,
  InformationCircleIcon,
  ExclamationCircleIcon,
} from "@heroicons/vue/24/outline";

const router = useRouter();
const { t } = useI18n();

interface Stats {
  total_nodes: number;
  online_nodes: number;
  active_tasks: number;
  storage_used: number;
  storage_total: number;
  total_backups: number;
  success_rate: number;
  running_tasks: number;
  pending_tasks: number;
  failed_tasks: number;
}

interface AIInsight {
  category: string;
  percentage: number;
  size: string;
}

interface Risk {
  type: string;
  count: number;
  severity: "critical" | "warning" | "info";
}

interface Optimization {
  type: string;
  size: string;
  description: string;
}

interface Alert {
  id: string;
  time: string;
  message: string;
  severity: "critical" | "warning" | "info";
  source: string;
}

interface ActiveTask {
  id: string;
  type: "backup" | "recovery" | "ai";
  name: string;
  progress: number;
  status: string;
}

const isLoading = ref(true);
const stats = ref<Stats>({
  total_nodes: 0,
  online_nodes: 0,
  active_tasks: 0,
  storage_used: 0,
  storage_total: 0,
  total_backups: 0,
  success_rate: 0,
  running_tasks: 0,
  pending_tasks: 0,
  failed_tasks: 0,
});

const recentTasks = ref<any[]>([]);

// AI Insights 数据
const aiInsights = ref<AIInsight[]>([
  { category: "documents", percentage: 45, size: "23 TB" },
  { category: "images", percentage: 20, size: "10 TB" },
  { category: "archives", percentage: 15, size: "8 TB" },
  { category: "videos", percentage: 12, size: "6 TB" },
  { category: "others", percentage: 8, size: "4 TB" },
]);

const risks = ref<Risk[]>([
  { type: "sensitive", count: 12, severity: "warning" },
  { type: "ransomware", count: 0, severity: "info" },
  { type: "permission", count: 32, severity: "warning" },
]);

const optimizations = ref<Optimization[]>([
  { type: "duplicate", size: "1.2 TB", description: "建议清理" },
  { type: "cold", size: "4.5 TB", description: "建议归档" },
  { type: "growth", size: "/var/log", description: "周增 200%" },
]);

// 监控数据
const alerts = ref<Alert[]>([
  {
    id: "1",
    time: "16:20",
    message: "Linux-03 离线",
    severity: "critical",
    source: "Proxy",
  },
  {
    id: "2",
    time: "15:10",
    message: "S3 存储连接超时",
    severity: "warning",
    source: "Storage",
  },
  {
    id: "3",
    time: "14:00",
    message: "策略 A 执行失败",
    severity: "warning",
    source: "Policy",
  },
  {
    id: "4",
    time: "昨天",
    message: "存储空间 > 80%",
    severity: "info",
    source: "System",
  },
  {
    id: "5",
    time: "2天前",
    message: "备份任务超时",
    severity: "warning",
    source: "Backup",
  },
]);

const activeTasks = ref<ActiveTask[]>([
  {
    id: "1",
    type: "backup",
    name: "财务数据备份",
    progress: 80,
    status: "running",
  },
  {
    id: "2",
    type: "recovery",
    name: "研发归档恢复",
    progress: 12,
    status: "running",
  },
  { id: "3", type: "ai", name: "文件扫描", progress: 45, status: "running" },
  {
    id: "4",
    type: "backup",
    name: "邮件系统备份",
    progress: 99,
    status: "running",
  },
]);

const lastSyncTime = ref("2026-04-23 10:00");

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    documents: t("aiInsights.categories.documents"),
    images: t("aiInsights.categories.images"),
    archives: t("aiInsights.categories.archives"),
    videos: t("aiInsights.categories.videos"),
    others: t("aiInsights.categories.others"),
  };
  return labels[category] || category;
}

function getRiskLabel(type: string): string {
  const labels: Record<string, string> = {
    sensitive: t("aiInsights.risks.sensitive"),
    ransomware: t("aiInsights.risks.ransomware"),
    permission: t("aiInsights.risks.permission"),
  };
  return labels[type] || type;
}

function getOptimizationLabel(type: string): string {
  const labels: Record<string, string> = {
    duplicate: t("aiInsights.optimizations.duplicate"),
    cold: t("aiInsights.optimizations.cold"),
    growth: t("aiInsights.optimizations.growth"),
  };
  return labels[type] || type;
}

function getTaskTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    backup: t("dashboard.taskTypes.backup"),
    recovery: t("dashboard.taskTypes.recovery"),
    ai: t("dashboard.taskTypes.ai"),
  };
  return labels[type] || type;
}

function getSeverityColor(severity: string): string {
  const colors: Record<string, string> = {
    critical:
      "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800",
    warning:
      "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800",
    info: "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",
  };
  return colors[severity] || colors.info;
}

function getSeverityIcon(severity: string) {
  const icons: Record<string, any> = {
    critical: ExclamationCircleIcon,
    warning: ExclamationTriangleIcon,
    info: InformationCircleIcon,
  };
  return icons[severity] || InformationCircleIcon;
}

async function fetchDashboardData() {
  isLoading.value = true;
  try {
    const [proxiesRes, tasksRes] = await Promise.all([
      proxiesApi.stats(),
      backupTasksApi.list({ ordering: "-created_at", page_size: 5 }),
    ]);

    const tasksData = tasksRes.data.results || [];
    const runningCount = tasksData.filter(
      (t: any) => t.status === "running",
    ).length;
    const pendingCount = tasksData.filter(
      (t: any) => t.status === "pending",
    ).length;
    const failedCount = tasksData.filter(
      (t: any) => t.status === "failed",
    ).length;

    stats.value = {
      total_nodes:
        proxiesRes.data.total_proxies || proxiesRes.data.total_nodes || 0,
      online_nodes:
        proxiesRes.data.active_proxies ||
        proxiesRes.data.active_nodes ||
        proxiesRes.data.online_nodes ||
        0,
      active_tasks: tasksRes.data.count || 0,
      storage_used: 161061273600, // 150GB
      storage_total: 1099511627776, // 1TB
      total_backups: 24,
      success_rate: 97.5,
      running_tasks: runningCount,
      pending_tasks: pendingCount,
      failed_tasks: failedCount,
    };

    recentTasks.value = tasksData;
  } catch (error) {
    console.error("Failed to fetch dashboard data:", error);
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  fetchDashboardData();
});
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">
          {{ t("dashboard.title") }}
        </h1>
        <p class="text-foreground-secondary mt-1">
          {{ t("dashboard.subtitle") }}
        </p>
      </div>
      <button
        @click="fetchDashboardData"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-foreground-secondary surface-card border border-border rounded-lg hover:bg-hover hover:border-slate-300 dark:hover:border-slate-500 transition-colors shadow-sm">
        <svg
          class="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        {{ t("common.refresh") }}
      </button>
    </div>

    <!-- Stats Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Total Nodes -->
      <div
        class="bg-card rounded-xl border border-border p-4 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm font-medium text-foreground-secondary">
              {{ t("dashboard.stats.totalNodes") }}
            </p>
            <p class="text-2xl font-bold text-foreground mt-1">
              {{ stats.total_nodes }}
            </p>
            <div class="flex items-center gap-1.5 mt-2">
              <span
                class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
              <span
                class="text-xs text-emerald-600 dark:text-emerald-400 font-medium"
                >{{ stats.online_nodes }} {{ t("common.active") }}</span
              >
            </div>
          </div>
          <div
            class="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-md">
            <ServerIcon class="w-5 h-5 text-white" />
          </div>
        </div>
      </div>

      <!-- Active Tasks -->
      <div
        class="bg-card rounded-xl border border-border p-4 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm font-medium text-foreground-secondary">
              {{ t("dashboard.stats.activeTasks") }}
            </p>
            <p class="text-2xl font-bold text-foreground mt-1">
              {{ stats.active_tasks }}
            </p>
            <div class="flex items-center gap-2 mt-2 text-xs">
              <span class="text-blue-600 dark:text-blue-400"
                >{{ stats.running_tasks }}
                {{ t("backupTasks.status.running") }}</span
              >
              <span class="text-foreground-muted">|</span>
              <span class="text-amber-600 dark:text-amber-400"
                >{{ stats.pending_tasks }}
                {{ t("backupTasks.status.pending") }}</span
              >
            </div>
          </div>
          <div
            class="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-600 rounded-lg flex items-center justify-center shadow-md">
            <BoltIcon class="w-5 h-5 text-white" />
          </div>
        </div>
      </div>

      <!-- Storage Used -->
      <div
        class="bg-card rounded-xl border border-border p-4 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm font-medium text-foreground-secondary">
              {{ t("dashboard.stats.storageUsed") }}
            </p>
            <p class="text-2xl font-bold text-foreground mt-1">
              {{ formatBytes(stats.storage_used) }}
            </p>
            <div class="mt-2">
              <div
                class="h-1.5 bg-background-tertiary rounded-full overflow-hidden">
                <div
                  class="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-500"
                  :style="{
                    width: `${Math.round((stats.storage_used / stats.storage_total) * 100)}%`,
                  }" />
              </div>
              <p class="text-xs text-foreground-secondary mt-1">
                {{
                  Math.round((stats.storage_used / stats.storage_total) * 100)
                }}% {{ t("dashboard.stats.used") }}
              </p>
            </div>
          </div>
          <div
            class="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg flex items-center justify-center shadow-md">
            <CircleStackIcon class="w-5 h-5 text-white" />
          </div>
        </div>
      </div>

      <!-- Success Rate -->
      <div
        class="bg-card rounded-xl border border-border p-4 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm font-medium text-foreground-secondary">
              {{ t("dashboard.stats.successRate") }}
            </p>
            <p class="text-2xl font-bold text-foreground mt-1">
              {{ stats.success_rate }}%
            </p>
            <div
              class="flex items-center gap-1 mt-2 text-emerald-600 dark:text-emerald-400">
              <ArrowTrendingUpIcon class="w-3.5 h-3.5" />
              <span class="text-xs font-medium">+2.5%</span>
            </div>
          </div>
          <div
            class="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-600 rounded-lg flex items-center justify-center shadow-md">
            <ChartBarIcon class="w-5 h-5 text-white" />
          </div>
        </div>
      </div>
    </div>

    <!-- AI Insights Section -->
    <div
      class="from-indigo-50 via-purple-50 to-pink-50 dark:from-indigo-950/30 dark:via-purple-950/30 dark:to-pink-950/30 rounded-xl border border-indigo-100 dark:border-indigo-900/50 overflow-hidden">
      <div
        class="px-5 py-4 flex items-center justify-between border-b dark:border-indigo-900/50 bg-white/50 dark:bg-slate-900/30">
        <div class="flex items-center gap-3">
          <div
            class="w-9 h-9 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-md">
            <SparklesIcon class="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 class="text-base font-semibold text-foreground">
              {{ t("dashboard.aiInsights.title") }}
            </h2>
            <p class="text-xs text-foreground-secondary">
              {{ t("dashboard.aiInsights.syncTime", { time: lastSyncTime }) }}
            </p>
          </div>
        </div>
        <button
          @click="router.push('/ai-insights')"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors">
          {{ t("dashboard.aiInsights.viewDetails") }}
          <ArrowRightIcon class="w-4 h-4" />
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-px dark:bg-indigo-900/50">
        <!-- File Categories -->
        <div class="bg-card p-4">
          <div class="flex items-center gap-2 mb-3">
            <FolderIcon class="w-4 h-4 text-indigo-500" />
            <h3 class="text-sm font-medium text-foreground-secondary">
              {{ t("dashboard.aiInsights.fileCategories") }}
            </h3>
          </div>
          <div class="space-y-2">
            <div
              v-for="item in aiInsights"
              :key="item.category"
              class="flex items-center justify-between">
              <div class="flex items-center gap-2 flex-1 min-w-0">
                <div
                  class="w-2 h-2 rounded-full"
                  :class="{
                    'bg-indigo-500': item.category === 'documents',
                    'bg-pink-500': item.category === 'images',
                    'bg-amber-500': item.category === 'archives',
                    'bg-purple-500': item.category === 'videos',
                    'bg-slate-400': item.category === 'others',
                  }"></div>
                <span class="text-sm text-foreground-secondary truncate">{{
                  getCategoryLabel(item.category)
                }}</span>
              </div>
              <div class="flex items-center gap-2 text-xs">
                <span class="font-medium text-foreground"
                  >{{ item.percentage }}%</span
                >
                <span class="text-slate-400">({{ item.size }})</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Risk Monitoring -->
        <div class="bg-card p-4">
          <div class="flex items-center gap-2 mb-3">
            <ShieldExclamationIcon class="w-4 h-4 text-red-500" />
            <h3 class="text-sm font-medium text-foreground-secondary">
              {{ t("dashboard.aiInsights.riskMonitoring") }}
            </h3>
          </div>
          <div class="space-y-2">
            <div
              v-for="risk in risks"
              :key="risk.type"
              class="flex items-center justify-between px-3 py-2 rounded-lg"
              :class="{
                'bg-amber-50 dark:bg-amber-900/20': risk.severity === 'warning',
                'bg-emerald-50 dark:bg-emerald-900/20':
                  risk.severity === 'info',
                'bg-red-50 dark:bg-red-900/20': risk.severity === 'critical',
              }">
              <span class="text-sm text-foreground-secondary">{{
                getRiskLabel(risk.type)
              }}</span>
              <span
                class="text-sm font-medium"
                :class="{
                  'text-amber-600 dark:text-amber-400':
                    risk.severity === 'warning',
                  'text-emerald-600 dark:text-emerald-400':
                    risk.severity === 'info',
                  'text-red-600 dark:text-red-400':
                    risk.severity === 'critical',
                }">
                {{
                  risk.count > 0
                    ? `${risk.count} ${t("dashboard.aiInsights.items")}`
                    : t("dashboard.aiInsights.safe")
                }}
              </span>
            </div>
          </div>
        </div>

        <!-- Storage Optimization -->
        <div class="bg-card p-4">
          <div class="flex items-center gap-2 mb-3">
            <FireIcon class="w-4 h-4 text-amber-500" />
            <h3 class="text-sm font-medium text-foreground-secondary">
              {{ t("dashboard.aiInsights.storageOptimization") }}
            </h3>
          </div>
          <div class="space-y-2">
            <div
              v-for="opt in optimizations"
              :key="opt.type"
              class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <DocumentDuplicateIcon
                  v-if="opt.type === 'duplicate'"
                  class="w-4 h-4 text-slate-400" />
                <CircleStackIcon
                  v-else-if="opt.type === 'cold'"
                  class="w-4 h-4 text-blue-400" />
                <ArrowTrendingUpIcon v-else class="w-4 h-4 text-red-400" />
                <span class="text-sm text-foreground-secondary">{{
                  getOptimizationLabel(opt.type)
                }}</span>
              </div>
              <div class="text-right">
                <span class="text-sm font-medium text-foreground">{{
                  opt.size
                }}</span>
                <p class="text-xs text-slate-400">{{ opt.description }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Monitoring & Compliance Section -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Alerts -->
      <div class="bg-card rounded-xl border border-border shadow-sm">
        <div class="px-5 py-4 border-b border-border">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <ExclamationTriangleIcon class="w-5 h-5 text-amber-500" />
              <h2 class="text-base font-semibold text-foreground">
                {{ t("dashboard.alerts.title") }}
              </h2>
            </div>
            <span
              class="px-2 py-0.5 text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-full"
              >{{ alerts.length }}</span
            >
          </div>
        </div>
        <div class="divide-y divide-slate-100 dark:divide-slate-700">
          <div
            v-for="alert in alerts"
            :key="alert.id"
            class="px-5 py-3 hover:bg-hover transition-colors">
            <div class="flex items-start gap-3">
              <div
                :class="[
                  'w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0',
                  getSeverityColor(alert.severity),
                ]">
                <component
                  :is="getSeverityIcon(alert.severity)"
                  class="w-3.5 h-3.5" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-foreground truncate">
                  {{ alert.message }}
                </p>
                <p class="text-xs text-slate-400 mt-0.5">
                  [{{ alert.time }}] {{ alert.source }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Active Tasks -->
      <div class="bg-card rounded-xl border border-border shadow-sm">
        <div class="px-5 py-4 border-b border-border">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <BoltIcon class="w-5 h-5 text-blue-500" />
              <h2 class="text-base font-semibold text-foreground">
                {{ t("dashboard.activeTasks.title") }}
              </h2>
            </div>
            <span
              class="px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-full"
              >{{ activeTasks.length }}</span
            >
          </div>
        </div>
        <div class="divide-y divide-slate-100 dark:divide-slate-700">
          <div v-for="task in activeTasks" :key="task.id" class="px-5 py-3">
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <span
                  :class="[
                    'text-xs font-medium px-1.5 py-0.5 rounded',
                    task.type === 'backup'
                      ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400'
                      : task.type === 'recovery'
                        ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'
                        : 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
                  ]">
                  {{ getTaskTypeLabel(task.type) }}
                </span>
                <span class="text-sm text-foreground truncate">{{
                  task.name
                }}</span>
              </div>
              <span class="text-sm font-medium text-foreground-secondary"
                >{{ task.progress }}%</span
              >
            </div>
            <div
              class="h-1.5 bg-background-tertiary rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-300"
                :class="
                  task.type === 'backup'
                    ? 'bg-gradient-to-r from-indigo-500 to-purple-500'
                    : task.type === 'recovery'
                      ? 'bg-gradient-to-r from-amber-500 to-orange-500'
                      : 'bg-gradient-to-r from-purple-500 to-pink-500'
                "
                :style="{ width: `${task.progress}%` }" />
            </div>
          </div>
        </div>
      </div>

      <!-- Compliance & License -->
      <div class="bg-card rounded-xl border border-border shadow-sm">
        <div class="px-5 py-4 border-b border-border">
          <div class="flex items-center gap-2">
            <CheckCircleIcon class="w-5 h-5 text-emerald-500" />
            <h2 class="text-base font-semibold text-foreground">
              {{ t("dashboard.compliance.title") }}
            </h2>
          </div>
        </div>
        <div class="p-5 space-y-3">
          <div
            class="flex items-center justify-between px-3 py-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-900/50">
            <span class="text-sm text-foreground-secondary">{{
              t("dashboard.compliance.licenseStatus")
            }}</span>
            <span
              class="flex items-center gap-1.5 text-sm font-medium text-emerald-600 dark:text-emerald-400">
              <CheckCircleIcon class="w-4 h-4" />
              {{ t("dashboard.compliance.normal") }}
            </span>
          </div>
          <div
            class="flex items-center justify-between px-3 py-2 rounded-lg bg-background-secondary">
            <span class="text-sm text-foreground-secondary">{{
              t("dashboard.compliance.storageQuota")
            }}</span>
            <span class="text-sm font-medium text-foreground">{{
              t("dashboard.compliance.quotaRemaining", { amount: "1.2 TB" })
            }}</span>
          </div>
          <div
            class="flex items-center justify-between px-3 py-2 rounded-lg bg-background-secondary">
            <span class="text-sm text-foreground-secondary">{{
              t("dashboard.compliance.expiryDate")
            }}</span>
            <span class="text-sm font-medium text-foreground">2027-01-01</span>
          </div>
          <div
            class="flex items-center justify-between px-3 py-2.5 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-100 dark:border-amber-900/50">
            <span class="text-sm text-foreground-secondary">{{
              t("dashboard.compliance.drill")
            }}</span>
            <span
              class="flex items-center gap-1.5 text-sm font-medium text-amber-600 dark:text-amber-400">
              <ExclamationTriangleIcon class="w-4 h-4" />
              {{ t("dashboard.compliance.drillOverdue") }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <button
        @click="router.push('/backup-tasks')"
        class="flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md hover:shadow-lg">
        <CloudArrowUpIcon class="w-5 h-5" />
        {{ t("dashboard.actions.newBackup") }}
      </button>
      <button
        @click="router.push('/recovery-tasks')"
        class="flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-foreground surface-card border border-border rounded-lg hover:bg-hover hover:border-slate-300 dark:hover:border-slate-500 transition-colors shadow-sm">
        <ArrowUturnLeftIcon class="w-5 h-5 text-foreground-secondary" />
        {{ t("dashboard.actions.newRecovery") }}
      </button>
      <button
        @click="router.push('/ai-insights')"
        class="flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-foreground surface-card border border-border rounded-lg hover:bg-hover hover:border-slate-300 dark:hover:border-slate-500 transition-colors shadow-sm">
        <SparklesIcon class="w-5 h-5 text-purple-500" />
        {{ t("dashboard.actions.aiInsights") }}
      </button>
      <button
        @click="router.push('/proxies')"
        class="flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-foreground surface-card border border-border rounded-lg hover:bg-hover hover:border-slate-300 dark:hover:border-slate-500 transition-colors shadow-sm">
        <ServerIcon class="w-5 h-5 text-foreground-secondary" />
        {{ t("dashboard.actions.manageProxies") }}
      </button>
    </div>
  </div>
</template>
