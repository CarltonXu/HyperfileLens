<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";
import { repositoriesApi, nodesApi } from "@/api";
import { useAppStore } from "@/stores/app";
import { getApiErrorMessage } from "@/utils/errors";
import type { Repository } from "@/types/repository";
import type { ProxyNode } from "@/types/proxy";
import RepositoryCardView from "@/components/repository/RepositoryCardView.vue";
import RepositoryDetailModal from "@/components/repository/RepositoryDetailModal.vue";
import RepositoryFormModal from "@/components/repository/RepositoryFormModal.vue";
import RepositoryListView from "@/components/repository/RepositoryListView.vue";
import RepositoryStats from "@/components/repository/RepositoryStats.vue";
import RepositoryTestResultModal from "@/components/repository/RepositoryTestResultModal.vue";
import RepositoryToolbar from "@/components/repository/RepositoryToolbar.vue";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import { useRepositoryFormatting } from "@/features/repository/useRepositoryFormatting";
import { useRepositoryLocalBrowser } from "@/features/repository/useRepositoryLocalBrowser";
import { useRepositoryS3Buckets } from "@/features/repository/useRepositoryS3Buckets";
import { useRepositoryActions } from "@/features/repository/useRepositoryActions";
import {
  PlusIcon,
  CloudIcon,
  ServerIcon,
  FolderIcon,
} from "@heroicons/vue/24/outline";

const { t } = useI18n();
const route = useRoute();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();
const VIEW_MODE_STORAGE_KEY = "hyperfilelens:repository:viewMode";

function getStoredViewMode(): "card" | "list" {
  try {
    const stored = localStorage.getItem(VIEW_MODE_STORAGE_KEY);
    return stored === "list" || stored === "card" ? stored : "card";
  } catch {
    return "card";
  }
}

const isLoading = ref(true);
const repositories = ref<Repository[]>([]);
const nodes = ref<ProxyNode[]>([]);
const {
  formatBytes,
  getProgressColor,
  getRepoTypeIcon,
  getRepoTypeColor,
  getRepoTypeLabel,
  getNodeName,
  getNode,
  getNodeStatus,
} = useRepositoryFormatting(t, nodes);
const searchQuery = ref("");
const typeFilter = ref("");
const showCreateModal = ref(false);
const showDetailModal = ref(false);
const selectedRepo = ref<Repository | null>(null);
const isEditMode = ref(false);
const editingRepoId = ref<string | null>(null);
const creatingBucket = ref(false);

// View mode
const viewMode = ref<"card" | "list">(getStoredViewMode());

// Pagination
const currentPage = ref(1);
const pageSize = ref(getPageSize("repository"));
const PAGE_STORAGE_KEY = "repository";

// Watch for page size changes and save to localStorage
watch(pageSize, (newSize) => {
  setPageSize(newSize, PAGE_STORAGE_KEY);
});

// Repository type selection
const repoTypes = computed(() => [
  {
    value: "s3",
    label: t("repository.types.s3"),
    icon: CloudIcon,
    color: "orange",
  },
  {
    value: "nas",
    label: t("repository.types.nas"),
    icon: ServerIcon,
    color: "purple",
  },
  {
    value: "local",
    label: t("repository.types.local"),
    icon: FolderIcon,
    color: "blue",
  },
]);

// New repository form
const newRepo = ref({
  name: "",
  repo_type: "s3" as "s3" | "nas" | "local",
  description: "",
  // Quota management (user-defined for capacity planning and alerts)
  quota: 0 as number, // 用户配额，单位 GB，0 表示无限制
  quota_enabled: false, // 是否启用配额监控
  quota_warning_threshold: 80, // 告警阈值（百分比）
  bound_node: "" as string | null,
  // S3 config
  s3_config: {
    endpoint: "",
    bucket: "",
    region: "",
    prefix: "",
    access_key: "",
    secret_key: "",
    use_tls: true,
    url_style: "virtual" as "virtual" | "path", // URL 访问风格：virtual (Virtual Hosted) 或 path (Path Style)
    bucket_mode: "existing" as "existing" | "new", // 选择已有或新建
  },
  // NAS config
  nas_config: {
    server: "",
    export_path: "",
    mount_type: "nfs" as "nfs" | "cifs",
    mount_options: "",
    username: "",
    password: "",
  },
  // Local config
  local_config: {
    path: "",
  },
});

