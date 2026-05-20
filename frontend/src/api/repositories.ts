import api from "./client";

export const repositoriesApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    repository_type?: string;
  }) => api.get("/api/v1/repositories/", { params }),

  detail: (id: number | string) => api.get(`/api/v1/repositories/${id}/`),

  create: (data: any) => api.post("/api/v1/repositories/", data),

  update: (id: number | string, data: any) =>
    api.patch(`/api/v1/repositories/${id}/`, data),

  delete: (id: number | string) => api.delete(`/api/v1/repositories/${id}/`),

  stats: () => api.get("/api/v1/repositories/statistics/"),

  testConnection: (id: number | string) =>
    api.post(`/api/v1/repositories/${id}/test_connection/`),

  initKopia: (
    id: number | string,
    data: { encryption_password: string; confirm_password: string },
  ) => api.post(`/api/v1/repositories/${id}/initialize/`, data),

  saveKopiaPassword: (
    id: number | string,
    data: { encryption_password: string; confirm_password: string },
  ) => api.post(`/api/v1/repositories/${id}/password/`, data),

  bindNode: (id: number | string, nodeId: number | string) =>
    api.post(`/api/v1/repositories/${id}/bind-node/`, { node_id: nodeId }),

  unbindNode: (id: number | string) =>
    api.post(`/api/v1/repositories/${id}/unbind-node/`),

  listBuckets: (data: {
    endpoint: string;
    region?: string;
    access_key: string;
    secret_key: string;
    use_tls?: boolean;
    filter_by_region?: boolean;
  }) =>
    api.post("/api/v1/repositories/list_s3_buckets/", data, { timeout: 60000 }),

  checkBucketName: (data: {
    endpoint: string;
    region?: string;
    access_key: string;
    secret_key: string;
    bucket_name: string;
    use_tls?: boolean;
  }) =>
    api.post("/api/v1/repositories/validate_s3_bucket_name/", data, {
      timeout: 30000,
    }),

  createBucket: (data: {
    endpoint: string;
    region?: string;
    access_key: string;
    secret_key: string;
    bucket_name: string;
    use_tls?: boolean;
  }) =>
    api.post("/api/v1/repositories/create_s3_bucket/", data, {
      timeout: 60000,
    }),

  syncUsage: (id: number | string) =>
    api.post(`/api/v1/repositories/${id}/sync_usage/`, {}, { timeout: 120000 }),
};
