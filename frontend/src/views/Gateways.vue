<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";
import { gatewaysApi } from "@/api";
import { useAppStore } from "@/stores/app";
import { getApiErrorMessage } from "@/utils/errors";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import { useGatewayFormatting } from "@/features/gateways/useGatewayFormatting";
import GatewayListView from "@/components/gateways/GatewayListView.vue";
import GatewayStats from "@/components/gateways/GatewayStats.vue";
import GatewayToolbar from "@/components/gateways/GatewayToolbar.vue";
import GatewayCreateModal from "@/components/gateways/GatewayCreateModal.vue";
import GatewayDetailDrawer from "@/components/gateways/GatewayDetailDrawer.vue";
import GatewayEditModal from "@/components/gateways/GatewayEditModal.vue";
import GatewayDeleteConfirmModal from "@/components/gateways/GatewayDeleteConfirmModal.vue";
import GatewayInstallInfoModal from "@/components/gateways/GatewayInstallInfoModal.vue";
import GatewayInstallWizardModal from "@/components/gateways/GatewayInstallWizardModal.vue";
import GatewayOverviewTab from "@/components/gateways/GatewayOverviewTab.vue";
import GatewayMountsTab from "@/components/gateways/GatewayMountsTab.vue";
import GatewayMonitoringTab from "@/components/gateways/GatewayMonitoringTab.vue";
import PageTitle from "@/components/PageTitle.vue";
import { CircleStackIcon, PlusIcon } from "@heroicons/vue/24/outline";

const { t } = useI18n();
const route = useRoute();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();
const { statusColors, getStatusLabel, formatBytes, formatDate } =
  useGatewayFormatting(t);

// Types
interface Gateway {
  id: string;
  name: string;
  description: string;
  hostname: string;
  internal_ip: string;
  ssh_port: number;
  status: string;
  os_version: string;
  version: string;
  kopia_version: string;
  cpu_cores: number;
  memory_total: number;
  disk_total: number;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  active_mounts: number;
  mount_base_path: string;
  max_concurrent_mounts: number;
  ai_enabled: boolean;
  indexer_status: string;
  last_index_time: string;
  last_heartbeat: string;
  is_online: boolean;
  tags: Record<string, string>;
  labels: string[];
  created_at: string;
  updated_at: string;
  registered_at: string;
  installed_at: string;
}

interface GatewayStats {
  total: number;
  active: number;
  offline: number;
  pending: number;
  error: number;
  total_mounts: number;
}

// State
const isLoading = ref(true);
const isRefreshing = ref(false);
const isFetchingGateways = ref(false);
const gateways = ref<Gateway[]>([]);
const stats = ref<GatewayStats | null>(null);
const searchQuery = ref("");
const selectedStatus = ref<string>("all");
let pollInterval: number | null = null;

// Pagination
const currentPage = ref(1);
const pageSize = ref(getPageSize("gateways"));
const PAGE_STORAGE_KEY = "gateways";
const VIEW_MODE_STORAGE_KEY = "hyperfilelens:gateways:viewMode";
const viewMode = ref<"card" | "list">(
  (() => {
    try {
      const stored = localStorage.getItem(VIEW_MODE_STORAGE_KEY);
      return stored === "list" || stored === "card" ? stored : "card";
    } catch {
      return "card";
    }
  })(),
);

watch(pageSize, (newSize) => {
  setPageSize(newSize, PAGE_STORAGE_KEY);
  fetchGateways(true);
});
watch(currentPage, () => {
  fetchGateways(true);
});
watch(viewMode, (mode) => {
  try {
    localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode);
  } catch {
    // Ignore storage errors.
  }
});
const totalItems = ref(0);

// Create Modal
const showCreateModal = ref(false);
const isCreating = ref(false);
const newGateway = ref({
  name: "",
  description: "",
  labels: "",
  tags: {} as Record<string, string>,
});

// Install Wizard (after creation)
const showInstallWizard = ref(false);
const createdGateway = ref<Gateway | null>(null);
const wizardStep = ref(1); // 1: info, 2: command, 3: waiting
const wizardInstallCommand = ref("");
const isLoadingWizardCommand = ref(false);

// Detail Drawer
const showDetailDrawer = ref(false);
const selectedGateway = ref<Gateway | null>(null);
const detailTab = ref<"overview" | "mounts" | "monitoring">("overview");
const isLoadingDetail = ref(false);

