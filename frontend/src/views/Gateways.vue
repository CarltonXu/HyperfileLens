<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import { gatewaysApi } from "@/api";
import { useAppStore } from "@/stores/app";
import { getApiErrorMessage } from "@/utils/errors";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import GatewayListView from "@/components/gateways/GatewayListView.vue";
import GatewayStats from "@/components/gateways/GatewayStats.vue";
import GatewayToolbar from "@/components/gateways/GatewayToolbar.vue";
import {
  ServerIcon,
  PlusIcon,
  ArrowPathIcon,
  CpuChipIcon,
  CircleStackIcon,
  CheckCircleIcon,
  XMarkIcon,
  ClipboardDocumentIcon,
  PlayIcon,
  PauseIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline";

const { t } = useI18n();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();

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
  labels: [] as string[],
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
const detailTab = ref<"overview" | "install" | "mounts" | "monitoring">(
  "overview",
);
const installCommand = ref("");
const isLoadingCommand = ref(false);
const commandCopied = ref(false);

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

// Status colors
const statusColors: Record<string, string> = {
  pending: "bg-slate-100 text-slate-700",
  installing:
    "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  online:
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  offline: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  error: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  maintenance:
    "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
};

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
    commandCopied.value = true;
    setTimeout(() => {
      commandCopied.value = false;
    }, 2000);
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
    labels: [],
    tags: {},
  };
}

async function viewGatewayDetail(gateway: Gateway) {
  selectedGateway.value = gateway;
  detailTab.value = "overview";
  showDetailDrawer.value = true;
  installCommand.value = "";
}

async function loadInstallCommand() {
  if (!selectedGateway.value) return;

  isLoadingCommand.value = true;
  try {
    const res = await gatewaysApi.installCommand(selectedGateway.value.id);
    installCommand.value = res.data.install_command;
  } catch (error) {
    console.error("Failed to get install command:", error);
  } finally {
    isLoadingCommand.value = false;
  }
}

async function copyCommand() {
  if (!installCommand.value) return;

  try {
    await navigator.clipboard.writeText(installCommand.value);
    commandCopied.value = true;
    setTimeout(() => {
      commandCopied.value = false;
    }, 2000);
  } catch (error) {
    console.error("Failed to copy:", error);
  }
}

async function activateGateway(gateway: Gateway) {
  try {
    await gatewaysApi.activate(gateway.id);
    await fetchGateways();
    if (selectedGateway.value?.id === gateway.id) {
      selectedGateway.value = { ...selectedGateway.value, status: "online" };
    }
  } catch (error) {
    console.error("Failed to activate gateway:", error);
  }
}

async function deactivateGateway(gateway: Gateway) {
  try {
    await gatewaysApi.deactivate(gateway.id);
    await fetchGateways();
    if (selectedGateway.value?.id === gateway.id) {
      selectedGateway.value = { ...selectedGateway.value, status: "inactive" };
    }
  } catch (error) {
    console.error("Failed to deactivate gateway:", error);
  }
}

async function deleteGateway(gateway: Gateway) {
  if (!confirm(t("gateways.confirmDelete"))) return;

  try {
    await gatewaysApi.delete(gateway.id);
    showDetailDrawer.value = false;
    await fetchGateways();
  } catch (error) {
    console.error("Failed to delete gateway:", error);
  }
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: t("gateways.statusPending"),
    installing: t("gateways.statusInstalling"),
    online: t("gateways.statusOnline"),
    offline: t("gateways.statusOffline"),
    error: t("gateways.statusError"),
    maintenance: t("gateways.statusMaintenance"),
  };
  return labels[status] || status;
}

function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString();
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

// Chart computed values
const chartData = computed(() => {
  if (!monitoringData.value.length) return null;

  const MAX_POINTS = 48;
  const data = monitoringData.value;

  // Sample data if too many points
  let sampledData = data;
  if (data.length > MAX_POINTS) {
    const step = Math.ceil(data.length / MAX_POINTS);
    sampledData = data.filter((_, i) => i % step === 0);
  }

  return {
    labels: sampledData.map((d) => new Date(d.timestamp).toLocaleTimeString()),
    cpu: sampledData.map((d) => d.cpu_usage || 0),
    memory: sampledData.map((d) => d.memory_usage || 0),
    disk: sampledData.map((d) => d.disk_usage || 0),
  };
});

