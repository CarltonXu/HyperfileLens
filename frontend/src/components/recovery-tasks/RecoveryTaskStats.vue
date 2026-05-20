<script setup lang="ts">
import { useI18n } from "vue-i18n";

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
      <p class="text-xs text-foreground-secondary">{{ t("common.total") }}</p>
      <p class="text-xl font-bold text-foreground mt-1">
        {{ stats.total_tasks }}
      </p>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <p class="text-xs text-foreground-secondary">
        {{ t("recoveryTasks.status.running") }}
      </p>
      <p class="text-xl font-bold text-indigo-600 mt-1">
        {{ stats.running_tasks }}
      </p>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <p class="text-xs text-foreground-secondary">
        {{ t("recoveryTasks.status.completed") }}
      </p>
      <p class="text-xl font-bold text-emerald-600 mt-1">
        {{ stats.completed_tasks }}
      </p>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <p class="text-xs text-foreground-secondary">
        {{ t("recoveryTasks.status.failed") }}
      </p>
      <p class="text-xl font-bold text-red-600 mt-1">
        {{ stats.failed_tasks }}
      </p>
    </div>
    <div class="bg-card rounded-xl border border-border p-4 shadow-sm">
      <p class="text-xs text-foreground-secondary">
        {{ t("recoveryTasks.progress.files") }}
      </p>
      <p class="text-xl font-bold text-foreground mt-1">
        {{ stats.total_files }}
      </p>
    </div>
  </div>
</template>
