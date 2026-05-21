<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  EyeIcon,
  LinkIcon,
  PencilIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline";
import Pagination from "@/components/Pagination.vue";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";
import type { ResourceType, SourceResource } from "@/types/sourceResource";

type SourceResourceColumnKey =
  | "name"
  | "resource_type"
  | "status"
  | "bound_node"
  | "connection"
  | "capacity"
  | "updated_at"
  | "actions";

type SourceResourceColumn = {
  key: SourceResourceColumnKey;
  label: string;
  min: number;
  max: number;
  sortable?: boolean;
  align?: "left" | "right" | "center";
};

const props = defineProps<{
  resources: SourceResource[];
  columns: SourceResourceColumn[];
  table: any;
  totalItems: number;
  getResourceIcon: (type: ResourceType) => any;
  getSourceConnection: (resource: SourceResource) => string;
  getUsagePercent: (resource: SourceResource) => number;
  getCapacityText: (resource: SourceResource) => string;
  formatDate: (date?: string | null) => string;
}>();

const currentPage = defineModel<number>("currentPage", { required: true });
const pageSize = defineModel<number>("pageSize", { required: true });

defineEmits<{
  detail: [resource: SourceResource];
  edit: [resource: SourceResource];
  delete: [resource: SourceResource];
  test: [resource: SourceResource];
}>();

const { t } = useI18n();

function sortColumn(key: string) {
  props.table.toggleSort(key as SourceResourceColumnKey);
}

function startResize(key: string, event: MouseEvent) {
  props.table.startResize(key as SourceResourceColumnKey, event);
}

function resetColumnWidth(key: string) {
  props.table.resetColumnWidth(key as SourceResourceColumnKey);
}
</script>

<template>
  <div class="overflow-hidden rounded-xl border border-border bg-card">
    <div class="overflow-x-auto">
      <table
        class="w-full table-fixed divide-y divide-border"
        :style="{ minWidth: table.tableMinWidth.value }"
      >
        <colgroup>
          <col
            v-for="column in columns"
            :key="column.key"
            :style="table.columnStyle(column.key)"
          />
        </colgroup>
        <thead class="bg-background-secondary">
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
        <tbody class="divide-y divide-border">
          <tr
            v-for="resource in resources"
            :key="resource.id"
            class="hover:bg-hover/50"
          >
            <td
              class="whitespace-nowrap px-4 py-3"
              :style="table.columnStyle('name')"
            >
              <div class="flex items-center gap-3">
                <component
                  :is="getResourceIcon(resource.resource_type)"
                  class="h-5 w-5 text-foreground-muted"
                />
                <div class="min-w-0">
                  <button
                    class="font-medium text-foreground hover:text-primary"
                    @click="$emit('detail', resource)"
                  >
                    {{ resource.name }}
                  </button>
                  <p class="truncate text-xs text-foreground-secondary">
                    {{ resource.description || resource.id }}
                  </p>
                </div>
              </div>
            </td>
            <td
              class="whitespace-nowrap px-4 py-3 text-sm text-foreground-secondary"
              :style="table.columnStyle('resource_type')"
            >
              {{ resource.resource_type_display || resource.resource_type }}
            </td>
            <td
              class="whitespace-nowrap px-4 py-3"
              :style="table.columnStyle('status')"
            >
              <span
                :class="[
                  'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                  resource.status === 'active'
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                    : resource.status === 'error'
                      ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      : 'bg-background-tertiary text-foreground-secondary',
                ]"
              >
                {{ resource.status_display || resource.status }}
              </span>
            </td>
            <td
              class="whitespace-nowrap px-4 py-3 text-sm text-foreground-secondary"
              :style="table.columnStyle('bound_node')"
            >
              {{
                resource.bound_node?.name || t("sourceResources.noBoundNode")
              }}
            </td>
            <td
              class="whitespace-nowrap px-4 py-3 text-sm text-foreground-secondary"
              :style="table.columnStyle('connection')"
            >
              <span class="block truncate font-mono text-xs text-foreground">
                {{ getSourceConnection(resource) }}
              </span>
            </td>
            <td
              class="whitespace-nowrap px-4 py-3"
              :style="table.columnStyle('capacity')"
            >
              <div class="min-w-0">
                <div class="flex items-center justify-between gap-3 text-xs">
                  <span class="truncate font-medium text-foreground">
                    {{ getCapacityText(resource) }}
                  </span>
                  <span class="shrink-0 text-foreground-secondary">
                    {{
                      resource.total_size
                        ? `${getUsagePercent(resource).toFixed(1)}%`
                        : "-"
                    }}
                  </span>
                </div>
                <div
                  class="mt-2 h-1.5 overflow-hidden rounded-full bg-background-tertiary"
                >
                  <div
                    class="h-full rounded-full bg-blue-500"
                    :style="{ width: `${getUsagePercent(resource)}%` }"
                  />
                </div>
              </div>
            </td>
            <td
              class="whitespace-nowrap px-4 py-3 text-sm text-foreground-secondary"
              :style="table.columnStyle('updated_at')"
            >
              {{ formatDate(resource.updated_at) }}
            </td>
            <td
              class="whitespace-nowrap px-4 py-3 text-right"
              :style="table.columnStyle('actions')"
            >
              <div class="flex justify-end gap-1">
                <button
                  class="rounded p-1.5 text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/30"
                  :title="t('sourceResources.testConnection')"
                  @click="$emit('test', resource)"
                >
                  <LinkIcon class="h-4 w-4" />
                </button>
                <button
                  class="rounded p-1.5 text-foreground-muted hover:bg-hover hover:text-foreground-secondary"
                  :title="t('common.view')"
                  @click="$emit('detail', resource)"
                >
                  <EyeIcon class="h-4 w-4" />
                </button>
                <button
                  class="rounded p-1.5 text-foreground-muted hover:bg-hover hover:text-foreground-secondary"
                  :title="t('common.edit')"
                  @click="$emit('edit', resource)"
                >
                  <PencilIcon class="h-4 w-4" />
                </button>
                <button
                  class="rounded p-1.5 text-foreground-muted hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30"
                  :title="t('common.delete')"
                  @click="$emit('delete', resource)"
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
