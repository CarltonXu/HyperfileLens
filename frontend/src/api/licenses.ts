import api from "./client";

export const licensesApi = {
  current: () => api.get("/api/v1/licenses/current/"),

  machineCode: () => api.get("/api/v1/licenses/machine_code/"),

  regenerateMachineCode: () => api.post("/api/v1/licenses/machine_code/"),

  activate: (data: { activation_code: string }) =>
    api.post("/api/v1/licenses/activate/", data),

  history: (params?: { page?: number; page_size?: number }) =>
    api.get("/api/v1/licenses/history/", { params }),

  validate: (quotaType: string, amount: number = 1) =>
    api.get("/api/v1/licenses/validate/", {
      params: { quota_type: quotaType, amount },
    }),

  list: (params?: { page?: number; page_size?: number; status?: string }) =>
    api.get("/api/v1/licenses/", { params }),

  revoke: (id: string) => api.post(`/api/v1/licenses/${id}/revoke/`),
};
