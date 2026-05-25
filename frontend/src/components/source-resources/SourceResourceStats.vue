<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ListBulletIcon,
  CheckCircleIcon,
  CircleStackIcon,
  ExclamationTriangleIcon,
} from "@heroicons/vue/24/outline";
import type { SourceResourceStats } from "@/types/sourceResource";

defineProps<{
  stats: SourceResourceStats | null;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
          <ListBulletIcon class="w-4 h-4 text-slate-600 dark:text-slate-400" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("sourceResources.stats.total") }}
          </p>
          <p class="mt-1 text-xl font-bold text-foreground">
            {{ stats?.total_resources || (stats as any)?.total || 0 }}
          </p>
        </div>
      </div>
    </div>
    <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
          <CheckCircleIcon class="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("sourceResources.stats.active") }}
          </p>
          <p class="mt-1 text-xl font-bold text-emerald-600">
            {{ stats?.active_resources || (stats as any)?.active || 0 }}
          </p>
        </div>
      </div>
    </div>
    <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
          <CircleStackIcon class="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("sourceResources.stats.mounted") }}
          </p>
          <p class="mt-1 text-xl font-bold text-indigo-600">
            {{ stats?.mounted_resources || (stats as any)?.mounted || 0 }}
          </p>
        </div>
      </div>
    </div>
    <div class="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
          <ExclamationTriangleIcon class="w-4 h-4 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("sourceResources.stats.error") }}
          </p>
          <p class="mt-1 text-xl font-bold text-red-600">
            {{ stats?.error_resources || (stats as any)?.error || 0 }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
