<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { invitationsApi } from "@/api";
import { useAuthStore } from "@/stores/auth";
import { useThemeStore } from "@/stores/theme";
import { getApiErrorMessage } from "@/utils/errors";
import BrandLogo from "@/components/BrandLogo.vue";
import {
  ComputerDesktopIcon,
  MoonIcon,
  SunIcon,
} from "@heroicons/vue/24/outline";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const themeStore = useThemeStore();
const { t, locale } = useI18n();

const loading = ref(true);
const submitting = ref(false);
const error = ref("");
const invitation = ref<{
  email: string;
  tenant: string;
  role: string;
  expires_at: string;
  user_exists: boolean;
} | null>(null);

const form = ref({
  first_name: "",
  last_name: "",
  password: "",
  confirm_password: "",
});

const token = computed(() => String(route.query.token || ""));
const isExistingUser = computed(() => Boolean(invitation.value?.user_exists));
const canSubmit = computed(() => {
  if (!token.value || !form.value.password) return false;
  if (isExistingUser.value) return true;
  return form.value.password === form.value.confirm_password;
});

function toggleLanguage() {
  const newLocale = locale.value === "zh-CN" ? "en" : "zh-CN";
  locale.value = newLocale;
  localStorage.setItem("locale", newLocale);
}

function cycleTheme() {
  const themes: ("light" | "dark" | "system")[] = ["light", "dark", "system"];
  const currentIndex = themes.indexOf(themeStore.theme);
  themeStore.setTheme(themes[(currentIndex + 1) % themes.length]);
}

async function loadInvitation() {
  loading.value = true;
  error.value = "";
  if (!token.value) {
    error.value = t("auth.invitationMissingToken");
    loading.value = false;
    return;
  }

  try {
    const response = await invitationsApi.validate(token.value);
    invitation.value = response.data;
  } catch (err) {
    error.value = getApiErrorMessage(err, t("auth.invitationInvalid"));
  } finally {
    loading.value = false;
  }
}

async function acceptInvitation() {
  if (!canSubmit.value) return;
  if (!isExistingUser.value && form.value.password !== form.value.confirm_password) {
    error.value = t("auth.passwordMismatch");
    return;
  }

  submitting.value = true;
  error.value = "";
  try {
    const response = await invitationsApi.accept({
      token: token.value,
      password: form.value.password,
      first_name: form.value.first_name,
      last_name: form.value.last_name,
    });
    authStore.setAuthenticatedSession(response.data);
    router.push("/");
  } catch (err) {
    error.value = getApiErrorMessage(err, t("auth.invitationAcceptFailed"));
  } finally {
    submitting.value = false;
  }
}

onMounted(loadInvitation);
</script>

<template>
  <div
    class="min-h-screen flex items-center justify-center relative overflow-hidden bg-gradient-to-br from-slate-100 via-slate-50 to-slate-100 dark:from-black dark:via-neutral-950 dark:to-black p-4"
  >
    <div class="fixed top-4 right-4 flex items-center gap-2 z-20">
      <button
        class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-foreground-secondary hover:text-slate-700 dark:hover:text-white transition-colors bg-card/90 backdrop-blur-sm rounded-lg border border-border shadow-sm"
        :title="t('theme.' + themeStore.theme)"
        @click="cycleTheme"
      >
        <SunIcon v-if="themeStore.theme === 'light'" class="w-4 h-4" />
        <MoonIcon v-else-if="themeStore.theme === 'dark'" class="w-4 h-4" />
        <ComputerDesktopIcon v-else class="w-4 h-4" />
      </button>
      <button
        class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-foreground-secondary hover:text-slate-700 dark:hover:text-white transition-colors bg-card/90 backdrop-blur-sm rounded-lg border border-border shadow-sm"
        @click="toggleLanguage"
      >
        {{ locale === "zh-CN" ? "EN" : "中文" }}
      </button>
    </div>

    <div class="w-full max-w-md relative z-10">
      <div class="text-center mb-8">
        <BrandLogo class="h-12 justify-center" />
      </div>

      <div class="bg-card/95 backdrop-blur-sm rounded-2xl shadow-2xl border border-border p-8">
        <div class="mb-6 text-center">
          <h1 class="text-2xl font-bold text-foreground">
            {{ t("auth.acceptInvitation") }}
          </h1>
          <p class="mt-2 text-sm text-foreground-secondary">
            {{ t("auth.acceptInvitationDesc") }}
          </p>
        </div>

        <div v-if="loading" class="py-10 text-center text-sm text-foreground-secondary">
          {{ t("common.loading") }}
        </div>

        <div v-else-if="error && !invitation" class="space-y-4">
          <div class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300">
            {{ error }}
          </div>
          <button
            class="w-full rounded-lg border border-border bg-background px-4 py-2 text-sm font-semibold text-foreground hover:bg-hover"
            @click="router.push('/login')"
          >
            {{ t("auth.backToLogin") }}
          </button>
        </div>

        <form v-else class="space-y-4" @submit.prevent="acceptInvitation">
          <div class="rounded-lg border border-border bg-background-secondary px-4 py-3 text-sm">
            <div class="font-medium text-foreground">{{ invitation?.tenant }}</div>
            <div class="mt-1 text-foreground-secondary">
              {{ invitation?.email }} · {{ invitation?.role }}
            </div>
          </div>

          <div v-if="!isExistingUser" class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-foreground-secondary">
                {{ t("users.firstName") }}
              </label>
              <input
                v-model="form.first_name"
                type="text"
                class="mt-1 block w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-foreground-secondary">
                {{ t("users.lastName") }}
              </label>
              <input
                v-model="form.last_name"
                type="text"
                class="mt-1 block w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-foreground-secondary">
              {{
                isExistingUser
                  ? t("auth.currentPassword")
                  : t("auth.createPassword")
              }}
            </label>
            <input
              v-model="form.password"
              type="password"
              class="mt-1 block w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div v-if="!isExistingUser">
            <label class="block text-sm font-medium text-foreground-secondary">
              {{ t("users.confirmPassword") }}
            </label>
            <input
              v-model="form.confirm_password"
              type="password"
              class="mt-1 block w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div
            v-if="error"
            class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300"
          >
            {{ error }}
          </div>

          <button
            type="submit"
            :disabled="!canSubmit || submitting"
            class="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {{
              submitting
                ? t("common.saving")
                : t("auth.acceptInvitation")
            }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
