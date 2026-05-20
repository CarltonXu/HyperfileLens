<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { repositoriesApi, nodesApi } from "@/api";
import { useAppStore } from "@/stores/app";
import { getApiErrorMessage } from "@/utils/errors";
import type { Repository } from "@/types/repository";
import type { ProxyNode } from "@/types/proxy";
import RepositoryCardView from "@/components/repository/RepositoryCardView.vue";
import RepositoryDetailModal from "@/components/repository/RepositoryDetailModal.vue";
import RepositoryListView from "@/components/repository/RepositoryListView.vue";
import RepositoryLocalConfigSection from "@/components/repository/RepositoryLocalConfigSection.vue";
import RepositoryNasConfigSection from "@/components/repository/RepositoryNasConfigSection.vue";
import RepositoryS3ConfigSection from "@/components/repository/RepositoryS3ConfigSection.vue";
import RepositoryStats from "@/components/repository/RepositoryStats.vue";
import RepositoryTestResultModal from "@/components/repository/RepositoryTestResultModal.vue";
import RepositoryToolbar from "@/components/repository/RepositoryToolbar.vue";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import {
  PlusIcon,
  CircleStackIcon,
  CloudIcon,
  ServerIcon,
  FolderIcon,
} from "@heroicons/vue/24/outline";

const { t } = useI18n();
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
const searchQuery = ref("");
const typeFilter = ref("");
const showCreateModal = ref(false);
const showDetailModal = ref(false);
const showTestResultModal = ref(false);
const selectedRepo = ref<Repository | null>(null);
const selectedTestResult = ref<{
  success: boolean;
  message: string;
  details?: any;
} | null>(null);
const isEditMode = ref(false);
const editingRepoId = ref<string | null>(null);

// Connection test states
const testingConnection = ref<string | null>(null);
const creatingBucket = ref(false);
const connectionTestResult = ref<
  Record<string, { success: boolean; message: string; details?: any }>
>({});

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

// S3 Bucket related states
const s3BucketList = ref<
  Array<{ name: string; creation_date?: string; size?: number }>
>([]);
const isLoadingBuckets = ref(false);
const bucketListError = ref("");
const checkingBucketName = ref(false);
const bucketNameAvailable = ref<boolean | null>(null);
const bucketNameMessage = ref("");

// Bucket name validation rules (S3 standard)
const BUCKET_NAME_RULES = {
  minLength: 3,
  maxLength: 63,
  // Must start and end with letter or number
  // Can contain lowercase letters, numbers, hyphens, and periods
  pattern: /^[a-z0-9][a-z0-9.-]*[a-z0-9]$|^[a-z0-9]$/,
  // Cannot be IP address format
  ipPattern: /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/,
  // Cannot contain consecutive periods or hyphens next to periods
  consecutivePattern: /\.\.|\.-|-\./,
};

// Validate bucket name according to S3 rules
function validateBucketName(name: string): { valid: boolean; message: string } {
  if (!name) {
    return { valid: false, message: t("repository.s3.bucketNameRequired") };
  }

  if (name.length < BUCKET_NAME_RULES.minLength) {
    return {
      valid: false,
      message: t("repository.s3.bucketNameTooShort", {
        min: BUCKET_NAME_RULES.minLength,
      }),
    };
  }

  if (name.length > BUCKET_NAME_RULES.maxLength) {
    return {
      valid: false,
      message: t("repository.s3.bucketNameTooLong", {
        max: BUCKET_NAME_RULES.maxLength,
      }),
    };
  }

  // Check for valid characters (lowercase letters, numbers, hyphens, periods)
  if (!/^[a-z0-9.-]+$/.test(name)) {
    return { valid: false, message: t("repository.s3.bucketNameInvalidChars") };
  }

  // Check start and end
  if (!/^[a-z0-9]/.test(name) || !/[a-z0-9]$/.test(name)) {
    return { valid: false, message: t("repository.s3.bucketNameStartEnd") };
  }

  // Check for IP address format
  if (BUCKET_NAME_RULES.ipPattern.test(name)) {
    return { valid: false, message: t("repository.s3.bucketNameIPFormat") };
  }

  // Check for consecutive periods or hyphens next to periods
  if (BUCKET_NAME_RULES.consecutivePattern.test(name)) {
    return { valid: false, message: t("repository.s3.bucketNameConsecutive") };
  }

  return { valid: true, message: "" };
}

