import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type AxiosError
} from 'axios'

// Create axios instance
// Use relative path to leverage server-side API proxy (avoids CORS issues)
const getBaseURL = () => {
  // Always use relative path - server will proxy /api/* requests to backend
  return ''
}

const api: AxiosInstance = axios.create({
  baseURL: getBaseURL(),
  timeout: Number(import.meta.env.VITE_API_TIMEOUT) || 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Token ${token}`
    }

    // Add CSRF token for non-GET requests
    if (config.method !== 'get') {
      const csrfToken = getCsrfToken()
      if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken
      }
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }

    // Handle 401 Unauthorized
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      // Clear token and redirect to login
      localStorage.removeItem('token')
      window.location.href = '/login'

      return Promise.reject(error)
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      console.error('Access forbidden:', error.response.data)
    }

    // Handle 500 Server Error
    if (error.response?.status === 500) {
      console.error('Server error:', error.response.data)
    }

    return Promise.reject(error)
  }
)

// Helper function to get CSRF token
function getCsrfToken(): string | null {
  const name = 'csrftoken'
  let cookieValue = null
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim()
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue
}

// ============== Auth API ==============
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/api/v1/accounts/login/', { email, password }),
  
  logout: () =>
    api.post('/api/v1/accounts/logout/'),
  
  register: (data: { email: string; password: string; full_name?: string }) =>
    api.post('/api/v1/accounts/register/', data),
  
  profile: () =>
    api.get('/api/v1/accounts/profile/'),
  
  updateProfile: (data: { full_name?: string; phone?: string }) =>
    api.patch('/api/v1/accounts/profile/', data),
  
  changePassword: (data: { old_password: string; new_password: string }) =>
    api.post('/api/v1/accounts/change-password/', data)
}

// ============== Proxies API ==============
export const proxiesApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; role?: string }) =>
    api.get('/api/v1/proxies/', { params }),
  
  detail: (id: number | string) =>
    api.get(`/api/v1/proxies/${id}/`),
  
  create: (data: any) =>
    api.post('/api/v1/proxies/', data),
  
  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/proxies/${id}/`, data),
  
  delete: (id: number | string) =>
    api.delete(`/api/v1/proxies/${id}/`),
  
  stats: () =>
    api.get('/api/v1/proxies/stats/'),
  
  // Generate installation command
  generateInstall: (data: { name: string; role: 'agent' | 'sync'; os: string; labels?: Record<string, string> }) =>
    api.post('/api/v1/proxies/generate_install/', data),
  
  // Regenerate proxy token
  regenerateToken: (id: number | string) =>
    api.post(`/api/v1/proxies/${id}/regenerate_token/`),
  
  // Registration endpoint (for proxy client, no auth required)
  register: (data: { token: string; name: string; role: string; hostname?: string; capabilities?: Record<string, unknown> }) =>
    api.post('/api/v1/proxies/register/', data),
  
  // Heartbeat endpoint (for proxy client)
  heartbeat: (data: { token: string; status: string; metrics?: Record<string, unknown>; capabilities?: Record<string, unknown> }) =>
    api.post('/api/v1/proxies/heartbeat/', data),
  
  // Get proxy tasks
  tasks: (id: number | string, params?: { page?: number; page_size?: number }) =>
    api.get(`/api/v1/proxies/${id}/tasks/`, { params }),
  
  // Get proxy heartbeats
  heartbeats: (id: number | string, params?: { page?: number; page_size?: number }) =>
    api.get(`/api/v1/proxies/${id}/heartbeats/`, { params }),
  
  // Legacy compatibility (deprecated, use proxiesApi instead)
  syncConfig: (id: number | string) =>
    api.post(`/api/v1/proxies/${id}/sync-config/`),
  
  listPaths: (id: number | string) =>
    api.get(`/api/v1/proxies/${id}/list-paths/`),
  
  verifyPath: (id: number | string, path: string) =>
    api.post(`/api/v1/proxies/${id}/verify-path/`, { path }),
  
  // Get proxy directories (for Sync Proxy local filesystem browser)
  getDirectories: (id: number | string, path: string = '/') =>
    api.get(`/api/v1/proxies/${id}/directories/`, { params: { path } })
}

// ============== Legacy Nodes API (alias for backward compatibility) ==============
/** @deprecated Use proxiesApi instead */
export const nodesApi = proxiesApi

