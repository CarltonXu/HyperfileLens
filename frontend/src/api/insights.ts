import api from "./client";

export const insightsApi = {
  indexSnapshot: (
    snapshotId: number | string,
    data?: { gateway_id?: string; force?: boolean },
  ) => api.post(`/api/v1/insights/snapshots/${snapshotId}/index/`, data || {}),

  indexStatus: (snapshotId: number | string) =>
    api.get(`/api/v1/insights/snapshots/${snapshotId}/index/status/`),

  files: (
    snapshotId: number | string,
    params?: {
      q?: string;
      category?: string;
      extension?: string;
      page?: number;
      page_size?: number;
      ordering?: string;
    },
  ) => api.get(`/api/v1/insights/snapshots/${snapshotId}/files/`, { params }),

  search: (
    snapshotId: number | string,
    params?: { q?: string; limit?: number },
  ) => api.get(`/api/v1/insights/snapshots/${snapshotId}/search/`, { params }),

  insights: (snapshotId: number | string) =>
    api.get(`/api/v1/insights/snapshots/${snapshotId}/insights/`),

  analyze: (snapshotId: number | string) =>
    api.post(`/api/v1/insights/snapshots/${snapshotId}/analyze/`),

  aiSummary: (
    snapshotId: number | string,
    data?: { gateway_id?: string; language?: string },
  ) =>
    api.post(
      `/api/v1/insights/snapshots/${snapshotId}/ai-summary/`,
      data || {},
    ),

  aiJobs: (snapshotId: number | string) =>
    api.get(`/api/v1/insights/snapshots/${snapshotId}/ai-jobs/`),
};