// Form validation errors
const formErrors = ref<Record<string, string>>({});

// Validate form before submission
function validateForm(): boolean {
  formErrors.value = {};

  // Name is required
  if (!newRepo.value.name.trim()) {
    formErrors.value.name = t("repository.validation.nameRequired");
  }

  // Validate based on repository type
  if (newRepo.value.repo_type === "s3") {
    if (!newRepo.value.s3_config.endpoint.trim()) {
      formErrors.value.endpoint = t("repository.validation.endpointRequired");
    }
    if (!newRepo.value.s3_config.bucket.trim()) {
      formErrors.value.bucket = t("repository.validation.bucketRequired");
    }
    if (!newRepo.value.s3_config.access_key.trim()) {
      formErrors.value.access_key = t(
        "repository.validation.accessKeyRequired",
      );
    }
    if (!newRepo.value.s3_config.secret_key.trim()) {
      formErrors.value.secret_key = t(
        "repository.validation.secretKeyRequired",
      );
    }
    if (!newRepo.value.bound_node) {
      formErrors.value.bound_node = t("repository.validation.proxyRequired");
    }
  } else if (newRepo.value.repo_type === "nas") {
    if (!newRepo.value.nas_config.server.trim()) {
      formErrors.value.server = t("repository.validation.serverRequired");
    }
    if (!newRepo.value.nas_config.export_path.trim()) {
      formErrors.value.export_path = t(
        "repository.validation.exportPathRequired",
      );
    }
    if (newRepo.value.nas_config.mount_type === "cifs") {
      if (!newRepo.value.nas_config.username.trim()) {
        formErrors.value.username = t("repository.validation.usernameRequired");
      }
      if (!newRepo.value.nas_config.password.trim()) {
        formErrors.value.password = t("repository.validation.passwordRequired");
      }
    }
    if (!newRepo.value.bound_node) {
      formErrors.value.bound_node = t("repository.validation.proxyRequired");
    }
  } else if (newRepo.value.repo_type === "local") {
    if (!newRepo.value.bound_node) {
      formErrors.value.bound_node = t("repository.validation.proxyRequired");
    }
    if (!newRepo.value.local_config.path.trim()) {
      formErrors.value.path = t("repository.validation.pathRequired");
    }
  }

  return Object.keys(formErrors.value).length === 0;
}

// Check if form is valid and complete
const isFormValid = computed(() => {
  // Name is always required
  if (!newRepo.value.name.trim()) return false;

  const type = newRepo.value.repo_type;

  if (type === "s3") {
    return !!(
      newRepo.value.s3_config.endpoint.trim() &&
      newRepo.value.s3_config.bucket.trim() &&
      newRepo.value.s3_config.access_key.trim() &&
      newRepo.value.s3_config.secret_key.trim() &&
      newRepo.value.bound_node
    );
  }

  if (type === "nas") {
    const hasBasic = !!(
      newRepo.value.nas_config.server.trim() &&
      newRepo.value.nas_config.export_path.trim() &&
      newRepo.value.bound_node
    );
    if (newRepo.value.nas_config.mount_type === "cifs") {
      return (
        hasBasic &&
        !!(
          newRepo.value.nas_config.username.trim() &&
          newRepo.value.nas_config.password.trim()
        )
      );
    }
    return hasBasic;
  }

  if (type === "local") {
    return !!(
      newRepo.value.bound_node && newRepo.value.local_config.path.trim()
    );
  }

  return false;
});

