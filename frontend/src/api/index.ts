import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type AxiosError,
} from "axios";
import { getApiErrorMessage } from "@/utils/errors";

// Create axios instance
// Use relative path to leverage server-side API proxy (avoids CORS issues)
const getBaseURL = () => {
  // Always use relative path - server will proxy /api/* requests to backend
  return "";
};

const api: AxiosInstance = axios.create({
  baseURL: getBaseURL(),
  timeout: Number(import.meta.env.VITE_API_TIMEOUT) || 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Token ${token}`;
    }

    // Add CSRF token for non-GET requests
    if (config.method !== "get") {
      const csrfToken = getCsrfToken();
      if (csrfToken) {
        config.headers["X-CSRFToken"] = csrfToken;
      }
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean;
      _skipGlobalErrorHandler?: boolean;
    };

    // Skip global error handling if requested (page will handle it)
    if (originalRequest._skipGlobalErrorHandler) {
      return Promise.reject(error);
    }

    // Handle 401 Unauthorized
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Clear token and redirect to login
      localStorage.removeItem("token");
      window.location.href = "/login";

      return Promise.reject(error);
    }

    // For 400 and 422 errors, let the page handle the specific error messages
    // These are usually validation errors that need contextual display
    if (error.response?.status === 400 || error.response?.status === 422) {
      return Promise.reject(error);
    }

    // Show error toast for network errors, server errors, and other HTTP errors
    // that are not handled by individual pages
    let errorMessage = "An unexpected error occurred";
    let errorTitle = "Error";

    if (error.response) {
      errorMessage = getApiErrorMessage(error, "The server returned an error");

      // Set title based on status code
      switch (error.response.status) {
        case 403:
          errorTitle = "Access Denied";
          break;
        case 404:
          errorTitle = "Not Found";
          break;
        case 500:
          errorTitle = "Server Error";
          errorMessage =
            errorMessage ||
            "An internal server error occurred. Please try again later.";
          break;
        case 502:
        case 503:
        case 504:
          errorTitle = "Service Unavailable";
          errorMessage =
            "The service is temporarily unavailable. Please try again later.";
          break;
      }
    } else if (error.request) {
      // Request was made but no response received
      if (error.code === "ECONNABORTED" || error.message.includes("timeout")) {
        errorTitle = "Request Timeout";
        errorMessage =
          "The request took too long to complete. Please try again.";
      } else {
        errorTitle = "Network Error";
        errorMessage =
          "Unable to connect to the server. Please check your network connection.";
      }
    } else {
      // Error setting up request
      errorMessage = error.message || "An unexpected error occurred";
    }

    // Show toast notification (dynamic import to avoid circular dependency)
    import("@/stores/app").then(({ useAppStore }) => {
      const appStore = useAppStore();
      appStore.showToast({
        type: "error",
        title: errorTitle,
        message: errorMessage,
        duration: 5000,
      });
    });

    return Promise.reject(error);
  },
);

// Helper function to get CSRF token
function getCsrfToken(): string | null {
  const name = "csrftoken";
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// ============== Auth API ==============
export const authApi = {
  login: (
    email: string,
    password: string,
    captcha_key?: string,
    captcha_code?: string,
  ) =>
    api.post("/api/v1/accounts/login/", {
      email,
      password,
      captcha_key,
      captcha_code,
    }),

  logout: () => api.post("/api/v1/accounts/logout/"),

  register: (data: {
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
    captcha_key?: string;
    captcha_code?: string;
  }) => api.post("/api/v1/accounts/register-v2/", data),

  profile: () => api.get("/api/v1/accounts/profile/"),

  updateProfile: (data: { full_name?: string; phone?: string }) =>
    api.patch("/api/v1/accounts/profile/", data),

  changePassword: (data: { old_password: string; new_password: string }) =>
    api.post("/api/v1/accounts/password/", data),

  forgotPassword: (
    email: string,
    captcha_key?: string,
    captcha_code?: string,
  ) =>
    api.post("/api/v1/accounts/forgot-password/", {
      email,
      captcha_key,
      captcha_code,
    }),

  verifyResetCode: (email: string, code: string) =>
    api.post("/api/v1/accounts/verify-reset-code/", { email, code }),

  resetPassword: (token: string, new_password: string) =>
    api.post("/api/v1/accounts/reset-password/", { token, new_password }),
};

// ============== Proxies API ==============
export const proxiesApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    role?: string;
  }) => api.get("/api/v1/proxies/", { params }),

  detail: (id: number | string) => api.get(`/api/v1/proxies/${id}/`),

  create: (data: any) => api.post("/api/v1/proxies/", data),

  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/proxies/${id}/`, data),

  delete: (id: number | string) => api.delete(`/api/v1/proxies/${id}/`),

  stats: () => api.get("/api/v1/proxies/stats/"),

  // Generate installation command
  generateInstall: (data: {
    name: string;
    role: "agent" | "sync";
    os: string;
    labels?: Record<string, string>;
  }) => api.post("/api/v1/proxies/generate_install/", data),

  // Regenerate proxy token
  regenerateToken: (id: number | string) =>
    api.post(`/api/v1/proxies/${id}/regenerate_token/`),

  // Registration endpoint (for proxy client, no auth required)
  register: (data: {
    token: string;
    name: string;
    role: string;
    hostname?: string;
    capabilities?: Record<string, unknown>;
  }) => api.post("/api/v1/proxies/register/", data),

  // Heartbeat endpoint (for proxy client)
  heartbeat: (data: {
    token: string;
    status: string;
    metrics?: Record<string, unknown>;
    capabilities?: Record<string, unknown>;
  }) => api.post("/api/v1/proxies/heartbeat/", data),

  // Get proxy tasks
  tasks: (
    id: number | string,
    params?: { page?: number; page_size?: number },
  ) => api.get(`/api/v1/proxies/${id}/tasks/`, { params }),

  // Get proxy heartbeats
  heartbeats: (
    id: number | string,
    params?: { page?: number; page_size?: number },
  ) => api.get(`/api/v1/proxies/${id}/heartbeats/`, { params }),

  // Legacy compatibility (deprecated, use proxiesApi instead)
  syncConfig: (id: number | string) =>
    api.post(`/api/v1/proxies/${id}/sync-config/`),

  listPaths: (id: number | string) =>
    api.get(`/api/v1/proxies/${id}/list-paths/`),

  verifyPath: (id: number | string, path: string) =>
    api.post(`/api/v1/proxies/${id}/verify-path/`, { path }),

  // Get proxy directories (for Sync Proxy local filesystem browser)
  getDirectories: (id: number | string, path: string = "/") =>
    api.get(`/api/v1/proxies/${id}/directories/`, { params: { path } }),
};