// Install command modal
const showInstallInfoModal = ref(false);
const installInfoGateway = ref<Gateway | null>(null);
const installInfoCommand = ref("");
const installInfoApiToken = ref("");
const installInfoTokenUsed = ref(false);
const isLoadingInstallInfoCommand = ref(false);

// Edit Modal
const showEditModal = ref(false);
const isEditing = ref(false);
const editFormData = ref({
  name: "",
  description: "",
  ssh_port: 22,
  mount_base_path: "/mnt/kopia",
  max_concurrent_mounts: 10,
  ai_enabled: true,
});

// Delete Confirm Modal
const showDeleteConfirm = ref(false);
const gatewayToDelete = ref<Gateway | null>(null);
const isDeletingGateway = ref(false);

// Mounts data
const mountsData = ref<any[]>([]);
const isLoadingMounts = ref(false);

// Monitoring data
const monitoringData = ref<
  Array<{
    timestamp: string;
    cpu_usage: number | null;
    memory_usage: number | null;
    disk_usage: number | null;
    active_mounts: number;
    network_bytes_sent?: number;
    network_bytes_recv?: number;
    network_packets_sent?: number;
    network_packets_recv?: number;
    memory_total?: number;
    disk_total?: number;
    cpu_cores?: number;
    load_average?: number[];
    process_count?: number;
    network_interfaces?: any;
    disk_io?: any[];
  }>
>([]);
const monitoringCurrent = ref<Record<string, any> | null>(null);
const monitoringNetworkIo = ref<any[]>([]);
const monitoringDiskIo = ref<any[]>([]);
const isLoadingMonitoring = ref(false);
const monitoringHours = ref(24);

// Computed
const filteredGateways = computed(() => {
  let result = gateways.value;

  if (selectedStatus.value !== "all") {
    result = result.filter((g) =>
      selectedStatus.value === "online" ? g.is_online : !g.is_online,
    );
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    result = result.filter(
      (g) =>
        g.name.toLowerCase().includes(query) ||
        g.hostname?.toLowerCase().includes(query) ||
        g.internal_ip?.toLowerCase().includes(query),
    );
  }

  return result;
});

type GatewayColumnKey =
  | "name"
  | "status"
  | "hostname"
  | "internal_ip"
  | "active_mounts"
  | "cpu_cores"
  | "memory_usage"
  | "disk_usage"
  | "kopia_version"
  | "last_heartbeat"
  | "actions";

const gatewayColumns = computed(() => [
  {
    key: "name" as const,
    label: t("common.name"),
    min: 240,
    max: 560,
  },
  { key: "status" as const, label: t("gateways.status"), min: 130, max: 240 },
  {
    key: "hostname" as const,
    label: t("gateways.hostname"),
    min: 180,
    max: 420,
  },
  {
    key: "internal_ip" as const,
    label: t("gateways.ipAddress"),
    min: 150,
    max: 280,
  },
  {
    key: "cpu_cores" as const,
    label: t("gateways.cpu"),
    min: 130,
    max: 240,
  },
  {
    key: "memory_usage" as const,
    label: t("gateways.memory"),
    min: 150,
    max: 260,
  },
  {
    key: "disk_usage" as const,
    label: t("gateways.disk"),
    min: 160,
    max: 280,
  },
  {
    key: "kopia_version" as const,
    label: t("gateways.kopiaVersion"),
    min: 160,
    max: 300,
  },
  {
    key: "active_mounts" as const,
    label: t("gateways.activeMounts"),
    min: 150,
    max: 260,
  },
  {
    key: "last_heartbeat" as const,
    label: t("gateways.lastHeartbeat"),
    min: 190,
    max: 340,
  },
  {
    key: "actions" as const,
    label: t("common.actions"),
    min: 140,
    max: 240,
    sortable: false,
    align: "right" as const,
  },
]);

