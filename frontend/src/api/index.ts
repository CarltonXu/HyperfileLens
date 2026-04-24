import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type AxiosError
} from 'axios'

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
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

// ============== Nodes API ==============
export const nodesApi = {
  list: (params?: { page?: number; page_size?: number; status?: string }) =>
    api.get('/api/v1/nodes/nodes/', { params }),
  
  detail: (id: number) =>
    api.get(`/api/v1/nodes/nodes/${id}/`),
  
  create: (data: any) =>
    api.post('/api/v1/nodes/nodes/', data),
  
  update: (id: number, data: any) =>
    api.patch(`/api/v1/nodes/nodes/${id}/`, data),
  
  delete: (id: number) =>
    api.delete(`/api/v1/nodes/nodes/${id}/`),
  
  stats: () =>
    api.get('/api/v1/nodes/nodes/stats/'),
  
  register: (data: { node_key: string; name: string; node_type: string }) =>
    api.post('/api/v1/nodes/register/', data),
  
  heartbeat: (id: number) =>
    api.post(`/api/v1/nodes/nodes/${id}/heartbeat/`),
  
  syncConfig: (id: number) =>
    api.post(`/api/v1/nodes/nodes/${id}/sync-config/`),
  
  listPaths: (id: number) =>
    api.get(`/api/v1/nodes/nodes/${id}/list-paths/`),
  
  verifyPath: (id: number, path: string) =>
    api.post(`/api/v1/nodes/nodes/${id}/verify-path/`, { path })
}

// ============== Backup Tasks API ==============
export const backupTasksApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; node?: number }) =>
    api.get('/api/v1/backup/tasks/', { params }),
  
  detail: (id: number) =>
    api.get(`/api/v1/backup/tasks/${id}/`),
  
  create: (data: any) =>
    api.post('/api/v1/backup/tasks/', data),
  
  update: (id: number, data: any) =>
    api.patch(`/api/v1/backup/tasks/${id}/`, data),
  
  delete: (id: number) =>
    api.delete(`/api/v1/backup/tasks/${id}/`),
  
  stats: () =>
    api.get('/api/v1/backup/tasks/stats/'),
  
  execute: (id: number) =>
    api.post(`/api/v1/backup/tasks/${id}/execute/`),
  
  cancel: (id: number) =>
    api.post(`/api/v1/backup/tasks/${id}/cancel/`),
  
  listSnapshots: (params?: { node?: number; repository?: number; page?: number; page_size?: number }) =>
    api.get('/api/v1/backup/snapshots/', { params }),
  
  snapshotDetail: (snapshotId: string) =>
    api.get(`/api/v1/backup/snapshots/${snapshotId}/`),
  
  listFiles: (snapshotId: string, path?: string) =>
    api.get(`/api/v1/backup/snapshots/${snapshotId}/files/`, { params: { path } })
}

// ============== Recovery Tasks API ==============
export const recoveryTasksApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; node?: number }) =>
    api.get('/api/v1/recovery/tasks/', { params }),
  
  detail: (id: number) =>
    api.get(`/api/v1/recovery/tasks/${id}/`),
  
  create: (data: any) =>
    api.post('/api/v1/recovery/tasks/', data),
  
  update: (id: number, data: any) =>
    api.patch(`/api/v1/recovery/tasks/${id}/`, data),
  
  delete: (id: number) =>
    api.delete(`/api/v1/recovery/tasks/${id}/`),
  
  stats: () =>
    api.get('/api/v1/recovery/tasks/stats/'),
  
  execute: (id: number) =>
    api.post(`/api/v1/recovery/tasks/${id}/execute/`),
  
  cancel: (id: number) =>
    api.post(`/api/v1/recovery/tasks/${id}/cancel/`)
}

// ============== Repositories API ==============
export const repositoriesApi = {
  list: (params?: { page?: number; page_size?: number; status?: string }) =>
    api.get('/api/v1/repository/repositories/', { params }),
  
  detail: (id: number) =>
    api.get(`/api/v1/repository/repositories/${id}/`),
  
  create: (data: any) =>
    api.post('/api/v1/repository/repositories/', data),
  
  update: (id: number, data: any) =>
    api.patch(`/api/v1/repository/repositories/${id}/`, data),
  
  delete: (id: number) =>
    api.delete(`/api/v1/repository/repositories/${id}/`),
  
  stats: () =>
    api.get('/api/v1/repository/repositories/stats/'),
  
  health: (id: number) =>
    api.get(`/api/v1/repository/repositories/${id}/health/`),
  
  testConnection: (data: any) =>
    api.post('/api/v1/repository/repositories/test-connection/', data),
  
  sync: (id: number) =>
    api.post(`/api/v1/repository/repositories/${id}/sync/`),
  
  browseSnapshots: (id: number) =>
    api.get(`/api/v1/repository/repositories/${id}/browse/`)
}

// ============== Policies API ==============
export const policiesApi = {
  list: (params?: { page?: number; page_size?: number; is_active?: boolean }) =>
    api.get('/api/v1/policies/policies/', { params }),
  
  detail: (id: number) =>
    api.get(`/api/v1/policies/policies/${id}/`),
  
  create: (data: any) =>
    api.post('/api/v1/policies/policies/', data),
  
  update: (id: number, data: any) =>
    api.patch(`/api/v1/policies/policies/${id}/`, data),
  
  delete: (id: number) =>
    api.delete(`/api/v1/policies/policies/${id}/`),
  
  enable: (id: number) =>
    api.post(`/api/v1/policies/policies/${id}/enable/`),
  
  disable: (id: number) =>
    api.post(`/api/v1/policies/policies/${id}/disable/`)
}

// ============== AI Query API ==============
export const aiQueryApi = {
  query: (data: { query: string; node?: number; repository?: number; snapshot_id?: string }) =>
    api.post('/api/v1/ai/query/', data),
  
  history: (params?: { page?: number; page_size?: number }) =>
    api.get('/api/v1/ai/query/history/', { params }),
  
  cancel: (id: number) =>
    api.post(`/api/v1/ai/query/${id}/cancel/`)
}

// ============== Audit Log API ==============
export const auditLogApi = {
  list: (params?: { page?: number; page_size?: number; action?: string; user?: number }) =>
    api.get('/api/v1/audit/logs/', { params }),
  
  detail: (id: number) =>
    api.get(`/api/v1/audit/logs/${id}/`),
  
  export: (params: { start_date?: string; end_date?: string; action?: string }) =>
    api.get('/api/v1/audit/logs/export/', { params, responseType: 'blob' })
}

// Export api instance
export default api

// Export types
export type { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError }
