<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  EllipsisHorizontalIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  PlusIcon,
  ServerIcon,
} from "@heroicons/vue/24/outline";
import Pagination from "@/components/Pagination.vue";
import type { ProxyNode } from "@/types/proxy";
import ProxyActionMenu from "./ProxyActionMenu.vue";

type ProxySortKey =
  | "name"
  | "role"
  | "status"
  | "hostname"
  | "internal_ip"
  | "cpu_cores"
  | "memory_usage"
  | "disk_usage"
  | "last_heartbeat";

type ProxyTableColumnKey = ProxySortKey | "actions";

defineProps<{
  loading: boolean;
  filteredCount: number;
  proxies: ProxyNode[];
  columns: Array<{ key: ProxySortKey; label: string }>;
  sortKey: ProxySortKey;
  tableMinWidth: string;
  resizingColumn: ProxyTableColumnKey | null;
  openMenuId: string | null;
  menuStyle: Record<string, string>;
  agentIcon: any;
  syncIcon: any;
  columnStyle: (key: ProxyTableColumnKey) => Record<string, string>;
  getSortIcon: (key: ProxySortKey) => any;
  getRoleColor: (role: string) => string;
  getStatusColor: (status: string) => string;
  timeSince: (date: string | null) => string;
}>();

const currentPage = defineModel<number>("currentPage", { required: true });
const pageSize = defineModel<number>("pageSize", { required: true });

defineEmits<{
  install: [];
  sort: [key: ProxySortKey];
  resizeStart: [key: ProxyTableColumnKey, event: MouseEvent];
  resizeReset: [key: ProxyTableColumnKey];
  toggleMenu: [proxyId: string, event: Event];
  closeMenu: [];
  detail: [proxy: ProxyNode];
  edit: [proxy: ProxyNode];
  regenerateToken: [proxy: ProxyNode];
  updateStatus: [proxy: ProxyNode, status: string];
  delete: [proxy: ProxyNode];
  installInfo: [proxy: ProxyNode];
}>();

const { t } = useI18n();
</script>