// Clear error for a field
function clearError(field: string) {
  delete formErrors.value[field];
}

const {
  s3BucketList,
  isLoadingBuckets,
  bucketListError,
  checkingBucketName,
  bucketNameAvailable,
  bucketNameMessage,
  fetchBucketList,
  checkBucketNameAvailability,
  resetBucketState,
} = useRepositoryS3Buckets({
  t,
  newRepo,
  clearError,
});

// Reset form to initial state
function resetForm() {
  isEditMode.value = false;
  editingRepoId.value = null;
  formErrors.value = {};
  resetConnectionResults();
  resetBucketState();

  // Reset form data
  newRepo.value = {
    name: "",
    repo_type: "s3",
    description: "",
    quota: 0,
    quota_enabled: false,
    quota_warning_threshold: 80,
    bound_node: null,
    s3_config: {
      endpoint: "",
      bucket: "",
      region: "",
      prefix: "",
      access_key: "",
      secret_key: "",
      use_tls: true,
      url_style: "virtual",
      bucket_mode: "existing",
    },
    nas_config: {
      server: "",
      export_path: "",
      mount_type: "nfs",
      mount_options: "",
      username: "",
      password: "",
    },
    local_config: {
      path: "",
    },
  };

  // Reset local directory browsing
  resetLocalBrowser();
}

// Available Sync Proxies (online + sync role)
const availableSyncProxies = computed(() => {
  return nodes.value.filter(
    (node) => node.role === "sync" && node.status === "online",
  );
});

const {
  proxyDirectories,
  isLoadingDirectories,
  currentPath,
  checkingLocalPath,
  localPathCheckResult,
  handleProxySelect,
  navigateToDirectory,
  navigateUp,
  selectCurrentPath,
  checkLocalPath,
  resetLocalBrowser,
} = useRepositoryLocalBrowser({
  t,
  appStore,
  newRepo,
  formErrors,
  availableSyncProxies,
  clearError,
});

const filteredRepos = computed(() => {
  let result = repositories.value;
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    result = result.filter(
      (r) =>
        r.name.toLowerCase().includes(query) ||
        r.repo_type?.toLowerCase().includes(query),
    );
  }
  if (typeFilter.value) {
    result = result.filter((r) => r.repo_type === typeFilter.value);
  }
  return result;
});

// Paginated repos for display
const paginatedRepos = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredRepos.value.slice(start, end);
});

type RepositoryColumnKey =
  | "name"
  | "repo_type"
  | "status"
  | "connection"
  | "bound_node"
  | "capacity"
  | "kopia_initialized"
  | "actions";

const repositoryColumns = computed(() => [
  {
    key: "name" as const,
    label: t("repository.list.name"),
    min: 260,
    max: 620,
  },
  {
    key: "repo_type" as const,
    label: t("repository.list.type"),
    min: 130,
    max: 240,
  },
  {
    key: "status" as const,
    label: t("repository.list.status"),
    min: 130,
    max: 240,
  },
  {
    key: "connection" as const,
    label: t("repository.list.connection"),
    min: 200,
    max: 420,
  },
  {
    key: "bound_node" as const,
    label: t("repository.list.boundNode"),
    min: 180,
    max: 420,
  },
  {
    key: "capacity" as const,
    label: t("repository.list.capacity"),
    min: 220,
    max: 420,
  },
  {
    key: "kopia_initialized" as const,
    label: t("repository.list.kopia"),
    min: 150,
    max: 260,
  },
  {
    key: "actions" as const,
    label: t("repository.list.actions"),
    min: 180,
    max: 260,
    sortable: false,
    align: "right" as const,
  },
]);

function getRepositoryConnectionText(repo: Repository) {
  if (repo.repo_type === "s3") return repo.config?.bucket || "-";
  if (repo.repo_type === "nas") return repo.config?.server || "-";
  return repo.config?.path || "-";
}

