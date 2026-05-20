import api from "./client";
import { aiInsightsApi } from "./aiInsights";
import { proxiesApi } from "./proxies";

export default api;

export type {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
} from "./client";

export * from "./accounts";
export * from "./aiInsights";
export * from "./alerts";
export * from "./audit";
export * from "./auth";
export * from "./backupTasks";
export * from "./checkpoints";
export * from "./gateways";
export * from "./insights";
export * from "./licenses";
export * from "./policies";
export * from "./proxies";
export * from "./repositories";
export * from "./recoveryExports";
export * from "./recoveryTasks";
export * from "./schedules";
export * from "./sourceResources";
export * from "./systemSettings";
export * from "./tasks";
export * from "./tenants";
export * from "./users";

/** @deprecated Use proxiesApi instead. */
export const nodesApi = proxiesApi;

/** @deprecated Use aiInsightsApi instead. */
export const aiQueryApi = aiInsightsApi;