// Fetch S3 bucket list
async function fetchBucketList() {
  const { endpoint, access_key, secret_key, use_tls } = newRepo.value.s3_config;

  // Check required fields first
  if (!endpoint || !access_key || !secret_key) {
    bucketListError.value = t("repository.s3.fillCredentialsFirst");
    return;
  }

  // Validate endpoint format
  try {
    const url = new URL(endpoint);
    if (!url.hostname) {
      bucketListError.value = t("repository.s3.invalidEndpoint");
      return;
    }
  } catch {
    bucketListError.value = t("repository.s3.invalidEndpoint");
    return;
  }

  isLoadingBuckets.value = true;
  bucketListError.value = "";
  s3BucketList.value = [];

  try {
    const response = await repositoriesApi.listBuckets({
      endpoint,
      region: newRepo.value.s3_config.region || undefined,
      access_key,
      secret_key,
      use_tls,
      filter_by_region: true, // Filter buckets by configured region
    });

    if (response.data.buckets) {
      s3BucketList.value = response.data.buckets;
    }

    // Show suggestion if no buckets match the configured region
    if (response.data.suggestion && response.data.matched_count === 0) {
      bucketListError.value = response.data.suggestion;
    }
  } catch (error: any) {
    console.error("[S3] Failed to fetch bucket list:", error);

    // Handle timeout specifically
    if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
      bucketListError.value = t("repository.s3.connectionTimeout");
      return;
    }

    // Handle network errors
    if (
      error.code === "ERR_NETWORK" ||
      error.message?.includes("Network Error")
    ) {
      bucketListError.value = t("repository.s3.networkError");
      return;
    }

    // Extract detailed error message from backend
    const errorData = error.response?.data || {};
    let errorMessage = t("repository.s3.fetchBucketsFailed");

    if (errorData.message) {
      errorMessage = errorData.message;
    }

    // Add hint if available
    if (errorData.hint) {
      errorMessage += ` ${errorData.hint}`;
    }

    // Add error code for debugging
    if (errorData.error_code) {
      console.error(
        `[S3] Error code: ${errorData.error_code}, HTTP: ${errorData.http_status}`,
      );
      errorMessage += ` (${errorData.error_code})`;
    }

    // Add details
    if (errorData.details) {
      console.error(`[S3] Details: ${errorData.details}`);
    }

    bucketListError.value = errorMessage;
  } finally {
    isLoadingBuckets.value = false;
  }
}

// Check bucket name availability
async function checkBucketNameAvailability() {
  const { endpoint, access_key, secret_key, bucket, use_tls } =
    newRepo.value.s3_config;

  // Validate bucket name format first
  const validation = validateBucketName(bucket);
  if (!validation.valid) {
    bucketNameAvailable.value = false;
    bucketNameMessage.value = validation.message;
    return;
  }

  // Check required fields
  if (!endpoint || !access_key || !secret_key) {
    bucketNameMessage.value = t("repository.s3.fillCredentialsFirst");
    return;
  }

  checkingBucketName.value = true;
  bucketNameMessage.value = "";

  try {
    const response = await repositoriesApi.checkBucketName({
      endpoint,
      region: newRepo.value.s3_config.region || undefined,
      access_key,
      secret_key,
      bucket_name: bucket,
      use_tls,
    });

    bucketNameAvailable.value = response.data.available;
    bucketNameMessage.value = response.data.message;
  } catch (error: any) {
    console.error("[S3] Failed to check bucket name:", error);

    const errorData = error.response?.data || {};
    let errorMessage = t("repository.s3.checkBucketFailed");

    if (errorData.message) {
      errorMessage = errorData.message;
    }

    if (errorData.hint) {
      errorMessage += ` ${errorData.hint}`;
    }

    if (errorData.error_code) {
      console.error(`[S3] Error code: ${errorData.error_code}`);
    }

    bucketNameAvailable.value = false;
    bucketNameMessage.value = errorMessage;
  } finally {
    checkingBucketName.value = false;
  }
}

