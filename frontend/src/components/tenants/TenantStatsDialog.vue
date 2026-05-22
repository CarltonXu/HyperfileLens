<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  CircleStackIcon,
  ServerIcon,
  UsersIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";
import type { Tenant } from "@/types/tenant";

defineProps<{
  show: boolean;
  tenant: Tenant | null;
  statsData: any;
  loading: boolean;
  formatBytes: (bytes: number) => string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n();
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-full items-center justify-center p-4">
        <div
          class="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
          @click="emit('close')"
        />

        <div
          class="relative modal-surface rounded-lg shadow-xl max-w-2xl w-full"
        >
          <div
            class="px-6 py-4 border-b border-border flex items-center justify-between"
          >
            <div>
              <h3 class="text-lg font-medium text-foreground">
                {{ t("tenants.stats") }}
              </h3>
              <p class="mt-1 text-sm text-foreground-secondary">
                {{ tenant?.name }}
              </p>
            </div>
            <button
              type="button"
              class="rounded-lg text-foreground-muted hover:text-slate-500 dark:hover:text-slate-400"
              @click="emit('close')"
            >
              <XMarkIcon class="h-6 w-6" aria-hidden="true" />
            </button>
          </div>

          <div class="px-6 py-4">
            <div v-if="loading" class="text-center py-8">
              <svg
                class="animate-spin h-8 w-8 text-indigo-600 mx-auto"
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

            <div v-else class="space-y-6">
              <div class="grid grid-cols-2 gap-4">
                <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                  <div class="flex items-center">
                    <UsersIcon class="h-8 w-8 text-blue-600" />
                    <div class="ml-3">
                      <p class="text-sm text-blue-600 dark:text-blue-400">
                        {{ t("tenants.userCount") }}
                      </p>
                      <p class="text-2xl font-bold text-foreground">
                        {{ statsData?.user_count || 0 }}
                      </p>
                    </div>
                  </div>
                  <p class="text-xs text-foreground-secondary mt-2">
                    {{ t("tenants.limit") || "Limit" }}:
                    {{ statsData?.max_users || "∞" }}
                  </p>
                </div>
                <div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                  <div class="flex items-center">
                    <ServerIcon class="h-8 w-8 text-green-600" />
                    <div class="ml-3">
                      <p class="text-sm text-green-600 dark:text-green-400">
                        {{ t("tenants.proxyCount") }}
                      </p>
                      <p class="text-2xl font-bold text-foreground">
                        {{ statsData?.proxy_count || 0 }}
                      </p>
                    </div>
                  </div>
                  <p class="text-xs text-foreground-secondary mt-2">
                    {{ t("tenants.limit") || "Limit" }}:
                    {{ statsData?.max_proxies || "∞" }}
                  </p>
                </div>
                <div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                  <div class="flex items-center">
                    <CircleStackIcon class="h-8 w-8 text-purple-600" />
                    <div class="ml-3">
                      <p class="text-sm text-purple-600 dark:text-purple-400">
                        {{ t("tenants.repositoryCount") }}
                      </p>
                      <p class="text-2xl font-bold text-foreground">
                        {{ statsData?.repository_count || 0 }}
                      </p>
                    </div>
                  </div>
                  <p class="text-xs text-foreground-secondary mt-2">
                    {{ t("tenants.limit") || "Limit" }}:
                    {{ statsData?.max_repositories || "∞" }}
                  </p>
                </div>
                <div class="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
                  <div class="flex items-center">
                    <CircleStackIcon class="h-8 w-8 text-orange-600" />
                    <div class="ml-3">
                      <p class="text-sm text-orange-600 dark:text-orange-400">
                        {{ t("tenants.storageUsed") }}
                      </p>
                      <p class="text-2xl font-bold text-foreground">
                        {{ formatBytes(statsData?.storage_used || 0) }}
                      </p>
                    </div>
                  </div>
                  <p class="text-xs text-foreground-secondary mt-2">
                    {{ t("tenants.limit") || "Limit" }}:
                    {{
                      statsData?.max_storage_gb
                        ? `${statsData.max_storage_gb} GB`
                        : "∞"
                    }}
                  </p>
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
