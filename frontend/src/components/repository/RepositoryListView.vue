<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { Component } from "vue";
import type { Repository } from "@/types/repository";
import Pagination from "@/components/Pagination.vue";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";
import {
  CheckCircleIcon,
  CircleStackIcon,
  InformationCircleIcon,
  KeyIcon,
  LinkIcon,
  PencilIcon,
  PlayIcon,
  SignalIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline";

defineProps<{
  loading: boolean;
  filteredCount: number;
  currentPage: number;
  pageSize: number;
  columns: Array<{
    key: string;
    label: string;
    sortable?: boolean;
    align?: "left" | "center" | "right";
  }>;
  table: any;
  testingConnection: string | null;
  connectionTestResult: Record<
    string,
    { success: boolean; message: string; details?: any }
  >;
  getRepoTypeColor: (type: string) => string;
  getRepoTypeIcon: (type: string) => Component;
  getRepoTypeLabel: (type: string | undefined | null) => string;
  getNodeName: (nodeId: string | null | undefined) => string;
  getProgressColor: (quotaStatus: string) => string;
  formatBytes: (bytes: number) => string;
}>();

const emit = defineEmits<{
  "update:currentPage": [value: number];
  "update:pageSize": [value: number];
  initKopia: [repo: Repository];
  saveKopiaPassword: [repo: Repository];
  testConnection: [repo: Repository];
  edit: [repo: Repository];
  detail: [repo: Repository];
  delete: [repo: Repository];
}>();

const { t } = useI18n();
</script>

<template>
  <template v-if="loading">
    <div class="flex items-center justify-center py-12">
      <div
        class="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"
      />
    </div>
  </template>

  <div
    v-else-if="filteredCount === 0"
    class="rounded-xl border border-border p-12 text-center"
  >
    <div
      class="w-16 h-16 bg-background-tertiary/50 rounded-full flex items-center justify-center mx-auto mb-4"
    >
      <CircleStackIcon class="w-8 h-8 text-foreground-muted" />
    </div>
    <h3 class="text-lg font-medium text-foreground mb-1">
      {{ t("repository.empty.title") }}
    </h3>
    <p class="text-foreground-secondary">
      {{ t("repository.empty.description") }}
    </p>
  </div>

  <div
    v-else
    class="flex max-h-[calc(100vh-19rem)] min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-card"
  >
    <div class="relative min-h-0 flex-1 overflow-auto bg-card">
      <table
        class="w-full table-fixed border-separate border-spacing-0"
        :style="{ minWidth: table.tableMinWidth.value }"
      >
        <colgroup>
          <col
            v-for="column in columns"
            :key="column.key"
            :style="table.columnStyle(column.key)"
          />
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
              :sticky="
                column.key === 'name'
                  ? 'left'
                  : column.key === 'actions'
                    ? 'right'
                    : undefined
              "
              @sort="table.toggleSort($event)"
              @resize-start="(key, event) => table.startResize(key, event)"
              @resize-reset="table.resetColumnWidth($event)"
            />
          </tr>
        </thead>
        <tbody class="bg-card [&>tr>td]:border-b [&>tr>td]:border-border">
          <tr
            v-for="repo in table.sortedRows.value"
            :key="repo.id"
            class="hover:bg-hover/50 transition-colors"
          >
            <td
              class="sticky left-0 bg-card px-4 py-3 whitespace-nowrap z-10"
              :style="table.columnStyle('name')"
            >
              <div class="flex items-center gap-3">
                <div
                  :class="[
                    'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                    getRepoTypeColor(repo.repo_type),
                  ]"
                >
                  <component
                    :is="getRepoTypeIcon(repo.repo_type)"
                    class="w-4 h-4 text-white"
                  />
                </div>
                <button
                  @click="emit('detail', repo)"
                  class="font-medium text-sm dark:text-slate-200 hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer transition-colors text-left"
                >
                  {{ repo.name }}
                </button>
              </div>
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap"
              :style="table.columnStyle('repo_type')"
            >
              <span
                :class="[
                  'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
                  repo.repo_type === 's3'
                    ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400'
                    : repo.repo_type === 'nas'
                      ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 dark:text-purple-400'
                      : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 dark:text-blue-400',
                ]"
              >
                {{ getRepoTypeLabel(repo.repo_type) }}
              </span>
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap"
              :style="table.columnStyle('status')"
            >
              <span
                :class="[
                  'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                  repo.status === 'active'
                    ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 dark:text-emerald-400'
                    : 'bg-background-tertiary/50 text-foreground-secondary',
                ]"
              >
                {{
                  repo.status === "active"
                    ? t("common.active")
                    : t("common.inactive")
                }}
              </span>
            </td>
            <td
              class="px-4 py-3 text-sm text-foreground-secondary max-w-[200px]"
              :style="table.columnStyle('connection')"
            >
              <template v-if="repo.repo_type === 's3'">
                <div class="truncate" :title="repo.config?.endpoint">
                  {{ repo.config?.bucket || "-" }}
                </div>
              </template>
              <template v-else-if="repo.repo_type === 'nas'">
                <div class="truncate" :title="repo.config?.server">
                  {{ repo.config?.server || "-" }}
                </div>
              </template>
              <template v-else>
                <div class="truncate" :title="repo.config?.path">
                  {{ repo.config?.path || "-" }}
                </div>
              </template>
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
              :style="table.columnStyle('bound_node')"
            >
              {{ getNodeName(repo.bound_node) }}
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap"
              :style="table.columnStyle('capacity')"
            >
              <div v-if="repo.capacity">
                <div class="flex items-center gap-2 mb-1">
                  <div
                    class="flex-1 h-1.5 bg-slate-200 dark:bg-slate-600 dark:bg-slate-600 rounded-full overflow-hidden relative"
                  >
                    <div
                      v-if="repo.quota_enabled && (repo.quota_bytes || 0) > 0"
                      class="h-full absolute left-0 bg-slate-300 dark:bg-slate-600/50 dark:bg-slate-600/50 opacity-50 rounded-full transition-all"
                      :style="{
                        width: `${Math.min(((repo.quota_bytes || 0) / repo.capacity) * 100, 100)}%`,
                      }"
                    />
                    <div
                      class="h-full rounded-full transition-all relative"
                      :class="
                        getProgressColor(repo.quota_status || 'unlimited')
                      "
                      :style="{
                        width: `${((repo.used_space || 0) / repo.capacity) * 100}%`,
                      }"
                    />
                  </div>
                </div>
                <div class="text-xs text-foreground-secondary">
                  <div>
                    {{ formatBytes(repo.used_space || 0) }} /
                    {{ formatBytes(repo.capacity) }}
                  </div>
                  <div
                    v-if="repo.quota_enabled && (repo.quota_bytes || 0) > 0"
                    class="flex items-center gap-1 mt-0.5"
                  >
                    <span class="text-foreground-muted">
                      {{ t("repository.stats.quota") }}:
                    </span>
                    <span
                      :class="[
                        'font-medium',
                        repo.quota_status === 'critical'
                          ? 'text-red-500 dark:text-red-400 dark:text-red-400'
                          : repo.quota_status === 'warning'
                            ? 'text-amber-500 dark:text-amber-400 dark:text-amber-400'
                            : 'text-foreground-secondary',
                      ]"
                    >
                      {{ repo.quota_bytes_formatted }}
                      ({{ repo.quota_usage_percentage?.toFixed(1) || 0 }}%)
                    </span>
                  </div>
                </div>
              </div>
              <span v-else class="text-foreground-muted text-sm">-</span>
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap"
              :style="table.columnStyle('kopia_initialized')"
            >
              <span
                v-if="repo.kopia_initialized"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 dark:text-blue-400"
              >
                <CheckCircleIcon class="w-3 h-3" />
                {{ t("repository.initialized") }}
              </span>
              <span v-else class="text-foreground-muted text-xs">-</span>
            </td>
            <td
              class="sticky right-0 bg-card px-4 py-3 whitespace-nowrap text-right z-10"
              :style="table.columnStyle('actions')"
            >
              <div class="flex items-center justify-end gap-1">
                <button
                  v-if="!repo.kopia_initialized && repo.bound_node"
                  @click="emit('initKopia', repo)"
                  class="p-1.5 text-blue-500 dark:text-blue-400 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/30 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                  :title="t('repository.initKopia')"
                >
                  <PlayIcon class="w-4 h-4" />
                </button>
                <button
                  v-if="repo.kopia_initialized"
                  @click="emit('saveKopiaPassword', repo)"
                  class="p-1.5 text-foreground-muted hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/30 rounded-lg transition-colors"
                  :title="t('repository.saveKopiaPassword')"
                >
                  <KeyIcon class="w-4 h-4" />
                </button>
                <button
                  @click="emit('testConnection', repo)"
                  :disabled="testingConnection === repo.id"
                  :class="[
                    'p-1.5 rounded-lg transition-colors',
                    testingConnection === repo.id
                      ? 'text-slate-300 cursor-wait'
                      : connectionTestResult[repo.id]?.success
                        ? 'text-emerald-500 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 dark:hover:text-emerald-300 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 dark:hover:bg-emerald-900/30'
                        : 'text-foreground-muted hover:text-foreground-secondary dark:hover:text-slate-300 hover:bg-background-tertiary/50',
                  ]"
                  :title="
                    testingConnection === repo.id
                      ? t('repository.testing')
                      : t('repository.testConnection')
                  "
                >
                  <SignalIcon
                    v-if="testingConnection === repo.id"
                    class="w-4 h-4 animate-pulse"
                  />
                  <CheckCircleIcon
                    v-else-if="connectionTestResult[repo.id]?.success"
                    class="w-4 h-4"
                  />
                  <LinkIcon v-else class="w-4 h-4" />
                </button>
                <button
                  @click="emit('edit', repo)"
                  class="p-1.5 text-foreground-muted hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                  :title="t('common.edit')"
                >
                  <PencilIcon class="w-4 h-4" />
                </button>
                <button
                  @click="emit('detail', repo)"
                  class="p-1.5 text-foreground-muted hover:text-foreground-secondary dark:hover:text-slate-300 hover:bg-background-tertiary/50 rounded-lg transition-colors"
                  :title="t('common.details')"
                >
                  <InformationCircleIcon class="w-4 h-4" />
                </button>
                <button
                  @click="emit('delete', repo)"
                  class="p-1.5 text-foreground-muted hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                  :title="t('common.delete')"
                >
                  <TrashIcon class="w-4 h-4" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <Pagination
      :current-page="currentPage"
      :page-size="pageSize"
      :total-items="filteredCount"
      @update:current-page="emit('update:currentPage', $event)"
      @update:page-size="emit('update:pageSize', $event)"
    />
  </div>
</template>
