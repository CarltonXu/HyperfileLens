import api from "./client";

export const usersApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    tenant_role?: string;
    is_active?: boolean;
  }) => api.get("/api/v1/accounts/users/", { params }),

  create: (data: {
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
    phone?: string;
    tenant_role?: string;
    is_superuser?: boolean;
    tenant_id?: string;
  }) => api.post("/api/v1/accounts/users/", data),

  update: (
    id: string,
    data: {
      email?: string;
      first_name?: string;
      last_name?: string;
      phone?: string;
      tenant_role?: string;
      is_superuser?: boolean;
    },
  ) => api.patch(`/api/v1/accounts/users/${id}/`, data),

  changeRole: (id: string, role: string) =>
    api.post(`/api/v1/accounts/users/${id}/change_role/`, { role }),

  setSuperuser: (id: string, is_superuser: boolean) =>
    api.post(`/api/v1/accounts/users/${id}/set_superuser/`, { is_superuser }),

  enable: (id: string) => api.post(`/api/v1/accounts/users/${id}/enable/`),

  disable: (id: string) => api.post(`/api/v1/accounts/users/${id}/disable/`),

  delete: (id: string) => api.delete(`/api/v1/accounts/users/${id}/`),

  resetPassword: (id: string, newPassword: string) =>
    api.post(`/api/v1/accounts/users/${id}/reset_password/`, {
      new_password: newPassword,
    }),
};
