import api from "./client";

export const auditLogApi = {
  list: (params?: Record<string, unknown>) =>
    api.get("/api/v1/audit/audit/", { params }),
  retrieve: (id: string) => api.get(`/api/v1/audit/audit/${id}/`),
  statistics: () => api.get("/api/v1/audit/audit/statistics/"),
  export: (format: "json" | "csv" = "json") =>
    api.get("/api/v1/audit/audit/export/", {
      params: { format },
      responseType: "blob",
    }),
};

export const eventLogApi = {
  list: (params?: Record<string, unknown>) =>
    api.get("/api/v1/audit/events/", { params }),
  retrieve: (id: string) => api.get(`/api/v1/audit/events/${id}/`),
  statistics: () => api.get("/api/v1/audit/events/statistics/"),
  alerts: () => api.get("/api/v1/audit/events/alerts/"),
  handle: (id: string, note?: string) =>
    api.post(`/api/v1/audit/events/${id}/handle/`, { note }),
  unhandle: (id: string) => api.post(`/api/v1/audit/events/${id}/unhandle/`),
};