// ============== Global Task Management API ==============
export const taskManagementApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    source?: string;
    search?: string;
    limit?: number;
  }) => api.get("/api/v1/tasks/", { params }),

  stats: () => api.get("/api/v1/tasks/stats/"),

  detail: (id: number | string) => api.get(`/api/v1/tasks/${id}/`),

  cancelTask: (id: number | string, data?: { reason?: string }) =>
    api.post(`/api/v1/tasks/${id}/cancel/`, data || {}),

  /** @deprecated Use cancelTask instead. */
  cancelProxyTask: (id: number | string) =>
    api.post(`/api/v1/tasks/${id}/cancel/`),
};

// ============== Global Alert Center API ==============
export const alertsApi = {
  systemMonitor: (params?: {
    hours?: number;
    start_at?: string;
    end_at?: string;
  }) => api.get("/api/v1/alerts/system/", { params }),

  policies: (params?: Record<string, unknown>) =>
    api.get("/api/v1/alerts/policies/", { params }),
  getPolicy: (id: string) => api.get(`/api/v1/alerts/policies/${id}/`),
  createPolicy: (data: Record<string, unknown>) =>
    api.post("/api/v1/alerts/policies/", data),
  updatePolicy: (id: string, data: Record<string, unknown>) =>
    api.patch(`/api/v1/alerts/policies/${id}/`, data),
  deletePolicy: (id: string) => api.delete(`/api/v1/alerts/policies/${id}/`),
  enablePolicy: (id: string) =>
    api.post(`/api/v1/alerts/policies/${id}/enable/`),
  disablePolicy: (id: string) =>
    api.post(`/api/v1/alerts/policies/${id}/disable/`),
  duplicatePolicy: (id: string) =>
    api.post(`/api/v1/alerts/policies/${id}/duplicate/`),

  records: (params?: Record<string, unknown>) =>
    api.get("/api/v1/alerts/records/", { params }),
  getRecord: (id: string) => api.get(`/api/v1/alerts/records/${id}/`),
  acknowledgeRecord: (id: string, note = "") =>
    api.post(`/api/v1/alerts/records/${id}/acknowledge/`, { note }),
  resolveRecord: (id: string, note = "") =>
    api.post(`/api/v1/alerts/records/${id}/resolve/`, { note }),

  notificationChannels: (params?: Record<string, unknown>) =>
    api.get("/api/v1/alerts/notification-channels/", { params }),
  createNotificationChannel: (data: Record<string, unknown>) =>
    api.post("/api/v1/alerts/notification-channels/", data),
  updateNotificationChannel: (id: string, data: Record<string, unknown>) =>
    api.patch(`/api/v1/alerts/notification-channels/${id}/`, data),
  deleteNotificationChannel: (id: string) =>
    api.delete(`/api/v1/alerts/notification-channels/${id}/`),
  testNotificationChannel: (id: string) =>
    api.post(
      `/api/v1/alerts/notification-channels/${id}/test/`,
      {},
      { timeout: 60000 },
    ), // 60 seconds timeout for email sending
  getChannelDetails: (id: string) =>
    api.get(`/api/v1/alerts/notification-channels/${id}/details/`),
  notificationLogs: (params?: Record<string, unknown>) =>
    api.get("/api/v1/alerts/notification-logs/", { params }),
  notificationLogStats: (params?: Record<string, unknown>) =>
    api.get("/api/v1/alerts/notification-logs/stats/", { params }),
  getNotificationLog: (id: string) =>
    api.get(`/api/v1/alerts/notification-logs/${id}/`),

  metadata: (kind: string, params?: Record<string, unknown>) =>
    api.get(`/api/v1/alerts/metadata/${kind}/`, { params }),

  metadataResources: (params?: { resource_type?: string }) =>
    api.get("/api/v1/alerts/metadata/resources/", { params }),
};

