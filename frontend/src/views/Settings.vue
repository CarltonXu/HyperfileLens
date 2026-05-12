<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { useAuthStore } from "@/stores/auth";
import {
  UserCircleIcon,
  KeyIcon,
  PaintBrushIcon,
  LanguageIcon,
  Cog6ToothIcon,
} from "@heroicons/vue/24/outline";
import ThemeSwitcher from "@/components/ThemeSwitcher.vue";
import { usePagination } from "@/composables/usePagination";

const { t, locale } = useI18n();
const authStore = useAuthStore();
const {
  globalPageSize,
  getGlobalPageSize,
  setGlobalPageSizeRef,
  resetAllPageSizes,
  DEFAULT_PAGE_SIZE,
} = usePagination();

const activeTab = ref("profile");

// Preferences form
const preferences = ref({
  defaultPageSize: getGlobalPageSize(),
});

// Profile form
const profile = ref({
  first_name: authStore.user?.first_name || "",
  last_name: authStore.user?.last_name || "",
  email: authStore.user?.email || "",
  phone: authStore.user?.phone || "",
});

// Password form
const passwordForm = ref({
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const isSaving = ref(false);
const isChangingPassword = ref(false);
const passwordError = ref("");
const passwordSuccess = ref("");

// Get user initials for avatar
const userInitials = computed(() => {
  const firstName = authStore.user?.first_name || "";
  const lastName = authStore.user?.last_name || "";
  if (firstName || lastName) {
    return (firstName.charAt(0) + lastName.charAt(0)).toUpperCase();
  }
  return authStore.user?.username?.charAt(0).toUpperCase() || "U";
});

// Format date
const formattedCreatedAt = computed(() => {
  if (!authStore.user?.date_joined) return "";
  const date = new Date(authStore.user.date_joined);
  return date.toLocaleDateString(locale.value === "zh-CN" ? "zh-CN" : "en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
});

// Get role display name
const roleDisplayName = computed(() => {
  const roleCode = authStore.user?.role?.code;
  if (roleCode === "admin") return t("settings.profile.roles.admin");
  if (roleCode === "operator") return t("settings.profile.roles.operator");
  return t("settings.profile.roles.viewer");
});

const tabs = computed(() => [
  {
    id: "profile",
    icon: UserCircleIcon,
    label: t("settings.sections.profile"),
  },
  { id: "security", icon: KeyIcon, label: t("settings.sections.security") },
  {
    id: "preferences",
    icon: Cog6ToothIcon,
    label: t("settings.sections.preferences"),
  },
  {
    id: "appearance",
    icon: PaintBrushIcon,
    label: t("settings.sections.appearance"),
  },
  {
    id: "language",
    icon: LanguageIcon,
    label: t("settings.sections.language"),
  },
]);

function setLocale(newLocale: string) {
  locale.value = newLocale;
  localStorage.setItem("locale", newLocale);
}

function savePreferences() {
  setGlobalPageSizeRef(preferences.value.defaultPageSize);
  // Show success message (toast)
  alert(t("settings.preferences.saved"));
}

function resetPreferences() {
  resetAllPageSizes();
  preferences.value.defaultPageSize = DEFAULT_PAGE_SIZE;
  // Show success message (toast)
  alert(t("settings.preferences.reset"));
}

async function saveProfile() {
  isSaving.value = true;
  try {
    // TODO: Call API to save profile
    await new Promise((resolve) => setTimeout(resolve, 500));
    // Show success message
  } finally {
    isSaving.value = false;
  }
}

async function changePassword() {
  passwordError.value = "";
  passwordSuccess.value = "";

  // Validation
  if (!passwordForm.value.currentPassword) {
    passwordError.value = t("settings.security.errors.currentRequired");
    return;
  }
  if (passwordForm.value.newPassword.length < 8) {
    passwordError.value = t("settings.security.errors.minLength");
    return;
  }
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    passwordError.value = t("settings.security.errors.mismatch");
    return;
  }

  isChangingPassword.value = true;
  try {
    // TODO: Call API to change password
    await new Promise((resolve) => setTimeout(resolve, 500));
    passwordSuccess.value = t("settings.security.success");
    passwordForm.value = {
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    };
  } finally {
    isChangingPassword.value = false;
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold text-foreground">
        {{ t("settings.title") }}
      </h1>
      <p class="text-foreground-secondary mt-1">{{ t("settings.subtitle") }}</p>
    </div>

    <!-- Top Tabs -->
    <div class="border-b border-border">
      <nav class="flex space-x-1">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="[
            'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
            activeTab === tab.id
              ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-foreground-secondary hover:text-gray-700 dark:hover:text-slate-300 hover:border-gray-300 dark:hover:border-slate-600',
          ]"
          @click="activeTab = tab.id">
          <component :is="tab.icon" class="w-5 h-5" />
          {{ tab.label }}
        </button>
      </nav>
    </div>

    <!-- Content -->
    <div>
      <!-- Profile -->
      <div
        v-if="activeTab === 'profile'"
        class="bg-card rounded-xl border border-border shadow-sm">
        <div class="px-6 py-4 border-b border-border">
          <h3 class="text-lg font-semibold text-foreground">
            {{ t("settings.profile.title") }}
          </h3>
        </div>
        <div class="p-6 space-y-6">
          <!-- Avatar Section -->
          <div class="flex items-center gap-4">
            <div
              class="w-16 h-16 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold shadow-lg">
              {{ userInitials }}
            </div>
            <div>
              <p class="font-medium text-foreground">
                {{ authStore.user?.username }}
              </p>
              <p class="text-sm text-foreground-secondary">
                {{ roleDisplayName }}
              </p>
            </div>
          </div>

          <!-- Form -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label
                class="block text-sm font-medium text-foreground-secondary mb-1"
                >{{ t("settings.profile.firstName") }}</label
              >
              <input
                v-model="profile.first_name"
                type="text"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div>
              <label
                class="block text-sm font-medium text-foreground-secondary mb-1"
                >{{ t("settings.profile.lastName") }}</label
              >
              <input
                v-model="profile.last_name"
                type="text"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
            <div>
              <label
                class="block text-sm font-medium text-foreground-secondary mb-1"
                >{{ t("settings.profile.email") }}</label
              >
              <input
                v-model="profile.email"
                type="email"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background-secondary text-foreground-secondary cursor-not-allowed"
                disabled />
            </div>
            <div>
              <label
                class="block text-sm font-medium text-foreground-secondary mb-1"
                >{{ t("settings.profile.phone") }}</label
              >
              <input
                v-model="profile.phone"
                type="tel"
                class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            </div>
          </div>

          <!-- Account Info -->
          <div class="pt-4 border-t border-border">
            <h4 class="text-sm font-medium text-foreground-secondary mb-3">
              {{ t("settings.profile.accountInfo") }}
            </h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span class="text-foreground-secondary"
                  >{{ t("settings.profile.username") }}:</span
                >
                <span class="ml-2 text-foreground">{{
                  authStore.user?.username
                }}</span>
              </div>
              <div>
                <span class="text-foreground-secondary"
                  >{{ t("settings.profile.role") }}:</span
                >
                <span class="ml-2 text-foreground">{{ roleDisplayName }}</span>
              </div>
              <div>
                <span class="text-foreground-secondary"
                  >{{ t("settings.profile.createdAt") }}:</span
                >
                <span class="ml-2 text-foreground">{{
                  formattedCreatedAt
                }}</span>
              </div>
            </div>
          </div>

          <div class="flex justify-end">
            <button
              class="px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg font-medium hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md"
              :disabled="isSaving"
              @click="saveProfile">
              {{ isSaving ? t("common.saving") : t("common.save") }}
            </button>
          </div>
        </div>
      </div>

      <!-- Security -->
      <div
        v-if="activeTab === 'security'"
        class="bg-card rounded-xl border border-border shadow-sm">
        <div class="px-6 py-4 border-b border-border">
          <h3 class="text-lg font-semibold text-foreground">
            {{ t("settings.security.title") }}
          </h3>
        </div>
        <div class="p-6 space-y-4">
          <!-- Error/Success Messages -->
          <div
            v-if="passwordError"
            class="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm">
            {{ passwordError }}
          </div>
          <div
            v-if="passwordSuccess"
            class="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 text-sm">
            {{ passwordSuccess }}
          </div>

          <div>
            <label
              class="block text-sm font-medium text-foreground-secondary mb-1"
              >{{ t("settings.security.currentPassword") }}</label
            >
            <input
              v-model="passwordForm.currentPassword"
              type="password"
              class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
          </div>
          <div>
            <label
              class="block text-sm font-medium text-foreground-secondary mb-1"
              >{{ t("settings.security.newPassword") }}</label
            >
            <input
              v-model="passwordForm.newPassword"
              type="password"
              class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            <p class="text-xs text-foreground-secondary mt-1">
              {{ t("settings.security.passwordHint") }}
            </p>
          </div>
          <div>
            <label
              class="block text-sm font-medium text-foreground-secondary mb-1"
              >{{ t("settings.security.confirmPassword") }}</label
            >
            <input
              v-model="passwordForm.confirmPassword"
              type="password"
              class="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
          </div>
          <div class="flex justify-end">
            <button
              class="px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg font-medium hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md"
              :disabled="isChangingPassword"
              @click="changePassword">
              {{
                isChangingPassword
                  ? t("common.saving")
                  : t("settings.security.changePassword")
              }}
            </button>
          </div>
        </div>
      </div>

      <!-- Preferences -->
      <div
        v-if="activeTab === 'preferences'"
        class="bg-card rounded-xl border border-border shadow-sm">
        <div class="px-6 py-4 border-b border-border">
          <h3 class="text-lg font-semibold text-foreground">
            {{ t("settings.preferences.title") }}
          </h3>
        </div>
        <div class="p-6 space-y-6">
          <div>
            <label
              class="block text-sm font-medium text-foreground-secondary mb-2"
              >{{ t("settings.preferences.defaultPageSize") }}</label
            >
            <p class="text-xs text-foreground-secondary mb-3">
              {{ t("settings.preferences.defaultPageSizeDesc") }}
            </p>
            <input
              v-model.number="preferences.defaultPageSize"
              type="number"
              min="5"
              max="100"
              step="5"
              class="w-full max-w-xs px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-indigo-500 focus:border-transparent" />
            <p class="mt-2 text-xs text-foreground-muted">
              {{ t("settings.preferences.currentValue") }}:
              <span class="font-medium text-foreground">{{
                globalPageSize
              }}</span>
            </p>
          </div>

          <div class="flex gap-3">
            <button
              @click="savePreferences"
              class="px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg font-medium hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md">
              {{ t("common.save") }}
            </button>
            <button
              @click="resetPreferences"
              class="px-4 py-2 border border-border bg-background text-foreground hover:bg-hover transition-colors">
              {{ t("settings.preferences.reset") }}
            </button>
          </div>
        </div>
      </div>

      <!-- Appearance -->
      <div
        v-if="activeTab === 'appearance'"
        class="bg-card rounded-xl border border-border shadow-sm">
        <div class="px-6 py-4 border-b border-border">
          <h3 class="text-lg font-semibold text-foreground">
            {{ t("settings.appearance.title") }}
          </h3>
        </div>
        <div class="p-6">
          <div class="space-y-4">
            <div>
              <label
                class="block text-sm font-medium text-foreground-secondary mb-3"
                >{{ t("settings.appearance.theme") }}</label
              >
              <ThemeSwitcher />
            </div>
          </div>
        </div>
      </div>

      <!-- Language -->
      <div
        v-if="activeTab === 'language'"
        class="bg-card rounded-xl border border-border shadow-sm">
        <div class="px-6 py-4 border-b border-border">
          <h3 class="text-lg font-semibold text-foreground">
            {{ t("settings.language.title") }}
          </h3>
        </div>
        <div class="p-6">
          <div class="space-y-3">
            <button
              :class="[
                'w-full flex items-center justify-between p-4 rounded-lg border-2 transition-colors',
                locale === 'en'
                  ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                  : 'border-border hover:border-gray-300 dark:hover:border-slate-500',
              ]"
              @click="setLocale('en')">
              <div class="flex items-center gap-3">
                <span class="text-2xl">🇺🇸</span>
                <div class="text-left">
                  <p class="font-medium text-foreground">
                    {{ t("settings.language.english") }}
                  </p>
                  <p class="text-sm text-foreground-secondary">English</p>
                </div>
              </div>
              <svg
                v-if="locale === 'en'"
                class="w-5 h-5 text-indigo-600 dark:text-indigo-400"
                fill="currentColor"
                viewBox="0 0 20 20">
                <path
                  fill-rule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clip-rule="evenodd" />
              </svg>
            </button>
            <button
              :class="[
                'w-full flex items-center justify-between p-4 rounded-lg border-2 transition-colors',
                locale === 'zh-CN'
                  ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                  : 'border-border hover:border-gray-300 dark:hover:border-slate-500',
              ]"
              @click="setLocale('zh-CN')">
              <div class="flex items-center gap-3">
                <span class="text-2xl">🇨🇳</span>
                <div class="text-left">
                  <p class="font-medium text-foreground">
                    {{ t("settings.language.chinese") }}
                  </p>
                  <p class="text-sm text-foreground-secondary">简体中文</p>
                </div>
              </div>
              <svg
                v-if="locale === 'zh-CN'"
                class="w-5 h-5 text-indigo-600 dark:text-indigo-400"
                fill="currentColor"
                viewBox="0 0 20 20">
                <path
                  fill-rule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