// Watch bucket mode changes
watch(
  () => newRepo.value.s3_config.bucket_mode,
  () => {
    // Reset bucket related states
    newRepo.value.s3_config.bucket = "";
    s3BucketList.value = [];
    bucketListError.value = "";
    bucketNameAvailable.value = null;
    bucketNameMessage.value = "";
    clearError("bucket");
  },
);

// Watch bucket name changes for new bucket mode
watch(
  () => newRepo.value.s3_config.bucket,
  (newName) => {
    if (newRepo.value.s3_config.bucket_mode === "new") {
      // Reset availability status when name changes
      bucketNameAvailable.value = null;
      bucketNameMessage.value = "";

      // Real-time validation
      if (newName) {
        const validation = validateBucketName(newName);
        if (!validation.valid) {
          bucketNameMessage.value = validation.message;
        }
      }
    }
  },
);

// Watch credentials changes to reset bucket list
watch(
  [
    () => newRepo.value.s3_config.endpoint,
    () => newRepo.value.s3_config.access_key,
    () => newRepo.value.s3_config.secret_key,
  ],
  () => {
    s3BucketList.value = [];
    bucketListError.value = "";
    bucketNameAvailable.value = null;
    bucketNameMessage.value = "";
  },
);

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

// Reset form to initial state
function resetForm() {
  isEditMode.value = false;
  editingRepoId.value = null;
  formErrors.value = {};
  connectionTestResult.value = {};
  s3BucketList.value = [];
  bucketListError.value = "";
  bucketNameAvailable.value = null;
  bucketNameMessage.value = "";

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
  selectedProxy.value = null;
  proxyDirectories.value = [];
  currentPath.value = "";
  localPathCheckResult.value = null;
}

// Available Sync Proxies (online + sync role)
const availableSyncProxies = computed(() => {
  return nodes.value.filter(
    (node) => node.role === "sync" && node.status === "online",
  );
});

// Selected proxy for local filesystem
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

// Fetch Sync Proxy directories
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

// Handle proxy selection for local type
function handleProxySelect(proxyId: string) {
  newRepo.value.bound_node = proxyId;
  localPathCheckResult.value = null;
  selectedProxy.value =
    availableSyncProxies.value.find((p) => p.id === proxyId) || null;
  if (proxyId) {
    fetchProxyDirectories(proxyId, "/");
  } else {
    proxyDirectories.value = [];
    currentPath.value = "";
  }
}

// Navigate to subdirectory
function navigateToDirectory(dir: string) {
  const newPath =
    currentPath.value === "/" ? `/${dir}` : `${currentPath.value}/${dir}`;
  fetchProxyDirectories(newRepo.value.bound_node!, newPath);
}

// Navigate up
function navigateUp() {
  if (currentPath.value === "/" || !currentPath.value) return;
  const parts = currentPath.value.split("/").filter(Boolean);
  parts.pop();
  const newPath = parts.length === 0 ? "/" : "/" + parts.join("/");
  fetchProxyDirectories(newRepo.value.bound_node!, newPath);
}

// Select current directory as backup path
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
      selectedProxy.value = null;
      proxyDirectories.value = [];
      currentPath.value = "";
      localPathCheckResult.value = null;
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