// ============== Legacy Nodes API (alias for backward compatibility) ==============
/** @deprecated Use proxiesApi instead */
export const nodesApi = proxiesApi;

// ============== Backup Tasks API ==============
export const backupTasksApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    node?: number;
  }) => api.get("/api/v1/backup-tasks/tasks/", { params }),

  detail: (id: number | string) => api.get(`/api/v1/backup-tasks/tasks/${id}/`),

  create: (data: any) => api.post("/api/v1/backup-tasks/tasks/", data),

  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/backup-tasks/tasks/${id}/`, data),

  delete: (id: number | string) =>
    api.delete(`/api/v1/backup-tasks/tasks/${id}/`),

  stats: () => api.get("/api/v1/backup-tasks/tasks/statistics/"),

  execute: (id: number | string) =>
    api.post(`/api/v1/backup-tasks/tasks/${id}/execute/`),

  cancel: (id: number | string) =>
    api.post(`/api/v1/backup-tasks/tasks/${id}/cancel/`),

  enable: (id: number | string) =>
    api.post(`/api/v1/backup-tasks/tasks/${id}/enable/`),

  disable: (id: number | string) =>
    api.post(`/api/v1/backup-tasks/tasks/${id}/disable/`),

  snapshots: (id: number | string) =>
    api.get(`/api/v1/backup-tasks/tasks/${id}/snapshots/`),

  syncSnapshots: (id: number | string) =>
    api.post(`/api/v1/backup-tasks/tasks/${id}/sync-snapshots/`),

  evaluateRetention: (id: number | string, data?: { delete?: boolean }) =>
    api.post(
      `/api/v1/backup-tasks/tasks/${id}/evaluate-retention/`,
      data || {},
    ),

  runMaintenance: (id: number | string, data?: { full?: boolean }) =>
    api.post(`/api/v1/backup-tasks/tasks/${id}/run-maintenance/`, data || {}),

  runs: (id: number | string, params?: { page?: number; page_size?: number }) =>
    api.get(`/api/v1/backup-tasks/tasks/${id}/runs/`, { params }),

  listSnapshots: (params?: {
    node?: number;
    repository?: number;
    page?: number;
    page_size?: number;
  }) => api.get("/api/v1/backup-tasks/snapshots/", { params }),

  snapshotDetail: (snapshotId: string) =>
    api.get(`/api/v1/backup-tasks/snapshots/${snapshotId}/`),

  listFiles: (snapshotId: string, path?: string) =>
    api.get(`/api/v1/backup-tasks/snapshots/${snapshotId}/files/`, {
      params: { path },
    }),
};

// ============== Recovery Tasks API ==============
export const recoveryTasksApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    node?: number;
  }) => api.get("/api/v1/recovery-tasks/tasks/", { params }),

  detail: (id: number | string) =>
    api.get(`/api/v1/recovery-tasks/tasks/${id}/`),

  create: (data: any) => api.post("/api/v1/recovery-tasks/tasks/", data),

  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/recovery-tasks/tasks/${id}/`, data),

  delete: (id: number | string) =>
    api.delete(`/api/v1/recovery-tasks/tasks/${id}/`),

  stats: () => api.get("/api/v1/recovery-tasks/tasks/statistics/"),

  execute: (id: number | string) =>
    api.post(`/api/v1/recovery-tasks/tasks/${id}/execute/`),

  cancel: (id: number | string) =>
    api.post(`/api/v1/recovery-tasks/tasks/${id}/cancel/`),
};

