<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useThemeStore } from "@/stores/theme";
import { authApi, captchaApi } from "@/api";
import BrandLogo from "@/components/BrandLogo.vue";
import {
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
} from "@heroicons/vue/24/outline";

const { t, locale } = useI18n();
const themeStore = useThemeStore();

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

// Steps: 1=输入邮箱, 2=验证码验证, 3=设置新密码, 4=成功
const currentStep = ref(1);

// Step 1: Email
const email = ref("");
const captcha = ref("");
const captchaUrl = ref("");
const captchaKey = ref("");
const captchaLoading = ref(false);

// Step 2: Verification code
const verificationCode = ref("");
const resetToken = ref("");

// Step 3: New password
const newPassword = ref("");
const confirmPassword = ref("");
const showNewPassword = ref(false);
const showConfirmPassword = ref(false);

const isLoading = ref(false);
const error = ref("");
const success = ref("");

const isValidStep1 = computed(
  () => email.value.length > 0 && captcha.value.length > 0,
);
const isValidStep2 = computed(() => verificationCode.value.length >= 6);
const isValidStep3 = computed(
  () =>
    newPassword.value.length >= 8 &&
    newPassword.value === confirmPassword.value,
);

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

async function sendResetEmail() {
  if (!isValidStep1.value) return;

  isLoading.value = true;
  error.value = "";
  success.value = "";

  try {
    const response = await authApi.forgotPassword(
      email.value,
      captchaKey.value,
      captcha.value,
    );
    resetToken.value = response.data.reset_token;
    currentStep.value = 2;
    success.value = t("auth.resetCodeSent");
  } catch (err: any) {
    error.value = err.response?.data?.error || t("auth.sendResetFailed");
    refreshCaptcha();
    captcha.value = "";
  } finally {
    isLoading.value = false;
  }
}

async function verifyCode() {
  if (!isValidStep2.value) return;

  isLoading.value = true;
  error.value = "";

  try {
    await authApi.verifyResetCode(email.value, verificationCode.value);
    currentStep.value = 3;
    success.value = t("auth.codeVerified");
  } catch (err: any) {
    error.value = err.response?.data?.error || t("auth.invalidCode");
    verificationCode.value = "";
  } finally {
    isLoading.value = false;
  }
}

