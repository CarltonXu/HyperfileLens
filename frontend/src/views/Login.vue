<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useThemeStore } from "@/stores/theme";
import { useI18n } from "vue-i18n";
import { captchaApi, mfaApi } from "@/api";
import BrandLogo from "@/components/BrandLogo.vue";
import {
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
} from "@heroicons/vue/24/outline";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const themeStore = useThemeStore();
const { t, locale } = useI18n();

function toggleLanguage() {
  const newLocale = locale.value === "zh-CN" ? "en" : "zh-CN";
  locale.value = newLocale;
  localStorage.setItem("locale", newLocale);
}

function cycleTheme() {
  const themes: ("light" | "dark" | "system")[] = ["light", "dark", "system"];
  const currentIndex = themes.indexOf(themeStore.theme);
  const nextIndex = (currentIndex + 1) % themes.length;
  themeStore.setTheme(themes[nextIndex]);
}

const email = ref("");
const password = ref("");
const captcha = ref("");
const rememberMe = ref(false);
const showPassword = ref(false);
const isLoading = ref(false);
const error = ref("");

const captchaUrl = ref("");
const captchaKey = ref("");
const captchaLoading = ref(false);

const showMfaDialog = ref(false);
const mfaCode = ref("");
const mfaMethod = ref<"email" | "totp">("email");
const pendingUserId = ref("");
const loginToken = ref("");

const isValid = computed(() => {
  return (
    email.value.length > 0 &&
    password.value.length > 0 &&
    captcha.value.length > 0
  );
});

async function refreshCaptcha() {
  captchaLoading.value = true;
  try {
    const response = await captchaApi.get();
    captchaUrl.value = response.data.image;
    captchaKey.value = response.data.key;
  } catch (err) {
    console.error("Failed to fetch captcha:", err);
  } finally {
    captchaLoading.value = false;
  }
}

async function handleLogin() {
  if (!isValid.value) return;
  isLoading.value = true;
  error.value = "";

  try {
    const response = await authStore.login({
      email: email.value,
      password: password.value,
      captcha_code: captcha.value,
      captcha_key: captchaKey.value,
    });

    if (response.mfa_required) {
      pendingUserId.value = response.user_id || "";
      mfaMethod.value = response.mfa_method || "email";
      loginToken.value = response.login_token || "";
      showMfaDialog.value = true;
      if (mfaMethod.value === "email") {
        await mfaApi.requestCode(email.value, loginToken.value);
      }
    } else {
      router.push((route.query.redirect as string) || "/");
    }
  } catch (err: any) {
    error.value = err.response?.data?.error || t("auth.invalidCredentials");
    refreshCaptcha();
    captcha.value = "";
  } finally {
    isLoading.value = false;
  }
}

async function handleVerifyMfa() {
  if (!mfaCode.value) return;
  try {
    isLoading.value = true;
    await authStore.verifyMfa(email.value, mfaCode.value, loginToken.value);
    router.push((route.query.redirect as string) || "/");
  } catch (err: any) {
    error.value = err.response?.data?.error || t("auth.invalidMfaCode");
    mfaCode.value = "";
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  refreshCaptcha();
});
</script>