// ============== Source Resources API ==============
export const sourceResourcesApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    resource_type?: string;
  }) => api.get("/api/v1/source-resources/", { params }),

  detail: (id: number | string) => api.get(`/api/v1/source-resources/${id}/`),

  create: (data: any) => api.post("/api/v1/source-resources/", data),

  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/source-resources/${id}/`, data),

  delete: (id: number | string) =>
    api.delete(`/api/v1/source-resources/${id}/`),

  stats: () => api.get("/api/v1/source-resources/statistics/"),

  testConnection: (id: number | string) =>
    api.post(`/api/v1/source-resources/${id}/test-connection/`),

  testDraft: (data: any) =>
    api.post("/api/v1/source-resources/test-draft/", data, {
      timeout: 60000,
    }),

  scan: (id: number | string, path?: string) =>
    api.get(`/api/v1/source-resources/${id}/scan/`, { params: { path } }),

  mount: (id: number | string) =>
    api.post(`/api/v1/source-resources/${id}/mount/`),

  unmount: (id: number | string) =>
    api.post(`/api/v1/source-resources/${id}/unmount/`),

  bindNode: (id: number | string, nodeId: number | string) =>
    api.post(`/api/v1/source-resources/${id}/bind-node/`, { node_id: nodeId }),

  unbindNode: (id: number | string) =>
    api.post(`/api/v1/source-resources/${id}/unbind-node/`),
};

// ============== Repositories API ==============
export const repositoriesApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    repository_type?: string;
  }) => api.get("/api/v1/repositories/", { params }),

  detail: (id: number | string) => api.get(`/api/v1/repositories/${id}/`),

  create: (data: any) => api.post("/api/v1/repositories/", data),

  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/repositories/${id}/`, data),

  delete: (id: number | string) => api.delete(`/api/v1/repositories/${id}/`),

  stats: () => api.get("/api/v1/repositories/statistics/"),

  testConnection: (id: number | string) =>
    api.post(`/api/v1/repositories/${id}/test_connection/`),

  initKopia: (
    id: number | string,
    data: { encryption_password: string; confirm_password: string },
  ) => api.post(`/api/v1/repositories/${id}/initialize/`, data),

  saveKopiaPassword: (
    id: number | string,
    data: { encryption_password: string; confirm_password: string },
  ) => api.post(`/api/v1/repositories/${id}/password/`, data),

  bindNode: (id: number | string, nodeId: number | string) =>
    api.post(`/api/v1/repositories/${id}/bind-node/`, { node_id: nodeId }),

  unbindNode: (id: number | string) =>
    api.post(`/api/v1/repositories/${id}/unbind-node/`),

  // S3 Bucket operations (with extended timeout for network operations)
  listBuckets: (data: {
    endpoint: string;
    region?: string;
    access_key: string;
    secret_key: string;
    use_tls?: boolean;
    filter_by_region?: boolean; // Filter buckets by configured region
  }) =>
    api.post("/api/v1/repositories/list_s3_buckets/", data, { timeout: 60000 }),

  checkBucketName: (data: {
    endpoint: string;
    region?: string;
    access_key: string;
    secret_key: string;
    bucket_name: string;
    use_tls?: boolean;
  }) =>
    api.post("/api/v1/repositories/validate_s3_bucket_name/", data, {
      timeout: 30000,
    }),

  createBucket: (data: {
    endpoint: string;
    region?: string;
    access_key: string;
    secret_key: string;
    bucket_name: string;
    use_tls?: boolean;
  }) =>
    api.post("/api/v1/repositories/create_s3_bucket/", data, {
      timeout: 60000,
    }),

  // Sync repository usage from S3 bucket
  syncUsage: (id: number | string) =>
    api.post(`/api/v1/repositories/${id}/sync_usage/`, {}, { timeout: 120000 }), // 2 minutes timeout
};

