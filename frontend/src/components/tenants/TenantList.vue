<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/vue";
import {
  BuildingOffice2Icon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EllipsisVerticalIcon,
} from "@heroicons/vue/24/outline";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";
import type { Tenant } from "@/types/tenant";

type TenantColumnKey =
  | "name"
  | "status"
  | "owner"
  | "user_count"
  | "proxy_count"
  | "created_at"
  | "actions";

defineProps<{
  loading: boolean;
  tenants: Tenant[];
  tenantColumns: Array<{
    key: TenantColumnKey;
    label: string;
    sortable?: boolean;
    align?: "left" | "center" | "right";
  }>;
  tenantTable: any;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
  };
  totalPages: number;
  displayedPages: number[];
  getStatusClass: (status: string) => string;
  formatDate: (date: string) => string;
}>();

const emit = defineEmits<{
  edit: [tenant: Tenant];
  users: [tenant: Tenant];
  stats: [tenant: Tenant];
  activate: [tenant: Tenant];
  deactivate: [tenant: Tenant];
  delete: [tenant: Tenant];
  previous: [];
  next: [];
  page: [page: number];
  pageSizeChange: [size: number];
}>();

const { t } = useI18n();
</script>

<template>
  <div
    class="bg-card shadow rounded-xl border border-border overflow-visible mb-4"
  >
    <div v-if="loading" class="p-8 text-center">
      <svg
        class="animate-spin h-8 w-8 text-indigo-600 mx-auto"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          class="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          stroke-width="4"
        />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      <p class="mt-2 text-sm text-foreground-secondary">
        {{ t("common.loading") }}
      </p>
    </div>

    <table
      v-else
      class="w-full table-fixed divide-y divide-border"
      :style="{ minWidth: tenantTable.tableMinWidth.value }"
    >
      <colgroup>
        <col
          v-for="column in tenantColumns"
          :key="column.key"
          :style="tenantTable.columnStyle(column.key)"
        />
      </colgroup>
      <thead class="bg-background-secondary">
        <tr>
          <ResizableSortableTh
            v-for="column in tenantColumns"
            :key="column.key"
            :column-key="column.key"
            :label="column.label"
            :style-value="tenantTable.columnStyle(column.key)"
            :sortable="column.sortable !== false"
            :active="tenantTable.sort.value.key === column.key"
            :align="column.align"
            :sort-icon="tenantTable.getSortIcon(column.key)"
            :resizing="tenantTable.resizingColumn.value === column.key"
            @sort="tenantTable.toggleSort($event as TenantColumnKey)"
            @resize-start="
              (key, event) =>
                tenantTable.startResize(key as TenantColumnKey, event)
            "
            @resize-reset="
              tenantTable.resetColumnWidth($event as TenantColumnKey)
            "
          />
        </tr>
      </thead>
      <tbody class="divide-y divide-border">
        <tr
          v-for="tenant in tenantTable.sortedRows.value"
          :key="tenant.id"
          class="hover:bg-hover"
        >
          <td
            class="whitespace-nowrap py-4 pl-4 pr-3 text-sm sm:pl-6"
            :style="tenantTable.columnStyle('name')"
          >
            <div class="flex items-center">
              <div
                class="h-10 w-10 flex-shrink-0 rounded-lg bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center"
              >
                <BuildingOffice2Icon
                  class="h-6 w-6 text-indigo-600 dark:text-indigo-400"
                />
              </div>
              <div class="ml-4">
                <div class="font-medium text-foreground">
                  {{ tenant.name }}
                </div>
                <div class="text-foreground-secondary">{{ tenant.slug }}</div>
              </div>
            </div>
          </td>
          <td
            class="whitespace-nowrap px-3 py-4 text-sm"
            :style="tenantTable.columnStyle('status')"
          >
            <span
              :class="getStatusClass(tenant.status)"
              class="inline-flex rounded-full px-2 py-1 text-xs font-semibold"
            >
              {{ t(`tenants.${tenant.status}`) }}
            </span>
          </td>
          <td
            class="whitespace-nowrap px-3 py-4 text-sm text-foreground-secondary"
            :style="tenantTable.columnStyle('owner')"
          >
            {{ tenant.owner_name || tenant.owner_email || "-" }}
          </td>
          <td
            class="whitespace-nowrap px-3 py-4 text-sm text-foreground-secondary"
            :style="tenantTable.columnStyle('user_count')"
          >
            {{ tenant.user_count || 0 }} / {{ tenant.max_users || "∞" }}
          </td>
          <td
            class="whitespace-nowrap px-3 py-4 text-sm text-foreground-secondary"
            :style="tenantTable.columnStyle('proxy_count')"
          >
            {{ tenant.proxy_count || 0 }} / {{ tenant.max_proxies || "∞" }}
          </td>
          <td
            class="whitespace-nowrap px-3 py-4 text-sm text-foreground-secondary"
            :style="tenantTable.columnStyle('created_at')"
          >
            {{ formatDate(tenant.created_at) }}
          </td>
          <td
            class="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6"
            :style="tenantTable.columnStyle('actions')"
          >
            <Menu as="div" class="relative inline-block text-left">
              <MenuButton
                class="flex items-center rounded-full text-foreground-muted hover:text-slate-600 dark:hover:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <span class="sr-only">Open options</span>
                <EllipsisVerticalIcon class="h-5 w-5" aria-hidden="true" />
              </MenuButton>
              <transition
                enter-active-class="transition ease-out duration-100"
                enter-from-class="transform opacity-0 scale-95"
                enter-to-class="transform opacity-100 scale-100"
                leave-active-class="transition ease-in duration-75"
                leave-from-class="transform opacity-100 scale-100"
                leave-to-class="transform opacity-0 scale-95"
              >
                <MenuItems
                  class="absolute right-0 z-50 mt-2 w-48 origin-top-right rounded-md popover-surface shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
                >
                  <MenuItem v-slot="{ active }">
                    <button
                      :class="[
                        active
                          ? 'bg-background-tertiary text-foreground'
                          : 'text-foreground-secondary',
                        'block w-full px-4 py-2 text-left text-sm',
                      ]"
                      @click="emit('edit', tenant)"
                    >
                      {{ t("common.edit") }}
                    </button>
                  </MenuItem>
                  <MenuItem v-slot="{ active }">
                    <button
                      :class="[
                        active
                          ? 'bg-background-tertiary text-foreground'
                          : 'text-foreground-secondary',
                        'block w-full px-4 py-2 text-left text-sm',
                      ]"
                      @click="emit('users', tenant)"
                    >
                      {{ t("tenants.manageUsers") }}
                    </button>
                  </MenuItem>
                  <MenuItem v-slot="{ active }">
                    <button
                      :class="[
                        active
                          ? 'bg-background-tertiary text-foreground'
                          : 'text-foreground-secondary',
                        'block w-full px-4 py-2 text-left text-sm',
                      ]"
                      @click="emit('stats', tenant)"
                    >
                      {{ t("tenants.stats") }}
                    </button>
                  </MenuItem>
                  <MenuItem
                    v-if="tenant.status === 'active'"
                    v-slot="{ active }"
                  >
                    <button
                      :class="[
                        active
                          ? 'bg-background-tertiary text-foreground'
                          : 'text-foreground-secondary',
                        'block w-full px-4 py-2 text-left text-sm',
                      ]"
                      @click="emit('deactivate', tenant)"
                    >
                      {{ t("tenants.deactivate") }}
                    </button>
                  </MenuItem>
                  <MenuItem v-else v-slot="{ active }">
                    <button
                      :class="[
                        active
                          ? 'bg-background-tertiary text-foreground'
                          : 'text-foreground-secondary',
                        'block w-full px-4 py-2 text-left text-sm',
                      ]"
                      @click="emit('activate', tenant)"
                    >
                      {{ t("tenants.activate") }}
                    </button>
                  </MenuItem>
                  <MenuItem v-slot="{ active }">
                    <button
                      :class="[
                        active ? 'bg-red-100 text-red-900' : 'text-red-700',
                        'block w-full px-4 py-2 text-left text-sm',
                      ]"
                      @click="emit('delete', tenant)"
                    >
                      {{ t("common.delete") }}
                    </button>
                  </MenuItem>
                </MenuItems>
              </transition>
            </Menu>
          </td>
        </tr>
        <tr v-if="tenants.length === 0">
          <td
            colspan="7"
            class="px-6 py-12 text-center text-sm text-foreground-secondary"
          >
            {{ t("common.noData") || "No tenants found" }}
          </td>
        </tr>
      </tbody>
    </table>

    <div
      v-if="pagination.total > 0"
      class="flex flex-col sm:flex-row items-center justify-between gap-4 px-4 py-3 bg-card border-t border-border"
    >
      <div class="flex flex-1 justify-between sm:hidden">
        <button
          :disabled="pagination.page === 1"
          class="relative inline-flex items-center rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover"
          @click="emit('previous')"
        >
          Previous
        </button>
        <button
          :disabled="pagination.page >= totalPages"
          class="relative ml-3 inline-flex items-center rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover"
          @click="emit('next')"
        >
          Next
        </button>
      </div>
      <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
        <div>
          <p class="text-sm text-foreground-secondary">
            {{ t("pagination.showing") }}
            {{ (pagination.page - 1) * pagination.pageSize + 1 }}
            {{ t("pagination.to") }}
            {{
              Math.min(pagination.page * pagination.pageSize, pagination.total)
            }}
            {{ t("pagination.of") }} {{ pagination.total }}
            {{ t("pagination.items") }}
          </p>
        </div>
        <div class="flex items-center gap-4">
          <!-- 每页条数选择 -->
          <div class="flex items-center gap-2">
            <span class="text-sm text-foreground-secondary">{{
              t("pagination.pageSize")
            }}</span>
            <select
              :value="pagination.pageSize"
              @change="emit('pageSizeChange', Number(($event.target as HTMLSelectElement).value))"
              class="px-2 py-1 text-sm border border-border bg-background text-foreground rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500">
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </div>

          <nav
            class="isolate inline-flex -space-x-px rounded-md shadow-sm"
            aria-label="Pagination"
          >
            <button
              :disabled="pagination.page === 1"
              class="relative inline-flex items-center rounded-l-lg border border-border px-2 py-2 text-foreground-muted hover:bg-hover focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="emit('previous')"
            >
              <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
            </button>
            <button
              v-for="page in displayedPages"
              :key="page"
              :class="[
                page === pagination.page
                  ? 'bg-indigo-600 text-white'
                  : 'text-foreground ring-1 ring-inset ring-gray-300 hover:bg-hover',
                'relative inline-flex items-center px-4 py-2 text-sm font-semibold focus:z-20 focus:outline-offset-0',
              ]"
              @click="emit('page', page)"
            >
              {{ page }}
            </button>
            <button
              :disabled="pagination.page >= totalPages"
              class="relative inline-flex items-center rounded-r-lg border border-border px-2 py-2 text-foreground-muted hover:bg-hover focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="emit('next')"
            >
              <ChevronRightIcon class="h-5 w-5" aria-hidden="true" />
            </button>
          </nav>
        </div>
      </div>
    </div>
  </div>
</template>
