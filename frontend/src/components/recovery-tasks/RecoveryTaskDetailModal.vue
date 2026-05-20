<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { Component } from "vue";
import type { RecoveryRun, RecoveryTask } from "@/types/recovery";
import {
  ArrowPathIcon,
  ClockIcon,
  XCircleIcon,
} from "@heroicons/vue/24/outline";

const detailTab = defineModel<"overview" | "runs">("detailTab", {
  required: true,
});

defineProps<{
  task: RecoveryTask;
  runs: RecoveryRun[];
  runsLoading: boolean;
  formatBytes: (bytes: number) => string;
  formatDateTime: (value?: string | null) => string;
  getStatusColor: (status: string) => string;
  getStatusIcon: (status: string) => Component;
}>();

defineEmits<{
  close: [];
  refreshRuns: [];
}>();

const { t } = useI18n();
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="$emit('close')" />
      <div
        class="relative modal-surface rounded-2xl shadow-xl w-full max-w-4xl max-h-[88vh] overflow-y-auto"
      >
        <div
          class="px-6 py-4 border-b border-border flex items-center justify-between"
        >
          <div>
            <h2 class="text-lg font-semibold text-foreground">
              {{ task.name }}
            </h2>
            <p class="text-xs text-foreground-secondary mt-1">
              {{ task.backup_task_name || "-" }} ·
              {{ task.repository_name || "-" }}
            </p>
          </div>
          <button
            @click="$emit('close')"
            class="p-1 hover:bg-background-tertiary rounded-lg"
          >
            <XCircleIcon class="w-5 h-5 text-slate-400" />
          </button>
        </div>

        <div class="px-6 pt-4 border-b border-border">
          <div class="flex items-center gap-2">
            <button
              @click="detailTab = 'overview'"
              :class="[
                'px-3 py-2 text-sm font-medium border-b-2 transition-colors',
                detailTab === 'overview'
                  ? 'border-emerald-500 text-emerald-600'
                  : 'border-transparent text-foreground-secondary hover:text-foreground',
              ]"
            >
              {{ t("recoveryTasks.tabs.overview") }}
            </button>
            <button
              @click="detailTab = 'runs'"
              :class="[
                'px-3 py-2 text-sm font-medium border-b-2 transition-colors',
                detailTab === 'runs'
                  ? 'border-emerald-500 text-emerald-600'
                  : 'border-transparent text-foreground-secondary hover:text-foreground',
              ]"
            >
              {{ t("recoveryTasks.tabs.runs") }}
            </button>
          </div>
        </div>

        <div v-if="detailTab === 'overview'" class="p-6 space-y-4">
          <div class="flex flex-wrap items-center gap-3">
            <span
              :class="[
                'inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium',
                getStatusColor(task.status),
              ]"
            >
              <component :is="getStatusIcon(task.status)" class="w-4 h-4" />
              {{ t(`recoveryTasks.status.${task.status}`) }}
            </span>
            <span
              class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-background-tertiary text-foreground"
            >
              {{ t(`recoveryTasks.types.${task.recovery_type || "original"}`) }}
            </span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-foreground-secondary">
                {{ t("recoveryTasks.form.snapshot") }}
              </p>
              <p class="font-medium text-foreground mt-1 break-all">
                {{ task.snapshot_name || task.snapshot }}
              </p>
              <p class="text-xs text-foreground-secondary mt-1">
                {{ formatBytes(task.snapshot_size || 0) }} ·
                {{ task.snapshot_file_count || 0 }}
                {{ t("recoveryTasks.progress.files") }}
              </p>
            </div>
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-foreground-secondary">
                {{ t("recoveryTasks.form.targetNode") }}
              </p>
              <p class="font-medium text-foreground mt-1">
                {{ task.target_node_name || "N/A" }}
              </p>
              <p class="text-xs text-foreground-secondary mt-1">
                {{ task.target_node_status || "-" }}
              </p>
            </div>
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-foreground-secondary">
                {{ t("recoveryTasks.form.targetPath") }}
              </p>
              <p class="font-medium text-foreground mt-1 font-mono text-xs break-all">
                {{ task.target_path || "Original Location" }}
              </p>
            </div>
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-foreground-secondary">
                {{ t("recoveryTasks.review.sourcePath") }}
              </p>
              <p class="font-mono text-xs text-foreground mt-1 break-all">
                {{ task.snapshot_source_path || task.metadata?.source_path || "-" }}
              </p>
            </div>
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-foreground-secondary">
                {{ t("recoveryTasks.scope.title") }}
              </p>
              <p class="font-medium text-foreground mt-1">
                {{
                  task.restore_scope === "selected_paths"
                    ? `${task.selected_paths?.length || 0} ${t("recoveryTasks.scope.selectedCount")}`
                    : t("recoveryTasks.scope.entire")
                }}
              </p>
              <p
                v-if="task.selected_paths?.length"
                class="font-mono text-xs text-foreground-secondary mt-1 break-all"
              >
                {{ task.selected_paths.slice(0, 3).join(", ") }}
                <span v-if="task.selected_paths.length > 3">...</span>
              </p>
            </div>
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-foreground-secondary">
                {{ t("recoveryTasks.form.conflictPolicy") }}
              </p>
              <p class="font-medium text-foreground mt-1">
                {{ t(`recoveryTasks.conflict.${task.conflict_policy || "skip"}`) }}
              </p>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-3 text-sm">
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-foreground-secondary">
                {{ t("recoveryTasks.progress.speed") }}
              </p>
              <p class="font-medium text-foreground mt-1">
                {{ (task.speed_mbps || 0).toFixed(2) }} MB/s
              </p>
            </div>
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-foreground-secondary">
                {{ t("recoveryTasks.progress.success") }}
              </p>
              <p class="font-medium text-foreground mt-1">
                {{ task.restored_files || 0 }}
              </p>
            </div>
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-foreground-secondary">
                {{ t("recoveryTasks.progress.failed") }}
              </p>
              <p class="font-medium text-foreground mt-1">
                {{ task.failed_files || 0 }}
              </p>
            </div>
            <div class="bg-background-secondary rounded-lg p-3">
              <p class="text-foreground-secondary">ETA</p>
              <p class="font-medium text-foreground mt-1">
                {{ task.eta || "-" }}
              </p>
            </div>
          </div>
          <div class="bg-background-secondary rounded-lg p-3">
            <div class="flex justify-between text-sm mb-2">
              <span class="text-foreground-secondary">{{
                t("recoveryTasks.progress.progress")
              }}</span>
              <span class="font-medium text-foreground">
                {{ task.progress || 0 }}%
              </span>
            </div>
            <div class="h-2 bg-background-tertiary rounded-full overflow-hidden">
              <div
                class="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full"
                :style="{ width: `${task.progress || 0}%` }"
              />
            </div>
            <div class="flex justify-between text-xs text-slate-500 mt-2">
              <span>
                {{ task.restored_files || 0 }} /
                {{ task.total_files || 0 }}
                {{ t("recoveryTasks.progress.files") }}
              </span>
              <span>{{ formatBytes(task.restored_size || 0) }}</span>
            </div>
          </div>
        </div>

        <div v-else class="p-6 space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-semibold text-foreground">
                {{ t("recoveryTasks.runs.title") }}
              </h3>
              <p class="text-xs text-foreground-secondary mt-1">
                {{ t("recoveryTasks.runs.description") }}
              </p>
            </div>
            <button
              @click="$emit('refreshRuns')"
              class="inline-flex items-center gap-2 px-3 py-2 text-sm border border-border rounded-lg hover:bg-hover"
            >
              <ArrowPathIcon class="w-4 h-4" />
              {{ t("common.refresh") }}
            </button>
          </div>
          <div v-if="runsLoading" class="py-10 flex justify-center">
            <div
              class="w-7 h-7 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin"
            />
          </div>
          <div
            v-else-if="runs.length === 0"
            class="rounded-lg border border-dashed border-border p-8 text-center"
          >
            <ClockIcon class="w-8 h-8 text-slate-400 mx-auto mb-3" />
            <p class="text-sm font-medium text-foreground">
              {{ t("recoveryTasks.runs.emptyTitle") }}
            </p>
            <p class="text-xs text-foreground-secondary mt-1">
              {{ t("recoveryTasks.runs.emptyDescription") }}
            </p>
          </div>
          <div v-else class="space-y-3">
            <div
              v-for="run in runs"
              :key="run.id"
              class="rounded-lg border border-border bg-background-secondary/40 p-4"
            >
              <div class="flex items-start justify-between gap-4">
                <div>
                  <div class="flex items-center gap-2">
                    <span
                      :class="[
                        'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium',
                        getStatusColor(run.status),
                      ]"
                    >
                      <component :is="getStatusIcon(run.status)" class="w-3.5 h-3.5" />
                      {{ t(`recoveryTasks.status.${run.status}`) }}
                    </span>
                    <span class="text-xs text-foreground-secondary">
                      {{ formatDateTime(run.created_at) }}
                    </span>
                  </div>
                  <p class="text-sm text-foreground mt-2">
                    {{ run.message || run.error_message || "-" }}
                  </p>
                  <p class="text-xs text-foreground-secondary mt-1 font-mono break-all">
                    {{ run.proxy_task || "-" }}
                  </p>
                  <p class="text-xs text-foreground-secondary mt-1">
                    {{ t("recoveryTasks.form.targetPath") }}:
                    <span class="font-mono">
                      {{ run.parameters?.target_path || "-" }}
                    </span>
                  </p>
                </div>
                <div class="text-right text-xs text-foreground-secondary min-w-[150px]">
                  <p>{{ run.progress || 0 }}%</p>
                  <p>{{ formatBytes(run.restored_size || 0) }}</p>
                  <p>
                    {{ run.restored_files || 0 }}
                    {{ t("recoveryTasks.progress.files") }}
                  </p>
                  <p>{{ (run.speed_mbps || 0).toFixed(2) }} MB/s</p>
                  <p>
                    {{ t("recoveryTasks.progress.failed") }}:
                    {{ run.failed_files || 0 }}
                  </p>
                </div>
              </div>
              <div class="h-1.5 bg-background-tertiary rounded-full overflow-hidden mt-3">
                <div
                  class="h-full bg-emerald-500 rounded-full"
                  :style="{ width: `${run.progress || 0}%` }"
                />
              </div>
            </div>
          </div>
        </div>

        <div class="px-6 py-4 border-t border-border flex justify-end">
          <button
            @click="$emit('close')"
            class="px-4 py-2 text-sm text-foreground-secondary border border-border rounded-lg hover:bg-hover"
          >
            {{ t("common.close") }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