// ============== Policies API ==============
export const policiesApi = {
  list: (params?: { page?: number; page_size?: number; is_active?: boolean }) =>
    api.get("/api/v1/policies/policies/", { params }),

  detail: (id: number | string) => api.get(`/api/v1/policies/policies/${id}/`),

  create: (data: any) => api.post("/api/v1/policies/policies/", data),

  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/policies/policies/${id}/`, data),

  delete: (id: number | string) =>
    api.delete(`/api/v1/policies/policies/${id}/`),

  enable: (id: number | string) =>
    api.post(`/api/v1/policies/policies/${id}/activate/`),

  disable: (id: number | string) =>
    api.post(`/api/v1/policies/policies/${id}/deactivate/`),
};

// ============== Schedules API ==============
export const schedulesApi = {
  list: (params?: Record<string, unknown>) =>
    api.get("/api/v1/schedules/backups/", { params }),

  create: (data: Record<string, unknown>) =>
    api.post("/api/v1/schedules/backups/", data),

  update: (id: string, data: Record<string, unknown>) =>
    api.patch(`/api/v1/schedules/backups/${id}/`, data),

  delete: (id: string) => api.delete(`/api/v1/schedules/backups/${id}/`),

  pause: (id: string) => api.post(`/api/v1/schedules/backups/${id}/pause/`),

  resume: (id: string) => api.post(`/api/v1/schedules/backups/${id}/resume/`),

  runNow: (id: string) => api.post(`/api/v1/schedules/backups/${id}/run_now/`),

  executions: (id: string, params?: Record<string, unknown>) =>
    api.get(`/api/v1/schedules/backups/${id}/executions/`, { params }),
};

// ============== Checkpoints API ==============
export const checkpointsApi = {
  listBackups: (params?: Record<string, unknown>) =>
    api.get("/api/v1/checkpoints/backups/", { params }),

  resume: (id: string) => api.post(`/api/v1/checkpoints/backups/${id}/resume/`),

  deleteCheckpoint: (id: string) =>
    api.post(`/api/v1/checkpoints/backups/${id}/delete_checkpoint/`),

  cleanupExpired: () =>
    api.post("/api/v1/checkpoints/backups/cleanup_expired/"),
};

// ============== AI Insights API ==============
// AI-powered file intelligence platform
export const gateway = {
  // AI Query
  aiQuery: (data: {
    query: string;
    repository_id?: string;
    filters?: Record<string, unknown>;
  }) => api.post("/api/v1/ai-insights/gateway/ai-query/", data),

  // File browsing
  listFiles: (params?: { path?: string; repository_id?: string }) =>
    api.get("/api/v1/ai-insights/gateway/files/", { params }),

  // Repository mount status
  mountStatus: () => api.get("/api/v1/ai-insights/gateway/mount-status/"),

  // Index status
  indexStatus: () => api.get("/api/v1/ai-insights/gateway/index-status/"),

  // Rebuild index
  rebuildIndex: (repositoryId: string) =>
    api.post("/api/v1/ai-insights/gateway/rebuild-index/", {
      repository_id: repositoryId,
    }),
};

// ============== AI Insights API (Django Backend) ==============
export const aiInsightsApi = {
  // Query history
  query: (data: {
    query: string;
    node?: number;
    repository?: number;
    snapshot_id?: string;
  }) => api.post("/api/v1/ai-insights/queries/", data),

  // Gateway AI Query (direct)
  gatewayQuery: (data: {
    query: string;
    repository_id?: string;
    filters?: Record<string, unknown>;
  }) => gateway.aiQuery(data),

  history: (params?: { page?: number; page_size?: number }) =>
    api.get("/api/v1/ai-insights/queries/", { params }),

  cancel: (id: number) => api.post(`/api/v1/ai-insights/queries/${id}/cancel/`),

  // ============== 智能洞察功能 API ==============
  // 洞察看板统计
  overview: () => api.get("/api/v1/ai-insights/overview/"),

  // 敏感数据扫描
  sensitiveData: (params?: { repository_id?: string }) =>
    api.get("/api/v1/ai-insights/sensitive-data/", { params }),

  // 内容分类画像
  contentProfiling: (params?: { repository_id?: string }) =>
    api.get("/api/v1/ai-insights/content-profile/", { params }),

  // 冷热数据分析
  dataHeatmap: (params?: { repository_id?: string; days?: number }) =>
    api.get("/api/v1/ai-insights/data-heatmap/", { params }),

  // 冗余内容识别
  redundancy: (params?: { repository_id?: string }) =>
    api.get("/api/v1/ai-insights/redundancy/", { params }),

  // 全局智搜
  smartSearch: (params?: {
    query?: string;
    repository_id?: string;
    filters?: Record<string, unknown>;
  }) => api.get("/api/v1/ai-insights/smart-search/", { params }),
};

// Legacy export for backward compatibility
export const aiQueryApi = aiInsightsApi;

// ============== Tenant API ==============
export const tenantsApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    search?: string;
  }) => api.get("/api/v1/tenants/", { params }),

  detail: (id: number | string) => api.get(`/api/v1/tenants/${id}/`),

  create: (data: any) => api.post("/api/v1/tenants/", data),

  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/tenants/${id}/`, data),

  delete: (id: number | string) => api.delete(`/api/v1/tenants/${id}/`),

  stats: (id: number | string) => api.get(`/api/v1/tenants/${id}/stats/`),

  users: (
    id: number | string,
    params?: { page?: number; page_size?: number },
  ) => api.get(`/api/v1/tenants/${id}/users/`, { params }),

  addUser: (
    id: number | string,
    data: { email: string; role: string; is_superuser?: boolean },
  ) => api.post(`/api/v1/tenants/${id}/users/`, data),

  updateUser: (
    id: number | string,
    userId: string,
    data: { role: string; is_superuser?: boolean },
  ) => api.patch(`/api/v1/tenants/${id}/users/${userId}/`, data),

  removeUser: (id: number | string, userId: string) =>
    api.delete(`/api/v1/tenants/${id}/users/${userId}/`),

  activate: (id: number | string) =>
    api.post(`/api/v1/tenants/${id}/activate/`),

  deactivate: (id: number | string) =>
    api.post(`/api/v1/tenants/${id}/deactivate/`),
};

