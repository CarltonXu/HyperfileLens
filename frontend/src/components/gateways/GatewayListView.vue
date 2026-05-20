<script setup lang="ts">
import { useI18n } from "vue-i18n";
import Pagination from "@/components/Pagination.vue";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";
import {
  ArrowPathIcon,
  ChatBubbleLeftRightIcon,
  ClipboardDocumentIcon,
  ServerIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline";

type Gateway = {
  id: string;
  name: string;
  description: string;
  hostname: string;
  internal_ip: string;
  ssh_port: number;
  status: string;
  os_version: string;
  version: string;
  kopia_version: string;
  cpu_cores: number;
  memory_total: number;
  disk_total: number;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  active_mounts: number;
  mount_base_path: string;
  max_concurrent_mounts: number;
  ai_enabled: boolean;
  indexer_status: string;
  last_index_time: string;
  last_heartbeat: string;
  is_online: boolean;
  tags: Record<string, string>;
  labels: string[];
  created_at: string;
  updated_at: string;
  registered_at: string;
  installed_at: string;
};

type GatewayColumnKey =
  | "name"
  | "status"
  | "hostname"
  | "internal_ip"
  | "active_mounts"
  | "cpu_cores"
  | "memory_total"
  | "kopia_version"
  | "last_heartbeat"
  | "actions";

const currentPage = defineModel<number>("currentPage", { required: true });
const pageSize = defineModel<number>("pageSize", { required: true });

defineProps<{
  loading: boolean;
  filteredGateways: Gateway[];
  viewMode: "card" | "list";
  totalItems: number;
  columns: Array<{
    key: GatewayColumnKey;
    label: string;
    min: number;
    max: number;
    sortable?: boolean;
    align?: "left" | "center" | "right";
  }>;
  table: any;
  statusColors: Record<string, string>;
  getStatusLabel: (status: string) => string;
  formatBytes: (bytes: number) => string;
  formatDate: (date: string) => string;
}>();

defineEmits<{
  detail: [gateway: Gateway];
  delete: [gateway: Gateway];
}>();

const { t } = useI18n();
</script>

<template>
  <div v-if="loading" class="flex items-center justify-center py-12">
    <ArrowPathIcon class="w-8 h-8 text-slate-400 animate-spin" />
  </div>

  <div v-else-if="filteredGateways.length === 0" class="text-center py-12">
    <ServerIcon class="w-16 h-16 text-foreground-muted mx-auto mb-4" />
    <p class="text-foreground-secondary">{{ t("gateways.noGateways") }}</p>
  </div>

  <div
    v-else-if="viewMode === 'card'"
    class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
  >
    <div
      v-for="gateway in filteredGateways"
      :key="gateway.id"
      class="bg-card rounded-xl border border-border p-5 hover:border-violet-300 dark:hover:border-violet-700 cursor-pointer transition-all"
      @click="$emit('detail', gateway)"
    >
      <div class="flex items-start justify-between mb-4">
        <div class="flex items-center gap-3">
          <div
            :class="[
              'w-10 h-10 rounded-lg flex items-center justify-center',
              gateway.is_online
                ? 'bg-emerald-100 dark:bg-emerald-900/30'
                : 'bg-background-tertiary',
            ]"
          >
            <ServerIcon
              :class="[
                'w-5 h-5',
                gateway.is_online
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'text-slate-400',
              ]"
            />
          </div>
          <div>
            <h3 class="font-semibold text-foreground">{{ gateway.name }}</h3>
            <p class="text-sm text-foreground-secondary">
              {{ gateway.hostname || gateway.internal_ip || "-" }}
            </p>
          </div>
        </div>
        <span
          :class="[
            'px-2 py-1 text-xs font-medium rounded-full',
            statusColors[gateway.status],
          ]"
        >
          {{ getStatusLabel(gateway.status) }}
        </span>
      </div>

      <div class="space-y-2 text-sm">
        <div class="flex items-center justify-between text-foreground-secondary">
          <span>{{ t("gateways.activeMounts") }}</span>
          <span class="font-medium text-foreground-secondary">{{
            gateway.active_mounts
          }}</span>
        </div>
        <div class="flex items-center justify-between text-foreground-secondary">
          <span>{{ t("gateways.cpuCores") }}</span>
          <span class="font-medium text-foreground-secondary">{{
            gateway.cpu_cores || "-"
          }}</span>
        </div>
        <div
          v-if="gateway.kopia_version"
          class="flex items-center justify-between text-foreground-secondary"
        >
          <span>{{ t("gateways.kopiaVersion") }}</span>
          <span class="font-medium text-foreground-secondary">{{
            gateway.kopia_version
          }}</span>
        </div>
      </div>

      <div v-if="gateway.ai_enabled" class="mt-4 pt-4 border-t border-border">
        <div
          class="flex items-center gap-2 text-sm text-violet-600 dark:text-violet-400"
        >
          <ChatBubbleLeftRightIcon class="w-4 h-4" />
          <span>{{ t("gateways.aiEnabled") }}</span>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="bg-card rounded-xl border border-border overflow-hidden">
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
              @sort="table.toggleSort($event as GatewayColumnKey)"
              @resize-start="
                (key, event) =>
                  table.startResize(key as GatewayColumnKey, event)
              "
              @resize-reset="table.resetColumnWidth($event as GatewayColumnKey)"
            />
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr
            v-for="gateway in table.sortedRows.value"
            :key="gateway.id"
            class="hover:bg-hover/50"
          >
            <td
              class="px-4 py-3 whitespace-nowrap"
              :style="table.columnStyle('name')"
            >
              <button
                @click="$emit('detail', gateway)"
                class="flex min-w-0 items-center gap-3 text-left"
              >
                <ServerIcon
                  :class="[
                    'w-5 h-5 flex-shrink-0',
                    gateway.is_online
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-foreground-muted',
                  ]"
                />
                <span class="min-w-0">
                  <span class="block truncate font-medium text-foreground">
                    {{ gateway.name }}
                  </span>
                  <span class="block truncate text-xs text-foreground-secondary">
                    {{ gateway.description || gateway.id }}
                  </span>
                </span>
              </button>
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap"
              :style="table.columnStyle('status')"
            >
              <span
                :class="[
                  'px-2 py-1 text-xs font-medium rounded-full',
                  statusColors[gateway.status],
                ]"
              >
                {{ getStatusLabel(gateway.status) }}
              </span>
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
              :style="table.columnStyle('hostname')"
            >
              {{ gateway.hostname || "-" }}
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
              :style="table.columnStyle('internal_ip')"
            >
              {{ gateway.internal_ip || "-" }}
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
              :style="table.columnStyle('active_mounts')"
            >
              {{ gateway.active_mounts }}
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
              :style="table.columnStyle('cpu_cores')"
            >
              {{ gateway.cpu_cores || "-" }}
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
              :style="table.columnStyle('memory_total')"
            >
              {{ formatBytes(gateway.memory_total) }}
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
              :style="table.columnStyle('kopia_version')"
            >
              {{ gateway.kopia_version || "-" }}
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
              :style="table.columnStyle('last_heartbeat')"
            >
              {{ formatDate(gateway.last_heartbeat) }}
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap text-right"
              :style="table.columnStyle('actions')"
            >
              <div class="flex justify-end gap-1">
                <button
                  @click="$emit('detail', gateway)"
                  class="p-1.5 text-foreground-muted hover:text-foreground-secondary hover:bg-hover rounded"
                  :title="t('common.details')"
                >
                  <ClipboardDocumentIcon class="w-4 h-4" />
                </button>
                <button
                  @click="$emit('delete', gateway)"
                  class="p-1.5 text-foreground-muted hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded"
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
      v-if="totalItems > pageSize"
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total-items="totalItems"
    />
  </div>
</template>