const gatewayTable = useResizableSortableTable<Gateway, GatewayColumnKey>({
  storageKey: "hyperfilelens:gateways:columnWidths",
  columns: gatewayColumns,
  rows: filteredGateways,
  defaultSort: { key: "name" },
  minTableWidth: 1500,
  getSortValue: (gateway, key) => {
    if (key === "status") return gateway.is_online ? "online" : "offline";
    if (key === "memory_usage") return gateway.memory_usage ?? -1;
    if (key === "disk_usage") return gateway.disk_usage ?? -1;
    if (key === "last_heartbeat") {
      return gateway.last_heartbeat
        ? new Date(gateway.last_heartbeat).getTime()
        : 0;
    }
    if (key === "actions") return "";
    return (gateway as any)[key] ?? "";
  },
  getColumnText: (gateway, key) => {
    if (key === "status") {
      return gateway.is_online ? t("gateways.online") : t("gateways.offline");
    }
    if (key === "memory_usage") {
      return gateway.memory_usage !== null && gateway.memory_usage !== undefined
        ? `${gateway.memory_usage.toFixed(0)}%`
        : "-";
    }
    if (key === "disk_usage") {
      return gateway.disk_usage !== null && gateway.disk_usage !== undefined
        ? `${gateway.disk_usage.toFixed(0)}%`
        : "-";
    }
    if (key === "last_heartbeat") return formatDate(gateway.last_heartbeat);
    if (key === "actions") return t("common.actions");
    return String((gateway as any)[key] ?? "");
  },
});

// Methods
async function fetchGateways(silent = false, showFeedback = false) {
  if (isFetchingGateways.value) return;
  isFetchingGateways.value = true;
  if (!silent) isLoading.value = true;
  if (showFeedback) isRefreshing.value = true;
  try {
    const [listRes, statsRes] = await Promise.all([
      gatewaysApi.list({ page: currentPage.value, page_size: pageSize.value }),
      gatewaysApi.stats(),
    ]);
    const nextGateways = listRes.data.results || listRes.data;
    gateways.value = nextGateways;
    totalItems.value = listRes.data.count || gateways.value.length;
    stats.value = statsRes.data;
    if (selectedGateway.value) {
      const latest = nextGateways.find(
        (gateway: Gateway) => gateway.id === selectedGateway.value?.id,
      );
      if (latest) {
        selectedGateway.value = {
          ...selectedGateway.value,
          ...latest,
        };
      }
    }
  } catch (error) {
    console.error("Failed to fetch gateways:", error);
  } finally {
    if (!silent) isLoading.value = false;
    if (showFeedback) isRefreshing.value = false;
    isFetchingGateways.value = false;
  }
}

async function createGateway() {
  if (!newGateway.value.name.trim()) return;

  isCreating.value = true;
  try {
    // Prepare data - convert labels string to array if needed
    const data = {
      name: newGateway.value.name.trim(),
      description: newGateway.value.description || "",
      labels:
        typeof newGateway.value.labels === "string"
          ? (newGateway.value.labels as string)
              .split(",")
              .map((l) => l.trim())
              .filter(Boolean)
          : newGateway.value.labels,
      tags: newGateway.value.tags || {},
    };

    const res = await gatewaysApi.create(data);
    console.log("Create gateway response:", res.data);

    // Ensure we have the gateway id
    if (!res.data || !res.data.id) {
      throw new Error("Invalid response from server: missing gateway id");
    }

    showCreateModal.value = false;
    createdGateway.value = res.data;
    wizardStep.value = 1;
    showInstallWizard.value = true;

    // Load install command
    await loadWizardInstallCommand();

    await fetchGateways(true);
  } catch (error) {
    console.error("Failed to create gateway:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(error, t("common.createFailed")),
    });
  } finally {
    isCreating.value = false;
  }
}

async function loadWizardInstallCommand() {
  if (!createdGateway.value) return;

  isLoadingWizardCommand.value = true;
  try {
    const res = await gatewaysApi.installCommand(createdGateway.value.id);
    wizardInstallCommand.value = res.data.install_command;
  } catch (error) {
    console.error("Failed to get install command:", error);
    wizardInstallCommand.value = "";
  } finally {
    isLoadingWizardCommand.value = false;
  }
}