// ============== License API ==============
export const licensesApi = {
  // Get current active license with usage stats
  current: () => api.get("/api/v1/licenses/current/"),

  // Get machine code (auto-generated)
  machineCode: () => api.get("/api/v1/licenses/machine_code/"),

  // Force regenerate machine code
  regenerateMachineCode: () => api.post("/api/v1/licenses/machine_code/"),

  // Activate license with activation code
  activate: (data: { activation_code: string }) =>
    api.post("/api/v1/licenses/activate/", data),

  // Get license history for audit
  history: (params?: { page?: number; page_size?: number }) =>
    api.get("/api/v1/licenses/history/", { params }),

  // Validate quota for specific operation
  validate: (quotaType: string, amount: number = 1) =>
    api.get("/api/v1/licenses/validate/", {
      params: { quota_type: quotaType, amount },
    }),

  // List all licenses (admin)
  list: (params?: { page?: number; page_size?: number; status?: string }) =>
    api.get("/api/v1/licenses/", { params }),

  // Revoke license (superuser)
  revoke: (id: string) => api.post(`/api/v1/licenses/${id}/revoke/`),
};

// ============== Users API ==============
export const usersApi = {
  // List users in current tenant
  list: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    tenant_role?: string;
    is_active?: boolean;
  }) => api.get("/api/v1/accounts/users/", { params }),

  // Create user in current tenant
  create: (data: {
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
    phone?: string;
    tenant_role?: string;
    is_superuser?: boolean;
    tenant_id?: string;
  }) => api.post("/api/v1/accounts/users/", data),

  // Update user
  update: (
    id: string,
    data: {
      email?: string;
      first_name?: string;
      last_name?: string;
      phone?: string;
      tenant_role?: string;
      is_superuser?: boolean;
    },
  ) => api.patch(`/api/v1/accounts/users/${id}/`, data),

  // Change user role
  changeRole: (id: string, role: string) =>
    api.post(`/api/v1/accounts/users/${id}/change_role/`, { role }),

  // Set superuser status (platform admin only)
  setSuperuser: (id: string, is_superuser: boolean) =>
    api.post(`/api/v1/accounts/users/${id}/set_superuser/`, { is_superuser }),

  // Enable user
  enable: (id: string) => api.post(`/api/v1/accounts/users/${id}/enable/`),

  // Disable user
  disable: (id: string) => api.post(`/api/v1/accounts/users/${id}/disable/`),

  // Delete user
  delete: (id: string) => api.delete(`/api/v1/accounts/users/${id}/`),

  // Reset user password
  resetPassword: (id: string, newPassword: string) =>
    api.post(`/api/v1/accounts/users/${id}/reset_password/`, {
      new_password: newPassword,
    }),
};

