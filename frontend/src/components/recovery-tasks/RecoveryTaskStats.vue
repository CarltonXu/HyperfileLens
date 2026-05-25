<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ListBulletIcon,
  PlayIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  DocumentArrowUpIcon,
} from "@heroicons/vue/24/outline";

defineProps<{
  stats: {
    total_tasks: number;
    running_tasks: number;
    completed_tasks: number;
    failed_tasks: number;
    total_files: number;
  };
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
            {{ t("recoveryTasks.status.running") }}
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
            {{ t("recoveryTasks.status.completed") }}
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
            {{ t("recoveryTasks.status.failed") }}
          </p>
          <p class="text-xl font-bold text-red-600 mt-0.5">
            {{ stats.failed_tasks }}
          </p>
        </div>
      </div>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
          <DocumentArrowUpIcon class="w-4 h-4 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <p class="text-xs text-foreground-secondary">
            {{ t("recoveryTasks.progress.files") }}
          </p>
          <p class="text-xl font-bold text-blue-600 mt-0.5">
            {{ stats.total_files }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
