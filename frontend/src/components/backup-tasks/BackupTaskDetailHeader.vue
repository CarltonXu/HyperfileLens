<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { Component } from "vue";
import type { BackupTask } from "@/types/backup";
import {
  ArrowPathIcon,
  PlayIcon,
  PowerIcon,
  XCircleIcon,
} from "@heroicons/vue/24/outline";

const detailTab = defineModel<"overview" | "snapshots" | "tasks">("detailTab", {
  required: true,
});
const autoRefresh = defineModel<boolean>("autoRefresh", { required: true });
const refreshInterval = defineModel<number>("refreshInterval", {
  required: true,
});

defineProps<{
  task: BackupTask;
  currentLoading: boolean;
  getStatusColor: (status: string) => string;
  getStatusIcon: (status: string) => Component;
  canRunTask: (task: BackupTask) => boolean;
}>();

defineEmits<{
  close: [];
  selectTab: [tab: "overview" | "snapshots" | "tasks"];
  refresh: [];
  execute: [task: BackupTask];
  toggleEnabled: [task: BackupTask];
}>();

const { t } = useI18n();
const tabs = ["overview", "snapshots", "tasks"] as const;
</script>

<template>
  <div
    class="sticky top-0 z-10 modal-surface px-6 py-4 border-b border-border flex items-start justify-between gap-4"
  >
    <div>
      <h2 class="text-lg font-semibold text-foreground">
        {{ task.name }}
      </h2>
      <p class="mt-1 text-sm text-foreground-secondary">
        {{ task.source_resource_name || "-" }} →
        {{ task.target_repository_name || "-" }}
      </p>
    </div>
    <button
      @click="$emit('close')"
      class="p-2 hover:bg-background-tertiary rounded-lg"
    >
      <XCircleIcon class="w-5 h-5 text-slate-400" />
    </button>
  </div>

  <div
    class="px-6 py-3 border-b border-border flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3"
  >
    <div class="flex flex-wrap items-center gap-2">
      <div
        class="inline-flex flex-wrap gap-1 rounded-lg border border-border bg-background-secondary p-1"
        role="tablist"
      >
        <button
          v-for="tab in tabs"
          :key="tab"
          type="button"
          role="tab"
          :aria-selected="detailTab === tab"
          @click="
            detailTab = tab;
            $emit('selectTab', tab);
          "
          :class="[
            'inline-flex items-center rounded-md border px-3 py-1.5 text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-primary/40',
            detailTab === tab
              ? 'border-primary bg-primary text-primary-foreground shadow-sm'
              : 'border-transparent text-foreground-secondary hover:border-border hover:bg-card hover:text-foreground',
          ]"
        >
          {{ t(`backupTasks.tabs.${tab}`) }}
        </button>
      </div>

      <div
        class="flex flex-wrap items-center gap-2 pl-0 xl:pl-3 xl:border-l xl:border-border"
      >
        <button
          type="button"
          :disabled="currentLoading"
          @click="$emit('refresh')"
          class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-border text-xs font-medium text-foreground hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ArrowPathIcon
            :class="['w-3.5 h-3.5', currentLoading ? 'animate-spin' : '']"
          />
          {{ t("common.refresh") }}
        </button>

        <label
          class="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-border text-xs font-medium text-foreground hover:bg-hover"
        >
          <input
            v-model="autoRefresh"
            type="checkbox"
            class="h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary"
          />
          {{ t("backupTasks.detail.autoRefresh") }}
        </label>

        <select
          v-model.number="refreshInterval"
          :disabled="!autoRefresh"
          class="px-2.5 py-1.5 rounded-lg border border-border bg-background text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        >
          <option :value="5">5s</option>
          <option :value="10">10s</option>
          <option :value="30">30s</option>
          <option :value="60">60s</option>
        </select>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-2 xl:justify-end">
      <span
        :class="[
          'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium',
          getStatusColor(task.status),
        ]"
      >
        <component :is="getStatusIcon(task.status)" class="w-3.5 h-3.5" />
        {{ t(`backupTasks.status.${task.status}`) }}
      </span>
      <span
        :class="[
          'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium',
          task.is_enabled === false
            ? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
            : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
        ]"
      >
        <span
          :class="[
            'h-2 w-2 rounded-full',
            task.is_enabled === false ? 'bg-red-500' : 'bg-emerald-500',
          ]"
        />
        {{
          task.is_enabled === false
            ? t("backupTasks.disabled")
            : t("backupTasks.enabled")
        }}
      </span>
      <button
        v-if="canRunTask(task)"
        @click="$emit('execute', task)"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-medium hover:bg-emerald-700 border border-emerald-700"
      >
        <PlayIcon class="w-3.5 h-3.5" />
        {{ t("backupTasks.actions.runNow") }}
      </button>
      <button
        @click="$emit('toggleEnabled', task)"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs font-medium text-foreground hover:bg-hover"
      >
        <PowerIcon class="w-3.5 h-3.5" />
        {{
          task.is_enabled === false
            ? t("backupTasks.actions.enable")
            : t("backupTasks.actions.disable")
        }}
      </button>
    </div>
  </div>
</template>
