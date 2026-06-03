import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
} from "axios";
import { getApiErrorMessage } from "@/utils/errors";

const getBaseURL = () => {
  return "";
};

const api: AxiosInstance = axios.create({
  baseURL: getBaseURL(),
  timeout: Number(import.meta.env.VITE_API_TIMEOUT) || 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    const requestUrl = config.url || "";
    const isPublicAuthRequest =
      requestUrl.includes("/api/v1/accounts/login/") ||
      requestUrl.includes("/api/v1/accounts/register") ||
      requestUrl.includes("/api/v1/accounts/forgot-password/") ||
      requestUrl.includes("/api/v1/accounts/verify-reset-code/") ||
      requestUrl.includes("/api/v1/accounts/reset-password/") ||
      requestUrl.includes("/api/v1/accounts/mfa/") ||
      requestUrl.includes("/api/v1/tenants/invitations/validate/") ||
      requestUrl.includes("/api/v1/tenants/invitations/accept/");
    const token = localStorage.getItem("token");
    if (token && !isPublicAuthRequest) {
      config.headers.Authorization = `Token ${token}`;
    }

    if (config.method !== "get") {
      const csrfToken = getCsrfToken();
      if (csrfToken) {
        config.headers["X-CSRFToken"] = csrfToken;
      }
    }

    return config;
  },
  (error) => Promise.reject(error),
);

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean;
      _skipGlobalErrorHandler?: boolean;
    };

    if (originalRequest._skipGlobalErrorHandler) {
      return Promise.reject(error);
    }

    const requestUrl = originalRequest.url || "";
    const isAuthRequest =
      requestUrl.includes("/api/v1/accounts/login/") ||
      requestUrl.includes("/api/v1/accounts/register") ||
      requestUrl.includes("/api/v1/accounts/forgot-password/") ||
      requestUrl.includes("/api/v1/accounts/verify-reset-code/") ||
      requestUrl.includes("/api/v1/accounts/reset-password/") ||
      requestUrl.includes("/api/v1/accounts/mfa/") ||
      requestUrl.includes("/api/v1/tenants/invitations/validate/") ||
      requestUrl.includes("/api/v1/tenants/invitations/accept/");

    if (error.response?.status === 401 && isAuthRequest) {
      return Promise.reject(error);
    }

    const isAuthPage = [
      "/login",
      "/register",
      "/forgot-password",
      "/accept-invitation",
    ].includes(window.location.pathname);

    if (error.response?.status === 401 && isAuthPage) {
      localStorage.removeItem("token");
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      localStorage.removeItem("token");
      window.location.href = "/login";
      return Promise.reject(error);
    }

    if (error.response?.status === 400 || error.response?.status === 422) {
      return Promise.reject(error);
    }

    let errorMessage = "An unexpected error occurred";
    let errorTitle = "Error";

    if (error.response) {
      errorMessage = getApiErrorMessage(error, "The server returned an error");

      switch (error.response.status) {
        case 403:
          errorTitle = "Access Denied";
          break;
        case 404:
          errorTitle = "Not Found";
          break;
        case 500:
          errorTitle = "Server Error";
          errorMessage =
            errorMessage ||
            "An internal server error occurred. Please try again later.";
          break;
        case 502:
        case 503:
        case 504:
          errorTitle = "Service Unavailable";
          errorMessage =
            "The service is temporarily unavailable. Please try again later.";
          break;
      }
    } else if (error.request) {
      if (error.code === "ECONNABORTED" || error.message.includes("timeout")) {
        errorTitle = "Request Timeout";
        errorMessage =
          "The request took too long to complete. Please try again.";
      } else {
        errorTitle = "Network Error";
        errorMessage =
          "Unable to connect to the server. Please check your network connection.";
      }
    } else {
      errorMessage = error.message || "An unexpected error occurred";
    }

    import("@/stores/app").then(({ useAppStore }) => {
      const appStore = useAppStore();
      appStore.showToast({
        type: "error",
        title: errorTitle,
        message: errorMessage,
        duration: 5000,
      });
    });

    return Promise.reject(error);
  },
);

function getCsrfToken(): string | null {
  const name = "csrftoken";
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

export default api;
export type { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse };
