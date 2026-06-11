<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import {
  aiInsightsApi,
  alertsApi,
  backupTasksApi,
  gatewaysApi,
  licensesApi,
  policiesApi,
  proxiesApi,
  recoveryTasksApi,
  repositoriesApi,
  sourceResourcesApi,
  taskManagementApi,
} from "@/api";
import DashboardGlobalTopology from "@/components/DashboardGlobalTopology.vue";
import PageTitle from "@/components/PageTitle.vue";
import ProductTour, {
  type ProductTourStep,
} from "@/components/ProductTour.vue";
import {
  ServerIcon,
  BoltIcon,
  CircleStackIcon,
  ArrowUturnLeftIcon,
  CloudIcon,
  ChartBarIcon,
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
const { t, locale } = useI18n();

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
  completed_tasks: number;
}

interface AIInsight {
  category: string;
  label: string;
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
  type: string;
  name: string;
  progress: number;
  status: string;
}

interface SetupStep {
  id: string;
  title: string;
  description: string;
  status: "done" | "action" | "blocked";
  metric: string;
  route: string;
  action: string;
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
  completed_tasks: 0,
});

const aiInsights = ref<AIInsight[]>([]);
const risks = ref<Risk[]>([]);
const optimizations = ref<Optimization[]>([]);
const alerts = ref<Alert[]>([]);
const activeTasks = ref<ActiveTask[]>([]);
const setupSteps = ref<SetupStep[]>([]);
const showTourPrompt = ref(false);
const isTourActive = ref(false);
const lastSyncTime = ref("-");
const compliance = ref({
  isValid: false,
  licenseStatus: "-",
  quotaRemaining: "-",
  expiryDate: "-",
  recoveryStatus: "-",
  recoverySeverity: "info" as "critical" | "warning" | "info",
});

const storageUsagePercent = computed(() => {
  if (!stats.value.storage_total) return 0;
  return Math.min(
    100,
    Math.round((stats.value.storage_used / stats.value.storage_total) * 100),
  );
});

const setupProgress = computed(() => {
  if (!setupSteps.value.length) return 0;
  const done = setupSteps.value.filter((step) => step.status === "done").length;
  return Math.round((done / setupSteps.value.length) * 100);
});

const setupComplete = computed(
  () =>
    setupSteps.value.length > 0 &&
    setupSteps.value.every((step) => step.status === "done"),
);

const architectureDiagram = computed(() => {
  const zh = locale.value === "zh-CN";
  return {
    title: zh ? "网络拓扑架构" : "Network Architecture",
    subtitle: zh
      ? "展示源端代理、同步代理、目标存储库、Gateway 索引节点和恢复任务之间的网络连接与动态数据流向。"
      : "Shows the network connections and live data flow between source proxies, sync proxies, target repositories, gateway indexers, and recovery jobs.",
    controlFlow: zh ? "控制流" : "Control flow",
    dataFlow: zh ? "备份/同步数据流" : "Backup / sync flow",
    indexFlow: zh ? "索引洞察流" : "Index insight flow",
    restoreFlow: zh ? "恢复流" : "Restore flow",
    controlPlane: zh ? "HyperFileLens 控制面" : "HyperFileLens Control Plane",
    controlDesc: zh
      ? "任务编排 / 策略下发 / 运行状态 / 告警监控"
      : "Task orchestration / policy dispatch / run status / alerting",
    sourceZone: zh ? "源端网络" : "Source Network",
    targetZone: zh ? "目标仓库网络" : "Target Repository Network",
    insightZone: zh ? "洞察分析网络" : "Insight Analysis Network",
    recoveryZone: zh ? "恢复执行网络" : "Recovery Execution Network",
    sourceData: zh ? "源端数据" : "Source Data",
    sourceDataDesc: zh ? "Local / SMB / NFS / NAS" : "Local / SMB / NFS / NAS",
    agentProxy: zh ? "Agent Proxy" : "Agent Proxy",
    agentProxyDesc: zh
      ? "靠近源端，执行本地/挂载数据备份与恢复"
      : "Runs backup and restore near local or mounted source data",
    syncProxy: zh ? "Sync Proxy" : "Sync Proxy",
    syncProxyDesc: zh
      ? "靠近目标仓库，执行仓库连接、同步、保留和维护"
      : "Runs repository access, sync, retention, and maintenance near storage",
    repository: zh ? "目标存储库" : "Target Repository",
    repositoryDesc: zh ? "Kopia Repository" : "Kopia Repository",
    objectStorage: zh ? "对象存储" : "Object Storage",
    filesystem: zh ? "文件系统" : "Filesystem",
    nas: zh ? "NAS / NFS / SMB" : "NAS / NFS / SMB",
    gateway: zh ? "Gateway 节点" : "Gateway Node",
    gatewayDesc: zh
      ? "挂载/读取仓库快照对象，拉取到本地进行索引"
      : "Mounts or reads repository snapshots and indexes them locally",
    localInsight: zh ? "本地索引与 AI 洞察" : "Local Index and AI Insights",
    localInsightDesc: zh
      ? "文件索引、搜索、敏感数据、重复数据、冷热分析"
      : "File index, search, sensitive data, duplicates, and heat analysis",
    recoveryTask: zh ? "恢复任务" : "Recovery Tasks",
    recoveryTaskDesc: zh
      ? "运行在 Agent Proxy 或 Sync Proxy，从仓库快照恢复数据"
      : "Runs on Agent Proxy or Sync Proxy and restores data from repository snapshots",
  };
});

const tourSteps = computed<ProductTourStep[]>(() => {
  const zh = locale.value === "zh-CN";
  return [
    {
      selector: '[data-tour="dashboard-setup-guide"]',
      title: zh ? "先看配置向导" : "Start with the setup guide",
      description: zh
        ? "这里展示从节点、数据源、仓库到备份、索引和恢复验证的完整路径。绿色表示已完成，紫色表示下一步可以操作。"
        : "This shows the full path from nodes and sources to repository, backup, indexing, and recovery validation. Green means complete; violet means actionable.",
    },
    {
      selector: '[data-tour="dashboard-setup-stepper"]',
      title: zh ? "按顺序完成流程" : "Follow the workflow",
      description: zh
        ? "每一步都可以悬停或点击展开说明。展开后点击操作入口，会跳到对应配置页面。"
        : "Hover or click each step to expand details. Use the action link to jump to the matching configuration page.",
    },
    {
      selector: '[data-tour="dashboard-core-metrics"]',
      title: zh ? "关注核心健康指标" : "Check core health",
      description: zh
        ? "这里聚合节点在线、活动任务、仓库容量和任务成功率，帮助你判断系统当前是否健康。"
        : "These cards summarize node availability, active tasks, repository capacity, and task success rate.",
    },
    {
      selector: '[data-tour="dashboard-ai-insights"]',
      title: zh ? "查看数据洞察" : "Review data insights",
      description: zh
        ? "快照索引完成后，这里会展示文件分类、风险监测和存储优化建议。"
        : "After snapshot indexing, this area shows file categories, risk signals, and storage optimization suggestions.",
    },
    {
      selector: '[data-tour="dashboard-attention"]',
      title: zh ? "处理当前关注项" : "Handle attention items",
      description: zh
        ? "这里展示待处理告警、正在运行任务以及授权和恢复验证状态。"
        : "This area shows firing alerts, running tasks, license status, and recovery verification state.",
    },
  ];
});

