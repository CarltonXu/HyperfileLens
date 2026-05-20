<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  CloudArrowUpIcon,
  EyeIcon,
  PencilSquareIcon,
  PlayIcon,
  PowerIcon,
  StopIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline";
import Pagination from "@/components/Pagination.vue";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";
import type { BackupTask } from "@/types/backup";

type BackupTaskColumnKey =
  | "name"
  | "policy"
  | "source"
  | "repository"
  | "status"
  | "last_backup"
  | "next_backup"
  | "actions";

type BackupTaskColumn = {
  key: BackupTaskColumnKey;
  label: string;
  min: number;
  max: number;
  sortable?: boolean;
  align?: "left" | "right" | "center";
};

const props = defineProps<{
  loading: boolean;
  totalItems: number;
  tasks: BackupTask[];
  columns: BackupTaskColumn[];
  table: any;
  getStatusColor: (status: string) => string;
  getStatusIcon: (status: string) => any;
  getTaskPolicySummary: (task: BackupTask) => string;
  canRunTask: (task: BackupTask) => boolean;
  formatDateTime: (value?: string | null) => string;
}>();

const currentPage = defineModel<number>("currentPage", { required: true });
const pageSize = defineModel<number>("pageSize", { required: true });

defineEmits<{
  execute: [task: BackupTask];
  toggleEnabled: [task: BackupTask];
  cancel: [task: BackupTask];
  detail: [task: BackupTask];
  edit: [task: BackupTask];
  delete: [task: BackupTask];
}>();

const { t } = useI18n();

function sortColumn(key: string) {
  props.table.toggleSort(key as BackupTaskColumnKey);
}

function startResize(key: string, event: MouseEvent) {
  props.table.startResize(key as BackupTaskColumnKey, event);
}

function resetColumnWidth(key: string) {
  props.table.resetColumnWidth(key as BackupTaskColumnKey);
}
</script>

