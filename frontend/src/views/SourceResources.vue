<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { PlusIcon } from "@heroicons/vue/24/outline";
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
import { useSourceResourceActions } from "@/features/source-resources/useSourceResourceActions";
import { useSourceResourceFormatting } from "@/features/source-resources/useSourceResourceFormatting";
import type {
  ResourceType,
  SourceResource,
  SourceResourceStats,
} from "@/types/sourceResource";

const { t } = useI18n();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();

const resources = ref<SourceResource[]>([]);
const stats = ref<SourceResourceStats | null>(null);
const nodes = ref<any[]>([]);

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

const selectedResource = ref<SourceResource | null>(null);

const {
  formatDate,
  formatBytes,
  getSourceConnection,
  getUsagePercent,
  getCapacityText,
  getResourceIcon,
  selectedResourceConfigRows,
  selectedResourceStatsRows,
} = useSourceResourceFormatting(t, selectedResource);

const {
  loading,
  showDetailModal,
  showDeleteModal,
  showResourceWizard,
  fetchData,
  openCreateModal,
  openDetailModal,
  openEditModal,
  openDeleteModal,
  saveResourceFromWizard,
  deleteResource,
  testConnection,
} = useSourceResourceActions({
  t,
  appStore,
  resources,
  stats,
  nodes,
  selectedResource,
});

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

const resourceTypes: { value: ResourceType; label: string }[] = [
  { value: "nas", label: "NAS Storage" },
  { value: "nfs", label: "NFS Share" },
  { value: "cifs", label: "CIFS/SMB Share" },
  { value: "s3", label: "Amazon S3" },
  { value: "azure", label: "Azure Blob" },
  { value: "gcs", label: "Google Cloud Storage" },
  { value: "local", label: "Local Filesystem" },
];

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
        data-tour="source-create-button"
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
