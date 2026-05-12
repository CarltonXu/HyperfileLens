<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="sm:flex sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">
          {{ t("users.title") }}
        </h1>
        <p class="mt-2 text-sm text-foreground-secondary">
          {{ t("users.description") }}
        </p>
      </div>
      <div class="mt-4 sm:mt-0 flex gap-3">
        <button
          type="button"
          class="inline-flex items-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover transition-colors"
          @click="openInviteDialog">
          <EnvelopeIcon class="-ml-0.5 mr-1.5 h-5 w-5" aria-hidden="true" />
          {{ t("users.inviteUser") }}
        </button>
        <button
          type="button"
          class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
          @click="openCreateDialog">
          <PlusIcon class="-ml-0.5 mr-1.5 h-5 w-5" aria-hidden="true" />
          {{ t("users.createUser") }}
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-card shadow rounded-xl border border-border p-4">
      <div class="flex flex-wrap gap-4">
        <div class="flex-1 min-w-0">
          <div class="relative">
            <MagnifyingGlassIcon
              class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="t('common.search')"
              class="block w-full rounded-lg border border-border py-2 pl-10 pr-3 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
              @input="debouncedSearch" />
          </div>
        </div>
        <div class="flex items-center gap-2">
          <select
            v-model="roleFilter"
            class="rounded-lg border border-border py-2 pl-3 pr-8 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm"
            @change="fetchUsers">
            <option class="bg-background" value="">
              {{ t("common.all") }}
            </option>
            <option class="bg-background" value="admin">
              {{ t("users.roles.admin") }}
            </option>
            <option class="bg-background" value="member">
              {{ t("users.roles.member") }}
            </option>
          </select>
          <select
            v-model="statusFilter"
            class="rounded-lg border border-border py-2 pl-3 pr-8 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm"
            @change="fetchUsers">
            <option class="bg-background" value="">
              {{ t("common.all") }}
            </option>
            <option class="bg-background" value="active">
              {{ t("users.active") }}
            </option>
            <option class="bg-background" value="inactive">
              {{ t("users.inactive") }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- Users Table -->
    <div class="bg-card shadow rounded-xl border border-border">
      <div v-if="loading" class="p-8 text-center">
        <svg
          class="animate-spin h-8 w-8 text-indigo-600 mx-auto"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24">
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"></circle>
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="mt-2 text-sm text-foreground-secondary">
          {{ t("common.loading") }}
        </p>
      </div>

      <table v-else class="min-w-full divide-y divide-border">
        <thead class="bg-background-secondary">
          <tr>
            <th
              scope="col"
              class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-foreground sm:pl-6">
              {{ t("users.user") }}
            </th>
            <th
              scope="col"
              class="px-3 py-3.5 text-left text-sm font-semibold text-foreground">
              {{ t("users.email") }}
            </th>
            <th
              v-if="isPlatformAdmin"
              scope="col"
              class="px-3 py-3.5 text-left text-sm font-semibold text-foreground">
              {{ t("users.tenant") }}
            </th>
            <th
              scope="col"
              class="px-3 py-3.5 text-left text-sm font-semibold text-foreground">
              {{ t("users.role") }}
            </th>
            <th
              scope="col"
              class="px-3 py-3.5 text-left text-sm font-semibold text-foreground">
              {{ t("users.status") }}
            </th>
            <th
              scope="col"
              class="px-3 py-3.5 text-left text-sm font-semibold text-foreground">
              {{ t("users.lastLogin") }}
            </th>
            <th scope="col" class="relative py-3.5 pl-3 pr-4 sm:pr-6">
              <span class="sr-only">{{ t("common.actions") }}</span>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="user in users" :key="user.id" class="hover:bg-hover">
            <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm sm:pl-6">
              <div class="flex items-center">
                <div
                  class="h-10 w-10 flex-shrink-0 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
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
              class="whitespace-nowrap px-3 py-4 text-sm text-foreground-secondary">
              {{ user.email }}
            </td>
            <td
              v-if="isPlatformAdmin"
              class="whitespace-nowrap px-3 py-4 text-sm text-foreground-secondary">
              {{ user.tenant_name || "-" }}
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm">
              <span
                :class="getUnifiedRoleClass(user)"
                class="inline-flex rounded-full px-2 py-1 text-xs font-semibold">
                {{ getUnifiedRoleName(user) }}
              </span>
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm">
              <span
                :class="
                  user.is_active
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                    : 'bg-gray-100 text-gray-800'
                "
                class="inline-flex rounded-full px-2 py-1 text-xs font-semibold">
                {{ user.is_active ? t("users.active") : t("users.inactive") }}
              </span>
            </td>
            <td
              class="whitespace-nowrap px-3 py-4 text-sm text-foreground-secondary">
              {{ user.last_login_at ? formatDate(user.last_login_at) : "-" }}
            </td>
            <td
              class="whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
              <Menu as="div" class="relative inline-block text-left">
                <MenuButton
                  class="flex items-center rounded-full bg-background p-1 text-foreground-muted hover:text-foreground-secondary focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  <EllipsisVerticalIcon class="h-5 w-5" aria-hidden="true" />
                </MenuButton>
                <transition
                  enter-active-class="transition ease-out duration-100"
                  enter-from-class="transform opacity-0 scale-95"
                  enter-to-class="transform opacity-100 scale-100"
                  leave-active-class="transition ease-in duration-75"
                  leave-from-class="transform opacity-100 scale-100"
                  leave-to-class="transform opacity-0 scale-95">
                  <MenuItems
                    class="absolute right-0 z-50 mt-2 w-56 origin-top-right rounded-md popover-surface shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                    <div class="py-1">
                      <MenuItem v-slot="{ active }">
                        <button
                          @click="openEditDialog(user)"
                          :class="[
                            active
                              ? 'bg-hover text-foreground'
                              : 'text-foreground',
                            'block w-full px-4 py-2 text-left text-sm',
                          ]">
                          {{ t("users.editUser") }}
                        </button>
                      </MenuItem>
                      <MenuItem v-slot="{ active }">
                        <button
                          @click="openResetPasswordDialog(user)"
                          :class="[
                            active
                              ? 'bg-hover text-foreground'
                              : 'text-foreground',
                            'block w-full px-4 py-2 text-left text-sm',
                          ]">
                          {{ t("users.resetPassword") }}
                        </button>
                      </MenuItem>
                      <MenuItem
                        v-if="isPlatformAdmin && !user.is_superuser"
                        v-slot="{ active }">
                        <button
                          @click="toggleSuperuser(user, true)"
                          :class="[
                            active
                              ? 'bg-hover text-foreground'
                              : 'text-foreground',
                            'block w-full px-4 py-2 text-left text-sm',
                          ]">
                          {{ t("users.setPlatformAdmin") }}
                        </button>
                      </MenuItem>
                      <MenuItem
                        v-if="
                          isPlatformAdmin &&
                          user.is_superuser &&
                          user.id !== currentUserId
                        "
                        v-slot="{ active }">
                        <button
                          @click="toggleSuperuser(user, false)"
                          :class="[
                            active
                              ? 'bg-hover text-foreground'
                              : 'text-foreground',
                            'block w-full px-4 py-2 text-left text-sm',
                          ]">
                          {{ t("users.removePlatformAdmin") }}
                        </button>
                      </MenuItem>
                      <MenuItem v-if="user.is_active" v-slot="{ active }">
                        <button
                          @click="toggleUserStatus(user, false)"
                          :class="[
                            active
                              ? 'bg-hover text-foreground'
                              : 'text-foreground',
                            'block w-full px-4 py-2 text-left text-sm',
                          ]">
                          {{ t("users.disableUser") }}
                        </button>
                      </MenuItem>
                      <MenuItem v-else v-slot="{ active }">
                        <button
                          @click="toggleUserStatus(user, true)"
                          :class="[
                            active
                              ? 'bg-hover text-foreground'
                              : 'text-foreground',
                            'block w-full px-4 py-2 text-left text-sm',
                          ]">
                          {{ t("users.enableUser") }}
                        </button>
                      </MenuItem>
                      <div class="border-t border-border my-1"></div>
                      <MenuItem
                        v-if="user.id !== currentUserId"
                        v-slot="{ active }">
                        <button
                          @click="openDeleteDialog(user)"
                          :class="[
                            active
                              ? 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                              : 'text-red-600 dark:text-red-400',
                            'block w-full px-4 py-2 text-left text-sm',
                          ]">
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
              class="px-3 py-12 text-center text-foreground-secondary">
              {{ t("common.noData") }}
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div
        v-if="totalCount > pageSize"
        class="flex items-center justify-between border-t border-border surface-card px-4 py-3 sm:px-6">
        <div class="flex flex-1 justify-between sm:hidden">
          <button
            @click="goToPage(currentPage - 1)"
            :disabled="currentPage === 1"
            class="relative inline-flex items-center rounded-md border border-border-secondary bg-background px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed">
            {{ t("common.previous") }}
          </button>
          <button
            @click="goToPage(currentPage + 1)"
            :disabled="currentPage * pageSize >= totalCount"
            class="relative ml-3 inline-flex items-center rounded-md border border-border-secondary bg-background px-4 py-2 text-sm font-medium text-foreground-secondary hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed">
            {{ t("common.next") }}
          </button>
        </div>
        <div
          class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
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
          <div>
            <nav
              class="isolate inline-flex -space-x-px rounded-md shadow-sm"
              aria-label="Pagination">
              <button
                @click="goToPage(currentPage - 1)"
                :disabled="currentPage === 1"
                class="relative inline-flex items-center rounded-l-lg border border-border px-2 py-2 text-slate-400 hover:bg-hover focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed">
                <span class="sr-only">{{ t("common.previous") }}</span>
                <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
              </button>
              <button
                v-for="page in visiblePages"
                :key="page"
                @click="goToPage(page)"
                :class="[
                  page === currentPage
                    ? 'bg-indigo-600 text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600'
                    : 'text-foreground ring-1 ring-inset ring-border hover:bg-hover',
                  'relative inline-flex items-center px-4 py-2 text-sm font-semibold',
                ]">
                {{ page }}
              </button>
              <button
                @click="goToPage(currentPage + 1)"
                :disabled="currentPage * pageSize >= totalCount"
                class="relative inline-flex items-center rounded-r-lg border border-border px-2 py-2 text-slate-400 hover:bg-hover focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed">
                <span class="sr-only">{{ t("common.next") }}</span>
                <ChevronRightIcon class="h-5 w-5" aria-hidden="true" />
              </button>
            </nav>
          </div>
        </div>
      </div>
    </div>

    <!-- Create User Dialog -->
    <Teleport to="body">
      <div v-if="showCreateDialog" class="fixed inset-0 z-50 overflow-y-auto">
        <div
          class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <div
            class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
            @click="closeCreateDialog"></div>
          <div
            class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
            <div>
              <div class="mt-3 text-center sm:mt-5">
                <h3 class="text-base font-semibold leading-6 text-foreground">
                  {{ t("users.createUser") }}
                </h3>
                <div class="mt-4 space-y-4 text-left">
                  <div>
                    <label
                      class="block text-sm font-medium text-foreground-secondary"
                      >{{ t("users.email") }} *</label
                    >
                    <input
                      v-model="createForm.email"
                      type="email"
                      class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                      :placeholder="t('users.emailPlaceholder')" />
                  </div>
                  <div>
                    <label
                      class="block text-sm font-medium text-foreground-secondary"
                      >{{ t("users.password") }} *</label
                    >
                    <input
                      v-model="createForm.password"
                      type="password"
                      class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                      :placeholder="t('users.passwordPlaceholder')" />
                  </div>
                  <div class="grid grid-cols-2 gap-4">
                    <div>
                      <label
                        class="block text-sm font-medium text-foreground-secondary"
                        >{{ t("users.firstName") }}</label
                      >
                      <input
                        v-model="createForm.first_name"
                        type="text"
                        class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm" />
                    </div>
                    <div>
                      <label
                        class="block text-sm font-medium text-foreground-secondary"
                        >{{ t("users.lastName") }}</label
                      >
                      <input
                        v-model="createForm.last_name"
                        type="text"
                        class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm" />
                    </div>
                  </div>
                  <div>
                    <label
                      class="block text-sm font-medium text-foreground-secondary"
                      >{{ t("users.phone") }}</label
                    >
                    <input
                      v-model="createForm.phone"
                      type="text"
                      class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm" />
                  </div>
                  <!-- Tenant selector for platform admin -->
                  <div v-if="isPlatformAdmin">
                    <label
                      class="block text-sm font-medium text-foreground-secondary"
                      >{{ t("users.tenant") }}</label
                    >
                    <select
                      v-model="createForm.tenant_id"
                      class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm"
                      :disabled="loadingTenants">
                      <option class="bg-background" value="">
                        {{
                          loadingTenants
                            ? t("common.loading")
                            : t("users.selectTenant")
                        }}
                      </option>
                      <option
                        class="bg-background"
                        v-for="tenant in tenants"
                        :key="tenant.id"
                        :value="tenant.id">
                        {{ tenant.name }}
                      </option>
                    </select>
                  </div>
                  <!-- 统一角色选择 -->
                  <div>
                    <label
                      class="block text-sm font-medium text-foreground-secondary"
                      >{{ t("users.role") }}</label
                    >
                    <select
                      v-model="createForm.role"
                      class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm">
                      <option
                        class="bg-background"
                        v-if="isPlatformAdmin"
                        value="platform_admin">
                        {{ t("users.roles.platformAdmin") }}
                      </option>
                      <option class="bg-background" value="admin">
                        {{ t("users.roles.tenantAdmin") }}
                      </option>
                      <option class="bg-background" value="member">
                        {{ t("users.roles.member") }}
                      </option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
            <div
              class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
              <button
                type="button"
                class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 sm:col-start-2"
                @click="createUser"
                :disabled="creating">
                {{ creating ? t("common.saving") : t("common.save") }}
              </button>
              <button
                type="button"
                class="mt-3 inline-flex w-full justify-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover sm:col-start-1 sm:mt-0 transition-colors"
                @click="closeCreateDialog">
                {{ t("common.cancel") }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Edit User Dialog -->
    <Teleport to="body">
      <div v-if="showEditDialog" class="fixed inset-0 z-50 overflow-y-auto">
        <div
          class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <div
            class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
            @click="closeEditDialog"></div>
          <div
            class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
            <div>
              <div class="mt-3 text-center sm:mt-5">
                <h3 class="text-base font-semibold leading-6 text-foreground">
                  {{ t("users.editUser") }}
                </h3>
                <p class="mt-2 text-sm text-foreground-secondary">
                  {{
                    t("users.editUserHint", {
                      user: editingUser?.full_name || editingUser?.email,
                    })
                  }}
                </p>
                <div class="mt-4 space-y-4 text-left">
                  <div>
                    <label
                      class="block text-sm font-medium text-foreground-secondary"
                      >{{ t("users.email") }}</label
                    >
                    <input
                      v-model="editForm.email"
                      type="email"
                      class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm" />
                  </div>
                  <div class="grid grid-cols-2 gap-4">
                    <div>
                      <label
                        class="block text-sm font-medium text-foreground-secondary"
                        >{{ t("users.firstName") }}</label
                      >
                      <input
                        v-model="editForm.first_name"
                        type="text"
                        class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm" />
                    </div>
                    <div>
                      <label
                        class="block text-sm font-medium text-foreground-secondary"
                        >{{ t("users.lastName") }}</label
                      >
                      <input
                        v-model="editForm.last_name"
                        type="text"
                        class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm" />
                    </div>
                  </div>
                  <div>
                    <label
                      class="block text-sm font-medium text-foreground-secondary"
                      >{{ t("users.phone") }}</label
                    >
                    <input
                      v-model="editForm.phone"
                      type="text"
                      class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm" />
                  </div>
                  <!-- 统一角色选择 -->
                  <div>
                    <label
                      class="block text-sm font-medium text-foreground-secondary"
                      >{{ t("users.role") }}</label
                    >
                    <select
                      v-model="editForm.role"
                      class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm">
                      <option
                        class="bg-background"
                        v-if="isPlatformAdmin"
                        value="platform_admin">
                        {{ t("users.roles.platformAdmin") }}
                      </option>
                      <option class="bg-background" value="admin">
                        {{ t("users.roles.tenantAdmin") }}
                      </option>
                      <option class="bg-background" value="member">
                        {{ t("users.roles.member") }}
                      </option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
            <div
              class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
              <button
                type="button"
                class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 sm:col-start-2"
                @click="updateUser"
                :disabled="updating">
                {{ updating ? t("common.saving") : t("users.updateUser") }}
              </button>
              <button
                type="button"
                class="mt-3 inline-flex w-full justify-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover sm:col-start-1 sm:mt-0 transition-colors"
                @click="closeEditDialog">
                {{ t("common.cancel") }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Invite User Dialog -->
    <Teleport to="body">
      <div v-if="showInviteDialog" class="fixed inset-0 z-50 overflow-y-auto">
        <div
          class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <div
            class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
            @click="closeInviteDialog"></div>
          <div
            class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
            <div>
              <div class="mt-3 text-center sm:mt-5">
                <h3 class="text-base font-semibold leading-6 text-foreground">
                  {{ t("users.inviteUser") }}
                </h3>
                <div class="mt-4 space-y-4 text-left">
                  <div>
                    <label
                      class="block text-sm font-medium text-foreground-secondary"
                      >{{ t("users.email") }}</label
                    >
                    <input
                      v-model="inviteForm.email"
                      type="email"
                      class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                      :placeholder="t('users.emailPlaceholder')" />
                  </div>
                  <div>
                    <label
                      class="block text-sm font-medium text-foreground-secondary"
                      >{{ t("users.role") }}</label
                    >
                    <select
                      v-model="inviteForm.role"
                      class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm">
                      <option class="bg-background" value="admin">
                        {{ t("users.roles.admin") }}
                      </option>
                      <option class="bg-background" value="member">
                        {{ t("users.roles.member") }}
                      </option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
            <div
              class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
              <button
                type="button"
                class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 sm:col-start-2"
                @click="sendInvite"
                :disabled="inviting">
                {{ inviting ? t("users.sending") : t("users.sendInvite") }}
              </button>
              <button
                type="button"
                class="mt-3 inline-flex w-full justify-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover sm:col-start-1 sm:mt-0 transition-colors"
                @click="closeInviteDialog">
                {{ t("common.cancel") }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Reset Password Dialog -->
    <Teleport to="body">
      <div
        v-if="showResetPasswordDialog"
        class="fixed inset-0 z-50 overflow-y-auto">
        <div
          class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <div
            class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
            @click="closeResetPasswordDialog"></div>
          <div
            class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
            <div>
              <div class="mt-3 text-center sm:mt-5">
                <h3 class="text-base font-semibold leading-6 text-foreground">
                  {{ t("users.resetPassword") }}
                </h3>
                <p class="mt-2 text-sm text-foreground-secondary">
                  {{ t("users.resetPasswordFor") }}: {{ resettingUser?.email }}
                </p>
                <div class="mt-4 space-y-4 text-left">
                  <div>
                    <label
                      class="block text-sm font-medium text-foreground-secondary"
                      >{{ t("users.newPassword") }} *</label
                    >
                    <input
                      v-model="resetPasswordForm.new_password"
                      type="password"
                      class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                      :placeholder="t('users.passwordPlaceholder')" />
                  </div>
                  <div>
                    <label
                      class="block text-sm font-medium text-foreground-secondary"
                      >{{ t("users.confirmPassword") }} *</label
                    >
                    <input
                      v-model="resetPasswordForm.confirm_password"
                      type="password"
                      class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                      :placeholder="t('users.confirmPasswordPlaceholder')" />
                  </div>
                </div>
              </div>
            </div>
            <div
              class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
              <button
                type="button"
                class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 sm:col-start-2"
                @click="resetPassword"
                :disabled="resetting">
                {{ resetting ? t("common.saving") : t("users.resetPassword") }}
              </button>
              <button
                type="button"
                class="mt-3 inline-flex w-full justify-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover sm:col-start-1 sm:mt-0 transition-colors"
                @click="closeResetPasswordDialog">
                {{ t("common.cancel") }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete User Dialog -->
    <Teleport to="body">
      <div v-if="showDeleteDialog" class="fixed inset-0 z-50 overflow-y-auto">
        <div
          class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <div
            class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
            @click="closeDeleteDialog"></div>
          <div
            class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
            <div class="sm:flex sm:items-start">
              <div
                class="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-red-100 dark:bg-red-900 sm:mx-0 sm:h-10 sm:w-10">
                <ExclamationTriangleIcon
                  class="h-6 w-6 text-red-600 dark:text-red-400"
                  aria-hidden="true" />
              </div>
              <div class="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                <h3 class="text-base font-semibold leading-6 text-foreground">
                  {{ t("users.deleteUser") }}
                </h3>
                <div class="mt-2">
                  <p class="text-sm text-foreground-secondary">
                    {{
                      t("users.confirmDeleteDesc", {
                        email: deletingUser?.email,
                      })
                    }}
                  </p>
                </div>
              </div>
            </div>
            <div class="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
              <button
                type="button"
                class="inline-flex w-full justify-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500 sm:ml-3 sm:w-auto"
                @click="deleteUser"
                :disabled="deleting">
                {{ deleting ? t("common.deleting") : t("users.deleteUser") }}
              </button>
              <button
                type="button"
                class="mt-3 inline-flex w-full justify-center rounded-md bg-card px-3 py-2 text-sm font-semibold text-foreground shadow-sm ring-1 ring-inset ring-border hover:bg-hover sm:mt-0 sm:w-auto"
                @click="closeDeleteDialog">
                {{ t("common.cancel") }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/vue";
import {
  PlusIcon,
  EnvelopeIcon,
  MagnifyingGlassIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EllipsisVerticalIcon,
  ExclamationTriangleIcon,
} from "@heroicons/vue/24/outline";
import { useAppStore } from "@/stores/app";
import { useAuthStore } from "@/stores/auth";
import { usersApi, invitationsApi, tenantsApi } from "@/api";
import { usePagination } from "@/composables/usePagination";

const { t } = useI18n();
const appStore = useAppStore();
const authStore = useAuthStore();
const { getPageSize, setPageSize } = usePagination();

interface User {
  id: string;
  email: string;
  full_name?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  tenant_role: string;
  tenant_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  last_login_at?: string;
  date_joined?: string;
}

const loading = ref(false);
const users = ref<User[]>([]);
const searchQuery = ref("");
const roleFilter = ref("");
const statusFilter = ref("");

// Pagination
const currentPage = ref(1);
const pageSize = ref(getPageSize("users"));
const PAGE_STORAGE_KEY = "users";
const totalCount = ref(0);

// Watch for page size changes and save to localStorage
watch(pageSize, (newSize) => {
  setPageSize(newSize, PAGE_STORAGE_KEY);
});

// Computed
const isPlatformAdmin = computed(() => authStore.user?.is_superuser);
const currentUserId = computed(() => authStore.user?.id);

const visiblePages = computed(() => {
  const totalPages = Math.ceil(totalCount.value / pageSize.value);
  const pages: number[] = [];
  const start = Math.max(1, currentPage.value - 2);
  const end = Math.min(totalPages, currentPage.value + 2);
  for (let i = start; i <= end; i++) {
    pages.push(i);
  }
  return pages;
});

// Create dialog
const showCreateDialog = ref(false);
const creating = ref(false);
const createForm = ref({
  email: "",
  password: "",
  first_name: "",
  last_name: "",
  phone: "",
  role: "member", // 统一角色：platform_admin / admin / member
  tenant_id: "",
});

// Tenant list for platform admin
const tenants = ref<{ id: string; name: string }[]>([]);
const loadingTenants = ref(false);

// Edit dialog
const showEditDialog = ref(false);
const updating = ref(false);
const editingUser = ref<User | null>(null);
const editForm = ref({
  email: "",
  first_name: "",
  last_name: "",
  phone: "",
  role: "", // 统一角色：platform_admin / admin / member
});

// Reset password dialog
const showResetPasswordDialog = ref(false);
const resetting = ref(false);
const resettingUser = ref<User | null>(null);
const resetPasswordForm = ref({
  new_password: "",
  confirm_password: "",
});

// Delete dialog
const showDeleteDialog = ref(false);
const deleting = ref(false);
const deletingUser = ref<User | null>(null);

// Invite dialog
const showInviteDialog = ref(false);
const inviting = ref(false);
const inviteForm = ref({
  email: "",
  role: "member",
});

// Debounce
let searchTimeout: ReturnType<typeof setTimeout> | null = null;
const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout);
  searchTimeout = setTimeout(fetchUsers, 300);
};

async function fetchUsers() {
  loading.value = true;
  try {
    const params: {
      page: number;
      page_size: number;
      search?: string;
      tenant_role?: string;
      is_active?: boolean;
    } = {
      page: currentPage.value,
      page_size: pageSize.value,
    };
    if (searchQuery.value) params.search = searchQuery.value;
    if (roleFilter.value) params.tenant_role = roleFilter.value;
    if (statusFilter.value) params.is_active = statusFilter.value === "active";

    const response = await usersApi.list(params);
    users.value = response.data.results || response.data;
    totalCount.value = response.data.count || users.value.length;
  } catch (error: unknown) {
    console.error("Failed to fetch users:", error);
    appStore.showToast({ type: "error", title: t("common.error") });
  } finally {
    loading.value = false;
  }
}

function goToPage(page: number) {
  if (page < 1 || page > Math.ceil(totalCount.value / pageSize.value)) return;
  currentPage.value = page;
  fetchUsers();
}

function getInitials(user: User) {
  if (user.full_name) {
    return user.full_name
      .split(" ")
      .map((n: string) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }
  if (user.first_name && user.last_name) {
    return (user.first_name[0] + user.last_name[0]).toUpperCase();
  }
  return (user.email || "U").slice(0, 2).toUpperCase();
}

// 统一角色辅助函数
function getUnifiedRoleName(user: User) {
  if (user.is_superuser) {
    return t("users.roles.platformAdmin");
  } else if (user.tenant_role === "admin") {
    return t("users.roles.tenantAdmin");
  }
  return t("users.roles.member");
}

function getUnifiedRoleClass(user: User) {
  if (user.is_superuser) {
    return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200";
  } else if (user.tenant_role === "admin") {
    return "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200";
  }
  return "bg-gray-100 text-gray-800";
}

function formatDate(date: string) {
  if (!date) return "-";
  return new Date(date).toLocaleDateString();
}

// Create
async function openCreateDialog() {
  createForm.value = {
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    phone: "",
    role: "member",
    tenant_id: "",
  };
  showCreateDialog.value = true;

  // Fetch tenants for platform admin
  if (isPlatformAdmin.value && tenants.value.length === 0) {
    loadingTenants.value = true;
    try {
      const response = await tenantsApi.list({ page_size: 100 });
      tenants.value = response.data.results || response.data;
    } catch (error) {
      console.error("Failed to fetch tenants:", error);
    } finally {
      loadingTenants.value = false;
    }
  }
}

function closeCreateDialog() {
  showCreateDialog.value = false;
}

async function createUser() {
  creating.value = true;
  try {
    // 将统一角色转换为后端字段
    const role = createForm.value.role;
    const is_superuser = role === "platform_admin";
    const tenant_role = role === "platform_admin" ? "admin" : role;

    const payload = {
      email: createForm.value.email,
      password: createForm.value.password,
      first_name: createForm.value.first_name,
      last_name: createForm.value.last_name,
      phone: createForm.value.phone,
      tenant_role,
      is_superuser,
      tenant_id: createForm.value.tenant_id || undefined,
    };
    await usersApi.create(payload);
    appStore.showToast({ type: "success", title: t("users.createSuccess") });
    closeCreateDialog();
    fetchUsers();
  } catch (error: unknown) {
    const err = error as {
      response?: { data?: { error?: string; field?: string } };
    };
    const errorMsg = err.response?.data?.error;
    if (
      errorMsg?.includes("email already exists") ||
      err.response?.data?.field === "email"
    ) {
      appStore.showToast({ type: "error", title: t("users.emailExists") });
    } else {
      appStore.showToast({
        type: "error",
        title: errorMsg || t("users.createFailed"),
      });
    }
  } finally {
    creating.value = false;
  }
}

// Edit
function openEditDialog(user: User) {
  editingUser.value = user;
  // 根据用户的 is_superuser 和 tenant_role 确定统一角色
  let role = "member";
  if (user.is_superuser) {
    role = "platform_admin";
  } else if (user.tenant_role === "admin") {
    role = "admin";
  }
  editForm.value = {
    email: user.email || "",
    first_name: user.first_name || "",
    last_name: user.last_name || "",
    phone: user.phone || "",
    role: role,
  };
  showEditDialog.value = true;
}

function closeEditDialog() {
  showEditDialog.value = false;
  editingUser.value = null;
}

async function updateUser() {
  if (!editingUser.value) return;
  updating.value = true;
  try {
    // Update basic info (including email)
    await usersApi.update(String(editingUser.value.id), {
      email: editForm.value.email,
      first_name: editForm.value.first_name,
      last_name: editForm.value.last_name,
      phone: editForm.value.phone,
    });

    // Calculate new role values
    const newRole = editForm.value.role;
    const newIsSuperuser = newRole === "platform_admin";
    const newTenantRole = newRole === "platform_admin" ? "admin" : newRole;

    // Update superuser status if changed
    if (newIsSuperuser !== editingUser.value.is_superuser) {
      await usersApi.setSuperuser(String(editingUser.value.id), newIsSuperuser);
    }

    // Update tenant role if changed
    if (newTenantRole !== editingUser.value.tenant_role) {
      await usersApi.changeRole(String(editingUser.value.id), newTenantRole);
    }

    appStore.showToast({ type: "success", title: t("users.updateSuccess") });
    closeEditDialog();
    fetchUsers();
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.error || t("users.updateFailed"),
    });
  } finally {
    updating.value = false;
  }
}

// Toggle superuser
async function toggleSuperuser(user: User, isSuperuser: boolean) {
  try {
    await usersApi.setSuperuser(user.id, isSuperuser);
    appStore.showToast({
      type: "success",
      title: isSuperuser
        ? t("users.setPlatformAdmin")
        : t("users.removePlatformAdmin"),
    });
    fetchUsers();
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.error || t("common.error"),
    });
  }
}

