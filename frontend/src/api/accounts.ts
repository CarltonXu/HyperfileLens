import api from "./client";

export const captchaApi = {
  get: () => api.get("/api/v1/accounts/captcha/"),
  validate: (key: string, code: string) =>
    api.post("/api/v1/accounts/captcha/validate/", { key, code }),
};

export const mfaApi = {
  getSetup: () => api.get("/api/v1/accounts/mfa/"),

  enable: (method: "email" | "totp", code: string) =>
    api.post("/api/v1/accounts/mfa/", { method, code }),

  disable: () => api.delete("/api/v1/accounts/mfa/"),

  requestCode: (email: string, login_token: string) =>
    api.post("/api/v1/accounts/mfa/verify/", { email, login_token }),

  verify: (email: string, login_token: string, code: string) =>
    api.put("/api/v1/accounts/mfa/verify/", { email, login_token, code }),
};