// ============== Invitations API ==============
export const invitationsApi = {
  // List invitations for current tenant
  list: (params?: { page?: number; page_size?: number }) =>
    api.get("/api/v1/tenants/invitations/", { params }),

  // Send invitation
  create: (data: { email: string; role: string }) =>
    api.post("/api/v1/tenants/invitations/", data),

  // Cancel invitation
  cancel: (id: string) => api.delete(`/api/v1/tenants/invitations/${id}/`),
};

// ============== Gateways API ==============
export const gatewaysApi = {
  list: (params?: { page?: number; page_size?: number; status?: string }) =>
    api.get("/api/v1/gateways/", { params }),

  detail: (id: string) => api.get(`/api/v1/gateways/${id}/`),

  create: (data: {
    name: string;
    description?: string;
    ssh_port?: number;
    mount_base_path?: string;
    max_concurrent_mounts?: number;
    ai_enabled?: boolean;
    tags?: Record<string, string>;
    labels?: string[];
  }) => api.post("/api/v1/gateways/", data),

  update: (
    id: string,
    data: Partial<{
      name: string;
      description: string;
      ssh_port: number;
      mount_base_path: string;
      max_concurrent_mounts: number;
      ai_enabled: boolean;
      tags: Record<string, string>;
      labels: string[];
    }>,
  ) => api.patch(`/api/v1/gateways/${id}/`, data),

  delete: (id: string) => api.delete(`/api/v1/gateways/${id}/`),

  stats: () => api.get("/api/v1/gateways/stats/"),

  // Generate installation command (creates a pending gateway)
  generateInstall: (data: {
    name: string;
    description?: string;
    ai_enabled?: boolean;
    tags?: Record<string, unknown>;
    labels?: string[];
    server_url?: string;
  }) => api.post("/api/v1/gateways/generate_install/", data),

  // Get installation command for existing gateway
  installCommand: (id: string) =>
    api.get(`/api/v1/gateways/${id}/install_command/`),

  // Activate gateway
  activate: (id: string) => api.post(`/api/v1/gateways/${id}/activate/`),

  // Deactivate gateway
  deactivate: (id: string) => api.post(`/api/v1/gateways/${id}/deactivate/`),

  // Put gateway into maintenance mode
  maintenance: (id: string) => api.post(`/api/v1/gateways/${id}/maintenance/`),

  // Regenerate API token
  regenerateToken: (id: string) =>
    api.post(`/api/v1/gateways/${id}/regenerate_token/`),

  // Get monitoring data (heartbeat history)
  monitoring: (id: string, hours?: number) =>
    api.get(`/api/v1/gateways/${id}/monitoring/`, {
      params: { hours: hours || 24 },
    }),

  // Get active mounts
  mounts: (id: string) => api.get(`/api/v1/gateways/${id}/mounts/`),
};