// Watch tab changes
watch(detailTab, (newTab) => {
  if (newTab === "install" && selectedGateway.value?.status === "pending") {
    loadInstallCommand();
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
    />

    <!-- Create Modal -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    >
      <div class="modal-surface rounded-xl w-full max-w-lg p-6">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-semibold text-foreground">
            {{ t("gateways.createGateway") }}
          </h2>
          <button
            @click="showCreateModal = false"
            class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            <XMarkIcon class="w-6 h-6" />
          </button>
        </div>

        <form @submit.prevent="createGateway" class="space-y-4">
          <div>
            <label
              class="block text-sm font-medium text-foreground-secondary mb-1"
            >
              {{ t("gateways.gatewayName") }}
              <span class="text-red-500">*</span>
            </label>
            <input
              v-model="newGateway.name"
              type="text"
              required
              class="w-full px-3 py-2 bg-background-secondary border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500"
              :placeholder="t('gateways.gatewayNamePlaceholder')"
            />
          </div>

          <div>
            <label
              class="block text-sm font-medium text-foreground-secondary mb-1"
            >
              {{ t("gateways.description") }}
            </label>
            <textarea
              v-model="newGateway.description"
              rows="2"
              class="w-full px-3 py-2 bg-background-secondary border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500"
              :placeholder="t('gateways.descriptionPlaceholder')"
            />
          </div>

          <div>
            <label
              class="block text-sm font-medium text-foreground-secondary mb-1"
            >
              {{ t("gateways.labels") }}
            </label>
            <input
              v-model="newGateway.labels"
              type="text"
              class="w-full px-3 py-2 bg-background-secondary border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500"
              :placeholder="t('gateways.labelsPlaceholder')"
            />
            <p class="mt-1 text-xs text-foreground-secondary">
              {{ t("gateways.labelsHint") }}
            </p>
          </div>

          <div class="flex justify-end gap-3 pt-4">
            <button
              type="button"
              @click="showCreateModal = false"
              class="px-4 py-2 text-foreground-secondary hover:bg-hover rounded-lg"
            >
              {{ t("common.cancel") }}
            </button>
            <button
              type="submit"
              :disabled="isCreating || !newGateway.name.trim()"
              class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ isCreating ? t("common.loading") : t("common.create") }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Install Wizard Modal -->
    <div
      v-if="showInstallWizard && createdGateway"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    >
      <div class="modal-surface rounded-xl w-full max-w-2xl p-6">
        <!-- Header -->
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-semibold text-foreground">
            {{ t("gateways.installWizard.title") }}
          </h2>
          <button
            @click="closeInstallWizard"
            class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            <XMarkIcon class="w-6 h-6" />
          </button>
        </div>

        <!-- Steps Indicator -->
        <div class="flex items-center justify-center mb-8">
          <div class="flex items-center">
            <div
              :class="[
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
                wizardStep >= 1
                  ? 'bg-violet-600 text-white'
                  : 'bg-slate-200 text-slate-500',
              ]"
            >
              1
            </div>
            <div
              :class="[
                'w-16 h-1',
                wizardStep >= 2 ? 'bg-violet-600' : 'bg-slate-200',
              ]"
            ></div>
            <div
              :class="[
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
                wizardStep >= 2
                  ? 'bg-violet-600 text-white'
                  : 'bg-slate-200 text-slate-500',
              ]"
            >
              2
            </div>
            <div
              :class="[
                'w-16 h-1',
                wizardStep >= 3 ? 'bg-violet-600' : 'bg-slate-200',
              ]"
            ></div>
            <div
              :class="[
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
                wizardStep >= 3
                  ? 'bg-violet-600 text-white'
                  : 'bg-slate-200 text-slate-500',
              ]"
            >
              3
            </div>
          </div>
        </div>

        <!-- Step 1: Gateway Info -->
        <div v-if="wizardStep === 1" class="space-y-4">
          <h3 class="text-lg font-medium text-foreground">
            {{ t("gateways.installWizard.step1Title") }}
          </h3>
          <p class="text-foreground-secondary">
            {{ t("gateways.installWizard.step1Desc") }}
          </p>

          <div class="bg-background-secondary rounded-lg p-4 space-y-3">
            <div class="flex justify-between">
              <span class="text-foreground-secondary">{{
                t("gateways.gatewayName")
              }}</span>
              <span class="font-medium text-foreground">{{
                createdGateway.name
              }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-foreground-secondary">{{
                t("gateways.gatewayId")
              }}</span>
              <span class="font-mono text-sm text-foreground">{{
                createdGateway.id
              }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-foreground-secondary">{{
                t("gateways.status")
              }}</span>
              <span
                class="px-2 py-1 text-xs font-medium rounded-full bg-background-tertiary text-foreground-secondary"
                >{{ t("gateways.statusPending") }}</span
              >
            </div>
          </div>

          <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
            <p class="text-sm text-blue-700 dark:text-blue-300">
              {{ t("gateways.installWizard.step1Note") }}
            </p>
          </div>
        </div>

        <!-- Step 2: Install Command -->
        <div v-if="wizardStep === 2" class="space-y-4">
          <h3 class="text-lg font-medium text-foreground">
            {{ t("gateways.installWizard.step2Title") }}
          </h3>
          <p class="text-foreground-secondary">
            {{ t("gateways.installWizard.step2Desc") }}
          </p>

          <div
            v-if="isLoadingWizardCommand"
            class="flex items-center justify-center py-8"
          >
            <ArrowPathIcon class="w-6 h-6 text-slate-400 animate-spin" />
          </div>

          <div v-else class="space-y-4">
            <div class="relative">
              <pre
                class="bg-slate-900 text-slate-100 rounded-lg p-4 text-sm overflow-x-auto whitespace-pre-wrap"
                >{{
                  wizardInstallCommand || t("gateways.installWizard.noCommand")
                }}</pre
              >
              <button
                @click="copyWizardCommand"
                class="absolute top-2 right-2 p-2 bg-slate-700 hover:bg-slate-600 rounded text-slate-300"
              >
                <ClipboardDocumentIcon class="w-4 h-4" />
              </button>
            </div>

            <div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
              <p class="text-sm text-yellow-700 dark:text-yellow-300">
                {{ t("gateways.installWizard.step2Note") }}
              </p>
            </div>
          </div>
        </div>

        <!-- Step 3: Waiting for Registration -->
        <div v-if="wizardStep === 3" class="space-y-4">
          <h3 class="text-lg font-medium text-foreground">
            {{ t("gateways.installWizard.step3Title") }}
          </h3>
          <p class="text-foreground-secondary">
            {{ t("gateways.installWizard.step3Desc") }}
          </p>

          <div class="flex flex-col items-center py-8">
            <div
              class="w-16 h-16 rounded-full bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center mb-4"
            >
              <ArrowPathIcon
                class="w-8 h-8 text-violet-600 dark:text-violet-400 animate-spin"
              />
            </div>
            <p class="text-foreground-secondary">
              {{ t("gateways.installWizard.waitingForRegistration") }}
            </p>
          </div>

          <div class="bg-background-secondary rounded-lg p-4">
            <h4 class="text-sm font-medium text-foreground mb-2">
              {{ t("gateways.installWizard.checklist") }}
            </h4>
            <ul class="space-y-2 text-sm text-foreground-secondary">
              <li class="flex items-center gap-2">
                <CheckCircleIcon class="w-4 h-4 text-emerald-500" />
                {{ t("gateways.installWizard.checklist1") }}
              </li>
              <li class="flex items-center gap-2">
                <CheckCircleIcon class="w-4 h-4 text-emerald-500" />
                {{ t("gateways.installWizard.checklist2") }}
              </li>
              <li class="flex items-center gap-2">
                <CheckCircleIcon class="w-4 h-4 text-emerald-500" />
                {{ t("gateways.installWizard.checklist3") }}
              </li>
            </ul>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex justify-between pt-6 mt-6 border-t border-border">
          <button
            v-if="wizardStep > 1"
            @click="prevWizardStep"
            class="px-4 py-2 text-foreground-secondary hover:bg-hover rounded-lg"
          >
            {{ t("common.previous") }}
          </button>
          <div v-else />

          <div class="flex gap-3">
            <button
              @click="closeInstallWizard"
              class="px-4 py-2 text-foreground-secondary hover:bg-hover rounded-lg"
            >
              {{ t("common.close") }}
            </button>
            <button
              v-if="wizardStep < 3"
              @click="nextWizardStep"
              :disabled="wizardStep === 2 && !wizardInstallCommand"
              class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ t("common.next") }}
            </button>
            <button
              v-else
              @click="closeInstallWizard"
              class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700"
            >
              {{ t("common.finish") }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Detail Drawer -->
    <Transition name="drawer">
      <div
        v-if="showDetailDrawer && selectedGateway"
        class="fixed inset-0 z-50"
      >
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/50"
          @click="showDetailDrawer = false"
        />
        <!-- Drawer Panel -->
        <div
          class="absolute top-0 right-0 h-full w-[640px] max-w-[90vw] drawer-panel shadow-2xl flex flex-col"
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between p-5 border-b border-border drawer-surface flex-shrink-0"
          >
            <div class="flex items-center gap-3">
              <div
                :class="[
                  'w-10 h-10 rounded-xl flex items-center justify-center',
                  selectedGateway.is_online
                    ? 'bg-gradient-to-br from-emerald-500 to-teal-600'
                    : 'bg-gradient-to-br from-slate-400 to-slate-500',
                ]"
              >
                <ServerIcon class="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 class="text-lg font-semibold text-foreground">
                  {{ selectedGateway.name }}
                </h2>
                <div class="flex items-center gap-2 mt-1">
                  <span
                    :class="[
                      'px-2 py-0.5 rounded-full text-xs font-medium',
                      statusColors[selectedGateway.status],
                    ]"
                  >
                    {{ getStatusLabel(selectedGateway.status) }}
                  </span>
                  <span
                    v-if="selectedGateway.is_online"
                    class="px-2 py-0.5 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 rounded-full text-xs font-medium"
                  >
                    {{ t("gateways.online") }}
                  </span>
                  <span
                    v-else
                    class="px-2 py-0.5 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-full text-xs font-medium"
                  >
                    {{ t("gateways.offline") }}
                  </span>
                </div>
              </div>
            </div>
            <button
              @click="showDetailDrawer = false"
              class="p-2 text-foreground-muted hover:text-slate-600 dark:hover:text-slate-300 hover:bg-hover rounded-lg"
            >
              <XMarkIcon class="w-5 h-5" />
            </button>
          </div>

          <!-- Tabs -->
          <div
            class="border-b border-border drawer-muted-surface px-5 flex-shrink-0"
          >
            <nav class="flex gap-1 -mb-px">
              <button
                @click="detailTab = 'overview'"
                :class="[
                  'px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                  detailTab === 'overview'
                    ? 'border-violet-500 text-violet-600'
                    : 'border-transparent text-foreground-secondary hover:text-foreground hover:border-slate-300 dark:hover:border-slate-600',
                ]"
              >
                {{ t("gateways.tabs.overview") }}
              </button>
              <button
                v-if="selectedGateway.status === 'pending'"
                @click="detailTab = 'install'"
                :class="[
                  'px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                  detailTab === 'install'
                    ? 'border-violet-500 text-violet-600'
                    : 'border-transparent text-foreground-secondary hover:text-foreground hover:border-slate-300 dark:hover:border-slate-600',
                ]"
              >
                {{ t("gateways.tabs.install") }}
              </button>
              <button
                @click="detailTab = 'mounts'"
                :class="[
                  'px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                  detailTab === 'mounts'
                    ? 'border-violet-500 text-violet-600'
                    : 'border-transparent text-foreground-secondary hover:text-foreground hover:border-slate-300 dark:hover:border-slate-600',
                ]"
              >
                {{ t("gateways.tabs.mounts") }}
              </button>
              <button
                @click="detailTab = 'monitoring'"
                :class="[
                  'px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                  detailTab === 'monitoring'
                    ? 'border-violet-500 text-violet-600'
                    : 'border-transparent text-foreground-secondary hover:text-foreground hover:border-slate-300 dark:hover:border-slate-600',
                ]"
              >
                {{ t("gateways.tabs.monitoring") }}
              </button>
            </nav>
          </div>

          <!-- Tab Content -->
          <div class="flex-1 overflow-y-auto p-6 drawer-surface">
            <!-- Overview Tab -->
            <div v-if="detailTab === 'overview'" class="space-y-6">
              <!-- Info Grid -->
              <div class="grid grid-cols-2 gap-4">
                <div class="bg-background-secondary rounded-lg p-4">
                  <p class="text-sm text-foreground-secondary">
                    {{ t("gateways.hostname") }}
                  </p>
                  <p class="text-base font-medium text-foreground mt-1">
                    {{ selectedGateway.hostname || "-" }}
                  </p>
                </div>
                <div class="bg-background-secondary rounded-lg p-4">
                  <p class="text-sm text-foreground-secondary">
                    {{ t("gateways.internalIp") }}
                  </p>
                  <p class="text-base font-medium text-foreground mt-1">
                    {{ selectedGateway.internal_ip || "-" }}
                  </p>
                </div>
                <div class="bg-background-secondary rounded-lg p-4">
                  <p class="text-sm text-foreground-secondary">
                    {{ t("gateways.osVersion") }}
                  </p>
                  <p class="text-base font-medium text-foreground mt-1">
                    {{ selectedGateway.os_version || "Ubuntu 22.04" }}
                  </p>
                </div>
                <div class="bg-background-secondary rounded-lg p-4">
                  <p class="text-sm text-foreground-secondary">
                    {{ t("gateways.kopiaVersion") }}
                  </p>
                  <p class="text-base font-medium text-foreground mt-1">
                    {{ selectedGateway.kopia_version || "-" }}
                  </p>
                </div>
              </div>

              <!-- Resources -->
              <div>
                <h3 class="text-sm font-semibold text-foreground mb-3">
                  {{ t("gateways.resources") }}
                </h3>
                <div class="grid grid-cols-3 gap-4">
                  <div class="bg-background-secondary rounded-lg p-4">
                    <div
                      class="flex items-center gap-2 text-foreground-secondary mb-1"
                    >
                      <CpuChipIcon class="w-4 h-4" />
                      <span class="text-sm">{{ t("gateways.cpu") }}</span>
                    </div>
                    <p class="text-lg font-semibold text-foreground">
                      {{ selectedGateway.cpu_cores || "-" }}
                      {{ t("gateways.cores") }}
                    </p>
                    <p
                      v-if="selectedGateway.cpu_usage"
                      class="text-sm text-foreground-secondary"
                    >
                      {{ selectedGateway.cpu_usage }}% {{ t("gateways.used") }}
                    </p>
                  </div>
                  <div class="bg-background-secondary rounded-lg p-4">
                    <div
                      class="flex items-center gap-2 text-foreground-secondary mb-1"
                    >
                      <CircleStackIcon class="w-4 h-4" />
                      <span class="text-sm">{{ t("gateways.memory") }}</span>
                    </div>
                    <p class="text-lg font-semibold text-foreground">
                      {{
                        selectedGateway.memory_total
                          ? formatBytes(selectedGateway.memory_total)
                          : "-"
                      }}
                    </p>
                    <p
                      v-if="selectedGateway.memory_usage"
                      class="text-sm text-foreground-secondary"
                    >
                      {{ selectedGateway.memory_usage }}%
                      {{ t("gateways.used") }}
                    </p>
                  </div>
                  <div class="bg-background-secondary rounded-lg p-4">
                    <div
                      class="flex items-center gap-2 text-foreground-secondary mb-1"
                    >
                      <CircleStackIcon class="w-4 h-4" />
                      <span class="text-sm">{{ t("gateways.disk") }}</span>
                    </div>
                    <p class="text-lg font-semibold text-foreground">
                      {{
                        selectedGateway.disk_total
                          ? formatBytes(selectedGateway.disk_total)
                          : "-"
                      }}
                    </p>
                    <p
                      v-if="selectedGateway.disk_usage"
                      class="text-sm text-foreground-secondary"
                    >
                      {{ selectedGateway.disk_usage }}% {{ t("gateways.used") }}
                    </p>
                  </div>
                </div>
              </div>

              <!-- Mount Info -->
              <div>
                <h3 class="text-sm font-semibold text-foreground mb-3">
                  {{ t("gateways.mountInfo") }}
                </h3>
                <div class="bg-background-secondary rounded-lg p-4">
                  <div class="flex items-center justify-between mb-2">
                    <span class="text-sm text-foreground-secondary">{{
                      t("gateways.activeMounts")
                    }}</span>
                    <span class="font-medium text-foreground"
                      >{{ selectedGateway.active_mounts }} /
                      {{ selectedGateway.max_concurrent_mounts }}</span
                    >
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-sm text-foreground-secondary">{{
                      t("gateways.mountBasePath")
                    }}</span>
                    <span class="font-medium text-foreground">{{
                      selectedGateway.mount_base_path
                    }}</span>
                  </div>
                </div>
              </div>

              <!-- AI Insights Status -->
              <div v-if="selectedGateway.ai_enabled">
                <h3 class="text-sm font-semibold text-foreground mb-3">
                  {{ t("gateways.aiInsights") }}
                </h3>
                <div class="bg-violet-50 dark:bg-violet-900/20 rounded-lg p-4">
                  <div
                    class="flex items-center gap-2 text-violet-600 dark:text-violet-400 mb-2"
                  >
                    <ChatBubbleLeftRightIcon class="w-5 h-5" />
                    <span class="font-medium">{{
                      t("gateways.aiEnabled")
                    }}</span>
                  </div>
                  <p
                    v-if="selectedGateway.last_index_time"
                    class="text-sm text-foreground-secondary"
                  >
                    {{ t("gateways.lastIndexTime") }}:
                    {{ formatDate(selectedGateway.last_index_time) }}
                  </p>
                </div>
              </div>

              <!-- Timestamps -->
              <div class="text-sm text-foreground-secondary space-y-1">
                <p>
                  {{ t("gateways.createdAt") }}:
                  {{ formatDate(selectedGateway.created_at) }}
                </p>
                <p v-if="selectedGateway.registered_at">
                  {{ t("gateways.registeredAt") }}:
                  {{ formatDate(selectedGateway.registered_at) }}
                </p>
                <p v-if="selectedGateway.last_heartbeat">
                  {{ t("gateways.lastHeartbeat") }}:
                  {{ formatDate(selectedGateway.last_heartbeat) }}
                </p>
              </div>

              <!-- Actions -->
              <div class="flex items-center gap-2 pt-4 border-t border-border">
                <button
                  v-if="selectedGateway.status !== 'online'"
                  @click="activateGateway(selectedGateway)"
                  class="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
                >
                  <PlayIcon class="w-4 h-4" />
                  {{ t("gateways.activate") }}
                </button>
                <button
                  v-if="selectedGateway.status === 'online'"
                  @click="deactivateGateway(selectedGateway)"
                  class="flex items-center gap-2 px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700"
                >
                  <PauseIcon class="w-4 h-4" />
                  {{ t("gateways.deactivate") }}
                </button>
                <button
                  @click="deleteGateway(selectedGateway)"
                  class="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                >
                  <TrashIcon class="w-4 h-4" />
                  {{ t("gateways.delete") }}
                </button>
              </div>
            </div>

            <!-- Install Tab -->
            <div v-if="detailTab === 'install'" class="space-y-6">
              <div
                v-if="selectedGateway.status === 'pending'"
                class="space-y-4"
              >
                <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                  <p class="text-sm text-blue-700 dark:text-blue-300">
                    {{ t("gateways.installInstructions") }}
                  </p>
                </div>

                <div
                  v-if="isLoadingCommand"
                  class="flex items-center justify-center py-8"
                >
                  <ArrowPathIcon class="w-6 h-6 text-slate-400 animate-spin" />
                </div>

                <div v-else-if="installCommand" class="space-y-4">
                  <div class="flex items-center justify-between">
                    <h3 class="text-sm font-semibold text-foreground">
                      {{ t("gateways.installCommand") }}
                    </h3>
                    <button
                      @click="copyCommand"
                      :class="[
                        'flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors',
                        commandCopied
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
                      ]"
                    >
                      <ClipboardDocumentIcon class="w-4 h-4" />
                      {{
                        commandCopied
                          ? t("gateways.copied")
                          : t("gateways.copyCommand")
                      }}
                    </button>
                  </div>
                  <pre
                    class="bg-slate-900 text-slate-100 p-4 rounded-lg text-sm overflow-x-auto whitespace-pre-wrap"
                    >{{ installCommand }}</pre
                  >
                </div>

                <div class="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4">
                  <p class="text-sm text-amber-700 dark:text-amber-300">
                    {{ t("gateways.installNote") }}
                  </p>
                </div>
              </div>

              <div v-else class="text-center py-12 text-foreground-secondary">
                <CheckCircleIcon
                  class="w-16 h-16 mx-auto mb-4 text-emerald-500"
                />
                <p>{{ t("gateways.alreadyInstalled") }}</p>
              </div>
            </div>

            <!-- Mounts Tab -->
            <div v-if="detailTab === 'mounts'" class="space-y-6">
              <div class="bg-background-secondary rounded-lg p-4">
                <div class="flex items-center justify-between mb-4">
                  <span class="text-sm font-medium text-foreground-secondary">{{
                    t("gateways.mountStatus")
                  }}</span>
                  <span class="text-lg font-semibold text-foreground"
                    >{{ selectedGateway.active_mounts }} /
                    {{ selectedGateway.max_concurrent_mounts }}</span
                  >
                </div>
                <div
                  class="h-2 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden"
                >
                  <div
                    class="h-full bg-violet-500 rounded-full transition-all"
                    :style="{
                      width: `${(selectedGateway.active_mounts / selectedGateway.max_concurrent_mounts) * 100}%`,
                    }"
                  />
                </div>
              </div>

              <div class="bg-background-secondary rounded-lg p-4">
                <p class="text-sm text-foreground-secondary mb-2">
                  {{ t("gateways.mountBasePath") }}
                </p>
                <code class="text-sm font-mono text-foreground">{{
                  selectedGateway.mount_base_path
                }}</code>
              </div>

              <p class="text-sm text-foreground-secondary text-center">
                {{ t("gateways.mountDetailsNote") }}
              </p>
            </div>

            <!-- Monitoring Tab -->
            <div v-if="detailTab === 'monitoring'" class="space-y-6">
              <!-- Time Range Selector -->
              <div class="flex items-center gap-4">
                <select
                  v-model="monitoringHours"
                  class="px-3 py-2 bg-background-secondary border border-border rounded-lg text-sm text-foreground-secondary"
                >
                  <option :value="1">1 {{ t("gateways.hour") }}</option>
                  <option :value="6">6 {{ t("gateways.hours") }}</option>
                  <option :value="12">12 {{ t("gateways.hours") }}</option>
                  <option :value="24">24 {{ t("gateways.hours") }}</option>
                </select>
                <button
                  @click="loadMonitoringData"
                  class="p-2 text-foreground-secondary hover:text-foreground hover:bg-hover rounded-lg"
                >
                  <ArrowPathIcon class="w-5 h-5" />
                </button>
              </div>

              <!-- Loading State -->
              <div
                v-if="isLoadingMonitoring"
                class="flex items-center justify-center py-12"
              >
                <ArrowPathIcon class="w-8 h-8 text-slate-400 animate-spin" />
              </div>

              <!-- No Data State -->
              <div
                v-else-if="!chartData || chartData.labels.length === 0"
                class="text-center py-12"
              >
                <CircleStackIcon
                  class="w-16 h-16 text-foreground-muted mx-auto mb-4"
                />
                <p class="text-foreground-secondary">
                  {{ t("gateways.noMonitoringData") }}
                </p>
              </div>

              <!-- Charts -->
              <div v-else class="space-y-6">
                <!-- CPU Usage Chart -->
                <div class="bg-background-secondary rounded-xl p-4">
                  <h4
                    class="text-sm font-medium text-foreground-secondary mb-3"
                  >
                    {{ t("gateways.cpuUsage") }}
                  </h4>
                  <div class="h-32 relative">
                    <svg
                      viewBox="0 0 400 100"
                      class="w-full h-full"
                      preserveAspectRatio="none"
                    >
                      <!-- Grid lines -->
                      <line
                        x1="0"
                        y1="0"
                        x2="400"
                        y2="0"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />
                      <line
                        x1="0"
                        y1="25"
                        x2="400"
                        y2="25"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />
                      <line
                        x1="0"
                        y1="50"
                        x2="400"
                        y2="50"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />
                      <line
                        x1="0"
                        y1="75"
                        x2="400"
                        y2="75"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />
                      <line
                        x1="0"
                        y1="100"
                        x2="400"
                        y2="100"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />

                      <!-- CPU Line -->
                      <polyline
                        :points="
                          (chartData?.cpu ?? [])
                            .map(
                              (v, i) =>
                                `${(i / Math.max((chartData?.cpu?.length ?? 1) - 1, 1)) * 400},${100 - v}`,
                            )
                            .join(' ')
                        "
                        fill="none"
                        stroke="#3b82f6"
                        stroke-width="2"
                      />
                    </svg>
                    <div class="absolute right-0 top-0 text-xs text-slate-400">
                      100%
                    </div>
                    <div
                      class="absolute right-0 bottom-0 text-xs text-slate-400"
                    >
                      0%
                    </div>
                  </div>
                  <div class="flex items-center justify-between mt-2 text-sm">
                    <span class="text-foreground-secondary">{{
                      chartData?.labels?.[0] || "-"
                    }}</span>
                    <span class="text-foreground-secondary">{{
                      chartData?.labels?.[
                        (chartData?.labels?.length ?? 1) - 1
                      ] || "-"
                    }}</span>
                  </div>
                </div>

                <!-- Memory Usage Chart -->
                <div class="bg-background-secondary rounded-xl p-4">
                  <h4
                    class="text-sm font-medium text-foreground-secondary mb-3"
                  >
                    {{ t("gateways.memoryUsage") }}
                  </h4>
                  <div class="h-32 relative">
                    <svg
                      viewBox="0 0 400 100"
                      class="w-full h-full"
                      preserveAspectRatio="none"
                    >
                      <!-- Grid lines -->
                      <line
                        x1="0"
                        y1="0"
                        x2="400"
                        y2="0"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />
                      <line
                        x1="0"
                        y1="25"
                        x2="400"
                        y2="25"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />
                      <line
                        x1="0"
                        y1="50"
                        x2="400"
                        y2="50"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />
                      <line
                        x1="0"
                        y1="75"
                        x2="400"
                        y2="75"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />
                      <line
                        x1="0"
                        y1="100"
                        x2="400"
                        y2="100"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />

                      <!-- Memory Line -->
                      <polyline
                        :points="
                          (chartData?.memory ?? [])
                            .map(
                              (v, i) =>
                                `${(i / Math.max((chartData?.memory?.length ?? 1) - 1, 1)) * 400},${100 - v}`,
                            )
                            .join(' ')
                        "
                        fill="none"
                        stroke="#10b981"
                        stroke-width="2"
                      />
                    </svg>
                    <div class="absolute right-0 top-0 text-xs text-slate-400">
                      100%
                    </div>
                    <div
                      class="absolute right-0 bottom-0 text-xs text-slate-400"
                    >
                      0%
                    </div>
                  </div>
                </div>

                <!-- Disk Usage Chart -->
                <div class="bg-background-secondary rounded-xl p-4">
                  <h4
                    class="text-sm font-medium text-foreground-secondary mb-3"
                  >
                    {{ t("gateways.diskUsage") }}
                  </h4>
                  <div class="h-32 relative">
                    <svg
                      viewBox="0 0 400 100"
                      class="w-full h-full"
                      preserveAspectRatio="none"
                    >
                      <!-- Grid lines -->
                      <line
                        x1="0"
                        y1="0"
                        x2="400"
                        y2="0"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />
                      <line
                        x1="0"
                        y1="25"
                        x2="400"
                        y2="25"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />
                      <line
                        x1="0"
                        y1="50"
                        x2="400"
                        y2="50"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />
                      <line
                        x1="0"
                        y1="75"
                        x2="400"
                        y2="75"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />
                      <line
                        x1="0"
                        y1="100"
                        x2="400"
                        y2="100"
                        stroke="currentColor"
                        stroke-opacity="0.1"
                      />

                      <!-- Disk Line -->
                      <polyline
                        :points="
                          (chartData?.disk ?? [])
                            .map(
                              (v, i) =>
                                `${(i / Math.max((chartData?.disk?.length ?? 1) - 1, 1)) * 400},${100 - v}`,
                            )
                            .join(' ')
                        "
                        fill="none"
                        stroke="#f59e0b"
                        stroke-width="2"
                      />
                    </svg>
                    <div class="absolute right-0 top-0 text-xs text-slate-400">
                      100%
                    </div>
                    <div
                      class="absolute right-0 bottom-0 text-xs text-slate-400"
                    >
                      0%
                    </div>
                  </div>
                </div>

                <!-- Legend -->
                <div class="flex items-center justify-center gap-6 text-sm">
                  <div class="flex items-center gap-2">
                    <div class="w-3 h-3 rounded-full bg-blue-500"></div>
                    <span class="text-foreground-secondary">{{
                      t("gateways.cpu")
                    }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <div class="w-3 h-3 rounded-full bg-emerald-500"></div>
                    <span class="text-foreground-secondary">{{
                      t("gateways.memory")
                    }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <div class="w-3 h-3 rounded-full bg-amber-500"></div>
                    <span class="text-foreground-secondary">{{
                      t("gateways.disk")
                    }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>
