import api from "./client";

export const tenantsApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    search?: string;
  }) => api.get("/api/v1/tenants/", { params }),

  detail: (id: number | string) => api.get(`/api/v1/tenants/${id}/`),

  create: (data: any) => api.post("/api/v1/tenants/", data),

  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/tenants/${id}/`, data),

  delete: (id: number | string) => api.delete(`/api/v1/tenants/${id}/`),

  stats: (id: number | string) => api.get(`/api/v1/tenants/${id}/stats/`),

  users: (
    id: number | string,
    params?: { page?: number; page_size?: number },
  ) => api.get(`/api/v1/tenants/${id}/users/`, { params }),

  userCandidates: (
    id: number | string,
    params?: { search?: string },
  ) => api.get(`/api/v1/tenants/${id}/user-candidates/`, { params }),

  addUser: (
    id: number | string,
    data: { email: string; role: string; is_superuser?: boolean },
  ) => api.post(`/api/v1/tenants/${id}/users/`, data),

  updateUser: (
    id: number | string,
    userId: string,
    data: { role: string; is_superuser?: boolean },
  ) => api.patch(`/api/v1/tenants/${id}/users/${userId}/`, data),

  removeUser: (id: number | string, userId: string) =>
    api.delete(`/api/v1/tenants/${id}/users/${userId}/`),

  activate: (id: number | string) =>
    api.post(`/api/v1/tenants/${id}/activate/`),

  deactivate: (id: number | string) =>
    api.post(`/api/v1/tenants/${id}/deactivate/`),
};

export const invitationsApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    api.get("/api/v1/tenants/invitations/", { params }),

  create: (data: { email: string; role: string; tenant_id?: string }) =>
    api.post("/api/v1/tenants/invitations/", data),

  validate: (token: string) =>
    api.get("/api/v1/tenants/invitations/validate/", { params: { token } }),

  accept: (data: {
    token: string;
    password: string;
    first_name?: string;
    last_name?: string;
  }) => api.post("/api/v1/tenants/invitations/accept/", data),

  cancel: (id: string) => api.delete(`/api/v1/tenants/invitations/${id}/`),
};