<template>
  <div
    class="min-h-screen flex items-center justify-center relative overflow-hidden bg-gradient-to-br from-slate-100 via-slate-50 to-slate-100 dark:from-black dark:via-neutral-950 dark:to-black p-4"
  >
    <!-- Animated Background -->
    <div class="absolute inset-0 overflow-hidden">
      <!-- Grid Pattern -->
      <div
        class="absolute inset-0 opacity-30 dark:opacity-20"
        style="
          background-image:
            linear-gradient(rgba(59, 130, 246, 0.3) 1px, transparent 1px),
            linear-gradient(90deg, rgba(59, 130, 246, 0.3) 1px, transparent 1px);
          background-size: 50px 50px;
        "
      ></div>

      <!-- Floating Particles -->
      <div
        class="absolute top-1/4 left-1/4 w-64 h-64 bg-blue-500/10 dark:bg-blue-500/10 rounded-full blur-3xl animate-pulse"
      ></div>
      <div
        class="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 dark:bg-purple-500/10 rounded-full blur-3xl animate-pulse"
        style="animation-delay: 1s"
      ></div>
      <div
        class="absolute top-1/2 right-1/3 w-48 h-48 bg-cyan-500/10 dark:bg-cyan-500/10 rounded-full blur-3xl animate-pulse"
        style="animation-delay: 2s"
      ></div>

      <!-- Data Stream Lines -->
      <svg
        class="absolute inset-0 w-full h-full opacity-10"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color: #3b82f6; stop-opacity: 0" />
            <stop offset="50%" style="stop-color: #3b82f6; stop-opacity: 1" />
            <stop offset="100%" style="stop-color: #3b82f6; stop-opacity: 0" />
          </linearGradient>
        </defs>
        <line
          x1="0"
          y1="20%"
          x2="100%"
          y2="25%"
          stroke="url(#lineGradient)"
          stroke-width="1"
          class="animate-pulse"
        />
        <line
          x1="0"
          y1="60%"
          x2="100%"
          y2="55%"
          stroke="url(#lineGradient)"
          stroke-width="1"
          class="animate-pulse"
          style="animation-delay: 0.5s"
        />
        <line
          x1="0"
          y1="80%"
          x2="100%"
          y2="85%"
          stroke="url(#lineGradient)"
          stroke-width="1"
          class="animate-pulse"
          style="animation-delay: 1s"
        />
      </svg>
    </div>

    <!-- Top Right Controls -->
    <div class="fixed top-4 right-4 flex items-center gap-2 z-20">
      <!-- Theme Switch -->
      <button
        @click="cycleTheme"
        class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-foreground-secondary hover:text-slate-700 dark:hover:text-white transition-colors bg-card/90 backdrop-blur-sm rounded-lg border border-border shadow-sm"
        :title="t('theme.' + themeStore.theme)"
      >
        <SunIcon v-if="themeStore.theme === 'light'" class="w-4 h-4" />
        <MoonIcon v-else-if="themeStore.theme === 'dark'" class="w-4 h-4" />
        <ComputerDesktopIcon v-else class="w-4 h-4" />
      </button>

      <!-- Language Switch -->
      <button
        @click="toggleLanguage"
        class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-foreground-secondary hover:text-slate-700 dark:hover:text-white transition-colors bg-card/90 backdrop-blur-sm rounded-lg border border-border shadow-sm"
      >
        <svg
          class="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
          />
        </svg>
        {{ locale === "zh-CN" ? "EN" : "中文" }}
      </button>
    </div>

    <div class="w-full max-w-sm relative z-10">
      <!-- Logo & Title -->
      <div class="text-center mb-6">
        <BrandLogo variant="full" size="lg" />
        <p class="text-sm text-foreground-secondary mt-1">
          {{ t("auth.loginSubtitle") }}
        </p>
      </div>

      <!-- Login Card -->
      <div
        class="bg-card/90 backdrop-blur-xl rounded-2xl shadow-xl dark:shadow-2xl border border-border p-5"
      >
        <form @submit.prevent="handleLogin" class="space-y-4">
          <!-- Error -->
          <div
            v-if="error"
            class="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 text-red-600 dark:text-red-400 text-sm px-3 py-2 rounded-lg"
          >
            {{ error }}
          </div>

          <!-- Email -->
          <div>
            <label class="block text-sm text-foreground-secondary mb-1">{{
              t("auth.email")
            }}</label>
            <div class="relative">
              <div
                class="absolute left-3 top-1/2 -translate-y-1/2 text-foreground-muted"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="1.5"
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
              </div>
              <input
                v-model="email"
                type="email"
                class="w-full pl-9 pr-3 py-2 text-sm bg-background-secondary border border-border rounded-lg text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
                :placeholder="t('auth.emailPlaceholder')"
                required
                autofocus
              />
            </div>
          </div>

          <!-- Password -->
          <div>
            <label class="block text-sm text-foreground-secondary mb-1">{{
              t("auth.password")
            }}</label>
            <div class="relative">
              <div
                class="absolute left-3 top-1/2 -translate-y-1/2 text-foreground-muted"
              >
                <svg
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="1.5"
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                  />
                </svg>
              </div>
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                class="w-full pl-9 pr-9 py-2 text-sm bg-background-secondary border border-border rounded-lg text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
                :placeholder="t('auth.passwordPlaceholder')"
                required
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <svg
                  v-if="!showPassword"
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="1.5"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="1.5"
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                  />
                </svg>
                <svg
                  v-else
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="1.5"
                    d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                  />
                </svg>
              </button>
            </div>
          </div>

          <!-- Captcha -->
          <div>
            <label class="block text-sm text-foreground-secondary mb-1">{{
              t("auth.captcha")
            }}</label>
            <div class="flex gap-2">
              <div class="relative flex-1">
                <div
                  class="absolute left-3 top-1/2 -translate-y-1/2 text-foreground-muted"
                >
                  <svg
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="1.5"
                      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                    />
                  </svg>
                </div>
                <input
                  v-model="captcha"
                  type="text"
                  maxlength="6"
                  class="w-full pl-9 pr-3 py-2 text-sm bg-background-secondary border border-border rounded-lg text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 uppercase tracking-wider text-center"
                  :placeholder="t('auth.captchaPlaceholder')"
                  required
                />
              </div>
              <div
                class="relative h-9 w-24 rounded-lg border border-border bg-background-secondary cursor-pointer overflow-hidden hover:border-blue-500/50 transition-colors"
                @click="refreshCaptcha"
                :title="t('auth.refreshCaptcha')"
              >
                <img
                  v-if="captchaUrl"
                  :src="captchaUrl"
                  alt="Captcha"
                  class="h-full w-full object-cover"
                />
                <div
                  v-if="captchaLoading"
                  class="absolute inset-0 bg-white/80 dark:bg-slate-900/80 flex items-center justify-center"
                >
                  <svg
                    class="w-4 h-4 text-blue-400 animate-spin"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      class="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      stroke-width="4"
                    ></circle>
                    <path
                      class="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                </div>
                <div
                  v-if="!captchaUrl && !captchaLoading"
                  class="h-full w-full flex items-center justify-center text-slate-400"
                >
                  <svg
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                </div>
              </div>
            </div>
          </div>

          <!-- Remember & Forgot -->
          <div class="flex items-center justify-between text-sm">
            <label class="flex items-center gap-1.5 cursor-pointer">
              <input
                v-model="rememberMe"
                type="checkbox"
                class="w-3.5 h-3.5 rounded border-border-secondary bg-background text-blue-500 focus:ring-blue-500/50"
              />
              <span class="text-foreground-secondary">{{
                t("auth.rememberMe")
              }}</span>
            </label>
            <router-link
              to="/forgot-password"
              class="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
            >
              {{ t("auth.forgotPassword") }}
            </router-link>
          </div>

          <!-- Submit -->
          <button
            type="submit"
            class="w-full py-2.5 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white text-sm font-medium rounded-lg transition-all shadow-lg shadow-blue-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="!isValid || isLoading"
          >
            <span
              v-if="isLoading"
              class="flex items-center justify-center gap-2"
            >
              <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              {{ t("auth.loggingIn") }}
            </span>
            <span v-else>{{ t("auth.login") }}</span>
          </button>
        </form>

        <!-- Divider -->
        <div class="relative my-4">
          <div class="absolute inset-0 flex items-center">
            <div class="w-full border-t border-border"></div>
          </div>
          <div class="relative flex justify-center text-xs">
            <span class="px-2 bg-card/90 text-foreground-muted">{{
              t("auth.or")
            }}</span>
          </div>
        </div>

        <!-- Register Link -->
        <p class="text-center text-sm text-foreground-secondary">
          {{ t("auth.noAccount") }}
          <router-link
            to="/register"
            class="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 font-medium transition-colors"
          >
            {{ t("auth.registerNow") }}
          </router-link>
        </p>
      </div>

      <!-- Footer -->
      <p class="text-center text-xs text-foreground-muted mt-4">
        &copy; 2024 HyperFileLens · AI-Powered Backup Intelligence
      </p>
    </div>

    <!-- MFA Dialog -->
    <div
      v-if="showMfaDialog"
      class="fixed inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
    >
      <div
        class="modal-surface border border-border rounded-2xl shadow-2xl p-5 w-full max-w-xs"
      >
        <div class="text-center mb-4">
          <BrandLogo variant="mark" size="lg" class="mb-3" />
          <h3 class="text-lg font-medium text-foreground">
            {{ t("auth.mfaRequired") }}
          </h3>
          <p class="text-sm text-foreground-secondary mt-1">
            {{ t("auth.mfaCodeSent") }}
          </p>
        </div>

        <input
          v-model="mfaCode"
          type="text"
          maxlength="6"
          class="w-full px-3 py-3 text-center text-xl tracking-widest bg-background-secondary border border-border rounded-lg text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 mb-4"
          :placeholder="t('auth.mfaCodePlaceholder')"
        />

        <div class="flex gap-2">
          <button
            @click="showMfaDialog = false"
            class="flex-1 py-2 border border-border text-foreground-secondary text-sm rounded-lg hover:bg-hover transition-colors"
          >
            {{ t("common.cancel") }}
          </button>
          <button
            @click="handleVerifyMfa"
            :disabled="!mfaCode || isLoading"
            class="flex-1 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white text-sm rounded-lg hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 transition-all"
          >
            {{ t("auth.verify") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