const repositoryTable = useResizableSortableTable<
  Repository,
  RepositoryColumnKey
>({
  storageKey: "hyperfilelens:repository:columnWidths",
  columns: repositoryColumns,
  rows: paginatedRepos,
  defaultSort: { key: "name" },
  minTableWidth: 1200,
  getSortValue: (repo, key) => {
    if (key === "connection") return getRepositoryConnectionText(repo);
    if (key === "bound_node") return getNodeName(repo.bound_node);
    if (key === "capacity") return repo.capacity || 0;
    if (key === "kopia_initialized") return repo.kopia_initialized ? 1 : 0;
    if (key === "actions") return "";
    return (repo as any)[key] ?? "";
  },
  getColumnText: (repo, key) => {
    if (key === "connection") return getRepositoryConnectionText(repo);
    if (key === "bound_node") return getNodeName(repo.bound_node);
    if (key === "capacity") {
      return repo.capacity
        ? `${formatBytes(repo.used_space || 0)} / ${formatBytes(repo.capacity)}`
        : "-";
    }
    if (key === "kopia_initialized") {
      return repo.kopia_initialized ? t("repository.initialized") : "-";
    }
    if (key === "actions") return t("repository.list.actions");
    return String((repo as any)[key] ?? "");
  },
});

// Reset page when filters change
watch([searchQuery, typeFilter], () => {
  currentPage.value = 1;
});

watch(viewMode, (mode) => {
  try {
    localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode);
  } catch {
    // Ignore storage errors in private browsing or restricted environments.
  }
});

// Reset local directory browser when leaving local type
watch(
  () => newRepo.value.repo_type,
  () => {
    if (newRepo.value.repo_type !== "local") {
      resetLocalBrowser();
    }
  },
);

const stats = computed(() => {
  const total = repositories.value.length;
  const active = repositories.value.filter((r) => r.status === "active").length;
  const initialized = repositories.value.filter(
    (r) => r.kopia_initialized,
  ).length;
  const totalCapacity = repositories.value.reduce(
    (sum, r) => sum + (r.capacity || 0),
    0,
  );
  const totalUsed = repositories.value.reduce(
    (sum, r) => sum + (r.used_space || 0),
    0,
  );
  return { total, active, initialized, totalCapacity, totalUsed };
});

async function fetchRepositories() {
  isLoading.value = true;
  try {
    const response = await repositoriesApi.list();
    repositories.value = response.data.results || response.data;
  } catch (error) {
    console.error("Failed to fetch repositories:", error);
  } finally {
    isLoading.value = false;
  }
}

async function openRouteDetail() {
  const detailId = route.query.detail;
  if (typeof detailId !== "string") return;
  const existing = repositories.value.find(
    (repo) => String(repo.id) === detailId,
  );
  if (existing) {
    selectedRepo.value = existing;
    showDetailModal.value = true;
    return;
  }

  try {
    const response = await repositoriesApi.detail(detailId);
    selectedRepo.value = response.data;
    showDetailModal.value = true;
  } catch (error) {
    console.error("Failed to open repository detail:", error);
  }
}

async function fetchNodes() {
  try {
    const response = await nodesApi.list();
    nodes.value = response.data.results || response.data;
  } catch (error) {
    console.error("Failed to fetch nodes:", error);
  }
}

const {
  showTestResultModal,
  selectedTestResult,
  testingConnection,
  connectionTestResult,
  deleteRepository,
  testConnection,
  initKopia,
  saveKopiaPassword,
  resetConnectionResults,
} = useRepositoryActions({
  t,
  appStore,
  fetchRepositories,
});

