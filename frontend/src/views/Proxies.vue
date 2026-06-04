<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";
import { proxiesApi } from "@/api";
import type { ProxyNode, ProxyStats, ProxyTask } from "@/types/proxy";
import { usePagination } from "@/composables/usePagination";
import { useProxyMonitorCharts } from "@/features/proxies/useProxyMonitorCharts";
import ProxiesCardView from "@/components/proxies/ProxiesCardView.vue";
import ProxiesListView from "@/components/proxies/ProxiesListView.vue";
import ProxiesStats from "@/components/proxies/ProxiesStats.vue";
import ProxiesToolbar from "@/components/proxies/ProxiesToolbar.vue";
import ProxyDeleteConfirmModal from "@/components/proxies/ProxyDeleteConfirmModal.vue";
import ProxyDetailDrawer from "@/components/proxies/ProxyDetailDrawer.vue";
import ProxyEditModal from "@/components/proxies/ProxyEditModal.vue";
import ProxyInstallInfoModal from "@/components/proxies/ProxyInstallInfoModal.vue";
import ProxyInstallTab from "@/components/proxies/ProxyInstallTab.vue";
import ProxyInstallWizard from "@/components/proxies/ProxyInstallWizard.vue";
import ProxyHeartbeatsTab from "@/components/proxies/ProxyHeartbeatsTab.vue";
import ProxyMonitorTab from "@/components/proxies/ProxyMonitorTab.vue";
import ProxyOverviewTab from "@/components/proxies/ProxyOverviewTab.vue";
import ProxyTasksTab from "@/components/proxies/ProxyTasksTab.vue";
import { useAppStore } from "@/stores/app";
import {
  PlusIcon,
  ArrowPathIcon,
  ComputerDesktopIcon,
  CircleStackIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  WrenchScrewdriverIcon,
  ArrowsUpDownIcon,
  ChevronUpIcon,
  ChevronDownIcon,
} from "@heroicons/vue/24/outline";

const { t } = useI18n();
const route = useRoute();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();
const VIEW_MODE_STORAGE_KEY = "hyperfilelens:proxies:viewMode";
const COLUMN_WIDTH_STORAGE_KEY = "hyperfilelens:proxies:columnWidths";

function getStoredViewMode(): "card" | "list" {
  try {
    const stored = localStorage.getItem(VIEW_MODE_STORAGE_KEY);
    return stored === "list" || stored === "card" ? stored : "card";
  } catch {
    return "card";
  }
}

// State
const isLoading = ref(true);
const proxies = ref<ProxyNode[]>([]);
const stats = ref<ProxyStats | null>(null);
const selectedRole = ref<string>("all");
const selectedStatus = ref<string>("all");
const searchQuery = ref("");
const viewMode = ref<"card" | "list">(getStoredViewMode()); // View mode: card or list
const showInstallInfoModal = ref(false);

// Monitor time range
const monitorTimeRange = ref<"1h" | "6h" | "24h" | "7d" | "30d" | "custom">(
  "24h",
);
const customTimeRange = ref<{ start: string; end: string }>({
  start: "",
  end: "",
});
const showCustomDatePicker = ref(false);

// Pagination
const currentPage = ref(1);
const pageSize = ref(getPageSize("proxies"));
const PAGE_STORAGE_KEY = "proxies";

watch(pageSize, (newSize) => {
  setPageSize(newSize, PAGE_STORAGE_KEY);
});

// Installation Wizard
const showInstallWizard = ref(false);
const installStep = ref(1); // 1: select role, 2: config, 3: command, 4: waiting
const installData = ref({
  name: "",
  role: "agent" as "agent" | "sync",
  os: "linux",
  labels: [] as string[],
  newLabel: "",
});
const installResult = ref<{
  proxy_id: string;
  name: string;
  role: string;
  install_token: string;
  api_token: string;
  install_command: string;
  linux_command?: string;
  macos_command?: string;
  windows_command: string;
  config_yaml: string;
  expires_at: string;
} | null>(null);
const isGeneratingInstall = ref(false);

// Detail Drawer
const showDetailDrawer = ref(false);
const selectedProxy = ref<ProxyNode | null>(null);
const detailTab = ref<
  "overview" | "install" | "monitor" | "tasks" | "heartbeats"
>("overview");

// Tab data states with loading and caching
const tabData = ref({
  overview: {
    data: null as any,
    loading: false,
    loaded: false,
  },
  install: {
    data: null as any,
    loading: false,
    loaded: false,
  },
  monitor: {
    data: null as any,
    loading: false,
    loaded: false,
  },
  tasks: {
    data: [] as ProxyTask[],
    stats: null as {
      total: number;
      completed: number;
      failed: number;
      running: number;
    } | null,
    loading: false,
    loaded: false,
  },
  heartbeats: {
    data: [] as any[],
    loading: false,
    loaded: false,
    pagination: {
      count: 0,
      page: 1,
      pageSize: getPageSize("proxy-heartbeats"),
    },
  },
});

// Watch for heartbeats page size changes and save to localStorage
watch(
  () => tabData.value.heartbeats.pagination.pageSize,
  (newSize) => {
    setPageSize(newSize, "proxy-heartbeats");
  },
);