async function fetchNodes() {
  try {
    const response = await nodesApi.list();
    nodes.value = response.data.results || response.data;
  } catch (error) {
    console.error("Failed to fetch nodes:", error);
  }
}

// Get app store for toast
const appStore = useAppStore();

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
      // Build detailed success message
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

      // Show detailed result modal if there are details
      if (
        details &&
        (details.connectivity || details.write_test || details.space_info)
      ) {
        selectedTestResult.value = {
          success: true,
          message: result.message,
          details: details,
        };
        showTestResultModal.value = true;
      }

      console.log("[Test Connection] Details:", details);

      // Auto-sync usage for S3 repositories (async, don't wait)
      if (repo.repo_type === "s3") {
        syncUsage(repo);
      }
    } else {
      appStore.error(
        `${t("repository.connectionTestFailed")}: ${result.message}`,
      );
    }

    // Refresh repository data
    await fetchRepositories();
  } catch (error: any) {
    console.error("Connection test failed:", error);
    // 处理后端返回的错误信息
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

    // 根据错误代码显示不同的提示
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

// Sync repository usage
async function syncUsage(repo: Repository) {
  try {
    const response = await repositoriesApi.syncUsage(repo.id);
    if (response.data.success) {
      const usage = response.data.usage;
      console.log(
        `[Usage Sync] ${repo.name}: ${usage.object_count} objects, ${usage.total_size_gb} GB`,
      );
      // Refresh repository data to show updated usage
      await fetchRepositories();
    }
  } catch (error: any) {
    console.error("Failed to sync usage:", error);
    // Don't show error to user - this is a background operation
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

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB", "PB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function getProgressColor(quotaStatus: string): string {
  // If quota is not enabled or unlimited, use default blue gradient
  if (quotaStatus === "disabled" || quotaStatus === "unlimited") {
    return "bg-gradient-to-r from-blue-500 to-cyan-500";
  }

  // Color based on quota status
  switch (quotaStatus) {
    case "critical":
      return "bg-gradient-to-r from-red-500 to-red-600";
    case "warning":
      return "bg-gradient-to-r from-amber-500 to-orange-500";
    case "ok":
      return "bg-gradient-to-r from-blue-500 to-cyan-500";
    default:
      return "bg-gradient-to-r from-blue-500 to-cyan-500";
  }
}

function getRepoTypeIcon(type: string) {
  const icons: Record<string, any> = {
    s3: CloudIcon,
    local: FolderIcon,
    nas: ServerIcon,
    nfs: ServerIcon,
    azure: CloudIcon,
    gcs: CloudIcon,
  };
  return icons[type] || CircleStackIcon;
}

function getRepoTypeColor(type: string): string {
  const colors: Record<string, string> = {
    s3: "bg-orange-100 text-orange-600",
    local: "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400",
    nas: "bg-purple-100 text-purple-600",
    nfs: "bg-purple-100 text-purple-600",
    azure: "bg-sky-100 text-sky-600",
    gcs: "bg-red-100 text-red-600",
  };
  return colors[type] || "bg-background-tertiary/50 text-foreground-secondary";
}

function getRepoTypeLabel(type: string | undefined | null): string {
  if (!type) return "-";
  const labels: Record<string, string> = {
    s3: "S3",
    local: t("repository.types.local"),
    nas: "NAS",
    nfs: "NFS",
    azure: "Azure",
    gcs: "GCS",
  };
  return labels[type] || type?.toUpperCase() || "-";
}

function getNodeName(nodeId: string | null | undefined): string {
  if (!nodeId) return t("sourceResources.noBoundNode");
  const node = nodes.value.find((n: ProxyNode) => String(n.id) === nodeId);
  return node?.name || nodeId;
}

function getNode(nodeId: string | null | undefined): ProxyNode | undefined {
  if (!nodeId) return undefined;
  return nodes.value.find((n: ProxyNode) => String(n.id) === nodeId);
}

function getNodeStatus(nodeId: string | null | undefined): string {
  const node = getNode(nodeId);
  return node?.status || "unknown";
}

onMounted(() => {
  fetchRepositories();
  fetchNodes();
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

    <!-- Create Modal -->
    <Teleport to="body">
      <div
        v-if="showCreateModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div
          class="absolute inset-0 bg-black/50"
          @click="showCreateModal = false"
        />
        <div
          class="relative modal-surface rounded-2xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col"
        >
          <!-- Fixed Header -->
          <div
            class="px-6 py-4 border-b border-border flex items-center justify-between flex-shrink-0"
          >
            <h2 class="text-lg font-semibold text-foreground">
              {{
                isEditMode
                  ? t("repository.form.editRepository")
                  : t("repository.form.addRepository")
              }}
            </h2>
            <button
              @click="
                showCreateModal = false;
                resetForm();
              "
              class="p-1 hover:bg-background-tertiary/50 rounded-lg"
            >
              <svg
                class="w-5 h-5 text-foreground-muted"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          <!-- Fixed Repository Type Selection -->
          <div class="px-6 py-4 border-b border-border flex-shrink-0">
            <label class="block text-sm font-medium text-foreground mb-3">{{
              t("repository.form.repositoryType")
            }}</label>
            <div class="grid grid-cols-3 gap-3">
              <button
                v-for="type in repoTypes"
                :key="type.value"
                @click="!isEditMode && (newRepo.repo_type = type.value as any)"
                :disabled="isEditMode"
                :class="[
                  'flex flex-col items-center gap-2 p-3 rounded-xl border-2 transition-all',
                  isEditMode ? 'cursor-not-allowed opacity-60' : '',
                  newRepo.repo_type === type.value
                    ? 'border-blue-500 dark:border-blue-400 bg-background/50 shadow-sm'
                    : 'border-border bg-background/50 hover:border-border-secondary dark:hover:border-slate-500',
                ]"
              >
                <div
                  :class="[
                    'w-9 h-9 rounded-lg flex items-center justify-center dark:bg-opacity-50',
                    type.color === 'orange'
                      ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400'
                      : type.color === 'purple'
                        ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400'
                        : 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
                  ]"
                >
                  <component :is="type.icon" class="w-5 h-5" />
                </div>
                <span
                  class="text-xs font-medium text-foreground dark:text-slate-200"
                  >{{ type.label }}</span
                >
              </button>
            </div>
          </div>

          <!-- Scrollable Content Area -->
          <div class="flex-1 overflow-y-auto p-6 space-y-4">
            <!-- Basic Info -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-foreground mb-1"
                  >{{ t("common.name") }} *</label
                >
                <input
                  v-model="newRepo.name"
                  type="text"
                  :placeholder="t('repository.form.namePlaceholder')"
                  :class="[
                    'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2',
                    formErrors.name
                      ? 'border-red-300 focus:ring-red-500'
                      : 'border-border focus:ring-blue-500',
                  ]"
                  @input="clearError('name')"
                />
                <p
                  v-if="formErrors.name"
                  class="mt-1 text-xs text-red-500 dark:text-red-400"
                >
                  {{ formErrors.name }}
                </p>
              </div>
              <div>
                <label class="block text-sm font-medium text-foreground mb-1">{{
                  t("common.description")
                }}</label>
                <input
                  v-model="newRepo.description"
                  type="text"
                  :placeholder="t('repository.form.descPlaceholder')"
                  class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-foreground mb-1">
                  {{ t("repository.form.storageQuota") }}
                  <span class="text-xs text-foreground-muted font-normal ml-1"
                    >({{ t("repository.form.quotaUnit") }})</span
                  >
                </label>
                <input
                  v-model.number="newRepo.quota"
                  type="number"
                  min="0"
                  :placeholder="t('repository.form.quotaPlaceholder')"
                  class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p class="mt-1 text-xs text-foreground-muted">
                  {{ t("repository.form.quotaHint") }}
                </p>
              </div>

              <!-- Quota Monitoring Toggle -->
              <div>
                <label
                  class="flex items-center gap-2 text-sm font-medium text-foreground mb-2"
                >
                  <input
                    v-model="newRepo.quota_enabled"
                    type="checkbox"
                    class="rounded border-border-secondary text-blue-600 focus:ring-blue-500"
                  />
                  {{ t("repository.form.quotaEnabled") }}
                </label>
                <div
                  v-if="newRepo.quota_enabled"
                  class="flex items-center gap-2 mt-2"
                >
                  <span class="text-sm text-foreground-secondary"
                    >{{ t("repository.form.quotaThreshold") }}:</span
                  >
                  <input
                    v-model.number="newRepo.quota_warning_threshold"
                    type="number"
                    min="50"
                    max="100"
                    class="w-16 px-2 py-1 text-sm border border-border rounded bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <span class="text-xs text-foreground-muted">%</span>
                  <p class="text-xs text-foreground-muted">
                    {{ t("repository.form.quotaThresholdHint") }}
                  </p>
                </div>
              </div>
            </div>

            <RepositoryS3ConfigSection
              v-if="newRepo.repo_type === 's3'"
              :new-repo="newRepo"
              :form-errors="formErrors"
              :available-sync-proxies="availableSyncProxies"
              :is-edit-mode="isEditMode"
              :s3-bucket-list="s3BucketList"
              :is-loading-buckets="isLoadingBuckets"
              :bucket-list-error="bucketListError"
              :checking-bucket-name="checkingBucketName"
              :bucket-name-available="bucketNameAvailable"
              :bucket-name-message="bucketNameMessage"
              @clear-error="clearError"
              @fetch-bucket-list="fetchBucketList"
              @check-bucket-name-availability="checkBucketNameAvailability"
            />

            <RepositoryNasConfigSection
              v-if="newRepo.repo_type === 'nas'"
              :new-repo="newRepo"
              :form-errors="formErrors"
              :available-sync-proxies="availableSyncProxies"
              :is-edit-mode="isEditMode"
              @clear-error="clearError"
            />

            <RepositoryLocalConfigSection
              v-if="newRepo.repo_type === 'local'"
              :new-repo="newRepo"
              :form-errors="formErrors"
              :available-sync-proxies="availableSyncProxies"
              :proxy-directories="proxyDirectories"
              :current-path="currentPath"
              :is-loading-directories="isLoadingDirectories"
              :checking-local-path="checkingLocalPath"
              :local-path-check-result="localPathCheckResult"
              :format-bytes="formatBytes"
              @handle-proxy-select="handleProxySelect"
              @check-local-path="checkLocalPath"
              @clear-error="clearError"
              @clear-local-path-check="localPathCheckResult = null"
              @navigate-up="navigateUp"
              @navigate-to-directory="navigateToDirectory"
              @select-current-path="selectCurrentPath"
            />
          </div>

          <!-- Fixed Footer -->
          <div
            class="px-6 py-4 rounded-2xl border-t border-border flex justify-end gap-3 flex-shrink-0 bg-card"
          >
            <button
              @click="
                showCreateModal = false;
                resetForm();
              "
              class="px-4 py-2 text-sm text-foreground-secondary border border-border rounded-lg hover:bg-hover/50 transition-colors"
            >
              {{ t("common.cancel") }}
            </button>
            <button
              @click="createRepository"
              :disabled="!isFormValid"
              :class="[
                'px-4 py-2 text-sm rounded-lg transition-colors',
                isFormValid
                  ? 'text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600'
                  : 'text-foreground-secondary bg-slate-200 dark:bg-slate-600 cursor-not-allowed',
              ]"
            >
              {{ isEditMode ? t("common.save") : t("common.create") }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

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
