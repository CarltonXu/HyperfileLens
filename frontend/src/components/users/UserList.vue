<script setup lang="ts">
import { ref } from "vue";
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

const props = defineProps<{
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
  joinTenant: [user: User];
  toggleSuperuser: [user: User, isSuperuser: boolean];
  toggleStatus: [user: User, active: boolean];
  delete: [user: User];
  page: [page: number];
  pageSizeChange: [size: number];
}>();

const { t } = useI18n();
const actionMenuStyle = ref<Record<string, string>>({});

function isCurrentUser(user: User) {
  return user.id === props.currentUserId;
}

function canManageUser(user: User) {
  if (isCurrentUser(user)) return false;
  if (props.isPlatformAdmin) return true;
  return !user.is_superuser;
}

function canJoinTenant(user: User) {
  return (
    props.isPlatformAdmin &&
    !user.is_superuser &&
    !user.tenant_name &&
    !isCurrentUser(user)
  );
}

function canPromoteToPlatformAdmin(user: User) {
  return props.isPlatformAdmin && !user.is_superuser && !isCurrentUser(user);
}

function canRemovePlatformAdmin(user: User) {
  return props.isPlatformAdmin && user.is_superuser && !isCurrentUser(user);
}

function hasUserActions(user: User) {
  return (
    isCurrentUser(user) ||
    canManageUser(user) ||
    canJoinTenant(user) ||
    canPromoteToPlatformAdmin(user) ||
    canRemovePlatformAdmin(user)
  );
}

function updateActionMenuPosition(
  event: MouseEvent,
  width = 224,
  preferredHeight = 360,
) {
  const target = event.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  const gap = 8;
  const viewportPadding = 8;
  const spaceBelow = window.innerHeight - rect.bottom - gap - viewportPadding;
  const spaceAbove = rect.top - gap - viewportPadding;
  const openAbove = spaceBelow < 220 && spaceAbove > spaceBelow;
  const maxHeight = Math.max(
    160,
    Math.min(preferredHeight, openAbove ? spaceAbove : spaceBelow),
  );
  const left = Math.min(
    Math.max(viewportPadding, rect.right - width),
    window.innerWidth - width - viewportPadding,
  );
  const top = openAbove
    ? Math.max(viewportPadding, rect.top - gap - maxHeight)
    : Math.min(rect.bottom + gap, window.innerHeight - maxHeight - viewportPadding);

  actionMenuStyle.value = {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    maxHeight: `${maxHeight}px`,
  };
}
</script>

