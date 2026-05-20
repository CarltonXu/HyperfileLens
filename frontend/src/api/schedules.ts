import api from "./client";

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
