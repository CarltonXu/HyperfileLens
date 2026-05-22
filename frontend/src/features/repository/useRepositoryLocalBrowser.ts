import { ref, type ComputedRef, type Ref } from "vue";
import { nodesApi } from "@/api";
import { getApiErrorMessage } from "@/utils/errors";
import type { ProxyNode } from "@/types/proxy";

type Translate = (key: string, params?: Record<string, any>) => string;
type AppStore = {
  success: (message: string) => void;
  error: (message: string) => void;
};

type RepositoryDraft = {
  bound_node: string | null;
  local_config: {
    path: string;
  };
};

export function useRepositoryLocalBrowser(options: {
  t: Translate;
  appStore: AppStore;
  newRepo: Ref<RepositoryDraft>;
  formErrors: Ref<Record<string, string>>;
  availableSyncProxies: ComputedRef<ProxyNode[]>;
  clearError: (field: string) => void;
}) {
  const { t, appStore, newRepo, formErrors, availableSyncProxies, clearError } =
    options;

  const selectedProxy = ref<ProxyNode | null>(null);
  const proxyDirectories = ref<string[]>([]);
  const isLoadingDirectories = ref(false);
  const currentPath = ref("");
  const checkingLocalPath = ref(false);
  const localPathCheckResult = ref<{
    success: boolean;
    path?: string;
    message?: string;
    error?: string;
    exists?: boolean;
    writable?: boolean;
    write_test?: Record<string, any>;
    space_info?: Record<string, any>;
  } | null>(null);

  async function fetchProxyDirectories(proxyId: string, path: string = "/") {
    if (!proxyId) return;
    isLoadingDirectories.value = true;
    try {
      const response = await nodesApi.getDirectories(proxyId, path);
      proxyDirectories.value = response.data.directories || [];
      currentPath.value = path;
    } catch (error) {
      console.error("Failed to fetch directories:", error);
      proxyDirectories.value = [];
      appStore.error(getApiErrorMessage(error));
    } finally {
      isLoadingDirectories.value = false;
    }
  }

  function handleProxySelect(proxyId: string) {
    newRepo.value.bound_node = proxyId;
    localPathCheckResult.value = null;
    selectedProxy.value =
      availableSyncProxies.value.find((proxy) => proxy.id === proxyId) || null;
    if (proxyId) {
      fetchProxyDirectories(proxyId, "/");
    } else {
      proxyDirectories.value = [];
      currentPath.value = "";
    }
  }

  function navigateToDirectory(dir: string) {
    const newPath =
      currentPath.value === "/" ? `/${dir}` : `${currentPath.value}/${dir}`;
    fetchProxyDirectories(newRepo.value.bound_node!, newPath);
  }

  function navigateUp() {
    if (currentPath.value === "/" || !currentPath.value) return;
    const parts = currentPath.value.split("/").filter(Boolean);
    parts.pop();
    const newPath = parts.length === 0 ? "/" : "/" + parts.join("/");
    fetchProxyDirectories(newRepo.value.bound_node!, newPath);
  }

  function selectCurrentPath() {
    newRepo.value.local_config.path = currentPath.value;
    localPathCheckResult.value = null;
    clearError("path");
  }

  async function checkLocalPath() {
    const proxyId = newRepo.value.bound_node;
    const path = newRepo.value.local_config.path.trim();
    if (!proxyId) {
      formErrors.value.bound_node = t("repository.validation.proxyRequired");
      return;
    }
    if (!path) {
      formErrors.value.path = t("repository.validation.pathRequired");
      return;
    }

    checkingLocalPath.value = true;
    localPathCheckResult.value = null;
    clearError("path");
    try {
      const response = await nodesApi.verifyPath(proxyId, path);
      localPathCheckResult.value = response.data;
      if (response.data.success === false || response.data.writable === false) {
        appStore.error(
          response.data.message ||
            response.data.error ||
            t("repository.local.pathCheckFailed"),
        );
      } else {
        appStore.success(t("repository.local.pathCheckSuccess"));
      }
    } catch (error: any) {
      const message =
        error.response?.data?.message ||
        error.response?.data?.error ||
        getApiErrorMessage(error);
      localPathCheckResult.value = {
        success: false,
        path,
        error: message,
      };
      appStore.error(`${t("repository.local.pathCheckFailed")}: ${message}`);
    } finally {
      checkingLocalPath.value = false;
    }
  }

  function resetLocalBrowser() {
    selectedProxy.value = null;
    proxyDirectories.value = [];
    currentPath.value = "";
    localPathCheckResult.value = null;
  }

  return {
    selectedProxy,
    proxyDirectories,
    isLoadingDirectories,
    currentPath,
    checkingLocalPath,
    localPathCheckResult,
    fetchProxyDirectories,
    handleProxySelect,
    navigateToDirectory,
    navigateUp,
    selectCurrentPath,
    checkLocalPath,
    resetLocalBrowser,
  };
}