<template>
  <div
    class="flex max-h-[calc(100vh-19rem)] min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-card shadow"
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

    <div v-else class="relative min-h-0 flex-1 overflow-auto bg-card">
      <table
      class="w-full table-fixed border-separate border-spacing-0"
      :style="{ minWidth: usersTable.tableMinWidth.value }"
    >
      <colgroup>
        <col
          v-for="column in userColumns"
          :key="column.key"
          :style="usersTable.columnStyle(column.key)"
        />
      </colgroup>
      <thead class="sticky top-0 z-30 bg-background-secondary shadow-sm">
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
            header-class="border-b border-border"
            @sort="usersTable.toggleSort($event as UserColumnKey)"
            @resize-start="
              (key, event) =>
                usersTable.startResize(key as UserColumnKey, event)
            "
            @resize-reset="usersTable.resetColumnWidth($event as UserColumnKey)"
          />
        </tr>
      </thead>
      <tbody class="[&>tr>td]:border-b [&>tr>td]:border-border">
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
            class="whitespace-nowrap px-3 py-4 text-center text-sm font-medium"
          >
            <Menu
              v-if="hasUserActions(user)"
              as="div"
              class="relative inline-block text-left"
            >
              <MenuButton
                class="flex items-center rounded-full bg-background p-1 text-foreground-muted hover:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-indigo-500"
                @click="updateActionMenuPosition($event)"
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
                  class="fixed z-[9999] overflow-auto rounded-md popover-surface shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
                  :style="actionMenuStyle"
                >
                  <div class="py-1">
                    <MenuItem
                      v-if="canManageUser(user) || isCurrentUser(user)"
                      v-slot="{ active }"
                    >
                      <button
                        :disabled="isCurrentUser(user)"
                        :class="[
                          isCurrentUser(user)
                            ? 'cursor-not-allowed text-foreground-muted opacity-50'
                            : active
                              ? 'bg-hover text-foreground'
                              : 'text-foreground',
                          'block w-full px-4 py-2 text-left text-sm',
                        ]"
                        @click="emit('edit', user)"
                      >
                        {{ t("users.editUser") }}
                      </button>
                    </MenuItem>
                    <MenuItem
                      v-if="canManageUser(user) || isCurrentUser(user)"
                      v-slot="{ active }"
                    >
                      <button
                        :disabled="isCurrentUser(user)"
                        :class="[
                          isCurrentUser(user)
                            ? 'cursor-not-allowed text-foreground-muted opacity-50'
                            : active
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
                      v-if="canJoinTenant(user)"
                      v-slot="{ active }"
                    >
                      <button
                        :class="[
                          active
                            ? 'bg-hover text-foreground'
                            : 'text-foreground',
                          'block w-full px-4 py-2 text-left text-sm',
                        ]"
                        @click="emit('joinTenant', user)"
                      >
                        {{ t("users.joinTenant") }}
                      </button>
                    </MenuItem>
                    <MenuItem
                      v-if="canPromoteToPlatformAdmin(user)"
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
                        canRemovePlatformAdmin(user) ||
                        (isPlatformAdmin && user.is_superuser && isCurrentUser(user))
                      "
                      v-slot="{ active }"
                    >
                      <button
                        :disabled="isCurrentUser(user)"
                        :class="[
                          isCurrentUser(user)
                            ? 'cursor-not-allowed text-foreground-muted opacity-50'
                            : active
                              ? 'bg-hover text-foreground'
                              : 'text-foreground',
                          'block w-full px-4 py-2 text-left text-sm',
                        ]"
                        @click="emit('toggleSuperuser', user, false)"
                      >
                        {{ t("users.removePlatformAdmin") }}
                      </button>
                    </MenuItem>
                    <MenuItem
                      v-if="
                        (canManageUser(user) || isCurrentUser(user)) &&
                        user.is_active
                      "
                      v-slot="{ active }"
                    >
                      <button
                        :disabled="isCurrentUser(user)"
                        :class="[
                          isCurrentUser(user)
                            ? 'cursor-not-allowed text-foreground-muted opacity-50'
                            : active
                              ? 'bg-hover text-foreground'
                              : 'text-foreground',
                          'block w-full px-4 py-2 text-left text-sm',
                        ]"
                        @click="emit('toggleStatus', user, false)"
                      >
                        {{ t("users.disableUser") }}
                      </button>
                    </MenuItem>
                    <MenuItem
                      v-else-if="canManageUser(user) || isCurrentUser(user)"
                      v-slot="{ active }"
                    >
                      <button
                        :disabled="isCurrentUser(user)"
                        :class="[
                          isCurrentUser(user)
                            ? 'cursor-not-allowed text-foreground-muted opacity-50'
                            : active
                              ? 'bg-hover text-foreground'
                              : 'text-foreground',
                          'block w-full px-4 py-2 text-left text-sm',
                        ]"
                        @click="emit('toggleStatus', user, true)"
                      >
                        {{ t("users.enableUser") }}
                      </button>
                    </MenuItem>
                    <div
                      v-if="canManageUser(user) || isCurrentUser(user)"
                      class="border-t border-border my-1"
                    />
                    <MenuItem
                      v-if="canManageUser(user) || isCurrentUser(user)"
                      v-slot="{ active }"
                    >
                      <button
                        :disabled="isCurrentUser(user)"
                        :class="[
                          isCurrentUser(user)
                            ? 'cursor-not-allowed text-foreground-muted opacity-50'
                            : active
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
            <span
              v-else
              class="inline-flex h-7 w-7 items-center justify-center text-foreground-muted"
            >
              -
            </span>
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
    </div>

    <div
      v-if="totalCount > 0"
      class="flex flex-shrink-0 flex-col sm:flex-row items-center justify-between gap-4 px-4 py-3 bg-card border-t border-border"
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
