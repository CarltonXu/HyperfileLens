import { ref } from "vue";
import { repositoriesApi } from "@/api";
import { getApiErrorMessage } from "@/utils/errors";
import type { Repository } from "@/types/repository";

type Translate = (key: string, params?: Record<string, any>) => string;
type AppStore = {
  success: (message: string) => void;
  error: (message: string, details?: string) => void;
};

export function useRepositoryActions(options: {
  t: Translate;
  appStore: AppStore;
  fetchRepositories: () => Promise<void>;
}) {
  const { t, appStore, fetchRepositories } = options;

  const showTestResultModal = ref(false);
  const selectedTestResult = ref<{
    success: boolean;
    message: string;
    details?: any;
  } | null>(null);
  const testingConnection = ref<string | null>(null);
  const connectionTestResult = ref<
    Record<string, { success: boolean; message: string; details?: any }>
  >({});

  async function deleteRepository(repo: Repository) {
    if (!confirm(t("repository.confirmDelete"))) return;
    try {
      await repositoriesApi.delete(repo.id);
      await fetchRepositories();
      appStore.success(t("repository.deleteSuccess"));
    } catch (error) {
      console.error("Failed to delete repository:", error);
      appStore.error(t("repository.deleteFailed"));
    }
  }

  async function syncUsage(repo: Repository) {
    try {
      const response = await repositoriesApi.syncUsage(repo.id);
      if (response.data.success) {
        const usage = response.data.usage;
        console.log(
          `[Usage Sync] ${repo.name}: ${usage.object_count} objects, ${usage.total_size_gb} GB`,
        );
        await fetchRepositories();
      }
    } catch (error: any) {
      console.error("Failed to sync usage:", error);
    }
  }

  async function testConnection(repo: Repository) {
    testingConnection.value = repo.id;
    connectionTestResult.value[repo.id] = { success: false, message: "" };

    try {
      const response = await repositoriesApi.testConnection(repo.id);
      const result = response.data;

      connectionTestResult.value[repo.id] = {
        success: result.success,
        message: result.message,
        details: result.details,
      };

      if (result.success) {
        let detailsMsg = result.message;
        const details = result.details || {};

        if (details.connectivity) {
          const conn = details.connectivity;
          detailsMsg += ` | Response time: ${conn.response_time || 0}ms`;
        }

        if (details.write_test) {
          const write = details.write_test;
          if (write.writable !== undefined) {
            detailsMsg += ` | Writable: ${write.writable ? "Yes" : "No"}`;
          }
          if (write.write_speed) {
            detailsMsg += ` | Write speed: ${write.write_speed} MB/s`;
          }
          if (write.read_speed) {
            detailsMsg += ` | Read speed: ${write.read_speed} MB/s`;
          }
        }

        if (details.space_info) {
          const space = details.space_info;
          const totalGB = (space.total_bytes / 1024 / 1024 / 1024).toFixed(2);
          const usedGB = (space.used_bytes / 1024 / 1024 / 1024).toFixed(2);
          const freeGB = (space.free_bytes / 1024 / 1024 / 1024).toFixed(2);
          detailsMsg += ` | Total: ${totalGB}GB | Used: ${usedGB}GB | Free: ${freeGB}GB`;
        }

        appStore.success(t("repository.connectionTestSuccess"));

        if (
          details &&
          (details.connectivity || details.write_test || details.space_info)
        ) {
          selectedTestResult.value = {
            success: true,
            message: result.message,
            details,
          };
          showTestResultModal.value = true;
        }

        console.log("[Test Connection] Details:", details);

        if (repo.repo_type === "s3") {
          syncUsage(repo);
        }
      } else {
        appStore.error(
          `${t("repository.connectionTestFailed")}: ${result.message}`,
        );
      }

      await fetchRepositories();
    } catch (error: any) {
      console.error("Connection test failed:", error);
      const errorData = error.response?.data || {};
      const errorMsg =
        errorData.message ||
        errorData.detail ||
        error.message ||
        t("common.unknownError");
      const errorCode = errorData.error_code || "";

      connectionTestResult.value[repo.id] = {
        success: false,
        message: errorMsg,
      };

      let displayMsg = errorMsg;
      if (errorCode === "NO_BOUND_NODE") {
        displayMsg = t("repository.errors.noBoundNode");
      } else if (errorCode === "NODE_NOT_ACTIVE") {
        displayMsg = t("repository.errors.nodeNotActive");
      } else if (errorCode === "MISSING_CONFIG") {
        displayMsg = t("repository.errors.missingConfig");
      } else if (errorCode === "ENDPOINT_UNREACHABLE") {
        displayMsg = t("repository.errors.endpointUnreachable");
      } else if (errorCode === "CONNECTION_TIMEOUT") {
        displayMsg = t("repository.errors.connectionTimeout");
      }

      appStore.error(`${t("repository.connectionTestFailed")}: ${displayMsg}`);
    } finally {
      testingConnection.value = null;
    }
  }

  async function initKopia(repo: Repository) {
    if (!confirm(t("repository.confirmInitKopia"))) return;

    const encryptionPassword = window.prompt(
      t("repository.encryptionPasswordPrompt"),
    );
    if (!encryptionPassword) {
      appStore.error(t("repository.validation.passwordRequired"));
      return;
    }

    const confirmPassword = window.prompt(t("repository.confirmPasswordPrompt"));
    if (encryptionPassword !== confirmPassword) {
      appStore.error(t("repository.passwordMismatch"));
      return;
    }

    try {
      await repositoriesApi.initKopia(repo.id, {
        encryption_password: encryptionPassword,
        confirm_password: confirmPassword || "",
      });
      appStore.success(t("repository.kopiaInitializationStarted"));
      await fetchRepositories();
    } catch (error: any) {
      console.error("Failed to initialize Kopia:", error);
      const data = error.response?.data;
      const errorMsg =
        data?.message ||
        data?.detail ||
        data?.error ||
        Object.values(data || {})
          .flat()
          .join(", ") ||
        error.message;
      appStore.error(`${t("repository.kopiaInitFailed")}: ${errorMsg}`);
    }
  }

  async function saveKopiaPassword(repo: Repository) {
    const encryptionPassword = window.prompt(
      t("repository.encryptionPasswordPrompt"),
    );
    if (!encryptionPassword) {
      appStore.error(t("repository.validation.passwordRequired"));
      return;
    }

    const confirmPassword = window.prompt(t("repository.confirmPasswordPrompt"));
    if (encryptionPassword !== confirmPassword) {
      appStore.error(t("repository.passwordMismatch"));
      return;
    }

    try {
      await repositoriesApi.saveKopiaPassword(repo.id, {
        encryption_password: encryptionPassword,
        confirm_password: confirmPassword || "",
      });
      appStore.success(t("repository.kopiaPasswordSaved"));
      await fetchRepositories();
    } catch (error: any) {
      console.error("Failed to save Kopia password:", error);
      appStore.error(
        getApiErrorMessage(error, t("repository.kopiaPasswordSaveFailed")),
      );
    }
  }

  function resetConnectionResults() {
    connectionTestResult.value = {};
  }

  return {
    showTestResultModal,
    selectedTestResult,
    testingConnection,
    connectionTestResult,
    deleteRepository,
    testConnection,
    initKopia,
    saveKopiaPassword,
    syncUsage,
    resetConnectionResults,
  };
}