async function createRepository() {
  // Validate form first
  if (!validateForm()) {
    appStore.error(
      t("repository.validation.formInvalid"),
      t("repository.validation.checkFields"),
    );
    return;
  }

  try {
    // If creating a new S3 bucket, create it first
    if (
      newRepo.value.repo_type === "s3" &&
      newRepo.value.s3_config.bucket_mode === "new"
    ) {
      if (!newRepo.value.s3_config.bucket) {
        formErrors.value.bucket = t("repository.s3.bucketNameRequired");
        return;
      }

      creatingBucket.value = true;
      try {
        const createBucketResponse = await repositoriesApi.createBucket({
          endpoint: newRepo.value.s3_config.endpoint,
          bucket_name: newRepo.value.s3_config.bucket,
          region: newRepo.value.s3_config.region,
          access_key: newRepo.value.s3_config.access_key,
          secret_key: newRepo.value.s3_config.secret_key,
          use_tls: newRepo.value.s3_config.use_tls,
        });

        if (!createBucketResponse.data.success) {
          appStore.error(
            `${t("repository.s3.createBucketFailed")}: ${createBucketResponse.data.message}`,
          );
          creatingBucket.value = false;
          return;
        }

        appStore.success(t("repository.s3.createBucketSuccess"));
      } catch (bucketError: any) {
        console.error("Failed to create bucket:", bucketError);
        const errorData = bucketError.response?.data || {};
        const errorMsg =
          errorData.message ||
          errorData.detail ||
          bucketError.message ||
          t("common.unknownError");
        appStore.error(`${t("repository.s3.createBucketFailed")}: ${errorMsg}`);
        creatingBucket.value = false;
        return;
      }
      creatingBucket.value = false;
    }

    let payload: any = {
      name: newRepo.value.name,
      repo_type: newRepo.value.repo_type,
      description: newRepo.value.description,
      quota_enabled: newRepo.value.quota_enabled,
      quota_bytes: newRepo.value.quota
        ? newRepo.value.quota * 1024 * 1024 * 1024
        : 0, // Convert GB to bytes
      quota_warning_threshold: newRepo.value.quota_warning_threshold,
      bound_node: newRepo.value.bound_node || null,
    };

    // Build config based on type
    if (newRepo.value.repo_type === "s3") {
      payload.config = {
        endpoint: newRepo.value.s3_config.endpoint,
        bucket: newRepo.value.s3_config.bucket,
        region: newRepo.value.s3_config.region,
        prefix: newRepo.value.s3_config.prefix,
        use_tls: newRepo.value.s3_config.use_tls,
        url_style: newRepo.value.s3_config.url_style,
      };
      payload.credentials = {
        access_key: newRepo.value.s3_config.access_key,
        secret_key: newRepo.value.s3_config.secret_key,
      };
    } else if (newRepo.value.repo_type === "nas") {
      payload.config = {
        server: newRepo.value.nas_config.server,
        export_path: newRepo.value.nas_config.export_path,
        mount_type: newRepo.value.nas_config.mount_type,
        mount_options: newRepo.value.nas_config.mount_options,
      };
      if (newRepo.value.nas_config.mount_type === "cifs") {
        payload.credentials = {
          username: newRepo.value.nas_config.username,
          password: newRepo.value.nas_config.password,
        };
      }
    } else if (newRepo.value.repo_type === "local") {
      payload.config = {
        path: newRepo.value.local_config.path,
      };
    }

    if (isEditMode.value && editingRepoId.value) {
      await repositoriesApi.update(editingRepoId.value, payload);
      appStore.success(t("repository.updateSuccess"));
    } else {
      await repositoriesApi.create(payload);
      appStore.success(t("repository.createSuccess"));
    }
    showCreateModal.value = false;
    resetForm();
    await fetchRepositories();
  } catch (error: any) {
    console.error("Failed to create repository:", error);
    // Handle backend validation errors
    const errorData = error?.response?.data;
    if (errorData) {
      if (errorData.name) {
        formErrors.value.name = errorData.name[0] || errorData.name;
      }
      if (errorData.config) {
        // Map config errors to specific fields
        const configError = errorData.config;
        if (typeof configError === "string") {
          appStore.error(t("repository.validation.configError"), configError);
        }
      }
      if (errorData.credentials) {
        appStore.error(
          t("repository.validation.credentialsError"),
          errorData.credentials,
        );
      }
      if (errorData.detail || errorData.non_field_errors) {
        appStore.error(
          t("common.error"),
          errorData.detail || errorData.non_field_errors,
        );
      } else if (errorData.error || errorData.message) {
        appStore.error(t("common.error"), errorData.error || errorData.message);
      }
    } else {
      appStore.error(
        isEditMode.value
          ? t("repository.updateFailed")
          : t("repository.createFailed"),
        getApiErrorMessage(error),
      );
    }
  }
}