// ============== Backup Tasks API ==============
export const backupTasksApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; node?: number }) =>
    api.get('/api/v1/backup-tasks/tasks/', { params }),
  
  detail: (id: number) =>
    api.get(`/api/v1/backup-tasks/tasks/${id}/`),
  
  create: (data: any) =>
    api.post('/api/v1/backup-tasks/tasks/', data),
  
  update: (id: number, data: any) =>
    api.patch(`/api/v1/backup-tasks/tasks/${id}/`, data),
  
  delete: (id: number) =>
    api.delete(`/api/v1/backup-tasks/tasks/${id}/`),
  
  stats: () =>
    api.get('/api/v1/backup-tasks/stats/'),
  
  execute: (id: number) =>
    api.post(`/api/v1/backup-tasks/tasks/${id}/execute/`),
  
  cancel: (id: number) =>
    api.post(`/api/v1/backup-tasks/tasks/${id}/cancel/`),
  
  listSnapshots: (params?: { node?: number; repository?: number; page?: number; page_size?: number }) =>
    api.get('/api/v1/backup-tasks/snapshots/', { params }),
  
  snapshotDetail: (snapshotId: string) =>
    api.get(`/api/v1/backup-tasks/snapshots/${snapshotId}/`),
  
  listFiles: (snapshotId: string, path?: string) =>
    api.get(`/api/v1/backup-tasks/snapshots/${snapshotId}/files/`, { params: { path } })
}

// ============== Recovery Tasks API ==============
export const recoveryTasksApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; node?: number }) =>
    api.get('/api/v1/recovery-tasks/tasks/', { params }),
  
  detail: (id: number | string) =>
    api.get(`/api/v1/recovery-tasks/tasks/${id}/`),
  
  create: (data: any) =>
    api.post('/api/v1/recovery-tasks/tasks/', data),
  
  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/recovery-tasks/tasks/${id}/`, data),
  
  delete: (id: number | string) =>
    api.delete(`/api/v1/recovery-tasks/tasks/${id}/`),
  
  stats: () =>
    api.get('/api/v1/recovery-tasks/tasks/statistics/'),
  
  execute: (id: number | string) =>
    api.post(`/api/v1/recovery-tasks/tasks/${id}/execute/`),
  
  cancel: (id: number | string) =>
    api.post(`/api/v1/recovery-tasks/tasks/${id}/cancel/`)
}

// ============== Source Resources API ==============
export const sourceResourcesApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; resource_type?: string }) =>
    api.get('/api/v1/source-resources/', { params }),
  
  detail: (id: number | string) =>
    api.get(`/api/v1/source-resources/${id}/`),
  
  create: (data: any) =>
    api.post('/api/v1/source-resources/', data),
  
  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/source-resources/${id}/`, data),
  
  delete: (id: number | string) =>
    api.delete(`/api/v1/source-resources/${id}/`),
  
  stats: () =>
    api.get('/api/v1/source-resources/stats/'),
  
  testConnection: (id: number | string) =>
    api.post(`/api/v1/source-resources/${id}/test-connection/`),
  
  mount: (id: number | string) =>
    api.post(`/api/v1/source-resources/${id}/mount/`),
  
  unmount: (id: number | string) =>
    api.post(`/api/v1/source-resources/${id}/unmount/`),
  
  bindNode: (id: number | string, nodeId: number | string) =>
    api.post(`/api/v1/source-resources/${id}/bind-node/`, { node_id: nodeId }),
  
  unbindNode: (id: number | string) =>
    api.post(`/api/v1/source-resources/${id}/unbind-node/`)
}

// ============== Repositories API ==============
export const repositoriesApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; repository_type?: string }) =>
    api.get('/api/v1/repositories/', { params }),
  
  detail: (id: number | string) =>
    api.get(`/api/v1/repositories/${id}/`),
  
  create: (data: any) =>
    api.post('/api/v1/repositories/', data),
  
  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/repositories/${id}/`, data),
  
  delete: (id: number | string) =>
    api.delete(`/api/v1/repositories/${id}/`),
  
  stats: () =>
    api.get('/api/v1/repositories/statistics/'),
  
  testConnection: (id: number | string) =>
    api.post(`/api/v1/repositories/${id}/test_connection/`),
  
  initKopia: (id: number | string) =>
    api.post(`/api/v1/repositories/${id}/init-kopia/`),
  
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
    filter_by_region?: boolean;  // Filter buckets by configured region
  }) =>
    api.post('/api/v1/repositories/list_s3_buckets/', data, { timeout: 60000 }),
  
  checkBucketName: (data: {
    endpoint: string;
    region?: string;
    access_key: string;
    secret_key: string;
    bucket_name: string;
    use_tls?: boolean;
  }) =>
    api.post('/api/v1/repositories/validate_s3_bucket_name/', data, { timeout: 30000 }),
  
  createBucket: (data: {
    endpoint: string;
    region?: string;
    access_key: string;
    secret_key: string;
    bucket_name: string;
    use_tls?: boolean;
  }) =>
    api.post('/api/v1/repositories/create_s3_bucket/', data, { timeout: 60000 }),
  
  // Sync repository usage from S3 bucket
  syncUsage: (id: number | string) =>
    api.post(`/api/v1/repositories/${id}/sync_usage/`, {}, { timeout: 120000 })  // 2 minutes timeout
}

// ============== Policies API ==============
export const policiesApi = {
  list: (params?: { page?: number; page_size?: number; is_active?: boolean }) =>
    api.get('/api/v1/policies/policies/', { params }),
  
  detail: (id: number | string) =>
    api.get(`/api/v1/policies/policies/${id}/`),
  
  create: (data: any) =>
    api.post('/api/v1/policies/policies/', data),
  
  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/policies/policies/${id}/`, data),
  
  delete: (id: number | string) =>
    api.delete(`/api/v1/policies/policies/${id}/`),
  
  enable: (id: number | string) =>
    api.post(`/api/v1/policies/policies/${id}/enable/`),
  
  disable: (id: number | string) =>
    api.post(`/api/v1/policies/policies/${id}/disable/`)
}

