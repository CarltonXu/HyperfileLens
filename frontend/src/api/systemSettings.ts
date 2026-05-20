import api from "./client";

export interface SystemSetting {
  id: string;
  key: string;
  value: string;
  description: string;
  category: string;
  is_public: boolean;
  created_at: string;
  updated_at: string;
}

export const systemSettingsApi = {
  list: () => api.get<SystemSetting[]>("/api/v1/system/settings/"),

  get: (id: string) => api.get<SystemSetting>(`/api/v1/system/settings/${id}/`),

  getByKey: (key: string) =>
    api.get<SystemSetting>(`/api/v1/system/settings/by_key/?key=${key}`),

  update: (id: string, data: Partial<SystemSetting>) =>
    api.patch<SystemSetting>(`/api/v1/system/settings/${id}/`, data),
};

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
