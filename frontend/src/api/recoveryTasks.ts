import api from "./client";

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

  pause: (id: number | string) =>
    api.post(`/api/v1/recovery-tasks/tasks/${id}/pause/`),

  runs: (id: number | string, params?: { page?: number; page_size?: number }) =>
    api.get(`/api/v1/recovery-tasks/tasks/${id}/runs/`, { params }),

  precheck: (id: number | string) =>
    api.post(`/api/v1/recovery-tasks/tasks/${id}/precheck/`),
};