async function copyWizardCommand() {
  if (!wizardInstallCommand.value) return;

  try {
    await copyText(wizardInstallCommand.value);
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

function closeInstallWizard() {
  showInstallWizard.value = false;
  createdGateway.value = null;
  wizardInstallCommand.value = "";
  wizardStep.value = 1;
  resetNewGateway();
}

async function onGatewayRegistered() {
  await fetchGateways(true);
  closeInstallWizard();
  appStore.showToast({
    type: "success",
    title: t("common.success"),
    message: t("gateways.gatewayRegistered"),
    duration: 3000,
  });
}

function nextWizardStep() {
  if (wizardStep.value < 3) {
    wizardStep.value++;
  }
}

function prevWizardStep() {
  if (wizardStep.value > 1) {
    wizardStep.value--;
  }
}

function resetNewGateway() {
  newGateway.value = {
    name: "",
    description: "",
    labels: "",
    tags: {},
  };
}

async function viewGatewayDetail(gateway: Gateway) {
  selectedGateway.value = gateway;
  detailTab.value = "overview";
  showDetailDrawer.value = true;
  mountsData.value = [];
  monitoringData.value = [];
}

async function openRouteDetail() {
  const detailId = route.query.detail;
  if (typeof detailId !== "string") return;
  const existing = gateways.value.find((gateway) => gateway.id === detailId);
  if (existing) {
    await viewGatewayDetail(existing);
    return;
  }

  try {
    const response = await gatewaysApi.detail(detailId);
    await viewGatewayDetail(response.data);
  } catch (error) {
    console.error("Failed to open gateway detail:", error);
  }
}

async function viewInstallInfo(gateway: Gateway) {
  installInfoGateway.value = gateway;
  installInfoCommand.value = "";
  installInfoApiToken.value = "";
  installInfoTokenUsed.value = false;
  showInstallInfoModal.value = true;
  isLoadingInstallInfoCommand.value = true;
  try {
    const res = await gatewaysApi.installCommand(gateway.id);
    installInfoCommand.value = res.data.install_command || "";
    installInfoApiToken.value = res.data.api_token || "";
    installInfoTokenUsed.value = Boolean(res.data.install_token_used);
  } catch (error) {
    console.error("Failed to get install command:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(error, t("common.actionFailed")),
    });
  } finally {
    isLoadingInstallInfoCommand.value = false;
  }
}

async function loadMountsData() {
  if (!selectedGateway.value) return;

  isLoadingMounts.value = true;
  try {
    const res = await gatewaysApi.mounts(selectedGateway.value.id);
    mountsData.value = res.data.mounts || [];
  } catch (error) {
    console.error("Failed to load mounts:", error);
    mountsData.value = [];
  } finally {
    isLoadingMounts.value = false;
  }
}

function openEditModal(gateway: Gateway) {
  editFormData.value = {
    name: gateway.name,
    description: gateway.description || "",
    ssh_port: gateway.ssh_port || 22,
    mount_base_path: gateway.mount_base_path || "/mnt/kopia",
    max_concurrent_mounts: gateway.max_concurrent_mounts || 10,
    ai_enabled: gateway.ai_enabled !== false,
  };
  gatewayToDelete.value = gateway;
  showEditModal.value = true;
}

async function submitEdit() {
  if (!gatewayToDelete.value) return;

  isEditing.value = true;
  try {
    await gatewaysApi.update(gatewayToDelete.value.id, editFormData.value);
    showEditModal.value = false;
    gatewayToDelete.value = null;
    await fetchGateways(true);
  } catch (error) {
    console.error("Failed to update gateway:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(error, t("common.updateFailed")),
    });
  } finally {
    isEditing.value = false;
  }
}

async function handleRegenerateToken(gateway: Gateway) {
  if (!confirm(t("gateways.actions.regenerateTokenConfirm"))) return;

  try {
    await gatewaysApi.regenerateToken(gateway.id);
    await fetchGateways(true);
    appStore.showToast({
      type: "success",
      title: t("common.success"),
      message: t("gateways.tokenRegenerated"),
    });
  } catch (error) {
    console.error("Failed to regenerate token:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(error, t("common.actionFailed")),
    });
  }
}

async function regenerateInstallInfoToken() {
  if (!installInfoGateway.value) return;
  if (!confirm(t("gateways.actions.regenerateTokenConfirm"))) return;

  try {
    const res = await gatewaysApi.regenerateToken(installInfoGateway.value.id);
    installInfoCommand.value = res.data.install_command || "";
    installInfoApiToken.value = res.data.api_token || "";
    installInfoTokenUsed.value = Boolean(res.data.install_token_used);
    appStore.showToast({
      type: "success",
      title: t("common.success"),
      message: t("gateways.tokenRegenerated"),
    });
  } catch (error) {
    console.error("Failed to regenerate token:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(error, t("common.actionFailed")),
    });
  }
}

