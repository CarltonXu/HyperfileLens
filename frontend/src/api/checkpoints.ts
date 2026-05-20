import api from "./client";

export const checkpointsApi = {
  listBackups: (params?: Record<string, unknown>) =>
    api.get("/api/v1/checkpoints/backups/", { params }),

  resume: (id: string) => api.post(`/api/v1/checkpoints/backups/${id}/resume/`),

  deleteCheckpoint: (id: string) =>
    api.post(`/api/v1/checkpoints/backups/${id}/delete_checkpoint/`),

  cleanupExpired: () =>
    api.post("/api/v1/checkpoints/backups/cleanup_expired/"),
};
