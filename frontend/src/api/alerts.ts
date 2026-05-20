import api from "./client";

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
    ),
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
