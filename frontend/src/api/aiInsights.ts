import api from "./client";

export const gateway = {
  aiQuery: (data: {
    query: string;
    repository_id?: string;
    filters?: Record<string, unknown>;
  }) => api.post("/api/v1/ai-insights/gateway/ai-query/", data),

  listFiles: (params?: { path?: string; repository_id?: string }) =>
    api.get("/api/v1/ai-insights/gateway/files/", { params }),

  mountStatus: () => api.get("/api/v1/ai-insights/gateway/mount-status/"),

  indexStatus: () => api.get("/api/v1/ai-insights/gateway/index-status/"),

  rebuildIndex: (repositoryId: string) =>
    api.post("/api/v1/ai-insights/gateway/rebuild-index/", {
      repository_id: repositoryId,
    }),
};

export const aiInsightsApi = {
  query: (data: {
    query?: string;
    query_text?: string;
    query_type?: string;
    node?: number;
    repository?: number;
    snapshot_id?: string;
    repository_id?: string;
    gateway_id?: string;
  }) => api.post("/api/v1/ai-insights/queries/", data),

  gatewayQuery: (data: {
    query: string;
    repository_id?: string;
    filters?: Record<string, unknown>;
  }) => gateway.aiQuery(data),

  history: (params?: { page?: number; page_size?: number }) =>
    api.get("/api/v1/ai-insights/queries/", { params }),

  getQuery: (id: number | string) => api.get(`/api/v1/ai-insights/queries/${id}/`),

  cancel: (id: number) => api.post(`/api/v1/ai-insights/queries/${id}/cancel/`),

  overview: () => api.get("/api/v1/ai-insights/overview/"),

  sensitiveData: (params?: { repository_id?: string }) =>
    api.get("/api/v1/ai-insights/sensitive-data/", { params }),

  contentProfiling: (params?: { repository_id?: string }) =>
    api.get("/api/v1/ai-insights/content-profile/", { params }),

  dataHeatmap: (params?: { repository_id?: string; days?: number }) =>
    api.get("/api/v1/ai-insights/data-heatmap/", { params }),

  redundancy: (params?: { repository_id?: string }) =>
    api.get("/api/v1/ai-insights/redundancy/", { params }),

  smartSearch: (params?: {
    query?: string;
    repository_id?: string;
    filters?: Record<string, unknown>;
  }) => api.get("/api/v1/ai-insights/smart-search/", { params }),

  providers: (params?: { page?: number; page_size?: number }) =>
    api.get("/api/v1/system/ai-providers/", { params }),

  defaultProvider: () => api.get("/api/v1/system/ai-providers/default/"),

  createProvider: (data: any) => api.post("/api/v1/system/ai-providers/", data),

  updateProvider: (id: number | string, data: any) =>
    api.patch(`/api/v1/system/ai-providers/${id}/`, data),

  setDefaultProvider: (id: number | string) =>
    api.post(`/api/v1/system/ai-providers/${id}/set-default/`),
};

export const aiQueryApi = aiInsightsApi;
