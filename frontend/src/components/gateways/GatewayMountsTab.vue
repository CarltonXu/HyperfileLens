<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  FolderIcon,
} from "@heroicons/vue/24/outline";

interface Gateway {
  id: string;
  name: string;
  active_mounts: number;
  max_concurrent_mounts: number;
  mount_base_path: string;
}

interface Mount {
  id: string;
  repository_name: string;
  source_path: string;
  mount_path: string;
  status: string;
  created_at: string;
}

defineProps<{
  gateway: Gateway;
  mounts: Mount[];
  isLoading: boolean;
}>();

const { t } = useI18n();

function formatDate(dateStr: string): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString();
}
</script>

<template>
  <div class="space-y-6">
    <!-- Mount Summary -->
    <div class="grid grid-cols-3 gap-4">
      <div class="bg-background-secondary rounded-lg p-4">
        <p class="text-sm text-foreground-secondary">
          {{ t("gateways.mounts.active") }}
        </p>
        <p class="text-2xl font-bold text-foreground mt-1">
          {{ gateway.active_mounts }}
        </p>
      </div>
      <div class="bg-background-secondary rounded-lg p-4">
        <p class="text-sm text-foreground-secondary">
          {{ t("gateways.mounts.maximum") }}
        </p>
        <p class="text-2xl font-bold text-foreground mt-1">
          {{ gateway.max_concurrent_mounts }}
        </p>
      </div>
      <div class="bg-background-secondary rounded-lg p-4">
        <p class="text-sm text-foreground-secondary">
          {{ t("gateways.mounts.basePath") }}
        </p>
        <p class="text-sm font-medium text-foreground mt-1 truncate">
          {{ gateway.mount_base_path }}
        </p>
      </div>
    </div>

    <!-- Mount List -->
    <div>
      <h3 class="text-sm font-semibold text-foreground mb-3">
        {{ t("gateways.mounts.title") }}
      </h3>

      <div
        v-if="isLoading"
        class="flex items-center justify-center py-8"
      >
        <div class="w-6 h-6 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
      </div>

      <div
        v-else-if="mounts.length === 0"
        class="text-center py-8"
      >
        <FolderIcon class="w-12 h-12 text-foreground-muted mx-auto mb-3" />
        <p class="text-foreground-secondary">
          {{ t("gateways.mounts.empty") }}
        </p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="mount in mounts"
          :key="mount.id"
          class="bg-background-secondary rounded-lg p-4"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-3">
              <div
                class="w-8 h-8 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center"
              >
                <FolderIcon class="w-4 h-4 text-violet-600 dark:text-violet-400" />
              </div>
              <div>
                <p class="font-medium text-foreground">
                  {{ mount.repository_name }}
                </p>
                <p class="text-sm text-foreground-secondary">
                  {{ mount.source_path }}
                </p>
              </div>
            </div>
            <span
              :class="[
                'px-2 py-1 text-xs font-medium rounded-full',
                mount.status === 'active'
                  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                  : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400',
              ]"
            >
              {{ mount.status }}
            </span>
          </div>
          <div class="flex items-center justify-between text-sm text-foreground-secondary">
            <div class="flex items-center gap-4">
              <span>{{ mount.mount_path }}</span>
              <span v-if="mount.created_at">{{ formatDate(mount.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
