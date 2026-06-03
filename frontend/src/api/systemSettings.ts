import api from "./client";

export interface SMTPConfig {
  id: string;
  name: string;
  host: string;
  port: number;
  username: string;
  use_tls: boolean;
  use_ssl: boolean;
  from_email: string;
  from_name: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  password?: string;
}

export const smtpApi = {
  list: () => api.get<SMTPConfig[]>("/api/v1/system/smtp/"),

  get: (id: string) => api.get<SMTPConfig>(`/api/v1/system/smtp/${id}/`),

  create: (data: Partial<SMTPConfig>) =>
    api.post<SMTPConfig>("/api/v1/system/smtp/", data),

  update: (id: string, data: Partial<SMTPConfig>) =>
    api.patch<SMTPConfig>(`/api/v1/system/smtp/${id}/`, data),

  delete: (id: string) => api.delete(`/api/v1/system/smtp/${id}/`),

  testConnection: (id: string) =>
    api.post<{ success: boolean; message: string }>(
      `/api/v1/system/smtp/${id}/test_connection/`,
    ),

  sendTestEmail: (id: string, to_email: string) =>
    api.post<{ success: boolean; message: string }>(
      `/api/v1/system/smtp/${id}/send_test_email/`,
      { to_email },
    ),

  setDefault: (id: string) =>
    api.post<{ success: boolean; message: string }>(
      `/api/v1/system/smtp/${id}/set_default/`,
    ),

  getDefault: () => api.get<SMTPConfig>("/api/v1/system/smtp/default/"),
};