// Auto refresh states
const autoRefresh = ref({
  monitor: { enabled: false, interval: 30, timer: null as number | null },
  heartbeats: { enabled: false, interval: 30, timer: null as number | null },
});

// Selected network interface and disk for chart filtering
const selectedNetIOInterface = ref<string>("");
const selectedDiskIO = ref<string>("");

const monitorData = computed(() => tabData.value.monitor.data);
const {
  networkIOStats,
  getUniqueNetworkInterfaces,
  getUniqueDisks,
  getCPUChartOption,
  getMemoryChartOption,
  getDiskChartOption,
  getDiskUtilAwaitChartOption,
  getDiskIOPSChartOption,
  getDiskBandwidthChartOption,
  getNetworkBytesChartOption,
  getNetworkPacketsChartOption,
} = useProxyMonitorCharts(monitorData, selectedNetIOInterface, selectedDiskIO);

const showEditModal = ref(false);
const editFormData = ref({
  name: "",
  hostname: "",
  heartbeat_interval: 10,
  tags: {} as Record<string, string>,
  labels: [] as string[],
});

// Delete Confirm
const showDeleteConfirm = ref(false);
const proxyToDelete = ref<ProxyNode | null>(null);

// Dropdown menu
const openMenuId = ref<string | null>(null);

type ProxySortKey =
  | "name"
  | "role"
  | "status"
  | "hostname"
  | "internal_ip"
  | "cpu_cores"
  | "memory_usage"
  | "disk_usage"
  | "last_heartbeat";

type ProxyTableColumnKey = ProxySortKey | "actions";

const proxySort = ref<{ key: ProxySortKey; direction: "asc" | "desc" }>({
  key: "name",
  direction: "asc",
});
const proxyManualColumnWidths = ref<
  Partial<Record<ProxyTableColumnKey, number>>
>(loadProxyColumnWidths());
const resizingProxyColumn = ref<ProxyTableColumnKey | null>(null);

// Polling for status updates
let pollInterval: number | null = null;
let removeProxyColumnResizeListeners: (() => void) | null = null;

const filteredProxies = computed(() => {
  let result = proxies.value;

  if (selectedRole.value !== "all") {
    result = result.filter((p) => p.role === selectedRole.value);
  }

  if (selectedStatus.value !== "all") {
    result = result.filter((p) => p.status === selectedStatus.value);
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    result = result.filter(
      (p) =>
        p.name.toLowerCase().includes(query) ||
        (p.hostname || "").toLowerCase().includes(query),
    );
  }

  return result;
});

const proxyTableColumns = computed(() => [
  { key: "name" as const, label: t("proxies.list.name"), min: 220, max: 720 },
  { key: "role" as const, label: t("proxies.list.role"), min: 110, max: 260 },
  {
    key: "status" as const,
    label: t("proxies.list.status"),
    min: 120,
    max: 260,
  },
  {
    key: "hostname" as const,
    label: t("proxies.list.hostname"),
    min: 160,
    max: 520,
  },
  {
    key: "internal_ip" as const,
    label: t("proxies.list.ip"),
    min: 140,
    max: 360,
  },
  {
    key: "cpu_cores" as const,
    label: t("proxies.list.cpuCores"),
    min: 120,
    max: 240,
  },
  {
    key: "memory_usage" as const,
    label: t("proxies.list.memory"),
    min: 140,
    max: 260,
  },
  {
    key: "disk_usage" as const,
    label: t("proxies.list.disk"),
    min: 140,
    max: 260,
  },
  {
    key: "last_heartbeat" as const,
    label: t("proxies.list.lastHeartbeat"),
    min: 150,
    max: 420,
  },
]);

function getProxySortValue(
  proxy: ProxyNode,
  key: ProxySortKey,
): string | number {
  switch (key) {
    case "name":
      return proxy.name || "";
    case "role":
      return proxy.role || "";
    case "status":
      return proxy.status || "";
    case "hostname":
      return proxy.hostname || "";
    case "internal_ip":
      return proxy.internal_ip || "";
    case "cpu_cores":
      return proxy.cpu_cores ?? -1;
    case "memory_usage":
      return proxy.memory_usage ?? -1;
    case "disk_usage":
      return proxy.disk_usage ?? -1;
    case "last_heartbeat":
      return proxy.last_heartbeat
        ? new Date(proxy.last_heartbeat).getTime()
        : 0;
    default:
      return "";
  }
}

const sortedProxies = computed(() => {
  const { key, direction } = proxySort.value;
  const multiplier = direction === "asc" ? 1 : -1;

  return [...filteredProxies.value].sort((a, b) => {
    const aValue = getProxySortValue(a, key);
    const bValue = getProxySortValue(b, key);

    if (typeof aValue === "number" && typeof bValue === "number") {
      return (aValue - bValue) * multiplier;
    }

    return (
      String(aValue).localeCompare(String(bValue), undefined, {
        numeric: true,
        sensitivity: "base",
      }) * multiplier
    );
  });
});

const displayedProxies = computed(() =>
  viewMode.value === "list" ? sortedProxies.value : filteredProxies.value,
);