// Export api instance
export default api;

// Export types
export type { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError };

// ==================== Audit Log APIs ====================
export const auditLogApi = {
  list: (params?: Record<string, unknown>) =>
    api.get("/api/v1/audit/audit/", { params }),
  retrieve: (id: string) => api.get(`/api/v1/audit/audit/${id}/`),
  statistics: () => api.get("/api/v1/audit/audit/statistics/"),
  export: (format: "json" | "csv" = "json") =>
    api.get("/api/v1/audit/audit/export/", {
      params: { format },
      responseType: "blob",
    }),
};

// ==================== Event Log APIs ====================
export const eventLogApi = {
  list: (params?: Record<string, unknown>) =>
    api.get("/api/v1/audit/events/", { params }),
  retrieve: (id: string) => api.get(`/api/v1/audit/events/${id}/`),
  statistics: () => api.get("/api/v1/audit/events/statistics/"),
  alerts: () => api.get("/api/v1/audit/events/alerts/"),
  handle: (id: string, note?: string) =>
    api.post(`/api/v1/audit/events/${id}/handle/`, { note }),
  unhandle: (id: string) => api.post(`/api/v1/audit/events/${id}/unhandle/`),
};

// ==================== Captcha APIs ====================
export const captchaApi = {
  get: () => api.get("/api/v1/accounts/captcha/"),
  validate: (key: string, code: string) =>
    api.post("/api/v1/accounts/captcha/validate/", { key, code }),
};

// ==================== MFA APIs ====================
export const mfaApi = {
  getSetup: () => api.get("/api/v1/accounts/mfa/"),

  enable: (method: "email" | "totp", code: string) =>
    api.post("/api/v1/accounts/mfa/", { method, code }),

  disable: () => api.delete("/api/v1/accounts/mfa/"),

  requestCode: (email: string, login_token: string) =>
    api.post("/api/v1/accounts/mfa/verify/", { email, login_token }),

  verify: (email: string, login_token: string, code: string) =>
    api.put("/api/v1/accounts/mfa/verify/", { email, login_token, code }),
};

// ==================== System Settings APIs ====================
export interface SystemSetting {
  id: string;
  key: string;
  value: string;
  description: string;
  category: string;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export const systemSettingsApi = {
  list: () => api.get<SystemSetting[]>("/api/v1/system/settings/"),

  get: (id: string) => api.get<SystemSetting>(`/api/v1/system/settings/${id}/`),

  getByKey: (key: string) =>
    api.get<SystemSetting>(`/api/v1/system/settings/by_key/?key=${key}`),

  update: (id: string, data: Partial<SystemSetting>) =>
    api.patch<SystemSetting>(`/api/v1/system/settings/${id}/`, data),
};

// ==================== SMTP Config APIs ====================
export interface SMTPConfig {
  id: string;
  name: string;
  host: string;
  port: number;
  username: string;
  use_tls: boolean;
  use_ssl: boolean;
  from_email: string;
  from_name: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  password?: string;
}

export const smtpApi = {
  list: () => api.get<SMTPConfig[]>("/api/v1/system/smtp/"),

  get: (id: string) => api.get<SMTPConfig>(`/api/v1/system/smtp/${id}/`),

  create: (data: Partial<SMTPConfig>) =>
    api.post<SMTPConfig>("/api/v1/system/smtp/", data),

  update: (id: string, data: Partial<SMTPConfig>) =>
    api.patch<SMTPConfig>(`/api/v1/system/smtp/${id}/`, data),

  delete: (id: string) => api.delete(`/api/v1/system/smtp/${id}/`),

  testConnection: (id: string) =>
    api.post<{ success: boolean; message: string }>(
      `/api/v1/system/smtp/${id}/test_connection/`,
    ),

  sendTestEmail: (id: string, to_email: string) =>
    api.post<{ success: boolean; message: string }>(
      `/api/v1/system/smtp/${id}/send_test_email/`,
      { to_email },
    ),

  setDefault: (id: string) =>
    api.post<{ success: boolean; message: string }>(
      `/api/v1/system/smtp/${id}/set_default/`,
    ),

  getDefault: () => api.get<SMTPConfig>("/api/v1/system/smtp/default/"),
};
