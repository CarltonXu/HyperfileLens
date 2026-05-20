import api from "./client";

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

  overview: (id: number | string) =>
    api.get(`/api/v1/proxies/${id}/overview/`),

  monitor: (id: number | string, params?: { hours?: number }) =>
    api.get(`/api/v1/proxies/${id}/monitor/`, { params }),

  setStatus: (id: number | string, status: string) =>
    api.post(`/api/v1/proxies/${id}/set_status/`, { status }),

  generateInstall: (data: {
    name: string;
    role: "agent" | "sync";
    os: string;
    labels?: string[] | Record<string, string>;
  }) => api.post("/api/v1/proxies/generate_install/", data),

  regenerateToken: (id: number | string) =>
    api.post(`/api/v1/proxies/${id}/regenerate_token/`),

  register: (data: {
    token: string;
    name: string;
    role: string;
    hostname?: string;
    capabilities?: Record<string, unknown>;
  }) => api.post("/api/v1/proxies/register/", data),

  heartbeat: (data: {
    token: string;
    status: string;
    metrics?: Record<string, unknown>;
    capabilities?: Record<string, unknown>;
  }) => api.post("/api/v1/proxies/heartbeat/", data),

  tasks: (
    id: number | string,
    params?: { page?: number; page_size?: number; limit?: number },
  ) => api.get(`/api/v1/proxies/${id}/tasks/`, { params }),

  heartbeats: (
    id: number | string,
    params?: { page?: number; page_size?: number; hours?: number },
  ) => api.get(`/api/v1/proxies/${id}/heartbeats/`, { params }),

  syncConfig: (id: number | string) =>
    api.post(`/api/v1/proxies/${id}/sync-config/`),

  listPaths: (id: number | string) =>
    api.get(`/api/v1/proxies/${id}/list-paths/`),

  verifyPath: (id: number | string, path: string) =>
    api.post(`/api/v1/proxies/${id}/verify-path/`, { path }),

  getDirectories: (id: number | string, path: string = "/") =>
    api.get(`/api/v1/proxies/${id}/directories/`, { params: { path } }),
};
