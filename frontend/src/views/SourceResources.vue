<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  CloudIcon,
  ComputerDesktopIcon,
  FolderIcon,
  PlusIcon,
  ServerIcon,
} from "@heroicons/vue/24/outline";
import { nodesApi, sourceResourcesApi } from "@/api";
import Pagination from "@/components/Pagination.vue";
import SourceResourceWizard from "@/components/SourceResourceWizard.vue";
import SourceResourceCardView from "@/components/source-resources/SourceResourceCardView.vue";
import SourceResourceDeleteModal from "@/components/source-resources/SourceResourceDeleteModal.vue";
import SourceResourceDetailModal from "@/components/source-resources/SourceResourceDetailModal.vue";
import SourceResourceListView from "@/components/source-resources/SourceResourceListView.vue";
import SourceResourceStatsCards from "@/components/source-resources/SourceResourceStats.vue";
import SourceResourceToolbar from "@/components/source-resources/SourceResourceToolbar.vue";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import { useAppStore } from "@/stores/app";
import type {
  ResourceType,
  SourceResource,
  SourceResourceStats,
} from "@/types/sourceResource";
import { getApiErrorMessage } from "@/utils/errors";

const { t } = useI18n();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();

const resources = ref<SourceResource[]>([]);
const stats = ref<SourceResourceStats | null>(null);
const nodes = ref<any[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

const searchQuery = ref("");
const typeFilter = ref("");
const statusFilter = ref("");

const currentPage = ref(1);
const pageSize = ref(getPageSize("source-resources"));
const PAGE_STORAGE_KEY = "source-resources";
const VIEW_MODE_STORAGE_KEY = "hyperfilelens:source-resources:viewMode";
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

const showDetailModal = ref(false);
const showDeleteModal = ref(false);
const showResourceWizard = ref(false);
const selectedResource = ref<SourceResource | null>(null);

watch(pageSize, (newSize) => {
  setPageSize(newSize, PAGE_STORAGE_KEY);
});

watch([searchQuery, typeFilter, statusFilter], () => {
  currentPage.value = 1;
});

watch(viewMode, (mode) => {
  try {
    localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode);
  } catch {
    // Ignore storage errors.
  }
});

const filteredResources = computed(() => {
  return resources.value.filter((resource) => {
    const matchesSearch =
      !searchQuery.value ||
      resource.name.toLowerCase().includes(searchQuery.value.toLowerCase());
    const matchesType =
      !typeFilter.value || resource.resource_type === typeFilter.value;
    const matchesStatus =
      !statusFilter.value || resource.status === statusFilter.value;
    return matchesSearch && matchesType && matchesStatus;
  });
});

const paginatedResources = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredResources.value.slice(start, end);
});

type SourceResourceColumnKey =
  | "name"
  | "resource_type"
  | "status"
  | "bound_node"
  | "connection"
  | "capacity"
  | "updated_at"
  | "actions";

const sourceResourceColumns = computed(() => [
  {
    key: "name" as const,
    label: t("sourceResources.form.name"),
    min: 260,
    max: 620,
  },
  {
    key: "resource_type" as const,
    label: t("sourceResources.form.type"),
    min: 150,
    max: 280,
  },
  {
    key: "status" as const,
    label: t("sourceResources.status.label"),
    min: 140,
    max: 260,
  },
  {
    key: "bound_node" as const,
    label: t("sourceResources.boundNode"),
    min: 190,
    max: 420,
  },
  {
    key: "connection" as const,
    label: t("sourceResources.connection"),
    min: 240,
    max: 560,
  },
  {
    key: "capacity" as const,
    label: t("sourceResources.capacity"),
    min: 220,
    max: 380,
  },
  {
    key: "updated_at" as const,
    label: t("common.updatedAt"),
    min: 180,
    max: 320,
  },
  {
    key: "actions" as const,
    label: t("common.actions"),
    min: 160,
    max: 260,
    sortable: false,
    align: "right" as const,
  },
]);

const sourceResourceTable = useResizableSortableTable<
  SourceResource,
  SourceResourceColumnKey
>({
  storageKey: "hyperfilelens:source-resources:columnWidths",
  columns: sourceResourceColumns,
  rows: paginatedResources,
  defaultSort: { key: "name" },
  minTableWidth: 1200,
  getSortValue: (resource, key) => {
    if (key === "bound_node") return resource.bound_node?.name || "";
    if (key === "connection") return getSourceConnection(resource);
    if (key === "capacity") return getUsagePercent(resource);
    if (key === "updated_at") {
      return resource.updated_at ? new Date(resource.updated_at).getTime() : 0;
    }
    if (key === "actions") return "";
    return (resource as any)[key] ?? "";
  },
  getColumnText: (resource, key) => {
    if (key === "bound_node") return resource.bound_node?.name || "-";
    if (key === "connection") return getSourceConnection(resource);
    if (key === "capacity") return getCapacityText(resource);
    if (key === "updated_at") return formatDate(resource.updated_at);
    if (key === "actions") return t("common.actions");
    return String((resource as any)[key] ?? "");
  },
});

const selectedResourceConfigRows = computed(() => {
  const resource = selectedResource.value;
  if (!resource) return [];
  const config = resource.config || {};
  const credentials = resource.credentials || {};
  const rows: Array<{ label: string; value: string }> = [];

  if (resource.resource_type === "local") {
    rows.push({
      label: t("sourceResources.form.path"),
      value: config.root_path || config.path || "-",
    });
  } else if (["nas", "nfs", "cifs"].includes(resource.resource_type)) {
    rows.push(
      {
        label: t("sourceResources.form.server"),
        value: config.server || "-",
      },
      {
        label:
          resource.resource_type === "cifs"
            ? t("sourceResources.form.share")
            : t("sourceResources.form.exportPath"),
        value: config.share || config.export_path || "-",
      },
      {
        label: t("sourceResources.form.mountOptions"),
        value: config.mount_options || "-",
      },
      {
        label: t("sourceResources.form.username"),
        value: credentials.username || "-",
      },
    );
  } else if (resource.resource_type === "s3") {
    rows.push(
      {
        label: t("sourceResources.form.endpoint"),
        value: config.endpoint || "-",
      },
      {
        label: t("sourceResources.form.bucket"),
        value: config.bucket || "-",
      },
      {
        label: t("sourceResources.form.region"),
        value: config.region || "-",
      },
      {
        label: t("sourceResources.form.prefix"),
        value: config.prefix || "-",
      },
      {
        label: t("sourceResources.form.accessKey"),
        value: maskValue(credentials.access_key),
      },
    );
  }

  return rows;
});

const selectedResourceStatsRows = computed(() => {
  const resource = selectedResource.value;
  if (!resource) return [];
  return [
    {
      label: t("sourceResources.connection"),
      value: getSourceConnection(resource),
    },
    {
      label: t("sourceResources.details.totalSize"),
      value: formatBytes(resource.total_size),
    },
    {
      label: t("sourceResources.details.usedSize"),
      value: formatBytes(resource.used_size),
    },
    {
      label: t("sourceResources.details.freeSize"),
      value: formatBytes(resource.free_size),
    },
    {
      label: t("sourceResources.details.usage"),
      value: resource.total_size
        ? `${getUsagePercent(resource).toFixed(1)}%`
        : "-",
    },
    {
      label: t("sourceResources.details.fileCount"),
      value: String(resource.file_count ?? 0),
    },
    {
      label: t("sourceResources.lastConnectionTest"),
      value: formatDate(resource.last_connection_test),
    },
    {
      label: t("common.createdAt"),
      value: formatDate(resource.created_at),
    },
    {
      label: t("common.updatedAt"),
      value: formatDate(resource.updated_at),
    },
  ];
});

const resourceTypes: { value: ResourceType; label: string }[] = [
  { value: "nas", label: "NAS Storage" },
  { value: "nfs", label: "NFS Share" },
  { value: "cifs", label: "CIFS/SMB Share" },
  { value: "s3", label: "Amazon S3" },
  { value: "azure", label: "Azure Blob" },
  { value: "gcs", label: "Google Cloud Storage" },
  { value: "local", label: "Local Filesystem" },
];

function normalizeResource(resource: any): SourceResource {
  return {
    ...resource,
    total_size: resource.total_size ?? 0,
    used_size: resource.used_size ?? 0,
    free_size: resource.free_size ?? 0,
    usage_percentage: resource.usage_percentage ?? 0,
    bound_node:
      resource.bound_node && typeof resource.bound_node === "object"
        ? resource.bound_node
        : resource.bound_node
          ? {
              id: resource.bound_node,
              name: resource.bound_node_name || resource.bound_node,
              hostname: "",
              status: resource.bound_node_status || "",
            }
          : null,
  };
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString();
}

function formatBytes(bytes?: number | null): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unit]}`;
}

function getSourceConnection(resource: SourceResource): string {
  const config = resource.config || {};
  if (resource.resource_type === "local") {
    return config.root_path || config.path || "-";
  }
  if (resource.resource_type === "s3") {
    return config.bucket || "-";
  }
  if (["nas", "nfs", "cifs"].includes(resource.resource_type)) {
    const server = config.server || "";
    const path = config.export_path || config.share || "";
    if (server && path) return `${server}:${path}`;
    return server || path || "-";
  }
  return config.path || config.endpoint || "-";
}

function getUsagePercent(resource: SourceResource): number {
  if (
    typeof resource.usage_percentage === "number" &&
    resource.usage_percentage > 0
  ) {
    return Math.min(100, Math.max(0, resource.usage_percentage));
  }
  if (!resource.total_size) return 0;
  return Math.min(
    100,
    Math.max(0, (resource.used_size / resource.total_size) * 100),
  );
}

function getCapacityText(resource: SourceResource): string {
  if (!resource.total_size) return "-";
  return `${formatBytes(resource.used_size)} / ${formatBytes(resource.total_size)}`;
}

function maskValue(value?: string) {
  if (!value) return "-";
  if (value.length <= 8) return "****";
  return `${value.slice(0, 4)}****${value.slice(-4)}`;
}

function getResourceIcon(type: ResourceType) {
  switch (type) {
    case "nas":
      return ServerIcon;
    case "nfs":
    case "cifs":
      return FolderIcon;
    case "s3":
    case "azure":
    case "gcs":
      return CloudIcon;
    case "local":
      return ComputerDesktopIcon;
    default:
      return FolderIcon;
  }
}

async function fetchData() {
  loading.value = true;
  error.value = null;
  try {
    const [resourcesRes, statsRes, nodesRes] = await Promise.all([
      sourceResourcesApi.list(),
      sourceResourcesApi.stats(),
      nodesApi.list({ page_size: 100 }),
    ]);
    const rawResources = resourcesRes.data.results || resourcesRes.data;
    resources.value = rawResources.map(normalizeResource);
    stats.value = statsRes.data;
    nodes.value = nodesRes.data.results || nodesRes.data;
  } catch (e: any) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

function openCreateModal() {
  selectedResource.value = null;
  showResourceWizard.value = true;
}

async function openDetailModal(resource: SourceResource) {
  selectedResource.value = resource;
  showDetailModal.value = true;
  try {
    const response = await sourceResourcesApi.detail(resource.id);
    selectedResource.value = normalizeResource(response.data);
  } catch {
    // Keep list data visible if detail loading fails.
  }
}

function openEditModal(resource: SourceResource) {
  selectedResource.value = resource;
  showResourceWizard.value = true;
}

function openDeleteModal(resource: SourceResource) {
  selectedResource.value = resource;
  showDeleteModal.value = true;
}

async function saveResourceFromWizard(payload: Record<string, any>) {
  try {
    if (selectedResource.value) {
      const updatePayload = { ...payload };
      delete updatePayload.resource_type;
      if (
        updatePayload.credentials &&
        Object.keys(updatePayload.credentials).length === 0
      ) {
        delete updatePayload.credentials;
      }
      await sourceResourcesApi.update(selectedResource.value.id, updatePayload);
      appStore.success(t("common.save"));
    } else {
      await sourceResourcesApi.create(payload);
      appStore.success(t("common.create"));
    }
    showResourceWizard.value = false;
    selectedResource.value = null;
    fetchData();
  } catch (e: any) {
    error.value = getApiErrorMessage(e, t("common.saveFailed"));
    appStore.showToast({
      type: "error",
      title: t("common.error"),
      message: error.value,
    });
  }
}

async function deleteResource() {
  if (!selectedResource.value) return;
  try {
    await sourceResourcesApi.delete(selectedResource.value.id);
    showDeleteModal.value = false;
    selectedResource.value = null;
    fetchData();
  } catch (e: any) {
    error.value = e.message;
  }
}

async function testConnection(resource: SourceResource) {
  try {
    const res = await sourceResourcesApi.testConnection(resource.id);
    if (res.data.success) {
      appStore.success(
        res.data.message || t("sourceResources.wizard.draftCheckPassed"),
      );
    } else {
      appStore.error(
        res.data.message || t("sourceResources.wizard.draftCheckFailed"),
      );
    }
    fetchData();
  } catch (e: any) {
    appStore.error(
      getApiErrorMessage(e, t("sourceResources.wizard.draftCheckFailed")),
    );
  }
}

onMounted(fetchData);
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">
          {{ t("sourceResources.title") }}
        </h1>
        <p class="mt-1 text-sm text-foreground-secondary dark:text-slate-400">
          {{ t("sourceResources.subtitle") }}
        </p>
      </div>
      <button
        class="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700"
        @click="openCreateModal"
      >
        <PlusIcon class="h-5 w-5" />
        {{ t("sourceResources.addResource") }}
      </button>
    </div>

    <SourceResourceStatsCards :stats="stats" />

    <SourceResourceToolbar
      v-model:search-query="searchQuery"
      v-model:type-filter="typeFilter"
      v-model:status-filter="statusFilter"
      v-model:view-mode="viewMode"
      :resource-types="resourceTypes"
      @refresh="fetchData"
    />

    <div v-if="loading" class="flex items-center justify-center py-12">
      <div
        class="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600"
      />
    </div>

    <div
      v-else-if="filteredResources.length === 0"
      class="rounded-xl border border-border bg-card p-12 text-center"
    >
      <div
        class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-background-tertiary"
      >
        <ServerIcon class="h-8 w-8 text-slate-400" />
      </div>
      <h3 class="mb-1 text-lg font-medium text-foreground">
        {{ t("sourceResources.noResources") }}
      </h3>
      <p class="text-foreground-secondary">
        {{ t("sourceResources.noResourcesDesc") }}
      </p>
    </div>

    <SourceResourceCardView
      v-else-if="viewMode === 'card'"
      :resources="paginatedResources"
      :get-resource-icon="getResourceIcon"
      :get-source-connection="getSourceConnection"
      :get-usage-percent="getUsagePercent"
      :format-bytes="formatBytes"
      @detail="openDetailModal"
      @edit="openEditModal"
      @delete="openDeleteModal"
      @test="testConnection"
    />

    <SourceResourceListView
      v-else
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :resources="sourceResourceTable.sortedRows.value"
      :columns="sourceResourceColumns"
      :table="sourceResourceTable"
      :total-items="filteredResources.length"
      :get-resource-icon="getResourceIcon"
      :get-source-connection="getSourceConnection"
      :get-usage-percent="getUsagePercent"
      :get-capacity-text="getCapacityText"
      :format-date="formatDate"
      @detail="openDetailModal"
      @edit="openEditModal"
      @delete="openDeleteModal"
      @test="testConnection"
    />

    <Pagination
      v-if="filteredResources.length > 0 && viewMode === 'card'"
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total-items="filteredResources.length"
    />

    <SourceResourceWizard
      v-if="showResourceWizard"
      :nodes="nodes"
      :model-value="selectedResource"
      @close="
        showResourceWizard = false;
        selectedResource = null;
      "
      @save="saveResourceFromWizard"
    />

    <SourceResourceDetailModal
      v-if="showDetailModal && selectedResource"
      :resource="selectedResource"
      :config-rows="selectedResourceConfigRows"
      :stats-rows="selectedResourceStatsRows"
      :get-resource-icon="getResourceIcon"
      :get-usage-percent="getUsagePercent"
      :get-capacity-text="getCapacityText"
      @close="showDetailModal = false"
    />

    <SourceResourceDeleteModal
      v-if="showDeleteModal && selectedResource"
      :resource="selectedResource"
      @close="showDeleteModal = false"
      @confirm="deleteResource"
    />
  </div>
</template>
