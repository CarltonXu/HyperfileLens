<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/vue";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  EllipsisVerticalIcon,
} from "@heroicons/vue/24/outline";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";

interface User {
  id: string;
  email: string;
  full_name?: string;
  first_name?: string;
  last_name?: string;
  tenant_role: string;
  tenant_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  last_login_at?: string;
}

type UserColumnKey =
  | "user"
  | "email"
  | "tenant_name"
  | "role"
  | "status"
  | "last_login_at"
  | "actions";

defineProps<{
  loading: boolean;
  users: User[];
  userColumns: Array<{
    key: UserColumnKey;
    label: string;
    sortable?: boolean;
    align?: "left" | "center" | "right";
  }>;
  usersTable: any;
  isPlatformAdmin: boolean;
  currentUserId?: string | null;
  totalCount: number;
  pageSize: number;
  currentPage: number;
  visiblePages: number[];
  getInitials: (user: User) => string;
  getUnifiedRoleClass: (user: User) => string;
  getUnifiedRoleName: (user: User) => string;
  formatDate: (date: string) => string;
}>();

const emit = defineEmits<{
  edit: [user: User];
  resetPassword: [user: User];
  toggleSuperuser: [user: User, isSuperuser: boolean];
  toggleStatus: [user: User, active: boolean];
  delete: [user: User];
  page: [page: number];
  pageSizeChange: [size: number];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="bg-card shadow rounded-xl border border-border">
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
      :style="{ minWidth: usersTable.tableMinWidth.value }"
    >
      <colgroup>
        <col
          v-for="column in userColumns"
          :key="column.key"
          :style="usersTable.columnStyle(column.key)"
        />
      </colgroup>
      <thead class="bg-background-secondary">
        <tr>
          <ResizableSortableTh
            v-for="column in userColumns"
            :key="column.key"
            :column-key="column.key"
            :label="column.label"
            :style-value="usersTable.columnStyle(column.key)"
            :sortable="column.sortable !== false"
            :active="usersTable.sort.value.key === column.key"
            :align="column.align"
            :sort-icon="usersTable.getSortIcon(column.key)"
            :resizing="usersTable.resizingColumn.value === column.key"
            @sort="usersTable.toggleSort($event as UserColumnKey)"
            @resize-start="
              (key, event) =>
                usersTable.startResize(key as UserColumnKey, event)
            "
            @resize-reset="usersTable.resetColumnWidth($event as UserColumnKey)"
          />
        </tr>
      </thead>
      <tbody class="divide-y divide-border">
        <tr
          v-for="user in usersTable.sortedRows.value"
          :key="user.id"
          class="hover:bg-hover"
        >
          <td
            class="whitespace-nowrap py-4 pl-4 pr-3 text-sm sm:pl-6"
            :style="usersTable.columnStyle('user')"
          >
            <div class="flex items-center">
              <div
                class="h-10 w-10 flex-shrink-0 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center"
              >
                <span class="text-white font-medium text-sm">
                  {{ getInitials(user) }}
                </span>
              </div>
              <div class="ml-4">
                <div class="font-medium text-foreground">
                  {{ user.full_name || user.email.split("@")[0] }}
                </div>
                <div class="text-foreground-secondary text-xs">
                  ID: {{ user.id }}
                </div>
              </div>
            </div>
          </td>
          <td
            :style="usersTable.columnStyle('email')"
            class="whitespace-nowrap px-3 py-4 text-sm text-foreground-secondary"
          >
            {{ user.email }}
          </td>
          <td
            v-if="isPlatformAdmin"
            :style="usersTable.columnStyle('tenant_name')"
            class="whitespace-nowrap px-3 py-4 text-sm text-foreground-secondary"
          >
            {{ user.tenant_name || "-" }}
          </td>
          <td
            class="whitespace-nowrap px-3 py-4 text-sm"
            :style="usersTable.columnStyle('role')"
          >
            <span
              :class="getUnifiedRoleClass(user)"
              class="inline-flex rounded-full px-2 py-1 text-xs font-semibold"
            >
              {{ getUnifiedRoleName(user) }}
            </span>
          </td>
          <td
            class="whitespace-nowrap px-3 py-4 text-sm"
            :style="usersTable.columnStyle('status')"
          >
            <span
              :class="
                user.is_active
                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                  : 'bg-gray-100 text-gray-800'
              "
              class="inline-flex rounded-full px-2 py-1 text-xs font-semibold"
            >
              {{ user.is_active ? t("users.active") : t("users.inactive") }}
            </span>
          </td>
          <td
            :style="usersTable.columnStyle('last_login_at')"
            class="whitespace-nowrap px-3 py-4 text-sm text-foreground-secondary"
          >
            {{ user.last_login_at ? formatDate(user.last_login_at) : "-" }}
          </td>
          <td
            :style="usersTable.columnStyle('actions')"
            class="whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6"
          >
            <Menu as="div" class="relative inline-block text-left">
              <MenuButton
                class="flex items-center rounded-full bg-background p-1 text-foreground-muted hover:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
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
                  class="absolute right-0 z-50 mt-2 w-56 origin-top-right rounded-md popover-surface shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
                >
                  <div class="py-1">
                    <MenuItem v-slot="{ active }">
                      <button
                        :class="[
                          active
                            ? 'bg-hover text-foreground'
                            : 'text-foreground',
                          'block w-full px-4 py-2 text-left text-sm',
                        ]"
                        @click="emit('edit', user)"
                      >
                        {{ t("users.editUser") }}
                      </button>
                    </MenuItem>
                    <MenuItem v-slot="{ active }">
                      <button
                        :class="[
                          active
                            ? 'bg-hover text-foreground'
                            : 'text-foreground',
                          'block w-full px-4 py-2 text-left text-sm',
                        ]"
                        @click="emit('resetPassword', user)"
                      >
                        {{ t("users.resetPassword") }}
                      </button>
                    </MenuItem>
                    <MenuItem
                      v-if="isPlatformAdmin && !user.is_superuser"
                      v-slot="{ active }"
                    >
                      <button
                        :class="[
                          active
                            ? 'bg-hover text-foreground'
                            : 'text-foreground',
                          'block w-full px-4 py-2 text-left text-sm',
                        ]"
                        @click="emit('toggleSuperuser', user, true)"
                      >
                        {{ t("users.setPlatformAdmin") }}
                      </button>
                    </MenuItem>
                    <MenuItem
                      v-if="
                        isPlatformAdmin &&
                        user.is_superuser &&
                        user.id !== currentUserId
                      "
                      v-slot="{ active }"
                    >
                      <button
                        :class="[
                          active
                            ? 'bg-hover text-foreground'
                            : 'text-foreground',
                          'block w-full px-4 py-2 text-left text-sm',
                        ]"
                        @click="emit('toggleSuperuser', user, false)"
                      >
                        {{ t("users.removePlatformAdmin") }}
                      </button>
                    </MenuItem>
                    <MenuItem v-if="user.is_active" v-slot="{ active }">
                      <button
                        :class="[
                          active
                            ? 'bg-hover text-foreground'
                            : 'text-foreground',
                          'block w-full px-4 py-2 text-left text-sm',
                        ]"
                        @click="emit('toggleStatus', user, false)"
                      >
                        {{ t("users.disableUser") }}
                      </button>
                    </MenuItem>
                    <MenuItem v-else v-slot="{ active }">
                      <button
                        :class="[
                          active
                            ? 'bg-hover text-foreground'
                            : 'text-foreground',
                          'block w-full px-4 py-2 text-left text-sm',
                        ]"
                        @click="emit('toggleStatus', user, true)"
                      >
                        {{ t("users.enableUser") }}
                      </button>
                    </MenuItem>
                    <div class="border-t border-border my-1" />
                    <MenuItem
                      v-if="user.id !== currentUserId"
                      v-slot="{ active }"
                    >
                      <button
                        :class="[
                          active
                            ? 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                            : 'text-red-600 dark:text-red-400',
                          'block w-full px-4 py-2 text-left text-sm',
                        ]"
                        @click="emit('delete', user)"
                      >
                        {{ t("users.deleteUser") }}
                      </button>
                    </MenuItem>
                  </div>
                </MenuItems>
              </transition>
            </Menu>
          </td>
        </tr>
        <tr v-if="users.length === 0">
          <td
            :colspan="isPlatformAdmin ? 7 : 6"
            class="px-3 py-12 text-center text-foreground-secondary"
          >
            {{ t("common.noData") }}
          </td>
        </tr>
      </tbody>
    </table>

    <div
      v-if="totalCount > 0"
      class="flex flex-col sm:flex-row items-center justify-between gap-4 px-4 py-3 bg-card border-t border-border"
    >
      <div class="flex flex-1 justify-between sm:hidden">
        <button
          :disabled="currentPage === 1"
          class="relative inline-flex items-center rounded-md border border-border-secondary bg-background px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
          @click="emit('page', currentPage - 1)"
        >
          {{ t("common.previous") }}
        </button>
        <button
          :disabled="currentPage * pageSize >= totalCount"
          class="relative ml-3 inline-flex items-center rounded-md border border-border-secondary bg-background px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
          @click="emit('page', currentPage + 1)"
        >
          {{ t("common.next") }}
        </button>
      </div>
      <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
        <div>
          <p class="text-sm text-foreground-secondary">
            {{ t("common.showing") }}
            <span class="font-medium">{{
              (currentPage - 1) * pageSize + 1
            }}</span>
            {{ t("common.to") }}
            <span class="font-medium">{{
              Math.min(currentPage * pageSize, totalCount)
            }}</span>
            {{ t("common.of") }}
            <span class="font-medium">{{ totalCount }}</span>
            {{ t("common.results") }}
          </p>
        </div>
        <div class="flex items-center gap-4">
          <!-- 每页条数选择 -->
          <div class="flex items-center gap-2">
            <span class="text-sm text-foreground-secondary">{{
              t("pagination.pageSize")
            }}</span>
            <select
              :value="pageSize"
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
              :disabled="currentPage === 1"
              class="relative inline-flex items-center rounded-l-lg border border-border px-2 py-2 text-slate-400 hover:bg-hover focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="emit('page', currentPage - 1)"
            >
              <span class="sr-only">{{ t("common.previous") }}</span>
              <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
            </button>
            <button
              v-for="page in visiblePages"
              :key="page"
              :class="[
                page === currentPage
                  ? 'bg-indigo-600 text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600'
                  : 'text-foreground ring-1 ring-inset ring-border hover:bg-hover',
                'relative inline-flex items-center px-4 py-2 text-sm font-semibold',
              ]"
              @click="emit('page', page)"
            >
              {{ page }}
            </button>
            <button
              :disabled="currentPage * pageSize >= totalCount"
              class="relative inline-flex items-center rounded-r-lg border border-border px-2 py-2 text-slate-400 hover:bg-hover focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
              @click="emit('page', currentPage + 1)"
            >
              <span class="sr-only">{{ t("common.next") }}</span>
              <ChevronRightIcon class="h-5 w-5" aria-hidden="true" />
            </button>
          </nav>
        </div>
      </div>
    </div>
  </div>
</template>
