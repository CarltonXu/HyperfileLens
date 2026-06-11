import api, { type AxiosRequestConfig } from "./client";

export const gatewaysApi = {
  list: (params?: { page?: number; page_size?: number; status?: string }) =>
    api.get("/api/v1/gateways/", { params }),

  detail: (id: string, config?: AxiosRequestConfig) =>
    api.get(`/api/v1/gateways/${id}/`, config),

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

  createInstallCommand: (data: {
    name: string;
    description?: string;
    ai_enabled?: boolean;
    tags?: Record<string, unknown>;
    labels?: string[];
    server_url?: string;
  }) => api.post("/api/v1/gateways/install_command/", data),

  installCommand: (id: string) =>
    api.get(`/api/v1/gateways/${id}/install_command/`),

  activate: (id: string) => api.post(`/api/v1/gateways/${id}/activate/`),

  deactivate: (id: string) => api.post(`/api/v1/gateways/${id}/deactivate/`),

  maintenance: (id: string) => api.post(`/api/v1/gateways/${id}/maintenance/`),

  regenerateToken: (id: string) =>
    api.post(`/api/v1/gateways/${id}/regenerate_token/`),

  monitoring: (id: string, hours?: number) =>
    api.get(`/api/v1/gateways/${id}/monitoring/`, {
      params: { hours: hours || 24 },
    }),

  mounts: (id: string) => api.get(`/api/v1/gateways/${id}/mounts/`),
};
