import api from "./client";

export const sourceResourcesApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    resource_type?: string;
  }) => api.get("/api/v1/source-resources/", { params }),

  detail: (id: number | string) => api.get(`/api/v1/source-resources/${id}/`),

  create: (data: any) => api.post("/api/v1/source-resources/", data),

  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/source-resources/${id}/`, data),

  delete: (id: number | string) =>
    api.delete(`/api/v1/source-resources/${id}/`),

  stats: () => api.get("/api/v1/source-resources/statistics/"),

  testConnection: (id: number | string) =>
    api.post(`/api/v1/source-resources/${id}/test-connection/`),

  testDraft: (data: any) =>
    api.post("/api/v1/source-resources/test-draft/", data, {
      timeout: 60000,
    }),

  scan: (id: number | string, path?: string) =>
    api.get(`/api/v1/source-resources/${id}/scan/`, { params: { path } }),

  mount: (id: number | string) =>
    api.post(`/api/v1/source-resources/${id}/mount/`),

  unmount: (id: number | string) =>
    api.post(`/api/v1/source-resources/${id}/unmount/`),

  bindNode: (id: number | string, nodeId: number | string) =>
    api.post(`/api/v1/source-resources/${id}/bind-node/`, { node_id: nodeId }),

  unbindNode: (id: number | string) =>
    api.post(`/api/v1/source-resources/${id}/unbind-node/`),
};