async function handleUpdateStatus(gateway: Gateway, status: string) {
  try {
    if (status === "active") {
      await gatewaysApi.activate(gateway.id);
    } else if (status === "maintenance") {
      await gatewaysApi.maintenance(gateway.id);
    } else {
      return;
    }
    await fetchGateways(true);
    if (selectedGateway.value?.id === gateway.id) {
      selectedGateway.value = { ...selectedGateway.value, status };
    }
    appStore.showToast({
      type: "success",
      title: t("common.success"),
      message: t("common.updateSuccess"),
      duration: 2000,
    });
  } catch (error) {
    console.error("Failed to update status:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(error, t("common.actionFailed")),
    });
  }
}

function openDeleteConfirm(gateway: Gateway) {
  gatewayToDelete.value = gateway;
  showDeleteConfirm.value = true;
}

async function confirmDelete() {
  if (!gatewayToDelete.value) return;

  isDeletingGateway.value = true;
  try {
    await gatewaysApi.delete(gatewayToDelete.value.id);
    showDeleteConfirm.value = false;
    showDetailDrawer.value = false;
    gatewayToDelete.value = null;
    await fetchGateways(true);
    appStore.showToast({
      type: "success",
      title: t("common.success"),
      message: t("common.deleteSuccess"),
    });
  } catch (error) {
    console.error("Failed to delete gateway:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(error, t("common.deleteFailed")),
    });
  } finally {
    isDeletingGateway.value = false;
  }
}

async function copyInstallInfoText(text: string, label: string = "Text") {
  if (!text) return;

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

async function deleteGateway(gateway: Gateway) {
  openDeleteConfirm(gateway);
}

async function loadMonitoringData() {
  if (!selectedGateway.value) return;

  isLoadingMonitoring.value = true;
  try {
    const res = await gatewaysApi.monitoring(
      selectedGateway.value.id,
      monitoringHours.value,
    );
    monitoringData.value = res.data.data || [];
    monitoringCurrent.value = res.data.current || null;
    monitoringNetworkIo.value = res.data.network_io || [];
    monitoringDiskIo.value = res.data.disk_io || [];
  } catch (error) {
    console.error("Failed to load monitoring data:", error);
    monitoringData.value = [];
    monitoringCurrent.value = null;
    monitoringNetworkIo.value = [];
    monitoringDiskIo.value = [];
  } finally {
    isLoadingMonitoring.value = false;
  }
}

// Monitoring stats computed
const monitoringStats = computed(() => {
  if (!monitoringData.value.length) return null;

  const data = monitoringData.value;
  const avgCpu =
    data.reduce((sum, d) => sum + (d.cpu_usage || 0), 0) / data.length;
  const avgMemory =
    data.reduce((sum, d) => sum + (d.memory_usage || 0), 0) / data.length;
  const avgDisk =
    data.reduce((sum, d) => sum + (d.disk_usage || 0), 0) / data.length;
  const maxCpu = Math.max(...data.map((d) => d.cpu_usage || 0));
  const maxMemory = Math.max(...data.map((d) => d.memory_usage || 0));
  const maxDisk = Math.max(...data.map((d) => d.disk_usage || 0));

  return {
    avgCpu,
    avgMemory,
    avgDisk,
    maxCpu,
    maxMemory,
    maxDisk,
  };
});

// Watch tab changes
watch(detailTab, (newTab) => {
  if (newTab === "mounts") {
    loadMountsData();
  }
  if (newTab === "monitoring") {
    loadMonitoringData();
  }
});

// Watch monitoring hours change
watch(monitoringHours, () => {
  if (detailTab.value === "monitoring") {
    loadMonitoringData();
  }
});

watch(
  () => route.query.detail,
  () => {
    openRouteDetail();
  },
);

// Lifecycle
onMounted(async () => {
  await fetchGateways();
  await openRouteDetail();
  pollInterval = window.setInterval(() => fetchGateways(true), 5000);
});

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval);
  }
});
</script>

<style scoped>
/* Drawer Transition */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.3s ease;
}