// Paginated proxies for display
const paginatedProxies = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return displayedProxies.value.slice(start, end);
});

// Reset page when filters change
watch([selectedRole, selectedStatus, searchQuery], () => {
  currentPage.value = 1;
});

watch(proxySort, () => {
  currentPage.value = 1;
});

function toggleProxySort(key: ProxySortKey) {
  if (proxySort.value.key === key) {
    proxySort.value.direction =
      proxySort.value.direction === "asc" ? "desc" : "asc";
    return;
  }

  proxySort.value = { key, direction: "asc" };
}

function getProxySortIcon(key: ProxySortKey) {
  if (proxySort.value.key !== key) return ArrowsUpDownIcon;
  return proxySort.value.direction === "asc" ? ChevronUpIcon : ChevronDownIcon;
}

function getProxyColumnText(proxy: ProxyNode, key: ProxySortKey) {
  switch (key) {
    case "name":
      return proxy.name || "";
    case "role":
      return t(`proxies.roles.${proxy.role}`);
    case "status":
      return t(`proxies.status.${proxy.status}`);
    case "hostname":
      return proxy.hostname || "-";
    case "internal_ip":
      return proxy.internal_ip || "-";
    case "cpu_cores":
      return proxy.cpu_cores
        ? `${proxy.cpu_cores} ${t("proxies.list.cores")}`
        : "-";
    case "memory_usage":
      return proxy.memory_usage !== null
        ? `${proxy.memory_usage.toFixed(0)}%`
        : "-";
    case "disk_usage":
      return proxy.disk_usage !== null
        ? `${proxy.disk_usage.toFixed(0)}%`
        : "-";
    case "last_heartbeat":
      return timeSince(proxy.last_heartbeat);
    default:
      return "";
  }
}

function estimateProxyColumnWidth(text: string, extra = 42) {
  let width = extra;
  for (const char of text) {
    width += /[\u4e00-\u9fff]/.test(char) ? 14 : 8;
  }
  return width;
}

function loadProxyColumnWidths(): Partial<Record<ProxyTableColumnKey, number>> {
  try {
    const stored = localStorage.getItem(COLUMN_WIDTH_STORAGE_KEY);
    if (!stored) return {};
    const parsed = JSON.parse(stored) as Partial<
      Record<ProxyTableColumnKey, number>
    >;
    return Object.fromEntries(
      Object.entries(parsed).filter(([, width]) => typeof width === "number"),
    ) as Partial<Record<ProxyTableColumnKey, number>>;
  } catch {
    return {};
  }
}

function saveProxyColumnWidths() {
  try {
    localStorage.setItem(
      COLUMN_WIDTH_STORAGE_KEY,
      JSON.stringify(proxyManualColumnWidths.value),
    );
  } catch {
    // Ignore storage errors in private browsing or restricted environments.
  }
}

function getProxyColumnConfig(key: ProxyTableColumnKey) {
  if (key === "actions") {
    return { key, label: t("proxies.list.actions"), min: 112, max: 220 };
  }
  return proxyTableColumns.value.find((column) => column.key === key);
}

const proxyTableAutoColumnWidths = computed<
  Record<ProxyTableColumnKey, number>
>(() => {
  const widths = {} as Record<ProxyTableColumnKey, number>;
  const sampleRows = sortedProxies.value.slice(0, 80);

  for (const column of proxyTableColumns.value) {
    const headerWidth = estimateProxyColumnWidth(column.label, 56);
    const cellWidth = sampleRows.reduce((maxWidth, proxy) => {
      const extra = column.key === "name" ? 96 : 48;
      return Math.max(
        maxWidth,
        estimateProxyColumnWidth(getProxyColumnText(proxy, column.key), extra),
      );
    }, headerWidth);

    widths[column.key] = Math.min(Math.max(cellWidth, column.min), column.max);
  }

  widths.actions = 132;
  return widths;
});

const proxyTableColumnWidths = computed<Record<ProxyTableColumnKey, number>>(
  () => ({
    ...proxyTableAutoColumnWidths.value,
    ...proxyManualColumnWidths.value,
  }),
);

const proxyTableMinWidth = computed(() => {
  const total = Object.values(proxyTableColumnWidths.value).reduce(
    (sum, width) => sum + width,
    0,
  );
  return `${Math.max(total, 900)}px`;
});

function proxyColumnStyle(key: ProxyTableColumnKey) {
  const width = proxyTableColumnWidths.value[key];
  return {
    width: `${width}px`,
    minWidth: `${width}px`,
  };
}

function setProxyColumnWidth(key: ProxyTableColumnKey, width: number) {
  const config = getProxyColumnConfig(key);
  const min = config?.min ?? 80;
  const max = config?.max ?? 720;
  const nextWidth = Math.round(Math.min(Math.max(width, min), max));

  proxyManualColumnWidths.value = {
    ...proxyManualColumnWidths.value,
    [key]: nextWidth,
  };
}

function resetProxyColumnWidth(key: ProxyTableColumnKey) {
  const nextWidths = { ...proxyManualColumnWidths.value };
  delete nextWidths[key];
  proxyManualColumnWidths.value = nextWidths;
  saveProxyColumnWidths();
}

