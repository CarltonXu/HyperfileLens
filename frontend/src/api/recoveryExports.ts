import api, { type AxiosRequestConfig } from "./client";

export const recoveryExportsApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    snapshot?: string;
    ordering?: string;
  }) => api.get("/api/v1/recovery-tasks/exports/", { params }),

  detail: (id: number | string) =>
    api.get(`/api/v1/recovery-tasks/exports/${id}/`),

  create: (data: any) => api.post("/api/v1/recovery-tasks/exports/", data),

  execute: (id: number | string) =>
    api.post(`/api/v1/recovery-tasks/exports/${id}/execute/`),

  cancel: (id: number | string) =>
    api.post(`/api/v1/recovery-tasks/exports/${id}/cancel/`),

  share: (id: number | string, data: any) =>
    api.post(`/api/v1/recovery-tasks/exports/${id}/share/`, data),

  publicInfo: (id: number | string, token: string) =>
    api.get(`/api/v1/recovery-tasks/exports/${id}/public-info/`, {
      params: { token },
      _skipGlobalErrorHandler: true,
    } as AxiosRequestConfig),

  publicDownload: (
    id: number | string,
    data: { token: string; password: string },
  ) =>
    api.post(`/api/v1/recovery-tasks/exports/${id}/public-download/`, data, {
      responseType: "blob",
      _skipGlobalErrorHandler: true,
    } as AxiosRequestConfig),

  bulkDelete: (ids: Array<number | string>) =>
    api.post("/api/v1/recovery-tasks/exports/bulk-delete/", { ids }),

  downloadUrl: (id: number | string) =>
    `/api/v1/recovery-tasks/exports/${id}/download/`,
};
