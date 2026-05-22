<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { PlusIcon, UserMinusIcon, XMarkIcon } from "@heroicons/vue/24/outline";
import type { Tenant } from "@/types/tenant";

defineProps<{
  show: boolean;
  tenant: Tenant | null;
  users: any[];
  loading: boolean;
  showAddUserForm: boolean;
  newUserEmail: string;
  newUserRole: string;
  currentUserId: string | null;
  getInitials: (user: any) => string;
  getDisplayName: (user: any) => string;
}>();

const emit = defineEmits<{
  close: [];
  "update:showAddUserForm": [value: boolean];
  "update:newUserEmail": [value: string];
  "update:newUserRole": [value: string];
  addUser: [];
  updateRole: [userId: string, role: string, isSuperuser: boolean];
  removeUser: [user: any];
}>();

const { t } = useI18n();
</script>

<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="fixed inset-0 z-50 overflow-y-auto"
      aria-labelledby="modal-title"
      role="dialog"
      aria-modal="true"
    >
      <div class="flex min-h-screen items-center justify-center p-4">
        <div
          class="fixed inset-0 bg-slate-900/75 dark:bg-slate-900/75 transition-opacity"
          @click="emit('close')"
        />

        <div
          class="relative modal-surface rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col"
        >
          <div
            class="px-6 py-4 border-b border-border flex items-center justify-between"
          >
            <div>
              <h3 class="text-lg font-semibold text-foreground">
                {{ tenant?.name }} - {{ t("tenants.manageUsers") }}
              </h3>
              <p class="text-sm text-foreground-secondary">
                {{ t("tenants.userCount") }}: {{ users.length }}
              </p>
            </div>
            <button
              class="text-foreground-muted hover:text-slate-600 dark:hover:text-slate-300"
              @click="emit('close')"
            >
              <XMarkIcon class="h-5 w-5" />
            </button>
          </div>

          <div class="flex-1 overflow-y-auto px-6 py-4">
            <div class="mb-6">
              <button
                class="flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-500"
                @click="emit('update:showAddUserForm', !showAddUserForm)"
              >
                <PlusIcon class="h-4 w-4" />
                {{ t("tenants.addUser") }}
              </button>

              <div
                v-if="showAddUserForm"
                class="mt-3 p-4 bg-background-secondary rounded-lg space-y-3"
              >
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label
                      class="block text-xs font-medium text-foreground-secondary mb-1"
                    >
                      {{ t("users.email") }}
                    </label>
                    <input
                      :value="newUserEmail"
                      type="email"
                      :placeholder="t('users.emailPlaceholder')"
                      class="w-full rounded-lg border border-border bg-background text-foreground px-3 py-2 text-sm"
                      @input="
                        emit(
                          'update:newUserEmail',
                          ($event.target as HTMLInputElement).value,
                        )
                      "
                    />
                  </div>
                  <div>
                    <label
                      class="block text-xs font-medium text-foreground-secondary mb-1"
                    >
                      {{ t("users.role") }}
                    </label>
                    <select
                      :value="newUserRole"
                      class="w-full rounded-lg border border-border bg-background text-foreground px-3 py-2 text-sm"
                      @change="
                        emit(
                          'update:newUserRole',
                          ($event.target as HTMLSelectElement).value,
                        )
                      "
                    >
                      <option class="bg-background" value="admin">
                        {{ t("users.roles.admin") }}
                      </option>
                      <option class="bg-background" value="member">
                        {{ t("users.roles.member") }}
                      </option>
                    </select>
                  </div>
                </div>
                <div class="flex justify-end gap-2">
                  <button
                    class="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 dark:text-slate-400"
                    @click="emit('update:showAddUserForm', false)"
                  >
                    {{ t("common.cancel") }}
                  </button>
                  <button
                    :disabled="!newUserEmail"
                    class="bg-indigo-600 text-white rounded-md px-3 py-1.5 text-sm hover:bg-indigo-500 disabled:opacity-50"
                    @click="emit('addUser')"
                  >
                    {{ t("common.add") }}
                  </button>
                </div>
              </div>
            </div>

            <div class="space-y-3">
              <div v-if="loading" class="text-center py-8">
                <svg
                  class="animate-spin h-6 w-6 text-indigo-600 mx-auto"
                  xmlns="http://www.w3.org/2000/svg"
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
                  />
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              </div>
              <div
                v-else-if="users.length === 0"
                class="text-center py-8 text-foreground-secondary"
              >
                {{ t("common.noData") }}
              </div>
              <div
                v-for="user in users"
                v-else
                :key="user.id"
                class="flex items-center justify-between p-4 bg-background rounded-lg border border-border hover:shadow-sm transition-shadow"
              >
                <div class="flex items-center gap-3">
                  <div
                    class="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white font-medium text-sm"
                  >
                    {{ getInitials(user) }}
                  </div>
                  <div>
                    <p class="font-medium text-foreground">
                      {{ getDisplayName(user) }}
                    </p>
                    <p
                      class="text-xs text-foreground-secondary dark:text-slate-400"
                    >
                      {{ user.email }} · ID: {{ user.id }}
                    </p>
                    <div
                      v-if="user.tenant_role === 'admin' && !user.is_superuser"
                      class="flex items-center gap-2 mt-1"
                    >
                      <span
                        class="bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                      >
                        {{ t("users.roles.admin") }}
                      </span>
                    </div>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <select
                    :value="user.tenant_role"
                    :disabled="user.is_superuser"
                    class="rounded-md border-border px-2 py-1.5 text-sm disabled:opacity-50"
                    @change="
                      emit(
                        'updateRole',
                        user.id,
                        ($event.target as HTMLSelectElement).value,
                        user.is_superuser,
                      )
                    "
                  >
                    <option class="bg-background" value="admin">
                      {{ t("users.roles.admin") }}
                    </option>
                    <option class="bg-background" value="member">
                      {{ t("users.roles.member") }}
                    </option>
                  </select>
                  <button
                    :disabled="user.is_superuser || user.id === currentUserId"
                    class="p-1.5 text-foreground-muted hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed"
                    :title="
                      user.is_superuser
                        ? t('tenants.cannotRemoveSuperuser')
                        : user.id === currentUserId
                          ? t('tenants.cannotRemoveSelf')
                          : t('common.remove')
                    "
                    @click="emit('removeUser', user)"
                  >
                    <UserMinusIcon class="h-5 w-5" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="px-6 py-4 border-t border-border flex justify-end">
            <button
              type="button"
              class="rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover transition-colors"
              @click="emit('close')"
            >
              {{ t("common.close") || "Close" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
