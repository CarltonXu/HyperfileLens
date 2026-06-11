<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import Pagination from "@/components/Pagination.vue";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";
import GatewayActionMenu from "@/components/gateways/GatewayActionMenu.vue";
import {
  ArrowPathIcon,
  ChatBubbleLeftRightIcon,
  CpuChipIcon,
  EllipsisVerticalIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  MapPinIcon,
  CircleStackIcon,
  ServerIcon,
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
  | "memory_usage"
  | "disk_usage"
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

const emit = defineEmits<{
  detail: [gateway: any];
  delete: [gateway: any];
  edit: [gateway: any];
  regenerateToken: [gateway: any];
  updateStatus: [gateway: any, status: string];
  installInfo: [gateway: any];
}>();

const { t } = useI18n();

// Action menu state
const actionMenu = ref<{
  open: boolean;
  gateway: Gateway | null;
  position: { x: number; y: number };
}>({
  open: false,
  gateway: null,
  position: { x: 0, y: 0 },
});

function openActionMenu(event: MouseEvent, gateway: Gateway) {
  event.stopPropagation();
  const target = event.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  actionMenu.value = {
    open: true,
    gateway,
    position: {
      x: rect.right - 180,
      y: rect.bottom + 4,
    },
  };
}

function closeActionMenu() {
  actionMenu.value.open = false;
  actionMenu.value.gateway = null;
}

function emitMenuAction(
  event: "detail" | "delete" | "edit" | "regenerateToken",
  gateway: any,
) {
  if (event === "detail") emit("detail", gateway);
  if (event === "delete") emit("delete", gateway);
  if (event === "edit") emit("edit", gateway);
  if (event === "regenerateToken") emit("regenerateToken", gateway);
  closeActionMenu();
}

function emitStatusUpdate(gateway: any, status: string) {
  emit("updateStatus", gateway, status);
  closeActionMenu();
}

function usageBarColor(value: number | null | undefined) {
  if (value === null || value === undefined) return "bg-slate-300";
  if (value > 80) return "bg-red-500";
  if (value > 60) return "bg-amber-500";
  return "bg-emerald-500";
}

function usageWidth(value: number | null | undefined) {
  if (value === null || value === undefined) return "0%";
  return `${Math.min(Math.max(value, 0), 100)}%`;
}

function displayStatusKey(gateway: Gateway): "online" | "offline" {
  return gateway.is_online ? "online" : "offline";
}

function displayStatusLabel(gateway: Gateway): string {
  return gateway.is_online ? t("gateways.online") : t("gateways.offline");
}
</script>

<template>
  <div v-if="loading" class="flex items-center justify-center py-12">
    <ArrowPathIcon class="w-8 h-8 text-slate-400 animate-spin" />
  </div>

  <div
    v-else-if="filteredGateways.length === 0"
    class="rounded-xl border border-border p-12 text-center"
  >
    <div
      class="w-16 h-16 bg-background-tertiary/50 rounded-full flex items-center justify-center mx-auto mb-4"
    >
      <ServerIcon class="w-8 h-8 text-foreground-muted" />
    </div>
    <h3 class="text-lg font-medium text-foreground mb-1">
      {{
        totalItems === 0
          ? t("gateways.empty.title")
          : t("gateways.noGateways")
      }}
    </h3>
    <p class="text-foreground-secondary">
      {{
        totalItems === 0
          ? t("gateways.empty.description")
          : t("common.noData")
      }}
    </p>
  </div>

  <div v-else-if="viewMode === 'card'" class="space-y-4">
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div
        v-for="gateway in filteredGateways"
        :key="gateway.id"
        class="bg-card rounded-xl border border-border p-5 shadow-sm hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600 transition-all group cursor-pointer"
        @click="$emit('detail', gateway)"
      >
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-3">
            <div
              :class="[
                'w-11 h-11 rounded-xl flex items-center justify-center',
                gateway.is_online
                  ? 'bg-gradient-to-br from-emerald-500 to-teal-600'
                  : 'bg-gradient-to-br from-slate-400 to-slate-600',
              ]"
            >
              <ServerIcon class="w-6 h-6 text-white" />
            </div>
            <div>
              <h3
                class="font-semibold text-foreground group-hover:text-indigo-600 transition-colors"
              >
                {{ gateway.name }}
              </h3>
              <span
                :class="[
                  'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium mt-1',
                  statusColors[displayStatusKey(gateway)],
                ]"
              >
                {{ displayStatusLabel(gateway) }}
              </span>
            </div>
          </div>
          <div class="relative" @click.stop>
            <button
              class="p-1.5 text-foreground-muted hover:text-foreground-secondary hover:bg-hover rounded-lg transition-colors"
              @click="openActionMenu($event, gateway)"
            >
              <EllipsisVerticalIcon class="w-5 h-5" />
            </button>
          </div>
        </div>

        <div class="space-y-3 text-sm">
          <div class="flex items-center gap-2 text-foreground-secondary">
            <MapPinIcon class="w-4 h-4 flex-shrink-0" />
            <span class="truncate">{{
              gateway.hostname || gateway.internal_ip || "-"
            }}</span>
          </div>
          <div class="flex items-center gap-2 text-foreground-secondary">
            <CircleStackIcon class="w-4 h-4 flex-shrink-0" />
            <span
              >{{ t("gateways.activeMounts") }}:
              {{ gateway.active_mounts }}</span
            >
          </div>
          <div class="flex items-center gap-2 text-foreground-secondary">
            <CpuChipIcon class="w-4 h-4 flex-shrink-0" />
            <span>
              {{ gateway.os_version || gateway.kopia_version || "Unknown" }}
              {{
                gateway.cpu_cores
                  ? `(${gateway.cpu_cores} ${t("gateways.cores")})`
                  : ""
              }}
            </span>
          </div>
        </div>

        <div
          v-if="gateway.cpu_usage !== null"
          class="mt-4 grid grid-cols-3 gap-2 text-center"
        >
          <div class="bg-background-secondary rounded-lg p-2">
            <p class="text-xs text-foreground-secondary">CPU</p>
            <p class="text-sm font-medium text-foreground">
              {{ gateway.cpu_usage?.toFixed(1) }}%
            </p>
          </div>
          <div class="bg-background-secondary rounded-lg p-2">
            <p class="text-xs text-foreground-secondary">
              {{ t("gateways.memory") }}
            </p>
            <p class="text-sm font-medium text-foreground">
              {{ gateway.memory_usage?.toFixed(1) }}%
            </p>
            <div class="h-1.5 bg-slate-200 rounded-full overflow-hidden mt-2">
              <div
                class="h-full rounded-full transition-all"
                :class="usageBarColor(gateway.memory_usage)"
                :style="{ width: usageWidth(gateway.memory_usage) }"
              />
            </div>
          </div>
          <div class="bg-background-secondary rounded-lg p-2">
            <p class="text-xs text-foreground-secondary">
              {{ t("gateways.disk") }}
            </p>
            <p class="text-sm font-medium text-foreground">
              {{ gateway.disk_usage?.toFixed(1) }}%
            </p>
            <div class="h-1.5 bg-slate-200 rounded-full overflow-hidden mt-2">
              <div
                class="h-full rounded-full transition-all"
                :class="usageBarColor(gateway.disk_usage)"
                :style="{ width: usageWidth(gateway.disk_usage) }"
              />
            </div>
          </div>
        </div>

        <div
          class="flex items-center justify-between mt-4 pt-4 border-t border-border"
        >
          <div
            v-if="gateway.ai_enabled"
            class="flex items-center gap-2 text-sm text-violet-600 dark:text-violet-400"
          >
            <ChatBubbleLeftRightIcon class="w-4 h-4" />
            <span>{{ t("gateways.aiEnabled") }}</span>
          </div>
          <span v-else />
          <button
            v-if="!gateway.is_online"
            class="text-sm font-medium text-amber-600 dark:text-amber-400 hover:text-amber-700 flex items-center gap-1"
            @click.stop="$emit('installInfo', gateway)"
          >
            <ExclamationTriangleIcon class="w-4 h-4" />
            {{ t("gateways.actions.viewInstall") }}
          </button>
        </div>
      </div>
    </div>

    <Pagination
      v-if="totalItems > pageSize"
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total-items="totalItems"
    />
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
              @sort="table.toggleSort($event as GatewayColumnKey)"
              @resize-start="
                (key, event) =>
                  table.startResize(key as GatewayColumnKey, event)
              "
              @resize-reset="table.resetColumnWidth($event as GatewayColumnKey)"
            />
          </tr>
        </thead>
        <tbody class="[&>tr>td]:border-b [&>tr>td]:border-border">
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
                  <span
                    class="block truncate text-xs text-foreground-secondary"
                  >
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
                  statusColors[displayStatusKey(gateway)],
                ]"
              >
                {{ displayStatusLabel(gateway) }}
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
              :style="table.columnStyle('cpu_cores')"
            >
              {{ gateway.cpu_cores || "-" }}
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap"
              :style="table.columnStyle('memory_usage')"
            >
              <div
                v-if="
                  gateway.memory_usage !== null &&
                  gateway.memory_usage !== undefined
                "
                class="flex items-center gap-2"
              >
                <div
                  class="w-16 h-1.5 bg-slate-200 rounded-full overflow-hidden"
                >
                  <div
                    class="h-full rounded-full transition-all"
                    :class="usageBarColor(gateway.memory_usage)"
                    :style="{ width: usageWidth(gateway.memory_usage) }"
                  />
                </div>
                <span class="text-xs text-foreground-secondary w-10">
                  {{ gateway.memory_usage?.toFixed(0) }}%
                </span>
              </div>
              <span v-else class="text-foreground-muted">-</span>
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap"
              :style="table.columnStyle('disk_usage')"
            >
              <div
                v-if="
                  gateway.disk_usage !== null &&
                  gateway.disk_usage !== undefined
                "
                class="flex items-center gap-2"
              >
                <div
                  class="w-16 h-1.5 bg-slate-200 rounded-full overflow-hidden"
                >
                  <div
                    class="h-full rounded-full transition-all"
                    :class="usageBarColor(gateway.disk_usage)"
                    :style="{ width: usageWidth(gateway.disk_usage) }"
                  />
                </div>
                <span class="text-xs text-foreground-secondary w-10">
                  {{ gateway.disk_usage?.toFixed(0) }}%
                </span>
              </div>
              <span v-else class="text-foreground-muted">-</span>
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
              :style="table.columnStyle('kopia_version')"
            >
              {{ gateway.kopia_version || "-" }}
            </td>
            <td
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
              :style="table.columnStyle('active_mounts')"
            >
              {{ gateway.active_mounts }}
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
                  v-if="!gateway.is_online"
                  @click="$emit('installInfo', gateway)"
                  class="p-1.5 text-amber-600 dark:text-amber-400 hover:bg-amber-50 rounded"
                  :title="t('gateways.actions.viewInstall')"
                >
                  <ExclamationTriangleIcon class="w-4 h-4" />
                </button>
                <button
                  @click="$emit('detail', gateway)"
                  class="p-1.5 text-foreground-muted hover:text-foreground-secondary hover:bg-hover rounded"
                  :title="t('common.details')"
                >
                  <EyeIcon class="w-4 h-4" />
                </button>
                <button
                  @click="openActionMenu($event, gateway)"
                  class="p-1.5 text-foreground-muted hover:text-foreground-secondary hover:bg-hover rounded"
                  :title="t('common.actions')"
                >
                  <EllipsisVerticalIcon class="w-4 h-4" />
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

  <!-- Action Menu -->
  <GatewayActionMenu
    v-if="actionMenu.open && actionMenu.gateway"
    :gateway="actionMenu.gateway"
    :open="actionMenu.open"
    :menu-style="{
      left: `${actionMenu.position.x}px`,
      top: `${actionMenu.position.y}px`,
    }"
    @close="closeActionMenu"
    @detail="(gateway) => emitMenuAction('detail', gateway)"
    @edit="(gateway) => emitMenuAction('edit', gateway)"
    @regenerate-token="(gateway) => emitMenuAction('regenerateToken', gateway)"
    @install-info="$emit('installInfo', $event)"
    @update-status="emitStatusUpdate"
    @delete="(gateway) => emitMenuAction('delete', gateway)"
  />
</template>