// ============== Gateway API (AI Query, File Index) ==============
// Gateway runs on a separate port (8001) with FastAPI
const gatewayApi = axios.create({
  baseURL: import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8001',
  timeout: 60000, // Longer timeout for AI queries
  headers: {
    'Content-Type': 'application/json'
  }
})

export const gateway = {
  // AI Query
  aiQuery: (data: { query: string; repository_id?: string; filters?: Record<string, unknown> }) =>
    gatewayApi.post('/ai/query', data),
  
  // File browsing
  listFiles: (params?: { path?: string; repository_id?: string }) =>
    gatewayApi.get('/files', { params }),
  
  // Repository mount status
  mountStatus: () =>
    gatewayApi.get('/mount/status'),
  
  // Index status
  indexStatus: () =>
    gatewayApi.get('/index/status'),
  
  // Rebuild index
  rebuildIndex: (repositoryId: string) =>
    gatewayApi.post('/index/rebuild', { repository_id: repositoryId })
}

// ============== AI Query API (Django Backend) ==============
export const aiQueryApi = {
  query: (data: { query: string; node?: number; repository?: number; snapshot_id?: string }) =>
    api.post('/api/v1/ai-query/queries/', data),
  
  // Gateway AI Query (direct)
  gatewayQuery: (data: { query: string; repository_id?: string; filters?: Record<string, unknown> }) =>
    gateway.aiQuery(data),
  
  history: (params?: { page?: number; page_size?: number }) =>
    api.get('/api/v1/ai-query/queries/', { params }),
  
  cancel: (id: number) =>
    api.post(`/api/v1/ai-query/queries/${id}/cancel/`)
}

// ============== Audit Log API ==============
export const auditLogApi = {
  list: (params?: { page?: number; page_size?: number; action?: string; user?: number }) =>
    api.get('/api/v1/audit/audit/', { params }),
  
  detail: (id: number) =>
    api.get(`/api/v1/audit/audit/${id}/`),
  
  export: (params: { start_date?: string; end_date?: string; action?: string }) =>
    api.get('/api/v1/audit/audit/export/', { params, responseType: 'blob' })
}

// ============== Tenant API ==============
export const tenantsApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; search?: string }) =>
    api.get('/api/v1/tenants/', { params }),
  
  detail: (id: number | string) =>
    api.get(`/api/v1/tenants/${id}/`),
  
  create: (data: any) =>
    api.post('/api/v1/tenants/', data),
  
  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/tenants/${id}/`, data),
  
  delete: (id: number | string) =>
    api.delete(`/api/v1/tenants/${id}/`),
  
  stats: (id: number | string) =>
    api.get(`/api/v1/tenants/${id}/stats/`),
  
  users: (id: number | string, params?: { page?: number; page_size?: number }) =>
    api.get(`/api/v1/tenants/${id}/users/`, { params }),
  
  addUser: (id: number | string, data: { user_id: number; role: string }) =>
    api.post(`/api/v1/tenants/${id}/add-user/`, data),
  
  removeUser: (id: number | string, userId: number) =>
    api.post(`/api/v1/tenants/${id}/remove-user/`, { user_id: userId }),
  
  activate: (id: number | string) =>
    api.post(`/api/v1/tenants/${id}/activate/`),
  
  deactivate: (id: number | string) =>
    api.post(`/api/v1/tenants/${id}/deactivate/`)
}

// ============== License API ==============
export const licensesApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; license_type?: string; search?: string }) =>
    api.get('/api/v1/licenses/', { params }),
  
  detail: (id: number | string) =>
    api.get(`/api/v1/licenses/${id}/`),
  
  create: (data: { name: string; license_key: string }) =>
    api.post('/api/v1/licenses/', data),
  
  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/licenses/${id}/`, data),
  
  delete: (id: number | string) =>
    api.delete(`/api/v1/licenses/${id}/`),
  
  validate: (id: number | string) =>
    api.post(`/api/v1/licenses/${id}/validate/`),
  
  validateAll: () =>
    api.post('/api/v1/licenses/validate-all/'),
  
  stats: () =>
    api.get('/api/v1/licenses/stats/'),
  
  importLicense: (data: { encoded_license: string }) =>
    api.post('/api/v1/licenses/import_license/', data)
}

// Export api instance
export default api

// Export types
export type { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError }
