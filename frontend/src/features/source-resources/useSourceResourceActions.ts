import { ref, type Ref } from "vue";
import { nodesApi, sourceResourcesApi } from "@/api";
import { getApiErrorMessage } from "@/utils/errors";
import type {
  SourceResource,
  SourceResourceStats,
} from "@/types/sourceResource";

type Translate = (key: string, params?: Record<string, any>) => string;
type AppStore = {
  success: (message: string) => void;
  error: (message: string) => void;
  showToast: (toast: {
    type: "error" | "success" | "warning" | "info";
    title: string;
    message?: string;
  }) => string;
};

export function normalizeSourceResource(resource: any): SourceResource {
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

export function useSourceResourceActions(options: {
  t: Translate;
  appStore: AppStore;
  resources: Ref<SourceResource[]>;
  stats: Ref<SourceResourceStats | null>;
  nodes: Ref<any[]>;
  selectedResource: Ref<SourceResource | null>;
}) {
  const { t, appStore, resources, stats, nodes, selectedResource } = options;
  const loading = ref(false);
  const error = ref<string | null>(null);
  const showDetailModal = ref(false);
  const showDeleteModal = ref(false);
  const showResourceWizard = ref(false);

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
      resources.value = rawResources.map(normalizeSourceResource);
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
      selectedResource.value = normalizeSourceResource(response.data);
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
        await sourceResourcesApi.update(
          selectedResource.value.id,
          updatePayload,
        );
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

  return {
    loading,
    error,
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
  };
}