<template>
  <div v-if="loading" class="flex items-center justify-center py-12">
    <div
      class="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600"
    />
  </div>

  <div
    v-else-if="totalItems === 0"
    class="rounded-xl border border-border bg-card p-12 text-center"
  >
    <div
      class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-background-tertiary"
    >
      <CloudArrowUpIcon class="h-8 w-8 text-slate-400" />
    </div>
    <h3 class="mb-1 text-lg font-medium text-foreground">
      {{ t("backupTasks.empty.title") }}
    </h3>
    <p class="text-foreground-secondary">
      {{ t("backupTasks.empty.description") }}
    </p>
  </div>

  <div v-else class="rounded-xl border border-border bg-card shadow-sm">
    <div class="overflow-x-auto">
      <table
        class="w-full table-fixed"
        :style="{ minWidth: table.tableMinWidth.value }"
      >
        <colgroup>
          <col
            v-for="column in columns"
            :key="column.key"
            :style="table.columnStyle(column.key)"
          />
        </colgroup>
        <thead class="border-b border-border bg-background-secondary">
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
              @sort="sortColumn"
              @resize-start="startResize"
              @resize-reset="resetColumnWidth"
            />
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 dark:divide-slate-700">
          <tr
            v-for="task in tasks"
            :key="task.id"
            class="transition-colors hover:bg-hover"
          >
            <td class="px-4 py-4" :style="table.columnStyle('name')">
              <div class="flex items-center gap-3">
                <div
                  :class="[
                    'flex h-9 w-9 items-center justify-center rounded-lg',
                    task.status === 'running'
                      ? 'bg-indigo-100'
                      : task.status === 'completed'
                        ? 'bg-emerald-100'
                        : task.status === 'failed'
                          ? 'bg-red-100'
                          : 'bg-slate-100',
                  ]"
                >
                  <CloudArrowUpIcon
                    :class="[
                      'h-5 w-5',
                      task.status === 'running'
                        ? 'text-indigo-600'
                        : task.status === 'completed'
                          ? 'text-emerald-600'
                          : task.status === 'failed'
                            ? 'text-red-600'
                            : 'text-slate-400',
                    ]"
                  />
                </div>
                <div>
                  <div class="flex items-center gap-2">
                    <span
                      :class="[
                        'h-2.5 w-2.5 shrink-0 rounded-full',
                        task.is_enabled === false
                          ? 'bg-red-500'
                          : 'bg-emerald-500',
                      ]"
                      :title="
                        task.is_enabled === false
                          ? t('backupTasks.disabled')
                          : t('backupTasks.enabled')
                      "
                    />
                    <button
                      type="button"
                      class="text-left text-sm font-medium text-foreground hover:text-primary"
                      @click="$emit('detail', task)"
                    >
                      {{ task.name }}
                    </button>
                  </div>
                  <p class="text-xs text-foreground-secondary">
                    {{ t(`backupTasks.types.${task.task_type || "full"}`) }} ·
                    {{ task.snapshot_count || 0 }}
                    {{ t("backupTasks.snapshots") }}
                  </p>
                </div>
              </div>
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('policy')">
              <p class="text-sm font-medium text-foreground">
                {{ task.schedule_name || t("backupTasks.form.noPolicy") }}
              </p>
              <p
                class="mt-1 max-w-[260px] truncate text-xs text-foreground-muted"
              >
                {{ getTaskPolicySummary(task) }}
              </p>
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('source')">
              <p class="text-sm text-foreground">
                {{ task.source_resource_name || "-" }}
              </p>
              <p class="text-xs text-foreground-muted">
                {{ task.execution_node_name || "-" }}
              </p>
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('repository')">
              <p class="text-sm text-foreground">
                {{ task.target_repository_name || "-" }}
              </p>
              <p class="text-xs text-foreground-muted">
                {{ task.target_repository_type || "-" }}
              </p>
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('status')">
              <span
                :class="[
                  'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium',
                  getStatusColor(task.status),
                ]"
              >
                <component
                  :is="getStatusIcon(task.status)"
                  class="h-3.5 w-3.5"
                />
                {{ t(`backupTasks.status.${task.status}`) }}
              </span>
            </td>
            <td
              class="px-4 py-4 text-sm text-foreground-secondary"
              :style="table.columnStyle('last_backup')"
            >
              {{ formatDateTime(task.last_run_time || task.completed_at) }}
            </td>
            <td
              class="px-4 py-4 text-sm text-foreground-secondary"
              :style="table.columnStyle('next_backup')"
            >
              {{ formatDateTime(task.next_run_time) }}
            </td>
            <td
              class="px-4 py-4 text-right"
              :style="table.columnStyle('actions')"
            >
              <div class="flex items-center justify-end gap-2">
                <button
                  v-if="canRunTask(task)"
                  class="rounded-lg p-1.5 text-emerald-600 transition-colors hover:bg-emerald-50"
                  :title="t('backupTasks.actions.runNow')"
                  @click="$emit('execute', task)"
                >
                  <PlayIcon class="h-4 w-4" />
                </button>
                <button
                  :class="[
                    'rounded-lg p-1.5 transition-colors',
                    task.is_enabled === false
                      ? 'text-emerald-600 hover:bg-emerald-50'
                      : 'text-amber-600 hover:bg-amber-50',
                  ]"
                  :title="
                    task.is_enabled === false
                      ? t('backupTasks.actions.enable')
                      : t('backupTasks.actions.disable')
                  "
                  @click="$emit('toggleEnabled', task)"
                >
                  <PowerIcon class="h-4 w-4" />
                </button>
                <button
                  v-if="task.status === 'running'"
                  class="rounded-lg p-1.5 text-red-600 transition-colors hover:bg-red-50"
                  :title="t('backupTasks.actions.cancel')"
                  @click="$emit('cancel', task)"
                >
                  <StopIcon class="h-4 w-4" />
                </button>
                <button
                  class="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-background-tertiary"
                  :title="t('common.details')"
                  @click="$emit('detail', task)"
                >
                  <EyeIcon class="h-4 w-4" />
                </button>
                <button
                  :disabled="task.status === 'running'"
                  class="rounded-lg p-1.5 text-indigo-600 transition-colors hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-40 dark:hover:bg-indigo-900/20"
                  :title="t('backupTasks.edit.title')"
                  @click="$emit('edit', task)"
                >
                  <PencilSquareIcon class="h-4 w-4" />
                </button>
                <button
                  class="rounded-lg p-1.5 text-red-600 transition-colors hover:bg-red-50 dark:hover:bg-red-900/20"
                  :title="t('backupTasks.actions.delete')"
                  @click="$emit('delete', task)"
                >
                  <TrashIcon class="h-4 w-4" />
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
      :total-items="totalItems"
    />
  </div>
</template>