// 编辑仓库
function openEditModal(repo: Repository) {
  isEditMode.value = true;
  editingRepoId.value = repo.id;

  // 填充基本信息
  newRepo.value.name = repo.name;
  newRepo.value.description = repo.description || "";
  newRepo.value.repo_type = (
    repo.repo_type === "nfs" ? "nas" : repo.repo_type
  ) as "s3" | "nas" | "local";
  // 确保 bound_node 是字符串类型（后端可能返回数字）
  newRepo.value.bound_node = repo.bound_node ? String(repo.bound_node) : null;
  // 回填配额信息，将字节转换为 GB
  newRepo.value.quota = repo.quota_bytes
    ? Math.round(repo.quota_bytes / (1024 * 1024 * 1024))
    : 0;
  newRepo.value.quota_enabled = repo.quota_enabled ?? false;
  newRepo.value.quota_warning_threshold = repo.quota_warning_threshold ?? 80;

  // 根据类型填充配置
  if (repo.repo_type === "s3" && repo.config) {
    newRepo.value.s3_config = {
      endpoint: repo.config.endpoint || "",
      bucket: repo.config.bucket || "",
      region: repo.config.region || "",
      prefix: repo.config.prefix || "",
      access_key: repo.credentials_masked?.access_key || "",
      secret_key: "", // 密钥不回显，需要用户重新输入
      use_tls: repo.config.use_tls !== false,
      url_style: repo.config.url_style || "virtual",
      bucket_mode: "existing" as "existing" | "new",
    };
  } else if (
    (repo.repo_type === "nas" || repo.repo_type === "nfs") &&
    repo.config
  ) {
    newRepo.value.nas_config = {
      server: repo.config.server || "",
      export_path: repo.config.export_path || "",
      mount_type: repo.config.nas_type || "nfs",
      mount_options: repo.config.mount_options || "",
      username: repo.credentials_masked?.username || "",
      password: "", // 密码不回显
    };
  } else if (repo.repo_type === "local" && repo.config) {
    newRepo.value.local_config = {
      path: repo.config.path || "",
    };
  }

  showCreateModal.value = true;
}

watch(
  () => route.query.detail,
  () => {
    openRouteDetail();
  },
);

