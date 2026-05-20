import api from "./client";

export const policiesApi = {
  list: (params?: { page?: number; page_size?: number; is_active?: boolean }) =>
    api.get("/api/v1/policies/policies/", { params }),

  detail: (id: number | string) => api.get(`/api/v1/policies/policies/${id}/`),

  create: (data: any) => api.post("/api/v1/policies/policies/", data),

  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/policies/policies/${id}/`, data),

  delete: (id: number | string) =>
    api.delete(`/api/v1/policies/policies/${id}/`),

  enable: (id: number | string) =>
    api.post(`/api/v1/policies/policies/${id}/activate/`),

  disable: (id: number | string) =>
    api.post(`/api/v1/policies/policies/${id}/deactivate/`),
};