function startProxyColumnResize(key: ProxyTableColumnKey, event: MouseEvent) {
  event.preventDefault();
  event.stopPropagation();

  removeProxyColumnResizeListeners?.();

  const startX = event.clientX;
  const startWidth = proxyTableColumnWidths.value[key];
  resizingProxyColumn.value = key;
  document.body.style.cursor = "col-resize";
  document.body.style.userSelect = "none";

  const onMouseMove = (moveEvent: MouseEvent) => {
    setProxyColumnWidth(key, startWidth + moveEvent.clientX - startX);
  };

  const onMouseUp = () => {
    resizingProxyColumn.value = null;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    saveProxyColumnWidths();
    removeProxyColumnResizeListeners?.();
    removeProxyColumnResizeListeners = null;
  };

  window.addEventListener("mousemove", onMouseMove);
  window.addEventListener("mouseup", onMouseUp, { once: true });

  removeProxyColumnResizeListeners = () => {
    window.removeEventListener("mousemove", onMouseMove);
    window.removeEventListener("mouseup", onMouseUp);
  };
}

watch(viewMode, (mode) => {
  try {
    localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode);
  } catch {
    // Ignore storage errors in private browsing or restricted environments.
  }
});

async function fetchProxies() {
  isLoading.value = true;
  try {
    const [proxiesRes, statsRes] = await Promise.all([
      proxiesApi.list(),
      proxiesApi.stats(),
    ]);
    proxies.value = proxiesRes.data.results || proxiesRes.data || [];
    stats.value = statsRes.data;
  } catch (error) {
    console.error("Failed to fetch proxies:", error);
  } finally {
    isLoading.value = false;
  }
}

// Tab data fetching functions
// silent=true 时不显示loading，静默刷新数据
async function fetchProxyOverview(proxyId: string, silent = false) {
  if (!silent) tabData.value.overview.loading = true;
  try {
    const res = await proxiesApi.overview(proxyId);
    tabData.value.overview.data = res.data;
    tabData.value.overview.loaded = true;
  } catch (error) {
    console.error("Failed to fetch proxy overview:", error);
  } finally {
    if (!silent) tabData.value.overview.loading = false;
  }
}

async function fetchProxyTasks(proxyId: string, page = 1, silent = false) {
  if (!silent) tabData.value.tasks.loading = true;
  try {
    const res = await proxiesApi.tasks(proxyId, { limit: 50, page });
    // Handle new response format with stats
    if (res.data.tasks) {
      tabData.value.tasks.data = res.data.tasks;
      tabData.value.tasks.stats = res.data.stats || {
        total: 0,
        completed: 0,
        failed: 0,
        running: 0,
      };
    } else if (res.data.results) {
      tabData.value.tasks.data = res.data.results;
    } else {
      tabData.value.tasks.data = res.data;
    }
    tabData.value.tasks.loaded = true;
  } catch (error) {
    console.error("Failed to fetch proxy tasks:", error);
    if (!silent) tabData.value.tasks.data = [];
  } finally {
    if (!silent) tabData.value.tasks.loading = false;
  }
}

async function fetchProxyHeartbeats(proxyId: string, page = 1, silent = false) {
  if (!silent) tabData.value.heartbeats.loading = true;
  try {
    const res = await proxiesApi.heartbeats(proxyId, {
      hours: 24,
      page,
      page_size: tabData.value.heartbeats.pagination.pageSize,
    });
    // Handle paginated response
    if (res.data.results) {
      tabData.value.heartbeats.data = res.data.results;
      tabData.value.heartbeats.pagination.count = res.data.count;
    } else {
      tabData.value.heartbeats.data = res.data;
    }
    tabData.value.heartbeats.loaded = true;
  } catch (error) {
    console.error("Failed to fetch proxy heartbeats:", error);
    if (!silent) tabData.value.heartbeats.data = [];
  } finally {
    if (!silent) tabData.value.heartbeats.loading = false;
  }
}

async function fetchProxyMonitor(proxyId: string, silent = false) {
  if (!silent) tabData.value.monitor.loading = true;
  try {
    // Convert time range to hours
    let hours = 24;
    if (monitorTimeRange.value === "1h") hours = 1;
    else if (monitorTimeRange.value === "6h") hours = 6;
    else if (monitorTimeRange.value === "24h") hours = 24;
    else if (monitorTimeRange.value === "7d") hours = 168;
    else if (monitorTimeRange.value === "30d") hours = 720;

    const res = await proxiesApi.monitor(proxyId, { hours });
    tabData.value.monitor.data = res.data;
    tabData.value.monitor.loaded = true;
  } catch (error) {
    console.error("Failed to fetch proxy monitor:", error);
    if (!silent) tabData.value.monitor.data = null;
  } finally {
    if (!silent) tabData.value.monitor.loading = false;
  }
}

function setTimeRange(range: "1h" | "6h" | "24h" | "7d" | "30d" | "custom") {
  monitorTimeRange.value = range;
  if (range !== "custom" && selectedProxy.value) {
    tabData.value.monitor.loaded = false;
    fetchProxyMonitor(selectedProxy.value.id);
  }
  showCustomDatePicker.value = range === "custom";
}