async function resetPassword() {
  if (!isValidStep3.value) return;

  if (newPassword.value !== confirmPassword.value) {
    error.value = t("auth.passwordMismatch");
    return;
  }

  isLoading.value = true;
  error.value = "";

  try {
    await authApi.resetPassword(resetToken.value, newPassword.value);
    currentStep.value = 4;
    success.value = t("auth.passwordResetSuccess");
  } catch (err: any) {
    error.value = err.response?.data?.error || t("auth.resetPasswordFailed");
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
            linear-gradient(rgba(168, 85, 247, 0.3) 1px, transparent 1px),
            linear-gradient(90deg, rgba(168, 85, 247, 0.3) 1px, transparent 1px);
          background-size: 50px 50px;
        "
      ></div>

      <!-- Floating Particles -->
      <div
        class="absolute top-1/4 left-1/4 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl animate-pulse"
      ></div>
      <div
        class="absolute bottom-1/4 right-1/4 w-96 h-96 bg-pink-500/10 rounded-full blur-3xl animate-pulse"
        style="animation-delay: 1s"
      ></div>
      <div
        class="absolute top-1/2 right-1/3 w-48 h-48 bg-violet-500/10 rounded-full blur-3xl animate-pulse"
        style="animation-delay: 2s"
      ></div>

      <!-- Data Stream Lines -->
      <svg
        class="absolute inset-0 w-full h-full opacity-10"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color: #a855f7; stop-opacity: 0" />
            <stop offset="50%" style="stop-color: #a855f7; stop-opacity: 1" />
            <stop offset="100%" style="stop-color: #a855f7; stop-opacity: 0" />
          </linearGradient>
        </defs>
        <line
          x1="0"
          y1="25%"
          x2="100%"
          y2="30%"
          stroke="url(#lineGradient)"
          stroke-width="1"
          class="animate-pulse"
        />
        <line
          x1="0"
          y1="55%"
          x2="100%"
          y2="50%"
          stroke="url(#lineGradient)"
          stroke-width="1"
          class="animate-pulse"
          style="animation-delay: 0.5s"
        />
        <line
          x1="0"
          y1="75%"
          x2="100%"
          y2="70%"
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
        <router-link
          to="/login"
          class="mb-3 inline-flex transition-transform hover:scale-105"
        >
          <BrandLogo variant="mark" size="lg" />
        </router-link>
        <h1 class="text-xl font-bold text-foreground tracking-tight">
          {{ t("auth.forgotPassword") }}
        </h1>
        <p class="text-sm text-foreground-secondary mt-1">
          {{ t("auth.forgotPasswordSubtitle") }}
        </p>
      </div>

      <!-- Progress Steps -->
      <div class="flex items-center justify-center gap-1 mb-5">
        <div
          :class="[
            'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-colors',
            currentStep >= 1
              ? 'bg-purple-500 text-white'
              : 'bg-slate-200 text-slate-400',
          ]"
        >
          1
        </div>
        <div
          :class="[
            'w-6 h-0.5 transition-colors',
            currentStep >= 2 ? 'bg-purple-500' : 'bg-slate-200',
          ]"
        ></div>
        <div
          :class="[
            'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-colors',
            currentStep >= 2
              ? 'bg-purple-500 text-white'
              : 'bg-slate-200 text-slate-400',
          ]"
        >
          2
        </div>
        <div
          :class="[
            'w-6 h-0.5 transition-colors',
            currentStep >= 3 ? 'bg-purple-500' : 'bg-slate-200',
          ]"
        ></div>
        <div
          :class="[
            'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-colors',
            currentStep >= 3
              ? 'bg-purple-500 text-white'
              : 'bg-slate-200 text-slate-400',
          ]"
        >
          3
        </div>
        <div
          :class="[
            'w-6 h-0.5 transition-colors',
            currentStep >= 4 ? 'bg-purple-500' : 'bg-slate-200',
          ]"
        ></div>
        <div
          :class="[
            'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-colors',
            currentStep >= 4
              ? 'bg-purple-500 text-white'
              : 'bg-slate-200 text-slate-400',
          ]"
        >
          <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fill-rule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clip-rule="evenodd"
            />
          </svg>
        </div>
      </div>

      <!-- Form Card -->
      <div
        class="bg-card/90 backdrop-blur-xl rounded-2xl shadow-xl dark:shadow-2xl border border-border p-5"
      >
        <!-- Error Message -->
        <div
          v-if="error"
          class="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 text-red-600 dark:text-red-400 text-sm px-3 py-2 rounded-lg mb-4"
        >
          {{ error }}
        </div>

        <!-- Success Message -->
        <div
          v-if="success"
          class="bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-sm px-3 py-2 rounded-lg mb-4"
        >
          {{ success }}
        </div>

        <!-- Step 1: Enter Email -->
        <form
          v-if="currentStep === 1"
          @submit.prevent="sendResetEmail"
          class="space-y-4"
        >
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
                class="w-full pl-9 pr-3 py-2 text-sm bg-background-secondary border border-border rounded-lg text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50"
                :placeholder="t('auth.emailPlaceholder')"
                required
              />
            </div>
          </div>

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
                  class="w-full pl-9 pr-3 py-2 text-sm bg-background-secondary border border-border rounded-lg text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 uppercase tracking-wider text-center"
                  :placeholder="t('auth.captchaPlaceholder')"
                  required
                />
              </div>
              <div
                class="relative h-9 w-24 rounded-lg border border-border bg-background-secondary cursor-pointer overflow-hidden hover:border-purple-500/50 transition-colors"
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
                    class="w-4 h-4 text-purple-400 animate-spin"
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

          <button
            type="submit"
            :disabled="!isValidStep1 || isLoading"
            class="w-full py-2.5 bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white text-sm font-medium rounded-lg transition-all shadow-lg shadow-purple-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t("auth.sendResetCode") }}
          </button>
        </form>

        <!-- Step 2: Verify Code -->
        <form
          v-if="currentStep === 2"
          @submit.prevent="verifyCode"
          class="space-y-4"
        >
          <p class="text-sm text-foreground-secondary">
            {{ t("auth.enterVerificationCode") }}
          </p>
          <div>
            <label class="block text-sm text-foreground-secondary mb-1">{{
              t("auth.verificationCode")
            }}</label>
            <input
              v-model="verificationCode"
              type="text"
              maxlength="6"
              class="w-full px-3 py-3 text-lg bg-background-secondary border border-border rounded-lg text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 text-center tracking-widest uppercase"
              :placeholder="t('auth.verificationCodePlaceholder')"
              required
            />
          </div>
          <button
            type="submit"
            :disabled="!isValidStep2 || isLoading"
            class="w-full py-2.5 bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white text-sm font-medium rounded-lg transition-all shadow-lg shadow-purple-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t("auth.verifyCode") }}
          </button>
        </form>

        <!-- Step 3: Set New Password -->
        <form
          v-if="currentStep === 3"
          @submit.prevent="resetPassword"
          class="space-y-4"
        >
          <div>
            <label class="block text-sm text-foreground-secondary mb-1">{{
              t("auth.newPassword")
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
                v-model="newPassword"
                :type="showNewPassword ? 'text' : 'password'"
                class="w-full pl-9 pr-9 py-2 text-sm bg-background-secondary border border-border rounded-lg text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50"
                :placeholder="t('auth.newPasswordPlaceholder')"
                required
              />
              <button
                type="button"
                @click="showNewPassword = !showNewPassword"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <svg
                  v-if="!showNewPassword"
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

          <div>
            <label class="block text-sm text-foreground-secondary mb-1">{{
              t("auth.confirmPassword")
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
                    d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                  />
                </svg>
              </div>
              <input
                v-model="confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                class="w-full pl-9 pr-9 py-2 text-sm bg-background-secondary border rounded-lg text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50"
                :class="
                  confirmPassword && newPassword !== confirmPassword
                    ? 'border-red-400 dark:border-red-500/50'
                    : 'border-border'
                "
                :placeholder="t('auth.confirmPasswordPlaceholder')"
                required
              />
              <button
                type="button"
                @click="showConfirmPassword = !showConfirmPassword"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <svg
                  v-if="!showConfirmPassword"
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
            <p
              v-if="confirmPassword && newPassword !== confirmPassword"
              class="text-xs text-red-500 dark:text-red-400 mt-1"
            >
              {{ t("auth.passwordMismatch") }}
            </p>
          </div>

          <button
            type="submit"
            :disabled="!isValidStep3 || isLoading"
            class="w-full py-2.5 bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white text-sm font-medium rounded-lg transition-all shadow-lg shadow-purple-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t("auth.resetPassword") }}
          </button>
        </form>

        <!-- Step 4: Success -->
        <div v-if="currentStep === 4" class="text-center py-4">
          <div
            class="w-14 h-14 bg-gradient-to-br from-emerald-500 to-cyan-600 rounded-xl flex items-center justify-center mx-auto mb-3 shadow-lg shadow-emerald-500/25"
          >
            <svg
              class="w-7 h-7 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h3 class="text-lg font-medium text-foreground mb-1">
            {{ t("auth.passwordResetSuccess") }}
          </h3>
          <p class="text-sm text-foreground-secondary mb-4">
            {{ t("auth.canNowLogin") }}
          </p>
          <router-link
            to="/login"
            class="inline-flex items-center justify-center px-5 py-2.5 bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white text-sm font-medium rounded-lg transition-all shadow-lg shadow-purple-500/25"
          >
            {{ t("auth.goToLogin") }}
          </router-link>
        </div>

        <!-- Back to Login -->
        <div
          v-if="currentStep < 4"
          class="mt-4 pt-4 border-t border-border text-center"
        >
          <router-link
            to="/login"
            class="text-sm text-foreground-secondary hover:text-slate-700 dark:hover:text-white inline-flex items-center gap-1 transition-colors"
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
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            {{ t("auth.backToLogin") }}
          </router-link>
        </div>
      </div>

      <!-- Footer -->
      <p class="text-center text-xs text-foreground-muted mt-4">
        &copy; 2024 HyperFileLens · AI-Powered Backup Intelligence
      </p>
    </div>
  </div>
</template>
