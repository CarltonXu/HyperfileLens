import api from "./client";

export const authApi = {
  login: (
    email: string,
    password: string,
    captcha_key?: string,
    captcha_code?: string,
  ) =>
    api.post("/api/v1/accounts/login/", {
      email,
      password,
      captcha_key,
      captcha_code,
    }),

  logout: () => api.post("/api/v1/accounts/logout/"),

  register: (data: {
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
    captcha_key?: string;
    captcha_code?: string;
  }) => api.post("/api/v1/accounts/register-v2/", data),

  profile: () => api.get("/api/v1/accounts/profile/"),

  updateProfile: (data: { full_name?: string; phone?: string }) =>
    api.patch("/api/v1/accounts/profile/", data),

  changePassword: (data: { old_password: string; new_password: string }) =>
    api.post("/api/v1/accounts/password/", data),

  forgotPassword: (
    email: string,
    captcha_key?: string,
    captcha_code?: string,
  ) =>
    api.post("/api/v1/accounts/forgot-password/", {
      email,
      captcha_key,
      captcha_code,
    }),

  verifyResetCode: (email: string, code: string) =>
    api.post("/api/v1/accounts/verify-reset-code/", { email, code }),

  resetPassword: (token: string, new_password: string) =>
    api.post("/api/v1/accounts/reset-password/", { token, new_password }),
};
