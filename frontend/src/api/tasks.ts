import api from "./client";

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