function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function pageItems(data: any): any[] {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

function resultData(result: PromiseSettledResult<any>) {
  return result.status === "fulfilled" ? result.value.data : null;
}

function toNumber(value: unknown): number {
  const numberValue = Number(value || 0);
  return Number.isFinite(numberValue) ? numberValue : 0;
}

function formatDateTime(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString(locale.value === "zh-CN" ? "zh-CN" : "en-US", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    document: t("aiInsights.categories.documents"),
    documents: t("aiInsights.categories.documents"),
    image: t("aiInsights.categories.images"),
    images: t("aiInsights.categories.images"),
    archive: t("aiInsights.categories.archives"),
    archives: t("aiInsights.categories.archives"),
    video: t("aiInsights.categories.videos"),
    videos: t("aiInsights.categories.videos"),
    other: t("aiInsights.categories.others"),
    others: t("aiInsights.categories.others"),
    code: "Code",
    database: "Database",
    audio: "Audio",
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
    restore: t("dashboard.taskTypes.recovery"),
    ai: t("dashboard.taskTypes.ai"),
    proxy: "Proxy",
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

function completeTour() {
  isTourActive.value = false;
  showTourPrompt.value = false;
  localStorage.setItem("dashboardTourCompleted", "true");
}

function skipTour() {
  isTourActive.value = false;
  showTourPrompt.value = false;
  localStorage.setItem("dashboardTourSkipped", "true");
}

function startTour() {
  showTourPrompt.value = false;
  isTourActive.value = true;
}

function startFullOnboardingTour() {
  showTourPrompt.value = false;
  isTourActive.value = false;
  window.dispatchEvent(new CustomEvent("hfl:start-onboarding-tour"));
}

function setupCopy() {
  const zh = locale.value === "zh-CN";
  return {
    title: zh ? "配置向导" : "Setup Guide",
    subtitle: zh
      ? "按顺序完成节点、数据源、仓库、策略、备份、索引和恢复验证。"
      : "Connect nodes, configure sources and repositories, run backups, index snapshots, and verify recovery.",
    ready: zh ? "系统已就绪" : "System ready",
    progress: zh ? "完成度" : "Progress",
    fullTour: zh ? "完整流程引导" : "Full workflow tour",
    actions: {
      manage: zh ? "去配置" : "Configure",
      view: zh ? "查看" : "View",
      fix: zh ? "处理" : "Resolve",
    },
  };
}

function buildSetupSteps(data: {
  proxyStats: any;
  gatewayStats: any;
  sourceStats: any;
  repositoryStats: any;
  policies: any[];
  backupStats: any;
  aiOverview: any;
  recoveryStats: any;
}) {
  const zh = locale.value === "zh-CN";
  const onlineNodes =
    toNumber(data.proxyStats.online_proxies) +
    toNumber(data.gatewayStats.active);
  const totalNodes =
    toNumber(data.proxyStats.total_proxies) + toNumber(data.gatewayStats.total);
  const sourceCount =
    toNumber(data.sourceStats.total) ||
    toNumber(data.sourceStats.total_resources);
  const initializedRepositories = toNumber(data.repositoryStats.initialized);
  const repositoryCount = toNumber(data.repositoryStats.total);
  const policyCount = data.policies.length;
  const backupCount = toNumber(data.backupStats.total_tasks);
  const indexedSnapshots = toNumber(data.aiOverview.indexed_snapshots);
  const recoveryCount = toNumber(data.recoveryStats.completed);

  setupSteps.value = [
    {
      id: "nodes",
      title: zh ? "连接执行节点" : "Connect nodes",
      description: zh
        ? "至少一个 Proxy 或 Gateway 在线"
        : "At least one proxy or gateway is online",
      status: onlineNodes > 0 ? "done" : totalNodes > 0 ? "blocked" : "action",
      metric: `${onlineNodes}/${totalNodes}`,
      route: "/proxies",
      action:
        onlineNodes > 0 ? setupCopy().actions.view : setupCopy().actions.manage,
    },
    {
      id: "sources",
      title: zh ? "配置数据源" : "Configure sources",
      description: zh ? "添加需要保护的数据源" : "Add data sources to protect",
      status: sourceCount > 0 ? "done" : onlineNodes > 0 ? "action" : "blocked",
      metric: String(sourceCount),
      route: "/source-resources",
      action:
        sourceCount > 0 ? setupCopy().actions.view : setupCopy().actions.manage,
    },
    {
      id: "repositories",
      title: zh ? "准备备份仓库" : "Prepare repository",
      description: zh
        ? "仓库需要初始化并可写"
        : "Repository should be initialized and writable",
      status:
        initializedRepositories > 0
          ? "done"
          : sourceCount > 0
            ? "action"
            : "blocked",
      metric: `${initializedRepositories}/${repositoryCount}`,
      route: "/repository",
      action:
        initializedRepositories > 0
          ? setupCopy().actions.view
          : setupCopy().actions.manage,
    },
    {
      id: "policies",
      title: zh ? "创建备份策略" : "Create policy",
      description: zh
        ? "配置保留、排除和调度规则"
        : "Define retention, exclusions, and schedule",
      status:
        policyCount > 0
          ? "done"
          : initializedRepositories > 0
            ? "action"
            : "blocked",
      metric: String(policyCount),
      route: "/policies",
      action:
        policyCount > 0 ? setupCopy().actions.view : setupCopy().actions.manage,
    },
    {
      id: "backup",
      title: zh ? "运行首次备份" : "Run first backup",
      description: zh
        ? "创建任务并生成快照"
        : "Create a task and produce snapshots",
      status: backupCount > 0 ? "done" : policyCount > 0 ? "action" : "blocked",
      metric: String(backupCount),
      route: "/backup-tasks",
      action:
        backupCount > 0 ? setupCopy().actions.view : setupCopy().actions.manage,
    },
    {
      id: "index",
      title: zh ? "索引快照" : "Index snapshots",
      description: zh
        ? "为搜索和 AI 洞察准备索引"
        : "Prepare snapshot indexes for search and AI",
      status:
        indexedSnapshots > 0 ? "done" : backupCount > 0 ? "action" : "blocked",
      metric: String(indexedSnapshots),
      route: "/ai-insights",
      action:
        indexedSnapshots > 0
          ? setupCopy().actions.view
          : setupCopy().actions.manage,
    },
    {
      id: "recovery",
      title: zh ? "验证恢复能力" : "Verify recovery",
      description: zh
        ? "至少完成一次恢复演练"
        : "Complete at least one recovery run",
      status:
        recoveryCount > 0 ? "done" : backupCount > 0 ? "action" : "blocked",
      metric: String(recoveryCount),
      route: "/recovery-tasks",
      action:
        recoveryCount > 0
          ? setupCopy().actions.view
          : setupCopy().actions.manage,
    },
  ];
}

async function fetchDashboardData() {
  isLoading.value = true;
  try {
    const [
      proxiesRes,
      gatewaysRes,
      taskStatsRes,
      activeTasksRes,
      backupStatsRes,
      recoveryStatsRes,
      repositoriesRes,
      sourceStatsRes,
      policiesRes,
      aiOverviewRes,
      alertsRes,
      licenseRes,
    ] = await Promise.allSettled([
      proxiesApi.stats(),
      gatewaysApi.stats(),
      taskManagementApi.stats(),
      taskManagementApi.list({ status: "running", page_size: 5 }),
      backupTasksApi.stats(),
      recoveryTasksApi.stats(),
      repositoriesApi.stats(),
      sourceResourcesApi.stats(),
      policiesApi.list({ page_size: 100 }),
      aiInsightsApi.overview(),
      alertsApi.records({ status: "firing", page_size: 5 }),
      licensesApi.current(),
    ]);

    const proxyStats = resultData(proxiesRes) || {};
    const gatewayStats = resultData(gatewaysRes) || {};
    const taskStats = resultData(taskStatsRes) || {};
    const backupStats = resultData(backupStatsRes) || {};
    const recoveryStats = resultData(recoveryStatsRes) || {};
    const repositoryStats = resultData(repositoriesRes) || {};
    const sourceStats = resultData(sourceStatsRes) || {};
    const policies = pageItems(resultData(policiesRes));
    const aiOverview = resultData(aiOverviewRes) || {};
    const licenseData = resultData(licenseRes) || {};

    const completedTasks =
      toNumber(backupStats.completed_tasks) + toNumber(recoveryStats.completed);
    const failedTasks =
      toNumber(backupStats.failed_tasks) + toNumber(recoveryStats.failed);
    const cancelledTasks =
      toNumber(backupStats.cancelled_tasks) + toNumber(recoveryStats.cancelled);
    const terminalTasks = completedTasks + failedTasks + cancelledTasks;

    stats.value = {
      total_nodes:
        toNumber(proxyStats.total_proxies) + toNumber(gatewayStats.total),
      online_nodes:
        toNumber(proxyStats.online_proxies) + toNumber(gatewayStats.active),
      active_tasks: toNumber(taskStats.running),
      storage_used: toNumber(repositoryStats.total_used),
      storage_total: toNumber(repositoryStats.total_capacity),
      total_backups: toNumber(backupStats.total_tasks),
      success_rate: terminalTasks
        ? Number(((completedTasks / terminalTasks) * 100).toFixed(1))
        : 0,
      running_tasks: toNumber(taskStats.by_status?.running),
      pending_tasks:
        toNumber(taskStats.by_status?.pending) +
        toNumber(taskStats.by_status?.dispatched) +
        toNumber(taskStats.by_status?.accepted),
      failed_tasks: toNumber(taskStats.failed) || failedTasks,
      completed_tasks: completedTasks,
    };

    activeTasks.value = pageItems(resultData(activeTasksRes)).map((task) => ({
      id: String(task.id),
      type: task.source || task.task_type || "proxy",
      name: task.name || task.task_type || task.id,
      progress: Math.max(0, Math.min(100, toNumber(task.progress))),
      status: task.status || "",
    }));

    lastSyncTime.value = formatDateTime(aiOverview.last_sync);
    aiInsights.value = (aiOverview.file_categories || [])
      .slice(0, 5)
      .map((item: any) => {
        const category = item.category || item.name?.toLowerCase() || "other";
        return {
          category,
          label:
            locale.value === "zh-CN"
              ? item.name_zh || getCategoryLabel(category)
              : item.name || getCategoryLabel(category),
          percentage: toNumber(item.percentage),
          size: item.size || formatBytes(item.size_bytes),
        };
      });

    const riskSummary = aiOverview.risk_summary || {};
    risks.value = [
      {
        type: "sensitive",
        count: toNumber(riskSummary.sensitive_files),
        severity: toNumber(riskSummary.sensitive_files) ? "warning" : "info",
      },
      {
        type: "ransomware",
        count: riskSummary.ransomware_risk === "safe" ? 0 : 1,
        severity: riskSummary.ransomware_risk === "safe" ? "info" : "critical",
      },
      {
        type: "permission",
        count: toNumber(riskSummary.permission_issues),
        severity: toNumber(riskSummary.permission_issues) ? "warning" : "info",
      },
    ];

    const suggestions = aiOverview.optimization_suggestions || {};
    optimizations.value = [
      {
        type: "duplicate",
        size: suggestions.duplicate_files?.size || "0 B",
        description: `${toNumber(suggestions.duplicate_files?.count)} ${t("dashboard.aiInsights.items")}`,
      },
      {
        type: "cold",
        size: suggestions.cold_data?.size || "0 B",
        description: `${toNumber(suggestions.cold_data?.count)} ${t("dashboard.aiInsights.items")}`,
      },
      {
        type: "growth",
        size: suggestions.fastest_growing?.path || "-",
        description: String(suggestions.fastest_growing?.growth_rate || 0),
      },
    ];

    alerts.value = pageItems(resultData(alertsRes)).map((alert) => ({
      id: String(alert.id),
      time: formatDateTime(alert.last_triggered_at || alert.created_at),
      message: alert.title || alert.message || "-",
      severity: alert.severity || "info",
      source: alert.resource_name || alert.resource_type || alert.type || "-",
    }));

    const storageLimitGb = toNumber(
      licenseData.limits?.max_storage_gb ?? licenseData.license?.max_storage_gb,
    );
    const storageUsedGb = toNumber(licenseData.usage?.storage_used_gb);
    const remainingGb = Math.max(storageLimitGb - storageUsedGb, 0);
    const daysUntilExpiry = licenseData.days_until_expiry;
    compliance.value = {
      isValid: Boolean(licenseData.is_valid),
      licenseStatus: licenseData.is_valid
        ? t("dashboard.compliance.normal")
        : licenseData.message || licenseData.error || "-",
      quotaRemaining: storageLimitGb
        ? formatBytes(remainingGb * 1024 ** 3)
        : "-",
      expiryDate:
        licenseData.license?.expires_at ||
        licenseData.license?.expiry_date ||
        (typeof daysUntilExpiry === "number" ? `${daysUntilExpiry}d` : "-"),
      recoveryStatus: toNumber(recoveryStats.completed)
        ? `${toNumber(recoveryStats.completed)} ${t("backupTasks.status.completed")}`
        : t("common.noData"),
      recoverySeverity: toNumber(recoveryStats.completed) ? "info" : "warning",
    };

    buildSetupSteps({
      proxyStats,
      gatewayStats,
      sourceStats,
      repositoryStats,
      policies,
      backupStats,
      aiOverview,
      recoveryStats,
    });
  } catch (error) {
    console.error("Failed to fetch dashboard data:", error);
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  fetchDashboardData();
  if (
    localStorage.getItem("dashboardTourCompleted") !== "true" &&
    localStorage.getItem("dashboardTourSkipped") !== "true"
  ) {
    window.setTimeout(() => {
      showTourPrompt.value = true;
    }, 600);
  }
});
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <PageTitle
        :icon="ChartBarIcon"
        :title="t('dashboard.title')"
        :subtitle="t('dashboard.subtitle')"
        icon-class="text-sky-600 dark:text-sky-400"
      />
      <button
        @click="fetchDashboardData"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-foreground-secondary surface-card border border-border rounded-lg hover:bg-hover hover:border-slate-300 dark:hover:border-slate-500 transition-colors shadow-sm"
      >
        <svg
          class="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
        {{ t("common.refresh") }}
      </button>
    </div>

    <!-- Setup Guide -->
    <section
      data-tour="dashboard-setup-guide"
      class="rounded-xl border border-border bg-card shadow-sm"
    >
      <div
        class="flex flex-col gap-3 border-b border-border px-5 py-4 lg:flex-row lg:items-center lg:justify-between"
      >
        <div>
          <div class="flex items-center gap-2">
            <CheckCircleIcon
              v-if="setupComplete"
              class="h-5 w-5 text-emerald-500"
            />
            <InformationCircleIcon v-else class="h-5 w-5 text-violet-500" />
            <h2 class="text-base font-semibold text-foreground">
              {{ setupCopy().title }}
            </h2>
            <span
              class="rounded-full bg-violet-50 px-2 py-0.5 text-xs font-medium text-violet-700 dark:bg-violet-950/40 dark:text-violet-300"
            >
              {{ setupCopy().progress }} {{ setupProgress }}%
            </span>
          </div>
          <p class="mt-1 text-sm text-foreground-secondary">
            {{ setupComplete ? setupCopy().ready : setupCopy().subtitle }}
          </p>
        </div>
        <div
          class="flex w-full flex-col gap-3 sm:flex-row sm:items-center lg:w-auto"
        >
          <button
            type="button"
            class="inline-flex items-center justify-center rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-sm font-medium text-violet-700 transition-colors hover:bg-violet-100 dark:border-violet-900/70 dark:bg-violet-950/30 dark:text-violet-300 dark:hover:bg-violet-950/50"
            @click="startFullOnboardingTour"
          >
            <SparklesIcon class="mr-2 h-4 w-4" />
            {{ setupCopy().fullTour }}
          </button>
          <div
            class="h-2 w-full overflow-hidden rounded-full bg-background-tertiary sm:w-48"
          >
            <div
              class="h-full rounded-full bg-gradient-to-r from-violet-500 via-fuchsia-500 to-indigo-500 transition-all duration-500"
              :style="{ width: `${setupProgress}%` }"
            />
          </div>
        </div>
      </div>

      <div
        data-tour="dashboard-setup-stepper"
        class="grid gap-px bg-border md:grid-cols-2 xl:grid-cols-7"
      >
        <button
          v-for="(step, index) in setupSteps"
          :key="step.id"
          type="button"
          class="group bg-card px-4 py-4 text-left transition-colors hover:bg-hover"
          @click="router.push(step.route)"
        >
          <div class="flex items-start gap-3">
            <div
              :class="[
                'flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-sm font-semibold',
                step.status === 'done'
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-600 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-400'
                  : step.status === 'action'
                    ? 'border-violet-200 bg-violet-50 text-violet-600 dark:border-violet-900 dark:bg-violet-950/30 dark:text-violet-300'
                    : 'border-slate-200 bg-slate-50 text-slate-400 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-500',
              ]"
            >
              <CheckCircleIcon v-if="step.status === 'done'" class="h-4 w-4" />
              <span v-else>{{ index + 1 }}</span>
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center justify-between gap-2">
                <h3 class="truncate text-sm font-semibold text-foreground">
                  {{ step.title }}
                </h3>
                <span
                  :class="[
                    'shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
                    step.status === 'done'
                      ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                      : step.status === 'action'
                        ? 'bg-violet-50 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300'
                        : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
                  ]"
                >
                  {{ step.metric }}
                </span>
              </div>
              <p class="mt-1 line-clamp-2 text-xs text-foreground-secondary">
                {{ step.description }}
              </p>
              <div
                class="mt-3 inline-flex items-center gap-1 text-xs font-medium text-violet-600 opacity-0 transition-opacity group-hover:opacity-100 dark:text-violet-300"
              >
                {{ step.action }}
                <ArrowRightIcon class="h-3.5 w-3.5" />
              </div>
            </div>
          </div>
        </button>
      </div>
    </section>

    <DashboardGlobalTopology />

    <!-- Architecture Diagram -->
    <section
      v-if="false"
      class="overflow-hidden rounded-xl border border-border bg-card shadow-sm"
    >
      <div
        class="flex flex-col gap-3 border-b border-border px-5 py-4 lg:flex-row lg:items-start lg:justify-between"
      >
        <div>
          <div class="flex items-center gap-2">
            <ChartBarIcon class="h-5 w-5 text-indigo-500" />
            <h2 class="text-base font-semibold text-foreground">
              {{ architectureDiagram.title }}
            </h2>
          </div>
          <p class="mt-1 max-w-3xl text-sm leading-6 text-foreground-secondary">
            {{ architectureDiagram.subtitle }}
          </p>
        </div>
        <div class="flex flex-wrap gap-2 text-xs">
          <span
            class="inline-flex items-center rounded-full border border-blue-100 bg-blue-50 px-3 py-1 font-medium text-blue-700 dark:border-blue-900/70 dark:bg-blue-950/30 dark:text-blue-300"
          >
            <span class="mr-1.5 h-1.5 w-5 rounded-full bg-blue-500"></span>
            {{ architectureDiagram.controlFlow }}
          </span>
          <span
            class="inline-flex items-center rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1 font-medium text-emerald-700 dark:border-emerald-900/70 dark:bg-emerald-950/30 dark:text-emerald-300"
          >
            <span class="mr-1.5 h-1.5 w-5 rounded-full bg-emerald-500"></span>
            {{ architectureDiagram.dataFlow }}
          </span>
          <span
            class="inline-flex items-center rounded-full border border-violet-100 bg-violet-50 px-3 py-1 font-medium text-violet-700 dark:border-violet-900/70 dark:bg-violet-950/30 dark:text-violet-300"
          >
            <span class="mr-1.5 h-1.5 w-5 rounded-full bg-violet-500"></span>
            {{ architectureDiagram.indexFlow }}
          </span>
        </div>
      </div>

      <div class="px-5 py-5">
        <div
          class="rounded-xl border border-border bg-background-secondary/40 p-4"
        >
          <div class="hidden overflow-x-auto pb-3 xl:block">
            <div class="architecture-canvas">
              <svg
                class="architecture-orthogonal-lines"
                viewBox="0 0 1160 560"
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                <defs>
                  <marker
                    id="arch-process-arrow-data"
                    markerWidth="8"
                    markerHeight="8"
                    refX="7"
                    refY="4"
                    orient="auto"
                  >
                    <path d="M0,0 L8,4 L0,8 Z" fill="rgb(16 185 129)" />
                  </marker>
                  <marker
                    id="arch-process-arrow-index"
                    markerWidth="8"
                    markerHeight="8"
                    refX="7"
                    refY="4"
                    orient="auto"
                  >
                    <path d="M0,0 L8,4 L0,8 Z" fill="rgb(139 92 246)" />
                  </marker>
                  <marker
                    id="arch-process-arrow-control"
                    markerWidth="8"
                    markerHeight="8"
                    refX="7"
                    refY="4"
                    orient="auto"
                  >
                    <path d="M0,0 L8,4 L0,8 Z" fill="rgb(59 130 246)" />
                  </marker>
                  <marker
                    id="arch-process-arrow-restore"
                    markerWidth="8"
                    markerHeight="8"
                    refX="7"
                    refY="4"
                    orient="auto"
                  >
                    <path d="M0,0 L8,4 L0,8 Z" fill="rgb(245 158 11)" />
                  </marker>
                </defs>
                <path
                  class="architecture-orthogonal-flow architecture-orthogonal-flow-control"
                  d="M580 144 L580 170 L174 170 L174 200"
                  marker-end="url(#arch-process-arrow-control)"
                />
                <path
                  class="architecture-orthogonal-flow architecture-orthogonal-flow-control"
                  d="M580 144 L580 170 L993 170 L993 200"
                  marker-end="url(#arch-process-arrow-control)"
                />
                <path
                  class="architecture-orthogonal-flow architecture-orthogonal-flow-data"
                  d="M324 335 L460 335"
                  marker-end="url(#arch-process-arrow-data)"
                />
                <path
                  class="architecture-orthogonal-flow architecture-orthogonal-flow-index"
                  d="M740 335 L795 335 L795 305 L850 305"
                  marker-end="url(#arch-process-arrow-index)"
                />
                <path
                  class="architecture-orthogonal-flow architecture-orthogonal-flow-index"
                  d="M993 410 L993 430"
                  marker-end="url(#arch-process-arrow-index)"
                />
                <path
                  class="architecture-orthogonal-flow architecture-orthogonal-flow-restore"
                  d="M740 378 L795 378 L795 482 L850 482"
                  marker-end="url(#arch-process-arrow-restore)"
                />
                <path
                  class="architecture-orthogonal-flow architecture-orthogonal-flow-restore"
                  d="M460 390 L392 390 L392 438 L324 438"
                  marker-end="url(#arch-process-arrow-restore)"
                />
                <circle
                  class="architecture-port architecture-port-control"
                  cx="580"
                  cy="144"
                  r="4"
                />
                <circle
                  class="architecture-port architecture-port-control"
                  cx="174"
                  cy="200"
                  r="4"
                />
                <circle
                  class="architecture-port architecture-port-control"
                  cx="993"
                  cy="200"
                  r="4"
                />
                <circle
                  class="architecture-port architecture-port-data"
                  cx="324"
                  cy="335"
                  r="4"
                />
                <circle
                  class="architecture-port architecture-port-data"
                  cx="460"
                  cy="335"
                  r="4"
                />
                <circle
                  class="architecture-port architecture-port-index"
                  cx="740"
                  cy="335"
                  r="4"
                />
                <circle
                  class="architecture-port architecture-port-index"
                  cx="850"
                  cy="305"
                  r="4"
                />
                <circle
                  class="architecture-port architecture-port-index"
                  cx="993"
                  cy="410"
                  r="4"
                />
                <circle
                  class="architecture-port architecture-port-index"
                  cx="993"
                  cy="430"
                  r="4"
                />
                <circle
                  class="architecture-port architecture-port-restore"
                  cx="740"
                  cy="378"
                  r="4"
                />
                <circle
                  class="architecture-port architecture-port-restore"
                  cx="850"
                  cy="482"
                  r="4"
                />
                <circle
                  class="architecture-port architecture-port-restore"
                  cx="460"
                  cy="390"
                  r="4"
                />
                <circle
                  class="architecture-port architecture-port-restore"
                  cx="324"
                  cy="438"
                  r="4"
                />
              </svg>

              <div
                class="architecture-process-node architecture-process-control"
              >
                <div
                  class="architecture-card architecture-card-control text-center"
                >
                  <BoltIcon class="mx-auto h-6 w-6 text-blue-600" />
                  <h3 class="mt-2 text-sm font-semibold text-foreground">
                    {{ architectureDiagram.controlPlane }}
                  </h3>
                  <p class="mt-1 text-xs leading-5 text-foreground-secondary">
                    {{ architectureDiagram.controlDesc }}
                  </p>
                </div>
              </div>

              <div
                class="architecture-process-node architecture-process-source"
              >
                <div class="architecture-zone-box architecture-zone-box-source">
                  <p
                    class="architecture-zone-title text-sky-700 dark:text-sky-300"
                  >
                    {{ architectureDiagram.sourceZone }}
                  </p>
                  <div class="mt-3 grid gap-3">
                    <div class="architecture-node">
                      <div class="architecture-icon bg-sky-50 text-sky-600">
                        <FolderIcon class="h-5 w-5" />
                      </div>
                      <div>
                        <h3 class="text-sm font-semibold text-foreground">
                          {{ architectureDiagram.sourceData }}
                        </h3>
                        <p class="mt-1 text-xs text-foreground-secondary">
                          {{ architectureDiagram.sourceDataDesc }}
                        </p>
                      </div>
                    </div>
                    <div class="architecture-node">
                      <div
                        class="architecture-icon bg-indigo-50 text-indigo-600"
                      >
                        <ServerIcon class="h-5 w-5" />
                      </div>
                      <div>
                        <h3 class="text-sm font-semibold text-foreground">
                          {{ architectureDiagram.agentProxy }}
                        </h3>
                        <p
                          class="mt-1 text-xs leading-5 text-foreground-secondary"
                        >
                          {{ architectureDiagram.agentProxyDesc }}
                        </p>
                      </div>
                    </div>
                    <div class="architecture-node">
                      <div
                        class="architecture-icon bg-violet-50 text-violet-600"
                      >
                        <ServerIcon class="h-5 w-5" />
                      </div>
                      <div>
                        <h3 class="text-sm font-semibold text-foreground">
                          {{ architectureDiagram.syncProxy }}
                        </h3>
                        <p
                          class="mt-1 text-xs leading-5 text-foreground-secondary"
                        >
                          {{ architectureDiagram.syncProxyDesc }}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="architecture-process-node architecture-process-repo">
                <div class="architecture-zone-box architecture-zone-box-repo">
                  <p
                    class="architecture-zone-title text-cyan-700 dark:text-cyan-300"
                  >
                    {{ architectureDiagram.targetZone }}
                  </p>
                  <div class="mt-3 architecture-node">
                    <div class="architecture-icon bg-cyan-50 text-cyan-600">
                      <CircleStackIcon class="h-5 w-5" />
                    </div>
                    <div>
                      <h3 class="text-sm font-semibold text-foreground">
                        {{ architectureDiagram.repository }}
                      </h3>
                      <p
                        class="mt-1 text-xs leading-5 text-foreground-secondary"
                      >
                        {{ architectureDiagram.repositoryDesc }}
                      </p>
                    </div>
                  </div>
                  <div class="mt-3 grid gap-2">
                    <div class="architecture-storage-option">
                      <CloudIcon class="h-4 w-4" />{{
                        architectureDiagram.objectStorage
                      }}
                    </div>
                    <div class="architecture-storage-option">
                      <CircleStackIcon class="h-4 w-4" />{{
                        architectureDiagram.filesystem
                      }}
                    </div>
                    <div class="architecture-storage-option">
                      <ServerIcon class="h-4 w-4" />{{
                        architectureDiagram.nas
                      }}
                    </div>
                  </div>
                </div>
              </div>

              <div
                class="architecture-process-node architecture-process-insight"
              >
                <div
                  class="architecture-zone-box architecture-zone-box-insight"
                >
                  <p
                    class="architecture-zone-title text-violet-700 dark:text-violet-300"
                  >
                    {{ architectureDiagram.insightZone }}
                  </p>
                  <div class="mt-3 grid gap-3">
                    <div class="architecture-node">
                      <div
                        class="architecture-icon bg-emerald-50 text-emerald-600"
                      >
                        <CloudIcon class="h-5 w-5" />
                      </div>
                      <div>
                        <h3 class="text-sm font-semibold text-foreground">
                          {{ architectureDiagram.gateway }}
                        </h3>
                        <p
                          class="mt-1 text-xs leading-5 text-foreground-secondary"
                        >
                          {{ architectureDiagram.gatewayDesc }}
                        </p>
                      </div>
                    </div>
                    <div class="architecture-node">
                      <div
                        class="architecture-icon bg-violet-50 text-violet-600"
                      >
                        <SparklesIcon class="h-5 w-5" />
                      </div>
                      <div>
                        <h3 class="text-sm font-semibold text-foreground">
                          {{ architectureDiagram.localInsight }}
                        </h3>
                        <p
                          class="mt-1 text-xs leading-5 text-foreground-secondary"
                        >
                          {{ architectureDiagram.localInsightDesc }}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div
                class="architecture-process-node architecture-process-recovery"
              >
                <div
                  class="architecture-zone-box architecture-zone-box-recovery"
                >
                  <p
                    class="architecture-zone-title text-amber-700 dark:text-amber-300"
                  >
                    {{ architectureDiagram.recoveryZone }}
                  </p>
                  <div class="mt-3 architecture-node">
                    <div class="architecture-icon bg-amber-50 text-amber-600">
                      <ArrowUturnLeftIcon class="h-5 w-5" />
                    </div>
                    <div>
                      <h3 class="text-sm font-semibold text-foreground">
                        {{ architectureDiagram.recoveryTask }}
                      </h3>
                      <p
                        class="mt-1 text-xs leading-5 text-foreground-secondary"
                      >
                        {{ architectureDiagram.recoveryTaskDesc }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div class="architecture-process-legend">
                <div class="architecture-legend architecture-legend-control">
                  <span></span>{{ architectureDiagram.controlFlow }}
                </div>
                <div class="architecture-legend architecture-legend-data">
                  <span></span>{{ architectureDiagram.dataFlow }}
                </div>
                <div class="architecture-legend architecture-legend-index">
                  <span></span>{{ architectureDiagram.indexFlow }}
                </div>
                <div class="architecture-legend architecture-legend-restore">
                  <span></span>{{ architectureDiagram.restoreFlow }}
                </div>
              </div>
            </div>
          </div>

          <div class="grid gap-4 xl:hidden">
            <div
              class="architecture-card architecture-card-control text-center"
            >
              <BoltIcon class="mx-auto h-6 w-6 text-blue-600" />
              <h3 class="mt-2 text-sm font-semibold text-foreground">
                {{ architectureDiagram.controlPlane }}
              </h3>
              <p class="mt-1 text-xs leading-5 text-foreground-secondary">
                {{ architectureDiagram.controlDesc }}
              </p>
            </div>
            <div class="architecture-zone-box architecture-zone-box-source">
              <p class="architecture-zone-title text-sky-700 dark:text-sky-300">
                {{ architectureDiagram.sourceZone }}
              </p>
              <div class="mt-3 grid gap-3">
                <div class="architecture-node">
                  <div class="architecture-icon bg-sky-50 text-sky-600">
                    <FolderIcon class="h-5 w-5" />
                  </div>
                  <div>
                    <h3 class="text-sm font-semibold text-foreground">
                      {{ architectureDiagram.sourceData }}
                    </h3>
                    <p class="mt-1 text-xs text-foreground-secondary">
                      {{ architectureDiagram.sourceDataDesc }}
                    </p>
                  </div>
                </div>
                <div class="architecture-node">
                  <div class="architecture-icon bg-indigo-50 text-indigo-600">
                    <ServerIcon class="h-5 w-5" />
                  </div>
                  <div>
                    <h3 class="text-sm font-semibold text-foreground">
                      {{ architectureDiagram.agentProxy }}
                    </h3>
                    <p class="mt-1 text-xs leading-5 text-foreground-secondary">
                      {{ architectureDiagram.agentProxyDesc }}
                    </p>
                  </div>
                </div>
                <div class="architecture-node">
                  <div class="architecture-icon bg-violet-50 text-violet-600">
                    <ServerIcon class="h-5 w-5" />
                  </div>
                  <div>
                    <h3 class="text-sm font-semibold text-foreground">
                      {{ architectureDiagram.syncProxy }}
                    </h3>
                    <p class="mt-1 text-xs leading-5 text-foreground-secondary">
                      {{ architectureDiagram.syncProxyDesc }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div class="architecture-zone-box architecture-zone-box-repo">
              <p
                class="architecture-zone-title text-cyan-700 dark:text-cyan-300"
              >
                {{ architectureDiagram.targetZone }}
              </p>
              <div class="mt-3 architecture-node">
                <div class="architecture-icon bg-cyan-50 text-cyan-600">
                  <CircleStackIcon class="h-5 w-5" />
                </div>
                <div>
                  <h3 class="text-sm font-semibold text-foreground">
                    {{ architectureDiagram.repository }}
                  </h3>
                  <p class="mt-1 text-xs leading-5 text-foreground-secondary">
                    {{ architectureDiagram.repositoryDesc }}
                  </p>
                </div>
              </div>
            </div>
            <div class="architecture-zone-box architecture-zone-box-insight">
              <p
                class="architecture-zone-title text-violet-700 dark:text-violet-300"
              >
                {{ architectureDiagram.insightZone }}
              </p>
              <div class="mt-3 grid gap-3">
                <div class="architecture-node">
                  <div class="architecture-icon bg-emerald-50 text-emerald-600">
                    <CloudIcon class="h-5 w-5" />
                  </div>
                  <div>
                    <h3 class="text-sm font-semibold text-foreground">
                      {{ architectureDiagram.gateway }}
                    </h3>
                    <p class="mt-1 text-xs leading-5 text-foreground-secondary">
                      {{ architectureDiagram.gatewayDesc }}
                    </p>
                  </div>
                </div>
                <div class="architecture-node">
                  <div class="architecture-icon bg-violet-50 text-violet-600">
                    <SparklesIcon class="h-5 w-5" />
                  </div>
                  <div>
                    <h3 class="text-sm font-semibold text-foreground">
                      {{ architectureDiagram.localInsight }}
                    </h3>
                    <p class="mt-1 text-xs leading-5 text-foreground-secondary">
                      {{ architectureDiagram.localInsightDesc }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div class="architecture-zone-box architecture-zone-box-recovery">
              <p
                class="architecture-zone-title text-amber-700 dark:text-amber-300"
              >
                {{ architectureDiagram.recoveryZone }}
              </p>
              <div class="mt-3 architecture-node">
                <div class="architecture-icon bg-amber-50 text-amber-600">
                  <ArrowUturnLeftIcon class="h-5 w-5" />
                </div>
                <div>
                  <h3 class="text-sm font-semibold text-foreground">
                    {{ architectureDiagram.recoveryTask }}
                  </h3>
                  <p class="mt-1 text-xs leading-5 text-foreground-secondary">
                    {{ architectureDiagram.recoveryTaskDesc }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Stats Grid -->
    <div
      data-tour="dashboard-core-metrics"
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
    >
      <!-- Total Nodes -->
      <div
        class="bg-card rounded-xl border border-border p-4 shadow-sm hover:shadow-md transition-shadow"
      >
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
                class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"
              ></span>
              <span
                class="text-xs text-emerald-600 dark:text-emerald-400 font-medium"
                >{{ stats.online_nodes }} {{ t("common.active") }}</span
              >
            </div>
          </div>
          <div
            class="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-md"
          >
            <ServerIcon class="w-5 h-5 text-white" />
          </div>
        </div>
      </div>

      <!-- Active Tasks -->
      <div
        class="bg-card rounded-xl border border-border p-4 shadow-sm hover:shadow-md transition-shadow"
      >
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
            class="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-600 rounded-lg flex items-center justify-center shadow-md"
          >
            <BoltIcon class="w-5 h-5 text-white" />
          </div>
        </div>
      </div>

      <!-- Storage Used -->
      <div
        class="bg-card rounded-xl border border-border p-4 shadow-sm hover:shadow-md transition-shadow"
      >
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
                class="h-1.5 bg-background-tertiary rounded-full overflow-hidden"
              >
                <div
                  class="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-500"
                  :style="{
                    width: `${storageUsagePercent}%`,
                  }"
                />
              </div>
              <p class="text-xs text-foreground-secondary mt-1">
                {{ storageUsagePercent }}% {{ t("dashboard.stats.used") }}
              </p>
            </div>
          </div>
          <div
            class="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg flex items-center justify-center shadow-md"
          >
            <CircleStackIcon class="w-5 h-5 text-white" />
          </div>
        </div>
      </div>

      <!-- Success Rate -->
      <div
        class="bg-card rounded-xl border border-border p-4 shadow-sm hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm font-medium text-foreground-secondary">
              {{ t("dashboard.stats.successRate") }}
            </p>
            <p class="text-2xl font-bold text-foreground mt-1">
              {{ stats.success_rate }}%
            </p>
            <div
              class="flex items-center gap-1 mt-2 text-emerald-600 dark:text-emerald-400"
            >
              <ArrowTrendingUpIcon class="w-3.5 h-3.5" />
              <span class="text-xs font-medium">
                {{ stats.completed_tasks }} /
                {{ stats.failed_tasks }}
              </span>
            </div>
          </div>
          <div
            class="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-600 rounded-lg flex items-center justify-center shadow-md"
          >
            <ChartBarIcon class="w-5 h-5 text-white" />
          </div>
        </div>
      </div>
    </div>

    <!-- AI Insights Section -->
    <div
      data-tour="dashboard-ai-insights"
      class="bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 dark:from-indigo-950/30 dark:via-purple-950/30 dark:to-pink-950/30 rounded-xl border border-indigo-100 dark:border-indigo-900/50 overflow-hidden"
    >
      <div
        class="px-5 py-4 flex items-center justify-between border-b dark:border-indigo-900/50 bg-white/50 dark:bg-slate-900/30"
      >
        <div class="flex items-center gap-3">
          <div
            class="w-9 h-9 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-md"
          >
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
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors"
        >
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
              class="flex items-center justify-between"
            >
              <div class="flex items-center gap-2 flex-1 min-w-0">
                <div
                  class="w-2 h-2 rounded-full"
                  :class="{
                    'bg-indigo-500': item.category === 'documents',
                    'bg-pink-500': item.category === 'images',
                    'bg-amber-500': item.category === 'archives',
                    'bg-purple-500': item.category === 'videos',
                    'bg-slate-400': item.category === 'others',
                  }"
                ></div>
                <span class="text-sm text-foreground-secondary truncate">
                  {{ item.label || getCategoryLabel(item.category) }}
                </span>
              </div>
              <div class="flex items-center gap-2 text-xs">
                <span class="font-medium text-foreground"
                  >{{ item.percentage }}%</span
                >
                <span class="text-slate-400">({{ item.size }})</span>
              </div>
            </div>
            <p
              v-if="!aiInsights.length"
              class="text-sm text-foreground-secondary"
            >
              {{ t("common.noData") }}
            </p>
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
              }"
            >
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
                }"
              >
                {{
                  risk.count > 0
                    ? `${risk.count} ${t("dashboard.aiInsights.items")}`
                    : t("dashboard.aiInsights.safe")
                }}
              </span>
            </div>
            <p v-if="!risks.length" class="text-sm text-foreground-secondary">
              {{ t("common.noData") }}
            </p>
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
              class="flex items-center justify-between"
            >
              <div class="flex items-center gap-2">
                <DocumentDuplicateIcon
                  v-if="opt.type === 'duplicate'"
                  class="w-4 h-4 text-slate-400"
                />
                <CircleStackIcon
                  v-else-if="opt.type === 'cold'"
                  class="w-4 h-4 text-blue-400"
                />
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
            <p
              v-if="!optimizations.length"
              class="text-sm text-foreground-secondary"
            >
              {{ t("common.noData") }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Monitoring & Compliance Section -->
    <div
      data-tour="dashboard-attention"
      class="grid grid-cols-1 lg:grid-cols-3 gap-6"
    >
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
            class="px-5 py-3 hover:bg-hover transition-colors"
          >
            <div class="flex items-start gap-3">
              <div
                :class="[
                  'w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0',
                  getSeverityColor(alert.severity),
                ]"
              >
                <component
                  :is="getSeverityIcon(alert.severity)"
                  class="w-3.5 h-3.5"
                />
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
          <p
            v-if="!alerts.length"
            class="px-5 py-6 text-center text-sm text-foreground-secondary"
          >
            {{ t("common.noData") }}
          </p>
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
                  ]"
                >
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
              class="h-1.5 bg-background-tertiary rounded-full overflow-hidden"
            >
              <div
                class="h-full rounded-full transition-all duration-300"
                :class="
                  task.type === 'backup'
                    ? 'bg-gradient-to-r from-indigo-500 to-purple-500'
                    : task.type === 'recovery'
                      ? 'bg-gradient-to-r from-amber-500 to-orange-500'
                      : 'bg-gradient-to-r from-purple-500 to-pink-500'
                "
                :style="{ width: `${task.progress}%` }"
              />
            </div>
          </div>
          <p
            v-if="!activeTasks.length"
            class="px-5 py-6 text-center text-sm text-foreground-secondary"
          >
            {{ t("common.noData") }}
          </p>
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
            :class="[
              'flex items-center justify-between px-3 py-2.5 rounded-lg border',
              compliance.isValid
                ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-100 dark:border-emerald-900/50'
                : 'bg-amber-50 dark:bg-amber-900/20 border-amber-100 dark:border-amber-900/50',
            ]"
          >
            <span class="text-sm text-foreground-secondary">{{
              t("dashboard.compliance.licenseStatus")
            }}</span>
            <span
              :class="[
                'flex items-center gap-1.5 text-sm font-medium',
                compliance.isValid
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-amber-600 dark:text-amber-400',
              ]"
            >
              <CheckCircleIcon class="w-4 h-4" />
              {{ compliance.licenseStatus }}
            </span>
          </div>
          <div
            class="flex items-center justify-between px-3 py-2 rounded-lg bg-background-secondary"
          >
            <span class="text-sm text-foreground-secondary">{{
              t("dashboard.compliance.storageQuota")
            }}</span>
            <span class="text-sm font-medium text-foreground">{{
              t("dashboard.compliance.quotaRemaining", {
                amount: compliance.quotaRemaining,
              })
            }}</span>
          </div>
          <div
            class="flex items-center justify-between px-3 py-2 rounded-lg bg-background-secondary"
          >
            <span class="text-sm text-foreground-secondary">{{
              t("dashboard.compliance.expiryDate")
            }}</span>
            <span class="text-sm font-medium text-foreground">{{
              compliance.expiryDate
            }}</span>
          </div>
          <div
            :class="[
              'flex items-center justify-between px-3 py-2.5 rounded-lg border',
              compliance.recoverySeverity === 'info'
                ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-100 dark:border-emerald-900/50'
                : 'bg-amber-50 dark:bg-amber-900/20 border-amber-100 dark:border-amber-900/50',
            ]"
          >
            <span class="text-sm text-foreground-secondary">{{
              t("dashboard.compliance.drill")
            }}</span>
            <span
              :class="[
                'flex items-center gap-1.5 text-sm font-medium',
                compliance.recoverySeverity === 'info'
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-amber-600 dark:text-amber-400',
              ]"
            >
              <ExclamationTriangleIcon class="w-4 h-4" />
              {{ compliance.recoveryStatus }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="showTourPrompt"
      class="fixed inset-0 z-[990] flex items-center justify-center bg-slate-950/50 p-4"
    >
      <div
        class="w-full max-w-md rounded-xl border border-border bg-card p-5 shadow-2xl"
      >
        <div class="flex items-start gap-3">
          <div
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-violet-50 text-violet-600 dark:bg-violet-950/40 dark:text-violet-300"
          >
            <SparklesIcon class="h-5 w-5" />
          </div>
          <div>
            <h2 class="text-base font-semibold text-foreground">
              {{
                locale === "zh-CN"
                  ? "需要快速了解 Dashboard 吗？"
                  : "Take a quick Dashboard tour?"
              }}
            </h2>
            <p class="mt-2 text-sm leading-6 text-foreground-secondary">
              {{
                locale === "zh-CN"
                  ? "我可以用几步引导你理解配置向导、核心指标、AI 洞察和当前关注项。"
                  : "A short walkthrough will explain the setup guide, core metrics, AI insights, and attention items."
              }}
            </p>
          </div>
        </div>
        <div class="mt-5 flex justify-end gap-3">
          <button
            type="button"
            class="rounded-lg border border-border px-3 py-2 text-sm text-foreground-secondary hover:bg-hover"
            @click="skipTour"
          >
            {{ locale === "zh-CN" ? "跳过" : "Skip" }}
          </button>
          <button
            type="button"
            class="rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white hover:bg-violet-700"
            @click="startTour"
          >
            {{ locale === "zh-CN" ? "开始引导" : "Start tour" }}
          </button>
        </div>
      </div>
    </div>

    <ProductTour
      :active="isTourActive"
      :steps="tourSteps"
      @finish="completeTour"
      @skip="skipTour"
    />
  </div>
</template>

<style scoped>
.architecture-node {
  @apply rounded-lg border border-border bg-card p-4 shadow-sm;
}

.architecture-icon {
  @apply flex h-10 w-10 shrink-0 items-center justify-center rounded-lg;
}

.architecture-storage-option {
  @apply flex items-center gap-2 rounded-lg border border-cyan-100 bg-white/70 px-3 py-2 text-xs font-medium text-cyan-700 dark:border-cyan-900/70 dark:bg-slate-950/40 dark:text-cyan-300;
}

.architecture-card {
  @apply rounded-xl border p-4 shadow-sm;
}

.architecture-card-control {
  @apply border-blue-100 bg-blue-50/90 dark:border-blue-900/60 dark:bg-blue-950/30;
}

.architecture-canvas {
  @apply relative h-[560px] min-w-[1160px] overflow-visible rounded-xl border border-border bg-background-secondary/40;
}

.architecture-orthogonal-lines {
  @apply pointer-events-none absolute inset-0 h-full w-full;
}

.architecture-process-node,
.architecture-zone {
  @apply absolute z-10;
}

.architecture-process-control {
  left: 440px;
  top: 24px;
  width: 280px;
  height: 120px;
}

.architecture-process-source {
  left: 24px;
  top: 200px;
  width: 300px;
  height: 270px;
}

.architecture-process-repo {
  left: 460px;
  top: 220px;
  width: 280px;
  height: 230px;
}

.architecture-process-insight {
  left: 850px;
  top: 200px;
  width: 286px;
  height: 210px;
}

.architecture-process-recovery {
  left: 850px;
  top: 430px;
  width: 286px;
  height: 105px;
}

.architecture-zone-box {
  @apply h-full rounded-xl border p-4;
}

.architecture-zone-box-source {
  @apply border-sky-100 bg-sky-50/50 dark:border-sky-900/60 dark:bg-sky-950/20;
}

.architecture-zone-box-repo {
  @apply border-cyan-100 bg-cyan-50/50 dark:border-cyan-900/60 dark:bg-cyan-950/20;
}

.architecture-zone-box-insight {
  @apply border-violet-100 bg-violet-50/50 dark:border-violet-900/60 dark:bg-violet-950/20;
}

.architecture-zone-box-recovery {
  @apply border-amber-100 bg-amber-50/60 dark:border-amber-900/60 dark:bg-amber-950/20;
}

.architecture-zone-title {
  @apply text-xs font-semibold uppercase;
}

.architecture-process-legend {
  @apply absolute bottom-4 left-4 right-4 z-10 grid gap-2 text-xs xl:grid-cols-4;
}

.architecture-legend {
  @apply inline-flex items-center rounded-full border bg-card px-3 py-2 font-medium text-foreground-secondary;
}

.architecture-legend span {
  @apply mr-2 h-1.5 w-6 rounded-full;
}

.architecture-legend-control {
  @apply border-blue-100 dark:border-blue-900/70;
}

.architecture-legend-control span {
  @apply bg-blue-500;
}

.architecture-legend-data {
  @apply border-emerald-100 dark:border-emerald-900/70;
}

.architecture-legend-data span {
  @apply bg-emerald-500;
}

.architecture-legend-index {
  @apply border-violet-100 dark:border-violet-900/70;
}

.architecture-legend-index span {
  @apply bg-violet-500;
}

.architecture-legend-restore {
  @apply border-amber-100 dark:border-amber-900/70;
}

.architecture-legend-restore span {
  @apply bg-amber-500;
}

.architecture-orthogonal-flow {
  fill: none;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 9 10;
  animation: architecture-orthogonal-flow 1.35s linear infinite;
}

.architecture-orthogonal-flow-control {
  stroke: rgb(59 130 246);
}

.architecture-orthogonal-flow-data {
  stroke: rgb(16 185 129);
}

.architecture-orthogonal-flow-index {
  stroke: rgb(139 92 246);
}

.architecture-orthogonal-flow-restore {
  stroke: rgb(245 158 11);
}

.architecture-port {
  stroke: white;
  stroke-width: 2;
}

.architecture-port-control {
  fill: rgb(59 130 246);
}

.architecture-port-data {
  fill: rgb(16 185 129);
}

.architecture-port-index {
  fill: rgb(139 92 246);
}

.architecture-port-restore {
  fill: rgb(245 158 11);
}

@keyframes architecture-orthogonal-flow {
  to {
    stroke-dashoffset: -38;
  }
}

@media (prefers-reduced-motion: reduce) {
  .architecture-orthogonal-flow {
    animation: none;
  }
}
</style>
