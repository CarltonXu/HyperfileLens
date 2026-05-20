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
  PauseIcon,
  PencilSquareIcon,
  PlayIcon,
  StopIcon,
} from "@heroicons/vue/24/outline";

type RecoveryTaskColumnKey =
  | "name"
  | "type"
  | "status"
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
</script>

<template>
  <div v-if="loading" class="flex items-center justify-center py-12">
    <div
      class="w-8 h-8 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin"
    />
  </div>

  <div
    v-else-if="filteredCount === 0"
    class="bg-card rounded-xl border border-border p-12 text-center"
  >
    <div
      class="w-16 h-16 bg-background-tertiary rounded-full flex items-center justify-center mx-auto mb-4"
    >
      <ArrowDownTrayIcon class="w-8 h-8 text-slate-400" />
    </div>
    <h3 class="text-lg font-medium text-slate-800 mb-1">
      {{ t("recoveryTasks.empty.title") }}
    </h3>
    <p class="text-foreground-secondary">
      {{ t("recoveryTasks.empty.description") }}
    </p>
  </div>

  <div v-else class="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
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
        <thead class="bg-background-secondary border-b border-border">
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
              @sort="table.toggleSort($event as RecoveryTaskColumnKey)"
              @resize-start="
                (key, event) =>
                  table.startResize(key as RecoveryTaskColumnKey, event)
              "
              @resize-reset="
                table.resetColumnWidth($event as RecoveryTaskColumnKey)
              "
            />
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 dark:divide-slate-700">
          <tr
            v-for="task in tasks"
            :key="task.id"
            class="hover:bg-hover transition-colors"
          >
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
                  ]"
                >
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
                    ]"
                  />
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
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-background-tertiary text-foreground"
              >
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
                ]"
              >
                <component :is="getStatusIcon(task.status)" class="w-3.5 h-3.5" />
                {{ t(`recoveryTasks.status.${task.status}`) }}
              </span>
            </td>
            <td class="px-4 py-4" :style="table.columnStyle('progress')">
              <div
                v-if="task.status === 'running' || task.progress"
                class="w-32"
              >
                <div
                  class="flex items-center justify-between text-xs text-slate-500 mb-1"
                >
                  <span>{{ task.progress || 0 }}%</span>
                </div>
                <div
                  class="h-1.5 bg-background-tertiary rounded-full overflow-hidden"
                >
                  <div
                    class="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-300"
                    :style="{ width: `${task.progress || 0}%` }"
                  />
                </div>
              </div>
              <span v-else class="text-sm text-slate-400">-</span>
            </td>
            <td
              class="px-4 py-4 text-sm text-foreground-secondary dark:text-slate-400"
              :style="table.columnStyle('date')"
            >
              {{ formatDateTime(task.created_at) }}
            </td>
            <td class="px-4 py-4 text-right" :style="table.columnStyle('actions')">
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
                  :title="t('recoveryTasks.actions.start')"
                >
                  <PlayIcon class="w-4 h-4" />
                </button>
                <button
                  v-if="task.status === 'running'"
                  @click="$emit('pause', task)"
                  class="p-1.5 text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                  :title="t('recoveryTasks.actions.pause')"
                >
                  <PauseIcon class="w-4 h-4" />
                </button>
                <button
                  v-if="task.status === 'running'"
                  @click="$emit('cancel', task)"
                  class="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  :title="t('recoveryTasks.actions.cancel')"
                >
                  <StopIcon class="w-4 h-4" />
                </button>
                <button
                  v-if="task.status !== 'running'"
                  @click="$emit('edit', task)"
                  class="p-1.5 text-slate-500 hover:bg-background-tertiary rounded-lg transition-colors"
                  :title="t('common.edit')"
                >
                  <PencilSquareIcon class="w-4 h-4" />
                </button>
                <button
                  @click="$emit('copy', task)"
                  class="p-1.5 text-slate-500 hover:bg-background-tertiary rounded-lg transition-colors"
                  :title="t('recoveryTasks.actions.copy')"
                >
                  <DocumentDuplicateIcon class="w-4 h-4" />
                </button>
                <button
                  @click="$emit('detail', task)"
                  class="p-1.5 text-slate-500 hover:bg-background-tertiary rounded-lg transition-colors"
                  :title="t('common.details')"
                >
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
      :total-items="filteredCount"
    />
  </div>
</template>
