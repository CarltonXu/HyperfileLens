<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  CircleStackIcon,
  CheckCircleIcon,
  ChartBarSquareIcon,
  ChartPieIcon,
} from "@heroicons/vue/24/outline";

defineProps<{
  stats: {
    total: number;
    active: number;
    totalCapacity: number;
    totalUsed: number;
  };
  formatBytes: (bytes: number) => string;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
          <CircleStackIcon class="w-4 h-4 text-slate-600 dark:text-slate-400" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("repository.stats.total") }}
          </p>
          <p class="text-xl font-bold text-foreground mt-0.5">{{ stats.total }}</p>
        </div>
      </div>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
          <CheckCircleIcon class="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("repository.stats.active") }}
          </p>
          <p class="text-xl font-bold text-emerald-600 mt-0.5">
            {{ stats.active }}
          </p>
        </div>
      </div>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
          <ChartBarSquareIcon class="w-4 h-4 text-violet-600 dark:text-violet-400" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("repository.stats.totalCapacity") }}
          </p>
          <p class="text-xl font-bold text-violet-600 mt-0.5">
            {{ formatBytes(stats.totalCapacity) }}
          </p>
        </div>
      </div>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
          <ChartPieIcon class="w-4 h-4 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("repository.stats.usedSpace") }}
          </p>
          <p class="text-xl font-bold text-blue-600 mt-0.5">
            {{ formatBytes(stats.totalUsed) }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
