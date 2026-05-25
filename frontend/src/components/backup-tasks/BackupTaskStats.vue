<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ListBulletIcon,
  PlayIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  CircleStackIcon,
} from "@heroicons/vue/24/outline";

defineProps<{
  stats: {
    total_tasks: number;
    running_tasks: number;
    completed_tasks: number;
    failed_tasks: number;
  };
  totalBackupSize: number;
  formatBytes: (bytes: number) => string;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
          <ListBulletIcon class="w-4 h-4 text-slate-600 dark:text-slate-400" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">{{ t("common.total") }}</p>
          <p class="text-xl font-bold text-foreground mt-0.5">
            {{ stats.total_tasks }}
          </p>
        </div>
      </div>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
          <PlayIcon class="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("backupTasks.status.running") }}
          </p>
          <p class="text-xl font-bold text-indigo-600 mt-0.5">
            {{ stats.running_tasks }}
          </p>
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
            {{ t("backupTasks.status.completed") }}
          </p>
          <p class="text-xl font-bold text-emerald-600 mt-0.5">
            {{ stats.completed_tasks }}
          </p>
        </div>
      </div>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
          <ExclamationTriangleIcon class="w-4 h-4 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("backupTasks.status.failed") }}
          </p>
          <p class="text-xl font-bold text-red-600 mt-0.5">
            {{ stats.failed_tasks }}
          </p>
        </div>
      </div>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-pink-100 dark:bg-pink-900/30 flex items-center justify-center">
          <CircleStackIcon class="w-4 h-4 text-pink-600 dark:text-pink-400" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("backupTasks.progress.size") }}
          </p>
          <p class="text-xl font-bold text-pink-600 mt-0.5">
            {{ totalBackupSize ? formatBytes(totalBackupSize) : "0 B" }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