// Invite
function openInviteDialog() {
  inviteForm.value = { email: "", role: "member" };
  showInviteDialog.value = true;
}

function closeInviteDialog() {
  showInviteDialog.value = false;
}

async function sendInvite() {
  inviting.value = true;
  try {
    await invitationsApi.create(inviteForm.value);
    appStore.showToast({ type: "success", title: t("users.inviteSuccess") });
    closeInviteDialog();
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.error || t("users.inviteFailed"),
    });
  } finally {
    inviting.value = false;
  }
}

// Toggle status
async function toggleUserStatus(user: User, active: boolean) {
  try {
    if (active) {
      await usersApi.enable(user.id);
    } else {
      await usersApi.disable(user.id);
    }
    appStore.showToast({
      type: "success",
      title: active ? t("users.enableSuccess") : t("users.disableSuccess"),
    });
    fetchUsers();
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.error || t("common.error"),
    });
  }
}

// Reset password
function openResetPasswordDialog(user: User) {
  resettingUser.value = user;
  resetPasswordForm.value = { new_password: "", confirm_password: "" };
  showResetPasswordDialog.value = true;
}

function closeResetPasswordDialog() {
  showResetPasswordDialog.value = false;
  resettingUser.value = null;
}

async function resetPassword() {
  if (!resettingUser.value) return;

  if (!resetPasswordForm.value.new_password) {
    appStore.showToast({ type: "error", title: t("users.passwordRequired") });
    return;
  }

  if (resetPasswordForm.value.new_password.length < 6) {
    appStore.showToast({ type: "error", title: t("users.passwordTooShort") });
    return;
  }

  if (
    resetPasswordForm.value.new_password !==
    resetPasswordForm.value.confirm_password
  ) {
    appStore.showToast({ type: "error", title: t("users.passwordMismatch") });
    return;
  }

  resetting.value = true;
  try {
    await usersApi.resetPassword(
      String(resettingUser.value.id),
      resetPasswordForm.value.new_password,
    );
    appStore.showToast({
      type: "success",
      title: t("users.resetPasswordSuccess"),
    });
    closeResetPasswordDialog();
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.error || t("users.resetPasswordFailed"),
    });
  } finally {
    resetting.value = false;
  }
}

// Delete user
function openDeleteDialog(user: User) {
  deletingUser.value = user;
  showDeleteDialog.value = true;
}

function closeDeleteDialog() {
  showDeleteDialog.value = false;
  deletingUser.value = null;
}

async function deleteUser() {
  if (!deletingUser.value) return;

  deleting.value = true;
  try {
    await usersApi.delete(String(deletingUser.value.id));
    appStore.showToast({ type: "success", title: t("users.deleteSuccess") });
    closeDeleteDialog();
    fetchUsers();
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.error || t("users.deleteFailed"),
    });
  } finally {
    deleting.value = false;
  }
}

onMounted(() => {
  fetchUsers();
});
</script>