.drawer-enter-active .absolute.top-0.right-0,
.drawer-leave-active .absolute.top-0.right-0 {
  transition: transform 0.3s ease;
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .absolute.top-0.right-0,
.drawer-leave-to .absolute.top-0.right-0 {
  transform: translateX(100%);
}
</style>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <PageTitle
        :icon="CircleStackIcon"
        :title="t('gateways.title')"
        :subtitle="t('gateways.subtitle')"
        icon-class="text-violet-600 dark:text-violet-400"
      />
      <button
        data-tour="gateway-create-button"
        @click="showCreateModal = true"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t("gateways.createGateway") }}
      </button>
    </div>

    <GatewayStats :stats="stats" />

    <GatewayToolbar
      v-model:search-query="searchQuery"
      v-model:selected-status="selectedStatus"
      v-model:view-mode="viewMode"
      :refreshing="isRefreshing"
      @refresh="fetchGateways(true, true)"
    />

    <GatewayListView
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :loading="isLoading"
      :filtered-gateways="filteredGateways"
      :view-mode="viewMode"
      :total-items="totalItems"
      :columns="gatewayColumns"
      :table="gatewayTable"
      :status-colors="statusColors"
      :get-status-label="getStatusLabel"
      :format-bytes="formatBytes"
      :format-date="formatDate"
      @detail="viewGatewayDetail"
      @delete="deleteGateway"
      @edit="openEditModal"
      @install-info="viewInstallInfo"
      @regenerate-token="handleRegenerateToken"
      @update-status="handleUpdateStatus"
    />

    <!-- Edit Modal -->
    <GatewayEditModal
      v-if="showEditModal"
      :form="editFormData"
      :saving="isEditing"
      @close="showEditModal = false"
      @submit="submitEdit"
    />

    <!-- Delete Confirm Modal -->
    <GatewayDeleteConfirmModal
      v-if="showDeleteConfirm"
      :gateway="gatewayToDelete"
      :deleting="isDeletingGateway"
      @close="showDeleteConfirm = false"
      @confirm="confirmDelete"
    />

    <GatewayCreateModal
      v-if="showCreateModal"
      :gateway="newGateway"
      :creating="isCreating"
      @close="showCreateModal = false"
      @submit="createGateway"
    />

    <GatewayInstallWizardModal
      v-if="showInstallWizard && createdGateway"
      :gateway="createdGateway"
      :step="wizardStep"
      :install-command="wizardInstallCommand"
      :loading-command="isLoadingWizardCommand"
      @close="closeInstallWizard"
      @previous="prevWizardStep"
      @next="nextWizardStep"
      @copy-command="copyWizardCommand"
      @registered="onGatewayRegistered"
    />

    <GatewayInstallInfoModal
      v-if="showInstallInfoModal && installInfoGateway"
      :gateway="installInfoGateway"
      :install-command="installInfoCommand"
      :api-token="installInfoApiToken"
      :install-token-used="installInfoTokenUsed"
      :loading="isLoadingInstallInfoCommand"
      @close="showInstallInfoModal = false"
      @copy="copyInstallInfoText"
      @regenerate-token="regenerateInstallInfoToken"
    />

    <!-- Detail Drawer -->
    <GatewayDetailDrawer
      v-if="showDetailDrawer && selectedGateway"
      :gateway="selectedGateway"
      :detail-tab="detailTab"
      :loading="isLoadingDetail"
      :status-colors="statusColors"
      @close="showDetailDrawer = false"
      @refresh="fetchGateways(true)"
      @update:detail-tab="(tab) => (detailTab = tab)"
    >
      <!-- Overview Tab -->
      <GatewayOverviewTab
        v-if="detailTab === 'overview' && selectedGateway"
        :gateway="selectedGateway"
      />

      <!-- Monitoring Tab -->
      <GatewayMonitoringTab
        v-else-if="detailTab === 'monitoring' && selectedGateway"
        :gateway="selectedGateway"
        :monitoring-data="monitoringData"
        :current="monitoringCurrent"
        :network-io="monitoringNetworkIo"
        :disk-io="monitoringDiskIo"
        :is-loading="isLoadingMonitoring"
        :time-range="monitoringHours"
        :stats="monitoringStats"
        @refresh="loadMonitoringData"
        @update:time-range="(h) => (monitoringHours = h)"
      />

      <!-- Mounts Tab -->
      <GatewayMountsTab
        v-else-if="detailTab === 'mounts' && selectedGateway"
        :gateway="selectedGateway"
        :mounts="mountsData"
        :is-loading="isLoadingMounts"
      />
    </GatewayDetailDrawer>
  </div>
</template>