function applyCustomTimeRange() {
  if (
    customTimeRange.value.start &&
    customTimeRange.value.end &&
    selectedProxy.value
  ) {
    // Calculate hours from the date range
    const start = new Date(customTimeRange.value.start);
    const end = new Date(customTimeRange.value.end);
    const hours = Math.ceil(
      (end.getTime() - start.getTime()) / (1000 * 60 * 60),
    );
    if (hours > 0) {
      tabData.value.monitor.loaded = false;
      fetchProxyMonitor(selectedProxy.value.id);
    }
  }
}

// Installation Wizard Functions
function openInstallWizard() {
  installStep.value = 1;
  installData.value = {
    name: "",
    role: "agent",
    os: "linux",
    labels: [],
    newLabel: "",
  };
  installResult.value = null;
  showInstallWizard.value = true;
}

function addLabel() {
  if (
    installData.value.newLabel &&
    !installData.value.labels.includes(installData.value.newLabel)
  ) {
    installData.value.labels.push(installData.value.newLabel);
    installData.value.newLabel = "";
  }
}

function removeLabel(label: string) {
  installData.value.labels = installData.value.labels.filter(
    (l) => l !== label,
  );
}

async function createInstallCommand() {
  if (!installData.value.name) return;

  isGeneratingInstall.value = true;
  try {
    const res = await proxiesApi.createInstallCommand({
      name: installData.value.name,
      role: installData.value.role,
      os: installData.value.os,
      labels: installData.value.labels,
    });
    installResult.value = res.data;
    installStep.value = 3;
  } catch (error: any) {
    console.error("Failed to generate install command:", error);
    const errorMessage =
      error.response?.data?.detail ||
      error.response?.data?.error ||
      "Failed to generate install command";
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: errorMessage,
    });
  } finally {
    isGeneratingInstall.value = false;
  }
}

async function copyCommand(command: string) {
  try {
    await copyText(command);
    appStore.showToast({
      type: "success",
      title: t("common.copied"),
      message: t("common.commandCopiedToClipboard"),
      duration: 2000,
    });
  } catch (error) {
    console.error("Failed to copy:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: t("common.copyFailedToClipboard"),
    });
  }
}

async function copyToClipboard(text: string, label: string = "Text") {
  try {
    await copyText(text);
    appStore.showToast({
      type: "success",
      title: t("common.copied"),
      message:
        label === "Command"
          ? t("common.commandCopiedToClipboard")
          : t("common.itemCopiedToClipboard", { item: label }),
      duration: 2000,
    });
  } catch (error) {
    console.error("Failed to copy:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: t("common.copyFailedToClipboard"),
    });
  }
}

