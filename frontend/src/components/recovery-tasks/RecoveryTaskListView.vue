<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { Component } from "vue";
import type { RecoveryTask } from "@/types/recovery";
import Pagination from "@/components/Pagination.vue";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";
import {
  ArrowDownTrayIcon,
  DocumentDuplicateIcon,
  EyeIcon,
  FolderIcon,
  PauseIcon,
  PencilSquareIcon,
  PlayIcon,
  ServerIcon,
  StopIcon,
} from "@heroicons/vue/24/outline";

type RecoveryTaskColumnKey =
  | "name"
  | "type"
  | "status"
  | "snapshot"
  | "repository"
  | "recovery_target"
  | "progress"
  | "date"
  | "actions";

const currentPage = defineModel<number>("currentPage", { required: true });
const pageSize = defineModel<number>("pageSize", { required: true });

defineProps<{
  loading: boolean;
  filteredCount: number;
  tasks: RecoveryTask[];
  columns: Array<{
    key: RecoveryTaskColumnKey;
    label: string;
    min: number;
    max: number;
    sortable?: boolean;
    align?: "left" | "center" | "right";
  }>;
  table: any;
  formatDateTime: (value?: string | null) => string;
  getStatusColor: (status: string) => string;
  getStatusIcon: (status: string) => Component;
}>();

defineEmits<{
  execute: [task: RecoveryTask];
  pause: [task: RecoveryTask];
  cancel: [task: RecoveryTask];
  edit: [task: RecoveryTask];
  copy: [task: RecoveryTask];
  detail: [task: RecoveryTask];
}>();

const { t } = useI18n();

