<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { ClipboardDocumentListIcon } from "@heroicons/vue/24/outline";
import type { ProxyTask } from "@/types/proxy";

defineProps<{
  tasks: ProxyTask[];
  stats: {
    total: number;
    completed: number;
    failed: number;
    running: number;
  } | null;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-4">
    <div class="grid grid-cols-4 gap-4">
      <div class="bg-background-secondary rounded-xl p-4">
        <p class="text-xs text-foreground-secondary">
          {{ t("proxies.tasks.total") }}
        </p>
        <p class="text-2xl font-bold text-foreground mt-1">
          {{ stats?.total || 0 }}
        </p>
      </div>
      <div class="bg-emerald-50 dark:bg-emerald-900/30 rounded-xl p-4">
        <p class="text-xs text-foreground-secondary">
          {{ t("proxies.tasks.completed") }}
        </p>
        <p
          class="text-2xl font-bold text-emerald-700 dark:text-emerald-400 mt-1"
        >
          {{ stats?.completed || 0 }}
        </p>
      </div>
      <div class="bg-red-50 dark:bg-red-900/30 rounded-xl p-4">
        <p class="text-xs text-foreground-secondary">
          {{ t("proxies.tasks.failed") }}
        </p>
        <p class="text-2xl font-bold text-red-700 dark:text-red-400 mt-1">
          {{ stats?.failed || 0 }}
        </p>
      </div>
      <div class="bg-blue-50 dark:bg-blue-900/30 rounded-xl p-4">
        <p class="text-xs text-foreground-secondary">
          {{ t("proxies.tasks.running") }}
        </p>
        <p class="text-2xl font-bold text-blue-700 dark:text-blue-400 mt-1">
          {{ stats?.running || 0 }}
        </p>
      </div>
    </div>

    <div
      v-if="tasks.length === 0"
      class="bg-background-secondary rounded-xl p-8 text-center"
    >
      <ClipboardDocumentListIcon
        class="w-16 h-16 mx-auto mb-4 text-slate-300"
      />
      <p class="text-foreground-secondary font-medium">
        {{ t("proxies.detail.noTasks") }}
      </p>
      <p class="text-sm text-foreground-muted mt-1">
        {{ t("proxies.detail.noTasksHint") }}
      </p>
    </div>
    <div v-else class="space-y-3">
      <div
        v-for="task in tasks"
        :key="task.id"
        class="bg-background-secondary rounded-xl p-4"
      >
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-3">
            <span
              :class="[
                'px-2 py-1 rounded text-xs font-medium',
                task.status === 'completed'
                  ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400'
                  : task.status === 'running'
                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                    : task.status === 'failed'
                      ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                      : 'bg-background-tertiary text-foreground',
              ]"
            >
              {{ t(`proxies.detail.taskStatus.${task.status}`) || task.status }}
            </span>
            <span class="text-sm font-medium text-foreground">
              {{ task.task_type }}
            </span>
          </div>
          <span class="text-xs text-foreground-secondary">
            {{ new Date(task.created_at).toLocaleString() }}
          </span>
        </div>
        <div
          v-if="task.progress !== null && task.progress !== undefined"
          class="mt-2"
        >
          <div
            class="flex items-center justify-between text-xs text-foreground-secondary mb-1"
          >
            <span>{{ task.progress_message || "" }}</span>
            <span>{{ task.progress }}%</span>
          </div>
          <div class="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
            <div
              class="h-full bg-indigo-500 rounded-full transition-all"
              :style="{ width: `${task.progress}%` }"
            />
          </div>
        </div>
        <p v-if="task.error_message" class="mt-2 text-xs text-red-600">
          {{ task.error_message }}
        </p>
      </div>
    </div>
  </div>
</template>