async function copyText(text: string) {
  if (navigator.clipboard?.writeText && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();

  try {
    const copied = document.execCommand("copy");
    if (!copied) throw new Error("copy command failed");
  } finally {
    document.body.removeChild(textarea);
  }
}

function downloadConfig() {
  if (!installResult.value) return;

  const blob = new Blob([installResult.value.config_yaml], {
    type: "text/yaml",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `hyperfilelens-proxy-${installData.value.name}.yaml`;
  a.click();
  URL.revokeObjectURL(url);
}

function getCommandForOS(): string {
  if (!installResult.value) return "";
  if (installData.value.os === "windows") {
    return installResult.value.windows_command;
  }
  if (installData.value.os === "macos") {
    return installResult.value.macos_command || installResult.value.install_command;
  }
  return installResult.value.linux_command || installResult.value.install_command;
}

// Proxy Actions
function viewProxyDetail(proxy: ProxyNode) {
  selectedProxy.value = proxy;
  showDetailDrawer.value = true;
  detailTab.value = "overview";

  // Reset tab data cache
  Object.keys(tabData.value).forEach((key) => {
    const k = key as keyof typeof tabData.value;
    tabData.value[k].loading = false;
    tabData.value[k].loaded = false;
    if (k === "tasks" || k === "heartbeats") {
      tabData.value[k].data = [];
    } else {
      tabData.value[k].data = null;
    }
  });

  // Load overview data immediately (方案A)
  fetchProxyOverview(proxy.id);

  openMenuId.value = null;
}

async function openRouteDetail() {
  const detailId = route.query.detail;
  if (typeof detailId !== "string") return;
  const existing = proxies.value.find((proxy) => String(proxy.id) === detailId);
  if (existing) {
    viewProxyDetail(existing);
    return;
  }

  try {
    const response = await proxiesApi.detail(detailId);
    viewProxyDetail(response.data);
  } catch (error) {
    console.error("Failed to open proxy detail:", error);
  }
}

// Watch tab changes to load data on demand
watch(detailTab, (newTab) => {
  if (!selectedProxy.value) return;

  const proxyId = selectedProxy.value.id;
  const tab = tabData.value[newTab];

  // Only fetch if not already loaded
  if (!tab.loaded && !tab.loading) {
    switch (newTab) {
      case "overview":
        fetchProxyOverview(proxyId);
        break;
      case "monitor":
        fetchProxyMonitor(proxyId);
        break;
      case "tasks":
        fetchProxyTasks(proxyId);
        break;
      case "heartbeats":
        fetchProxyHeartbeats(proxyId);
        break;
    }
  }
});

// Auto refresh functions
function setAutoRefresh(
  tab: "monitor" | "heartbeats",
  enabled: boolean,
  intervalSeconds: number,
) {
  const refresh = autoRefresh.value[tab];

  // Clear existing timer
  if (refresh.timer) {
    clearInterval(refresh.timer);
    refresh.timer = null;
  }

  refresh.enabled = enabled;
  refresh.interval = intervalSeconds;

  if (enabled && selectedProxy.value) {
    refresh.timer = window.setInterval(() => {
      if (selectedProxy.value) {
        if (tab === "monitor") {
          fetchProxyMonitor(selectedProxy.value.id, true); // 静默刷新
        } else {
          fetchProxyHeartbeats(selectedProxy.value.id, 1, true); // 静默刷新
        }
      }
    }, intervalSeconds * 1000);
  }
}

// Refresh current tab
function refreshCurrentTab() {
  if (!selectedProxy.value) return;

  const proxyId = selectedProxy.value.id;
  // 静默刷新，不显示loading，只更新数据
  switch (detailTab.value) {
    case "overview":
      fetchProxyOverview(proxyId, true);
      break;
    case "monitor":
      fetchProxyMonitor(proxyId, true);
      break;
    case "tasks":
      fetchProxyTasks(proxyId, 1, true);
      break;
    case "heartbeats":
      fetchProxyHeartbeats(proxyId, 1, true);
      fetchProxyOverview(proxyId, true); // Also refresh overview for stats
      break;
  }
}

// Close drawer and cleanup
function closeDetailDrawer() {
  // Stop all auto refresh timers
  if (autoRefresh.value.monitor.timer) {
    clearInterval(autoRefresh.value.monitor.timer);
    autoRefresh.value.monitor.timer = null;
  }
  if (autoRefresh.value.heartbeats.timer) {
    clearInterval(autoRefresh.value.heartbeats.timer);
    autoRefresh.value.heartbeats.timer = null;
  }
  autoRefresh.value.monitor.enabled = false;
  autoRefresh.value.heartbeats.enabled = false;

  showDetailDrawer.value = false;
}

async function viewInstallInfo(proxy: ProxyNode) {
  // Fetch fresh proxy data and regenerate the install command from current settings.
  try {
    const [detailResponse, installResponse] = await Promise.all([
      proxiesApi.detail(proxy.id),
      proxiesApi.installCommand(proxy.id),
    ]);
    selectedProxy.value = {
      ...detailResponse.data,
      ...installResponse.data,
      id: detailResponse.data.id,
    };
    showInstallInfoModal.value = true;
    openMenuId.value = null;
  } catch (error) {
    console.error("Failed to fetch proxy install info:", error);
  }
}

function editProxy(proxy: ProxyNode) {
  selectedProxy.value = proxy;
  editFormData.value = {
    name: proxy.name,
    hostname: proxy.hostname || "",
    heartbeat_interval: proxy.heartbeat_interval,
    tags: proxy.tags || {},
    labels: proxy.labels || [],
  };
  showEditModal.value = true;
  openMenuId.value = null;
}

async function updateProxy() {
  if (!selectedProxy.value) return;
  try {
    await proxiesApi.update(selectedProxy.value.id, editFormData.value);
    showEditModal.value = false;
    await fetchProxies();
  } catch (error) {
    console.error("Failed to update proxy:", error);
  }
}

function confirmDeleteProxy(proxy: ProxyNode) {
  proxyToDelete.value = proxy;
  showDeleteConfirm.value = true;
  openMenuId.value = null;
}

async function deleteProxy() {
  if (!proxyToDelete.value) return;
  try {
    await proxiesApi.delete(proxyToDelete.value.id);
    showDeleteConfirm.value = false;
    proxyToDelete.value = null;
    await fetchProxies();
  } catch (error) {
    console.error("Failed to delete proxy:", error);
  }
}

async function updateProxyStatus(proxy: ProxyNode, newStatus: string) {
  try {
    await proxiesApi.setStatus(proxy.id, newStatus);
    await fetchProxies();
    openMenuId.value = null;
  } catch (error) {
    console.error("Failed to update status:", error);
  }
}

async function regenerateToken(proxy: ProxyNode) {
  if (!confirm(t("proxies.actions.regenerateTokenConfirm"))) return;
  try {
    await proxiesApi.regenerateToken(proxy.id);
    await fetchProxies();
    openMenuId.value = null;
  } catch (error) {
    console.error("Failed to regenerate token:", error);
  }
}

async function regenerateTokenFromModal() {
  const proxyId = selectedProxy.value?.id;
  if (!proxyId) {
    console.error("No proxy ID found");
    return;
  }
  if (!confirm(t("proxies.actions.regenerateTokenConfirm"))) return;

  try {
    const response = await proxiesApi.regenerateToken(proxyId);
    console.log("Regenerate response:", response.data);
    // Update selectedProxy with the new data, ensuring id is preserved
    selectedProxy.value = {
      ...selectedProxy.value,
      ...response.data,
      id: response.data.id || response.data.proxy_id || proxyId, // Ensure id is always set
    };
    await fetchProxies();
  } catch (error) {
    console.error("Failed to regenerate token:", error);
    alert(
      t("proxies.actions.regenerateTokenFailed") ||
        "Failed to regenerate token",
    );
  }
}

// 菜单位置样式
const menuStyle = ref<Record<string, string>>({});

function toggleMenu(proxyId: string, event?: Event) {
  if (openMenuId.value === proxyId) {
    openMenuId.value = null;
    return;
  }
  openMenuId.value = proxyId;

  // 计算菜单位置
  if (event?.target) {
    const target = event.target as HTMLElement;
    const rect = target.getBoundingClientRect();
    menuStyle.value = {
      top: `${rect.bottom + 8}px`,
      right: `${window.innerWidth - rect.right}px`,
      width: "192px",
    };
  }
}

// Status helpers
function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    online:
      "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400",
    offline: "bg-background-tertiary text-foreground-secondary",
    error: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400",
    maintenance:
      "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
    pending: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
    installing:
      "bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400",
  };
  return colors[status] || "bg-background-tertiary text-foreground-secondary";
}

function getStatusIcon(status: string) {
  const icons: Record<string, any> = {
    online: CheckCircleIcon,
    offline: XCircleIcon,
    error: XCircleIcon,
    maintenance: WrenchScrewdriverIcon,
    pending: ClockIcon,
    installing: ArrowPathIcon,
  };
  return icons[status] || CircleStackIcon;
}

function getRoleColor(role: string): string {
  return role === "agent"
    ? "bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400"
    : "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400";
}

function formatUptime(seconds: number | null): string {
  if (!seconds) return "N/A";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function timeSince(date: string | null): string {
  if (!date) return t("common.never");
  const seconds = Math.floor(
    (new Date().getTime() - new Date(date).getTime()) / 1000,
  );
  if (seconds < 60) return t("common.justNow");
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}${t("common.minutesAgo")}`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}${t("common.hoursAgo")}`;
  const days = Math.floor(hours / 24);
  return `${days}${t("common.daysAgo")}`;
}

function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function formatNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return "0";
  if (num >= 1000000) return (num / 1000000).toFixed(2) + "M";
  if (num >= 1000) return (num / 1000).toFixed(2) + "K";
  return num.toString();
}