function formatBytes(bytes?: number): string {
  if (!bytes) return "-";
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function formatDuration(startedAt?: string, completedAt?: string): string {
  if (!startedAt) return "-";
  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  const diffSeconds = Math.floor((end - start) / 1000);
  if (diffSeconds < 60) return `${diffSeconds}s`;
  if (diffSeconds < 3600)
    return `${Math.floor(diffSeconds / 60)}m ${diffSeconds % 60}s`;
  return `${Math.floor(diffSeconds / 3600)}h ${Math.floor((diffSeconds % 3600) / 60)}m`;
}
</script>

<template>
  <div v-if="loading" class="flex items-center justify-center py-12">
    <div
      class="w-8 h-8 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin" />
  </div>

  <div
    v-else-if="filteredCount === 0"
    class="bg-card rounded-xl border border-border p-12 text-center">
    <div
      class="w-16 h-16 bg-background-tertiary rounded-full flex items-center justify-center mx-auto mb-4">
      <ArrowDownTrayIcon class="w-8 h-8 text-slate-400" />
    </div>
    <h3 class="text-lg font-medium text-slate-800 mb-1">
      {{ t("recoveryTasks.empty.title") }}
    </h3>
    <p class="text-foreground-secondary">
      {{ t("recoveryTasks.empty.description") }}
    </p>
  </div>

  <div
    v-else
    class="flex max-h-[calc(100vh-19rem)] min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-card shadow-sm">
    <div class="relative min-h-0 flex-1 overflow-auto bg-card">
      <table
        class="w-full table-fixed border-separate border-spacing-0"
        :style="{ minWidth: table.tableMinWidth.value }">
        <colgroup>
          <col
            v-for="column in columns"
            :key="column.key"
            :style="table.columnStyle(column.key)" />
        </colgroup>
        <thead class="sticky top-0 z-30 bg-background-secondary shadow-sm">
          <tr>
            <ResizableSortableTh
              v-for="column in columns"
              :key="column.key"
              :column-key="column.key"
              :label="column.label"
              :style-value="table.columnStyle(column.key)"
              :sortable="column.sortable !== false"
              :active="table.sort.value.key === column.key"
              :align="column.align"
              :sort-icon="table.getSortIcon(column.key)"
              :resizing="table.resizingColumn.value === column.key"
              header-class="border-b border-border"
              @sort="table.toggleSort($event as RecoveryTaskColumnKey)"
              @resize-start="
                (key, event) =>
                  table.startResize(key as RecoveryTaskColumnKey, event)
              "
              @resize-reset="
                table.resetColumnWidth($event as RecoveryTaskColumnKey)
              " />
          </tr>
        </thead>
        <tbody class="[&>tr>td]:border-b [&>tr>td]:border-border">
          <tr
            v-for="task in tasks"
            :key="task.id"
            class="hover:bg-hover transition-colors">
            <td class="px-4 py-4" :style="table.columnStyle('name')">
              <div class="flex items-center gap-3">
                <div
                  :class="[
                    'w-9 h-9 rounded-lg flex items-center justify-center',
                    task.status === 'running'
                      ? 'bg-emerald-100'
                      : task.status === 'completed'
                        ? 'bg-emerald-100'
                        : task.status === 'failed'
                          ? 'bg-red-100'
                          : 'bg-slate-100',
                  ]">
                  <ArrowDownTrayIcon
                    :class="[
                      'w-5 h-5',
                      task.status === 'running'
                        ? 'text-emerald-600'
                        : task.status === 'completed'
                          ? 'text-emerald-600'
                          : task.status === 'failed'
                            ? 'text-red-600'
                            : 'text-slate-400',
                    ]" />
                </div>
                <div>
                  <p class="text-sm font-medium text-foreground">
                    {{ task.name }}
                  </p>
                  <p class="text-xs text-foreground-secondary">
                    {{ task.target_node_name || "Node" }}
                  </p>
                </div>
              </div>
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('type')">
              <span
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-background-tertiary text-foreground">
                {{
                  t(`recoveryTasks.types.${task.recovery_type || "original"}`)
                }}
              </span>
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('status')">
              <span
                :class="[
                  'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium',
                  getStatusColor(task.status),
                ]">
                <component
                  :is="getStatusIcon(task.status)"
                  class="w-3.5 h-3.5" />
                {{ t(`recoveryTasks.status.${task.status}`) }}
              </span>
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('snapshot')">
              <div class="space-y-1">
                <div
                  class="flex items-center gap-1.5"
                  :title="task.snapshot_name || '-'">
                  <FolderIcon class="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span class="truncate text-sm text-foreground-secondary">
                    {{ task.snapshot_name || "-" }}
                  </span>
                </div>
                <p
                  class="text-xs text-foreground-muted truncate pl-5"
                  :title="task.snapshot_id">
                  ID: {{ task.snapshot_id || task.snapshot || "-" }}
                </p>
              </div>
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('repository')">
              <div class="space-y-1">
                <span
                  class="text-sm text-foreground-secondary truncate block"
                  :title="task.repository_name || '-'">
                  {{ task.repository_name || "-" }}
                </span>
                <p
                  v-if="task.snapshot_source_path || task.metadata?.source_path"
                  class="text-xs text-foreground-muted truncate"
                  :title="`Share: ${task.snapshot_source_path || task.metadata?.source_path}`">
                  {{ task.snapshot_source_path || task.metadata?.source_path }}
                </p>
              </div>
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('recovery_target')">
              <div class="space-y-1">
                <div
                  class="flex items-center gap-1.5"
                  :title="task.target_path || '-'">
                  <ServerIcon class="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span class="truncate text-sm text-foreground-secondary">
                    {{ task.target_node_name || "-" }}
                  </span>
                </div>
                <p
                  class="text-xs text-foreground-muted truncate pl-5"
                  :title="task.target_path || '-'">
                  {{ task.target_path || "-" }}
                </p>
              </div>
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('progress')">
              <div
                v-if="task.status === 'running' || task.progress"
                class="space-y-1 min-w-[160px]">
                <div class="flex items-center justify-between text-xs text-foreground-muted">
                  <span class="font-medium text-foreground">{{ task.progress || 0 }}%</span>
                  <span>{{ t("recoveryTasks.progress.duration") }}: {{ formatDuration(task.started_at, task.completed_at) }}</span>
                </div>
                <div class="h-1.5 bg-background-tertiary rounded-full overflow-hidden">
                  <div
                    class="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-300"
                    :style="{ width: `${task.progress || 0}%` }" />
                </div>
                <div class="grid grid-cols-[1fr_auto_1fr] gap-x-2 text-xs text-foreground-muted">
                  <span>{{ t("recoveryTasks.progress.size") }}: {{ formatBytes(task.restored_size) }}/{{ formatBytes(task.total_size) }}</span>
                  <span class="text-center">{{ t("recoveryTasks.progress.files") }}: {{ task.restored_files || 0 }}/{{ task.total_files || 0 }}</span>
                  <span class="text-right" v-if="task.speed_mbps">{{ task.speed_mbps.toFixed(1) }} MB/s</span>
                  <span v-else></span>
                </div>
              </div>
              <span v-else class="text-sm text-slate-400">-</span>
            </td>
            <td
              class="px-4 py-4 text-sm text-foreground-secondary dark:text-slate-400"
              :style="table.columnStyle('date')">
              {{ formatDateTime(task.created_at) }}
            </td>
            <td
              class="px-4 py-4 text-right"
              :style="table.columnStyle('actions')">
              <div class="flex items-center justify-end gap-2">
                <button
                  v-if="
                    [
                      'pending',
                      'failed',
                      'paused',
                      'completed',
                      'cancelled',
                    ].includes(task.status)
                  "
                  @click="$emit('execute', task)"
                  class="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                  :title="t('recoveryTasks.actions.start')">
                  <PlayIcon class="w-4 h-4" />
                </button>
                <button
                  v-if="task.status === 'running'"
                  @click="$emit('pause', task)"
                  class="p-1.5 text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                  :title="t('recoveryTasks.actions.pause')">
                  <PauseIcon class="w-4 h-4" />
                </button>
                <button
                  v-if="task.status === 'running'"
                  @click="$emit('cancel', task)"
                  class="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  :title="t('recoveryTasks.actions.cancel')">
                  <StopIcon class="w-4 h-4" />
                </button>
                <button
                  v-if="task.status !== 'running'"
                  @click="$emit('edit', task)"
                  class="p-1.5 text-slate-500 hover:bg-background-tertiary rounded-lg transition-colors"
                  :title="t('common.edit')">
                  <PencilSquareIcon class="w-4 h-4" />
                </button>
                <button
                  @click="$emit('copy', task)"
                  class="p-1.5 text-slate-500 hover:bg-background-tertiary rounded-lg transition-colors"
                  :title="t('recoveryTasks.actions.copy')">
                  <DocumentDuplicateIcon class="w-4 h-4" />
                </button>
                <button
                  @click="$emit('detail', task)"
                  class="p-1.5 text-slate-500 hover:bg-background-tertiary rounded-lg transition-colors"
                  :title="t('common.details')">
                  <EyeIcon class="w-4 h-4" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total-items="filteredCount" />
  </div>
</template>