<template>
  <template v-if="loading">
    <div class="flex items-center justify-center py-12">
      <div
        class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"
      />
    </div>
  </template>

  <div
    v-else-if="filteredCount === 0"
    class="bg-card rounded-xl border border-border p-12 text-center"
  >
    <div
      class="w-16 h-16 bg-background-tertiary rounded-full flex items-center justify-center mx-auto mb-4"
    >
      <ServerIcon class="w-8 h-8 text-foreground-muted" />
    </div>
    <h3 class="text-lg font-medium text-foreground mb-1">
      {{ t("proxies.empty.title") }}
    </h3>
    <p class="text-foreground-secondary">
      {{ t("proxies.empty.description") }}
    </p>
    <button
      class="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
      @click="$emit('install')"
    >
      <PlusIcon class="w-4 h-4" />
      {{ t("proxies.installProxy") }}
    </button>
  </div>

  <div
    v-else
    class="flex max-h-[calc(100vh-19rem)] min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-card"
  >
    <div class="relative min-h-0 flex-1 overflow-auto bg-card">
      <table
        class="w-full table-fixed border-separate border-spacing-0"
        :style="{ minWidth: tableMinWidth }"
      >
        <colgroup>
          <col
            v-for="column in columns"
            :key="column.key"
            :style="columnStyle(column.key)"
          />
          <col :style="columnStyle('actions')" />
        </colgroup>
        <thead class="sticky top-0 z-30 bg-background-secondary shadow-sm">
          <tr>
            <th
              v-for="column in columns"
              :key="column.key"
              :style="columnStyle(column.key)"
              :class="[
                'relative border-b border-border bg-background-secondary px-4 py-3 text-left text-xs font-medium text-foreground-secondary uppercase tracking-wider whitespace-nowrap',
                column.key === 'name' ? 'sticky left-0 z-10' : '',
              ]"
            >
              <button
                type="button"
                class="group/sort inline-flex max-w-full items-center gap-1.5 rounded-md text-left hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                @click="$emit('sort', column.key)"
              >
                <span class="truncate uppercase tracking-wider">{{
                  column.label
                }}</span>
                <component
                  :is="getSortIcon(column.key)"
                  :class="[
                    'h-3.5 w-3.5 flex-shrink-0 transition-colors',
                    sortKey === column.key
                      ? 'text-primary'
                      : 'text-foreground-muted group-hover/sort:text-foreground-secondary',
                  ]"
                />
              </button>
              <span
                role="separator"
                aria-orientation="vertical"
                :class="[
                  'absolute right-0 top-0 h-full w-2 cursor-col-resize select-none touch-none',
                  'after:absolute after:right-0 after:top-2 after:h-[calc(100%-1rem)] after:w-px after:bg-border',
                  'hover:after:bg-primary',
                  resizingColumn === column.key ? 'after:bg-primary' : '',
                ]"
                @mousedown="$emit('resizeStart', column.key, $event)"
                @dblclick.stop="$emit('resizeReset', column.key)"
              />
            </th>
            <th
              :style="columnStyle('actions')"
              class="sticky right-0 z-10 border-b border-border bg-background-secondary px-4 py-3 text-right text-xs font-medium text-foreground-secondary"
            >
              <span class="uppercase tracking-wider">{{
                t("proxies.list.actions")
              }}</span>
            </th>
          </tr>
        </thead>
        <tbody class="bg-card [&>tr>td]:border-b [&>tr>td]:border-border">
          <tr
            v-for="proxy in proxies"
            :key="proxy.id"
            class="group hover:bg-hover transition-colors"
          >
            <td
              :style="columnStyle('name')"
              class="sticky left-0 bg-card px-4 py-3 whitespace-nowrap z-10 group-hover:bg-hover"
            >
              <div class="flex items-center gap-3">
                <div
                  :class="[
                    'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                    proxy.role === 'agent'
                      ? 'bg-gradient-to-br from-indigo-500 to-blue-600'
                      : 'bg-gradient-to-br from-purple-500 to-violet-600',
                  ]"
                >
                  <component
                    :is="proxy.role === 'agent' ? agentIcon : syncIcon"
                    class="w-4 h-4 text-white"
                  />
                </div>
                <button
                  class="font-medium text-sm hover:text-indigo-600 cursor-pointer transition-colors text-left"
                  @click="$emit('detail', proxy)"
                >
                  {{ proxy.name }}
                </button>
              </div>
            </td>
            <td
              :style="columnStyle('role')"
              class="px-4 py-3 whitespace-nowrap"
            >
              <span
                :class="[
                  'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
                  getRoleColor(proxy.role),
                ]"
              >
                {{ t(`proxies.roles.${proxy.role}`) }}
              </span>
            </td>
            <td
              :style="columnStyle('status')"
              class="px-4 py-3 whitespace-nowrap"
            >
              <span
                :class="[
                  'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                  getStatusColor(proxy.status),
                ]"
              >
                {{ t(`proxies.status.${proxy.status}`) }}
              </span>
            </td>
            <td
              :style="columnStyle('hostname')"
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
            >
              {{ proxy.hostname || "-" }}
            </td>
            <td
              :style="columnStyle('internal_ip')"
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
            >
              {{ proxy.internal_ip || "-" }}
            </td>
            <td
              :style="columnStyle('cpu_cores')"
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
            >
              {{
                proxy.cpu_cores
                  ? `${proxy.cpu_cores} ${t("proxies.list.cores")}`
                  : "-"
              }}
            </td>
            <td
              :style="columnStyle('memory_usage')"
              class="px-4 py-3 whitespace-nowrap"
            >
              <div
                v-if="proxy.memory_usage !== null"
                class="flex items-center gap-2"
              >
                <div
                  class="w-16 h-1.5 bg-slate-200 rounded-full overflow-hidden"
                >
                  <div
                    class="h-full rounded-full transition-all"
                    :class="
                      proxy.memory_usage > 80
                        ? 'bg-red-500'
                        : proxy.memory_usage > 60
                          ? 'bg-amber-500'
                          : 'bg-emerald-500'
                    "
                    :style="{ width: `${Math.min(proxy.memory_usage, 100)}%` }"
                  />
                </div>
                <span class="text-xs text-foreground-secondary w-10"
                  >{{ proxy.memory_usage?.toFixed(0) }}%</span
                >
              </div>
              <span v-else class="text-foreground-muted">-</span>
            </td>
            <td
              :style="columnStyle('disk_usage')"
              class="px-4 py-3 whitespace-nowrap"
            >
              <div
                v-if="proxy.disk_usage !== null"
                class="flex items-center gap-2"
              >
                <div
                  class="w-16 h-1.5 bg-slate-200 rounded-full overflow-hidden"
                >
                  <div
                    class="h-full rounded-full transition-all"
                    :class="
                      proxy.disk_usage > 80
                        ? 'bg-red-500'
                        : proxy.disk_usage > 60
                          ? 'bg-amber-500'
                          : 'bg-emerald-500'
                    "
                    :style="{ width: `${Math.min(proxy.disk_usage, 100)}%` }"
                  />
                </div>
                <span class="text-xs text-foreground-secondary w-10"
                  >{{ proxy.disk_usage?.toFixed(0) }}%</span
                >
              </div>
              <span v-else class="text-foreground-muted">-</span>
            </td>
            <td
              :style="columnStyle('last_heartbeat')"
              class="px-4 py-3 whitespace-nowrap text-sm text-foreground-secondary"
            >
              {{ timeSince(proxy.last_heartbeat) }}
            </td>
            <td
              :style="columnStyle('actions')"
              class="sticky right-0 bg-card px-4 py-3 whitespace-nowrap z-10 group-hover:bg-hover"
            >
              <div class="flex items-center justify-end gap-2">
                <button
                  v-if="proxy.status === 'pending'"
                  class="p-1.5 text-amber-600 dark:text-amber-400 hover:bg-amber-50 rounded-lg transition-colors"
                  :title="t('proxies.actions.viewInstall')"
                  @click="$emit('installInfo', proxy)"
                >
                  <ExclamationTriangleIcon class="w-4 h-4" />
                </button>
                <button
                  class="p-1.5 text-foreground-muted hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                  :title="t('proxies.actions.viewDetails')"
                  @click="$emit('detail', proxy)"
                >
                  <InformationCircleIcon class="w-4 h-4" />
                </button>
                <div class="relative" @click.stop>
                  <button
                    class="p-1.5 text-foreground-muted hover:text-foreground-secondary hover:bg-hover rounded-lg transition-colors"
                    @click="$emit('toggleMenu', proxy.id, $event)"
                  >
                    <EllipsisHorizontalIcon class="w-4 h-4" />
                  </button>
                  <ProxyActionMenu
                    :proxy="proxy"
                    :open="openMenuId === proxy.id"
                    :menu-style="menuStyle"
                    @close="$emit('closeMenu')"
                    @detail="$emit('detail', $event)"
                    @edit="$emit('edit', $event)"
                    @regenerate-token="$emit('regenerateToken', $event)"
                    @update-status="
                      (item, status) => $emit('updateStatus', item, status)
                    "
                    @delete="$emit('delete', $event)"
                  />
                </div>
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
