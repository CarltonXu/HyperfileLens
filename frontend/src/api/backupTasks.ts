import api from "./client";

export const backupTasksApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    node?: number;
    ordering?: string;
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

  snapshots: (
    id: number | string,
    params?: { page?: number; page_size?: number },
  ) => api.get(`/api/v1/backup-tasks/tasks/${id}/snapshots/`, { params }),

  syncSnapshots: (id: number | string) =>
    api.post(`/api/v1/backup-tasks/tasks/${id}/sync-snapshots/`),

  evaluateRetention: (id: number | string, data?: { delete?: boolean }) =>
    api.post(
      `/api/v1/backup-tasks/tasks/${id}/evaluate-retention/`,
      data || {},
    ),

  runMaintenance: (id: number | string, data?: { full?: boolean }) =>
    api.post(`/api/v1/backup-tasks/tasks/${id}/run-maintenance/`, data || {}),

  runs: (id: number | string, params?: {
    page?: number;
    page_size?: number;
    status?: string;
    trigger_type?: string;
    result?: string;
    ordering?: string;
  }) =>
    api.get(`/api/v1/backup-tasks/tasks/${id}/runs/`, { params }),

  listSnapshots: (params?: {
    node?: number | string;
    repository?: number | string;
    search?: string;
    status?: string;
    snapshot_status?: string;
    snapshot_kind?: string;
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