// Close menu when clicking outside
function closeMenu() {
  openMenuId.value = null;
}

// Role icons
const AgentIcon = ComputerDesktopIcon;
const SyncIcon = CircleStackIcon;

watch(
  () => route.query.detail,
  () => {
    openRouteDetail();
  },
);

onMounted(async () => {
  await fetchProxies();
  await openRouteDetail();
  document.addEventListener("click", closeMenu);

  // Poll for updates every 30 seconds
  pollInterval = window.setInterval(fetchProxies, 30000);
});

onUnmounted(() => {
  document.removeEventListener("click", closeMenu);
  removeProxyColumnResizeListeners?.();
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
  if (pollInterval) {
    clearInterval(pollInterval);
  }
});
</script>

<template>
  <div class="space-y-6" @click.stop>
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">
          {{ t("proxies.title") }}
        </h1>
        <p class="text-foreground-secondary mt-1">
          {{ t("proxies.subtitle") }}
        </p>
      </div>
      <button
        data-tour="proxy-install-button"
        @click="openInstallWizard"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t("proxies.installProxy") }}
      </button>
    </div>

    <ProxiesStats :stats="stats" />

    <ProxiesToolbar
      v-model:search-query="searchQuery"
      v-model:selected-role="selectedRole"
      v-model:selected-status="selectedStatus"
      v-model:view-mode="viewMode"
      @refresh="fetchProxies"
    />

    <ProxiesCardView
      v-if="viewMode === 'card'"
      :loading="isLoading"
      :filtered-count="filteredProxies.length"
      :proxies="paginatedProxies"
      :open-menu-id="openMenuId"
      :menu-style="menuStyle"
      :agent-icon="AgentIcon"
      :sync-icon="SyncIcon"
      :get-role-color="getRoleColor"
      :get-status-color="getStatusColor"
      :get-status-icon="getStatusIcon"
      :time-since="timeSince"
      @install="openInstallWizard"
      @toggle-menu="toggleMenu"
      @close-menu="openMenuId = null"
      @detail="viewProxyDetail"
      @edit="editProxy"
      @regenerate-token="regenerateToken"
      @update-status="updateProxyStatus"
      @delete="confirmDeleteProxy"
      @install-info="viewInstallInfo"
    />

    <ProxiesListView
      v-else
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :loading="isLoading"
      :filtered-count="filteredProxies.length"
      :proxies="paginatedProxies"
      :columns="proxyTableColumns"
      :sort-key="proxySort.key"
      :table-min-width="proxyTableMinWidth"
      :resizing-column="resizingProxyColumn"
      :open-menu-id="openMenuId"
      :menu-style="menuStyle"
      :agent-icon="AgentIcon"
      :sync-icon="SyncIcon"
      :column-style="proxyColumnStyle"
      :get-sort-icon="getProxySortIcon"
      :get-role-color="getRoleColor"
      :get-status-color="getStatusColor"
      :time-since="timeSince"
      @install="openInstallWizard"
      @sort="toggleProxySort"
      @resize-start="startProxyColumnResize"
      @resize-reset="resetProxyColumnWidth"
      @toggle-menu="toggleMenu"
      @close-menu="openMenuId = null"
      @detail="viewProxyDetail"
      @edit="editProxy"
      @regenerate-token="regenerateToken"
      @update-status="updateProxyStatus"
      @delete="confirmDeleteProxy"
      @install-info="viewInstallInfo"
    />

    <ProxyInstallWizard
      v-if="showInstallWizard"
      v-model:install-step="installStep"
      :install-data="installData"
      :install-result="installResult"
      :is-generating-install="isGeneratingInstall"
      :command="getCommandForOS()"
      @close="showInstallWizard = false"
      @add-label="addLabel"
      @remove-label="removeLabel"
      @generate="createInstallCommand"
      @download-config="downloadConfig"
      @copy-command="copyCommand"
      @done="
        showInstallWizard = false;
        fetchProxies();
      "
    />

    <ProxyInstallInfoModal
      v-if="showInstallInfoModal && selectedProxy"
      :proxy="selectedProxy"
      @close="showInstallInfoModal = false"
      @copy="copyToClipboard"
      @regenerate-token="regenerateTokenFromModal"
    />

    <ProxyDetailDrawer
      v-if="showDetailDrawer"
      v-model:detail-tab="detailTab"
      :proxy="selectedProxy"
      :loading="tabData[detailTab]?.loading"
      :get-role-color="getRoleColor"
      :get-status-color="getStatusColor"
      @close="closeDetailDrawer"
      @refresh="refreshCurrentTab"
    >
      <!-- Overview Tab -->
      <ProxyOverviewTab
        v-if="detailTab === 'overview'"
        :data="tabData.overview.data"
        :get-status-color="getStatusColor"
        :format-uptime="formatUptime"
        @copy="copyToClipboard"
      />

      <!-- Install Tab -->
      <ProxyInstallTab
        v-else-if="
          detailTab === 'install' &&
          selectedProxy &&
          selectedProxy.status === 'pending'
        "
        :proxy="selectedProxy"
        @copy="copyToClipboard"
        @regenerate-token="regenerateTokenFromModal"
      />

      <!-- Monitor Tab -->
      <ProxyMonitorTab
        v-else-if="detailTab === 'monitor'"
        v-model:interval="autoRefresh.monitor.interval"
        v-model:selected-disk-i-o="selectedDiskIO"
        v-model:selected-net-i-o-interface="selectedNetIOInterface"
        :data="tabData.monitor.data"
        :monitor-time-range="monitorTimeRange"
        :custom-time-range="customTimeRange"
        :show-custom-date-picker="showCustomDatePicker"
        :network-i-o-stats="networkIOStats"
        :unique-disks="getUniqueDisks()"
        :unique-network-interfaces="getUniqueNetworkInterfaces()"
        :get-c-p-u-chart-option="getCPUChartOption"
        :get-memory-chart-option="getMemoryChartOption"
        :get-disk-chart-option="getDiskChartOption"
        :get-disk-util-await-chart-option="getDiskUtilAwaitChartOption"
        :get-disk-i-o-p-s-chart-option="getDiskIOPSChartOption"
        :get-disk-bandwidth-chart-option="getDiskBandwidthChartOption"
        :get-network-bytes-chart-option="getNetworkBytesChartOption"
        :get-network-packets-chart-option="getNetworkPacketsChartOption"
        :format-uptime="formatUptime"
        :format-bytes="formatBytes"
        :format-number="formatNumber"
        @set-auto-refresh="
          (interval) => setAutoRefresh('monitor', interval > 0, interval)
        "
        @refresh="refreshCurrentTab"
        @set-time-range="setTimeRange"
        @apply-custom-time-range="applyCustomTimeRange"
      />

      <!-- Tasks Tab -->
      <ProxyTasksTab
        v-else-if="detailTab === 'tasks'"
        :tasks="tabData.tasks.data"
        :stats="tabData.tasks.stats"
      />

      <!-- Heartbeats Tab -->
      <ProxyHeartbeatsTab
        v-else-if="detailTab === 'heartbeats'"
        v-model:interval="autoRefresh.heartbeats.interval"
        :heartbeats="tabData.heartbeats.data"
        :stats="tabData.overview.data?.stats"
        @set-auto-refresh="
          (interval) => setAutoRefresh('heartbeats', interval > 0, interval)
        "
        @refresh="refreshCurrentTab"
      />
    </ProxyDetailDrawer>
    <ProxyEditModal
      v-if="showEditModal"
      :form="editFormData"
      @close="showEditModal = false"
      @submit="updateProxy"
    />

    <ProxyDeleteConfirmModal
      v-if="showDeleteConfirm && proxyToDelete"
      :proxy="proxyToDelete"
      @cancel="
        showDeleteConfirm = false;
        proxyToDelete = null;
      "
      @confirm="deleteProxy"
    />
  </div>
</template>
