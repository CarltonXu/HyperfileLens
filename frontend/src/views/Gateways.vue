<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useI18n } from "vue-i18n";
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
import { PlusIcon } from "@heroicons/vue/24/outline";

const { t } = useI18n();
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
const gateways = ref<Gateway[]>([]);
const stats = ref<GatewayStats | null>(null);
const searchQuery = ref("");
const selectedStatus = ref<string>("all");

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
  fetchGateways();
});
watch(currentPage, () => {
  fetchGateways();
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
const isLoadingInstallInfoCommand = ref(false);
const installInfoCommandCopied = ref(false);

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
  }>
>([]);
const isLoadingMonitoring = ref(false);
const monitoringHours = ref(24);

// Computed
const filteredGateways = computed(() => {
  let result = gateways.value;

  if (selectedStatus.value !== "all") {
    result = result.filter((g) => g.status === selectedStatus.value);
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
  | "memory_total"
  | "kopia_version"
  | "last_heartbeat"
  | "actions";

const gatewayColumns = computed(() => [
  {
    key: "name" as const,
    label: t("gateways.gatewayName"),
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
    label: t("gateways.internalIp"),
    min: 150,
    max: 280,
  },
  {
    key: "active_mounts" as const,
    label: t("gateways.activeMounts"),
    min: 150,
    max: 260,
  },
  {
    key: "cpu_cores" as const,
    label: t("gateways.cpuCores"),
    min: 130,
    max: 240,
  },
  {
    key: "memory_total" as const,
    label: t("gateways.memoryTotal"),
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
  minTableWidth: 1350,
  getSortValue: (gateway, key) => {
    if (key === "status") return getStatusLabel(gateway.status);
    if (key === "memory_total") return gateway.memory_total || 0;
    if (key === "last_heartbeat") {
      return gateway.last_heartbeat
        ? new Date(gateway.last_heartbeat).getTime()
        : 0;
    }
    if (key === "actions") return "";
    return (gateway as any)[key] ?? "";
  },
  getColumnText: (gateway, key) => {
    if (key === "status") return getStatusLabel(gateway.status);
    if (key === "memory_total") return formatBytes(gateway.memory_total);
    if (key === "last_heartbeat") return formatDate(gateway.last_heartbeat);
    if (key === "actions") return t("common.actions");
    return String((gateway as any)[key] ?? "");
  },
});

// Methods
async function fetchGateways() {
  isLoading.value = true;
  try {
    const [listRes, statsRes] = await Promise.all([
      gatewaysApi.list({ page: currentPage.value, page_size: pageSize.value }),
      gatewaysApi.stats(),
    ]);
    gateways.value = listRes.data.results || listRes.data;
    totalItems.value = listRes.data.count || gateways.value.length;
    stats.value = statsRes.data;
  } catch (error) {
    console.error("Failed to fetch gateways:", error);
  } finally {
    isLoading.value = false;
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

    await fetchGateways();
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
    await navigator.clipboard.writeText(wizardInstallCommand.value);
  } catch (error) {
    console.error("Failed to copy:", error);
  }
}

function closeInstallWizard() {
  showInstallWizard.value = false;
  createdGateway.value = null;
  wizardInstallCommand.value = "";
  wizardStep.value = 1;
  resetNewGateway();
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

async function viewInstallInfo(gateway: Gateway) {
  installInfoGateway.value = gateway;
  installInfoCommand.value = "";
  installInfoCommandCopied.value = false;
  showInstallInfoModal.value = true;
  isLoadingInstallInfoCommand.value = true;
  try {
    const res = await gatewaysApi.installCommand(gateway.id);
    installInfoCommand.value = res.data.install_command || "";
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
    await fetchGateways();
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
  try {
    await gatewaysApi.regenerateToken(gateway.id);
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
    await fetchGateways();
    if (selectedGateway.value?.id === gateway.id) {
      selectedGateway.value = { ...selectedGateway.value, status };
    }
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

  try {
    await gatewaysApi.delete(gatewayToDelete.value.id);
    showDeleteConfirm.value = false;
    showDetailDrawer.value = false;
    gatewayToDelete.value = null;
    await fetchGateways();
  } catch (error) {
    console.error("Failed to delete gateway:", error);
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: getApiErrorMessage(error, t("common.deleteFailed")),
    });
  }
}

async function copyInstallInfoCommand() {
  if (!installInfoCommand.value) return;

  try {
    await navigator.clipboard.writeText(installInfoCommand.value);
    installInfoCommandCopied.value = true;
    setTimeout(() => {
      installInfoCommandCopied.value = false;
    }, 2000);
  } catch (error) {
    console.error("Failed to copy:", error);
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
  } catch (error) {
    console.error("Failed to load monitoring data:", error);
    monitoringData.value = [];
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

// Lifecycle
onMounted(() => {
  fetchGateways();
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
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-foreground">
          {{ t("gateways.title") }}
        </h1>
        <p class="text-foreground-secondary mt-1">
          {{ t("gateways.subtitle") }}
        </p>
      </div>
      <button
        @click="showCreateModal = true"
        class="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors"
      >
        <PlusIcon class="w-5 h-5" />
        {{ t("gateways.createGateway") }}
      </button>
    </div>

    <GatewayStats :stats="stats" />

    <GatewayToolbar
      v-model:search-query="searchQuery"
      v-model:selected-status="selectedStatus"
      v-model:view-mode="viewMode"
      @refresh="fetchGateways"
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
      @close="showEditModal = false"
      @submit="submitEdit"
    />

    <!-- Delete Confirm Modal -->
    <GatewayDeleteConfirmModal
      v-if="showDeleteConfirm"
      :gateway="gatewayToDelete"
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
    />

    <GatewayInstallInfoModal
      v-if="showInstallInfoModal && installInfoGateway"
      :gateway="installInfoGateway"
      :install-command="installInfoCommand"
      :loading="isLoadingInstallInfoCommand"
      :command-copied="installInfoCommandCopied"
      @close="showInstallInfoModal = false"
      @copy="copyInstallInfoCommand"
    />

    <!-- Detail Drawer -->
    <GatewayDetailDrawer
      v-if="showDetailDrawer && selectedGateway"
      :gateway="selectedGateway"
      :detail-tab="detailTab"
      :loading="isLoadingDetail"
      :status-colors="statusColors"
      @close="showDetailDrawer = false"
      @refresh="fetchGateways"
      @update:detail-tab="(tab) => (detailTab = tab)"
    >
      <!-- Overview Tab -->
      <GatewayOverviewTab
        v-if="detailTab === 'overview' && selectedGateway"
        :gateway="selectedGateway"
      />

      <!-- Mounts Tab -->
      <GatewayMountsTab
        v-else-if="detailTab === 'mounts' && selectedGateway"
        :gateway="selectedGateway"
        :mounts="mountsData"
        :is-loading="isLoadingMounts"
      />

      <!-- Monitoring Tab -->
      <GatewayMonitoringTab
        v-else-if="detailTab === 'monitoring' && selectedGateway"
        :gateway="selectedGateway"
        :monitoring-data="monitoringData"
        :is-loading="isLoadingMonitoring"
        :time-range="monitoringHours"
        :stats="monitoringStats"
        @refresh="loadMonitoringData"
        @update:time-range="(h) => (monitoringHours = h)"
      />
    </GatewayDetailDrawer>
  </div>
</template>