onMounted(async () => {
  await Promise.all([fetchRepositories(), fetchNodes()]);
  await openRouteDetail();
});
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">
          {{ t("repository.title") }}
        </h1>
        <p class="text-foreground-secondary mt-1">
          {{ t("repository.subtitle") }}
        </p>
      </div>
      <button
        data-tour="repository-create-button"
        @click="showCreateModal = true"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-blue-500 to-cyan-600 rounded-lg hover:from-blue-600 hover:to-cyan-700 transition-all shadow-md hover:shadow-lg"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t("repository.form.addRepository") }}
      </button>
    </div>

    <RepositoryStats :stats="stats" :format-bytes="formatBytes" />

    <RepositoryToolbar
      v-model:search-query="searchQuery"
      v-model:type-filter="typeFilter"
      v-model:view-mode="viewMode"
      @refresh="fetchRepositories"
    />

    <!-- Card View -->
    <RepositoryCardView
      v-if="viewMode === 'card'"
      :loading="isLoading"
      :filtered-count="filteredRepos.length"
      :repositories="paginatedRepos"
      :testing-connection="testingConnection"
      :connection-test-result="connectionTestResult"
      :get-repo-type-color="getRepoTypeColor"
      :get-repo-type-icon="getRepoTypeIcon"
      :get-repo-type-label="getRepoTypeLabel"
      :get-node-name="getNodeName"
      :get-progress-color="getProgressColor"
      :format-bytes="formatBytes"
      @init-kopia="initKopia"
      @save-kopia-password="saveKopiaPassword"
      @test-connection="testConnection"
      @edit="openEditModal"
      @detail="
        (repo) => {
          selectedRepo = repo;
          showDetailModal = true;
        }
      "
      @delete="deleteRepository"
    />

    <!-- List View -->
    <RepositoryListView
      v-else
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :loading="isLoading"
      :filtered-count="filteredRepos.length"
      :columns="repositoryColumns"
      :table="repositoryTable"
      :testing-connection="testingConnection"
      :connection-test-result="connectionTestResult"
      :get-repo-type-color="getRepoTypeColor"
      :get-repo-type-icon="getRepoTypeIcon"
      :get-repo-type-label="getRepoTypeLabel"
      :get-node-name="getNodeName"
      :get-progress-color="getProgressColor"
      :format-bytes="formatBytes"
      @init-kopia="initKopia"
      @save-kopia-password="saveKopiaPassword"
      @test-connection="testConnection"
      @edit="openEditModal"
      @detail="
        (repo) => {
          selectedRepo = repo;
          showDetailModal = true;
        }
      "
      @delete="deleteRepository"
    />

    <RepositoryFormModal
      v-if="showCreateModal"
      :is-edit-mode="isEditMode"
      :new-repo="newRepo"
      :form-errors="formErrors"
      :repo-types="repoTypes"
      :is-form-valid="isFormValid"
      :available-sync-proxies="availableSyncProxies"
      :s3-bucket-list="s3BucketList"
      :is-loading-buckets="isLoadingBuckets"
      :bucket-list-error="bucketListError"
      :checking-bucket-name="checkingBucketName"
      :bucket-name-available="bucketNameAvailable"
      :bucket-name-message="bucketNameMessage"
      :proxy-directories="proxyDirectories"
      :current-path="currentPath"
      :is-loading-directories="isLoadingDirectories"
      :checking-local-path="checkingLocalPath"
      :local-path-check-result="localPathCheckResult"
      :format-bytes="formatBytes"
      @close="showCreateModal = false"
      @reset="resetForm"
      @submit="createRepository"
      @clear-error="clearError"
      @fetch-bucket-list="fetchBucketList"
      @check-bucket-name-availability="checkBucketNameAvailability"
      @handle-proxy-select="handleProxySelect"
      @check-local-path="checkLocalPath"
      @clear-local-path-check="localPathCheckResult = null"
      @navigate-up="navigateUp"
      @navigate-to-directory="navigateToDirectory"
      @select-current-path="selectCurrentPath"
    />

    <RepositoryDetailModal
      v-if="showDetailModal && selectedRepo"
      :repository="selectedRepo"
      :get-repo-type-color="getRepoTypeColor"
      :get-repo-type-icon="getRepoTypeIcon"
      :get-repo-type-label="getRepoTypeLabel"
      :get-progress-color="getProgressColor"
      :get-node-name="getNodeName"
      :get-node="getNode"
      :get-node-status="getNodeStatus"
      :format-bytes="formatBytes"
      @close="showDetailModal = false"
    />

    <RepositoryTestResultModal
      v-if="showTestResultModal"
      :result="selectedTestResult"
      :format-bytes="formatBytes"
      @close="showTestResultModal = false"
    />
  </div>
</template>
