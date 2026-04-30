<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="sm:flex sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900 dark:text-white">{{ t('tenants.title') }}</h1>
        <p class="mt-2 text-sm text-gray-700 dark:text-gray-300">
          {{ t('tenants.description') || 'Manage tenants and resource isolation' }}
        </p>
      </div>
      <div class="mt-4 sm:mt-0">
        <button
          type="button"
          class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
          @click="openCreateDialog"
        >
          <PlusIcon class="-ml-0.5 mr-1.5 h-5 w-5" aria-hidden="true" />
          {{ t('tenants.createTenant') }}
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white dark:bg-gray-800 shadow rounded-lg p-4">
      <div class="flex flex-wrap gap-4">
        <div class="flex-1 min-w-0">
          <div class="relative">
            <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="t('common.search')"
              class="block w-full rounded-md border-0 py-1.5 pl-10 pr-3 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
              @input="debouncedSearch"
            />
          </div>
        </div>
        <div class="flex items-center gap-2">
          <select
            v-model="statusFilter"
            class="rounded-md border-0 py-1.5 pl-3 pr-8 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
            @change="fetchTenants"
          >
            <option class="bg-white dark:bg-slate-700" value="">{{ t('common.all') || 'All Status' }}</option>
            <option class="bg-white dark:bg-slate-700" value="active">{{ t('tenants.active') }}</option>
            <option class="bg-white dark:bg-slate-700" value="inactive">{{ t('tenants.inactive') }}</option>
            <option class="bg-white dark:bg-slate-700" value="suspended">{{ t('tenants.suspended') }}</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Tenants Table -->
    <div class="bg-white dark:bg-gray-800 shadow rounded-lg overflow-visible mb-4">
      <div v-if="loading" class="p-8 text-center">
        <svg class="animate-spin h-8 w-8 text-indigo-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">{{ t('common.loading') }}</p>
      </div>

      <table v-else class="min-w-full divide-y divide-gray-300 dark:divide-gray-700">
        <thead class="bg-gray-50 dark:bg-gray-900">
          <tr>
            <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 dark:text-white sm:pl-6">{{ t('tenants.tenantName') }}</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('tenants.status') }}</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('tenants.owner') }}</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('tenants.userCount') }}</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('tenants.proxyCount') }}</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('tenants.createdAt') }}</th>
            <th scope="col" class="relative py-3.5 pl-3 pr-4 sm:pr-6">
              <span class="sr-only">{{ t('common.actions') }}</span>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
          <tr v-for="tenant in tenants" :key="tenant.id" class="hover:bg-gray-50 dark:hover:bg-gray-700/50">
            <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm sm:pl-6">
              <div class="flex items-center">
                <div class="h-10 w-10 flex-shrink-0 rounded-lg bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center">
                  <BuildingOffice2Icon class="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div class="ml-4">
                  <div class="font-medium text-gray-900 dark:text-white">{{ tenant.name }}</div>
                  <div class="text-gray-500 dark:text-gray-400">{{ tenant.slug }}</div>
                </div>
              </div>
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm">
              <span :class="getStatusClass(tenant.status)" class="inline-flex rounded-full px-2 py-1 text-xs font-semibold">
                {{ t(`tenants.${tenant.status}`) }}
              </span>
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
              {{ tenant.owner_name || tenant.owner_email || '-' }}
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
              {{ tenant.user_count || 0 }} / {{ tenant.max_users || '∞' }}
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
              {{ tenant.proxy_count || 0 }} / {{ tenant.max_proxies || '∞' }}
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
              {{ formatDate(tenant.created_at) }}
            </td>
            <td class="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
              <Menu as="div" class="relative inline-block text-left">
                <MenuButton class="flex items-center rounded-full text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-100">
                  <span class="sr-only">Open options</span>
                  <EllipsisVerticalIcon class="h-5 w-5" aria-hidden="true" />
                </MenuButton>
                <transition enter-active-class="transition ease-out duration-100" enter-from-class="transform opacity-0 scale-95" enter-to-class="transform opacity-100 scale-100" leave-active-class="transition ease-in duration-75" leave-from-class="transform opacity-100 scale-100" leave-to-class="transform opacity-0 scale-95">
                  <MenuItems class="absolute right-0 z-50 mt-2 w-48 origin-top-right rounded-md bg-white dark:bg-gray-800 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                    <MenuItem v-slot="{ active }">
                      <button @click="openEditDialog(tenant)" :class="[active ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300', 'block w-full px-4 py-2 text-left text-sm']">
                        {{ t('common.edit') }}
                      </button>
                    </MenuItem>
                    <MenuItem v-slot="{ active }">
                      <button @click="openUsersDialog(tenant)" :class="[active ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300', 'block w-full px-4 py-2 text-left text-sm']">
                        {{ t('tenants.manageUsers') }}
                      </button>
                    </MenuItem>
                    <MenuItem v-slot="{ active }">
                      <button @click="viewTenantStats(tenant)" :class="[active ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300', 'block w-full px-4 py-2 text-left text-sm']">
                        {{ t('tenants.stats') }}
                      </button>
                    </MenuItem>
                    <MenuItem v-if="tenant.status === 'active'" v-slot="{ active }">
                      <button @click="deactivateTenant(tenant)" :class="[active ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300', 'block w-full px-4 py-2 text-left text-sm']">
                        {{ t('tenants.deactivate') }}
                      </button>
                    </MenuItem>
                    <MenuItem v-else v-slot="{ active }">
                      <button @click="activateTenant(tenant)" :class="[active ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300', 'block w-full px-4 py-2 text-left text-sm']">
                        {{ t('tenants.activate') }}
                      </button>
                    </MenuItem>
                    <MenuItem v-slot="{ active }">
                      <button @click="confirmDeleteTenant(tenant)" :class="[active ? 'bg-red-100 text-red-900' : 'text-red-700', 'block w-full px-4 py-2 text-left text-sm']">
                        {{ t('common.delete') }}
                      </button>
                    </MenuItem>
                  </MenuItems>
                </transition>
              </Menu>
            </td>
          </tr>
          <tr v-if="tenants.length === 0">
            <td colspan="7" class="px-6 py-12 text-center text-sm text-gray-500 dark:text-gray-400">
              {{ t('common.noData') || 'No tenants found' }}
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div v-if="pagination.total > pagination.pageSize" class="flex items-center justify-between border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 sm:px-6">
        <div class="flex flex-1 justify-between sm:hidden">
          <button @click="prevPage" :disabled="pagination.page === 1" class="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Previous</button>
          <button @click="nextPage" :disabled="pagination.page >= totalPages" class="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Next</button>
        </div>
        <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
          <div>
            <p class="text-sm text-gray-700 dark:text-gray-300">
              {{ t('pagination.showing') }} {{ (pagination.page - 1) * pagination.pageSize + 1 }} {{ t('pagination.to') }} {{ Math.min(pagination.page * pagination.pageSize, pagination.total) }} {{ t('pagination.of') }} {{ pagination.total }} {{ t('pagination.items') }}
            </p>
          </div>
          <div>
            <nav class="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
              <button @click="prevPage" :disabled="pagination.page === 1" class="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed">
                <ChevronLeftIcon class="h-5 w-5" aria-hidden="true" />
              </button>
              <button v-for="page in displayedPages" :key="page" @click="goToPage(page)" :class="[page === pagination.page ? 'bg-indigo-600 text-white' : 'text-gray-900 dark:text-white ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700', 'relative inline-flex items-center px-4 py-2 text-sm font-semibold focus:z-20 focus:outline-offset-0']">{{ page }}</button>
              <button @click="nextPage" :disabled="pagination.page >= totalPages" class="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed">
                <ChevronRightIcon class="h-5 w-5" aria-hidden="true" />
              </button>
            </nav>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Dialog -->
    <TransitionRoot appear :show="showDialog" as="template">
      <Dialog as="div" class="relative z-10" @close="closeDialog">
        <TransitionChild as="template" enter="duration-300 ease-out" enter-from="opacity-0" enter-to="opacity-100" leave="duration-200 ease-in" leave-from="opacity-100" leave-to="opacity-0">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </TransitionChild>

        <div class="fixed inset-0 z-10 overflow-y-auto">
          <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <TransitionChild as="template" enter="duration-300 ease-out" enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95" enter-to="opacity-100 translate-y-0 sm:scale-100" leave="duration-200 ease-in" leave-from="opacity-100 translate-y-0 sm:scale-100" leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95">
              <DialogPanel class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
                <div class="absolute right-0 top-0 pr-4 pt-4">
                  <button type="button" class="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none" @click="closeDialog">
                    <XMarkIcon class="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>
                <div class="sm:flex sm:items-start">
                  <div class="mt-3 text-center sm:mt-0 sm:text-left w-full">
                    <DialogTitle as="h3" class="text-base font-semibold leading-6 text-gray-900 dark:text-white">
                      {{ editingTenant ? t('tenants.editTenant') : t('tenants.createTenant') }}
                    </DialogTitle>
                    <form @submit.prevent="saveTenant" class="mt-4 space-y-4">
                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('tenants.tenantName') }} *</label>
                        <input v-model="formData.name" type="text" required :placeholder="t('tenants.tenantNamePlaceholder') || '请输入租户名称'" class="mt-1 block w-full rounded-lg border border-slate-200 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-indigo-500 text-sm" />
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('tenants.tenantSlug') }} *</label>
                        <input v-model="formData.slug" type="text" required pattern="[a-z0-9-]+" :placeholder="t('tenants.tenantSlugPlaceholder') || '例如: my-company'" class="mt-1 block w-full rounded-lg border border-slate-200 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-indigo-500 text-sm" />
                        <p class="mt-1 text-xs text-gray-500">{{ t('tenants.tenantSlugHelp') || '只能使用小写字母、数字和连字符' }}</p>
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('tenants.description') }}</label>
                        <textarea v-model="formData.description" rows="2" :placeholder="t('tenants.descriptionPlaceholder') || '请输入租户描述（可选）'" class="mt-1 block w-full rounded-lg border border-slate-200 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-indigo-500 text-sm" />
                      </div>
                      <div class="grid grid-cols-2 gap-4">
                        <div>
                          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('tenants.maxUsers') }}</label>
                          <input v-model.number="formData.max_users" type="number" min="1" :placeholder="t('common.unlimited') || '无限制'" class="mt-1 block w-full rounded-lg border border-slate-200 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-indigo-500 text-sm" />
                        </div>
                        <div>
                          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('tenants.maxProxies') }}</label>
                          <input v-model.number="formData.max_proxies" type="number" min="1" :placeholder="t('common.unlimited') || '无限制'" class="mt-1 block w-full rounded-lg border border-slate-200 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-indigo-500 text-sm" />
                        </div>
                      </div>
                      <div class="grid grid-cols-2 gap-4">
                        <div>
                          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('tenants.maxRepositories') }}</label>
                          <input v-model.number="formData.max_repositories" type="number" min="1" :placeholder="t('common.unlimited') || '无限制'" class="mt-1 block w-full rounded-lg border border-slate-200 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-indigo-500 text-sm" />
                        </div>
                        <div>
                          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('tenants.maxStorageGb') }}</label>
                          <input v-model.number="formData.max_storage_gb" type="number" min="1" :placeholder="t('common.unlimited') || '无限制'" class="mt-1 block w-full rounded-lg border border-slate-200 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 text-slate-800 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-indigo-500 text-sm" />
                        </div>
                      </div>
                      <div class="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                        <button type="submit" :disabled="saving" class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 sm:ml-3 sm:w-auto disabled:opacity-50">
                          {{ saving ? t('common.saving') : t('common.save') }}
                        </button>
                        <button type="button" class="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 sm:w-auto dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600" @click="closeDialog">
                          {{ t('common.cancel') }}
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>

    <!-- Stats Dialog -->
    <Teleport to="body">
      <div v-if="showStatsDrawer" class="fixed inset-0 z-50 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4">
          <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity" @click="closeStatsDrawer"></div>
          
          <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full">
            <!-- Header -->
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div>
                <h3 class="text-lg font-medium text-gray-900 dark:text-white">
                  {{ t('tenants.stats') }}
                </h3>
                <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {{ statsTenant?.name }}
                </p>
              </div>
              <button type="button" class="rounded-md text-gray-400 hover:text-gray-500" @click="closeStatsDrawer">
                <XMarkIcon class="h-6 w-6" aria-hidden="true" />
              </button>
            </div>
            
            <!-- Content -->
            <div class="px-6 py-4">
              <div v-if="loadingStats" class="text-center py-8">
                <svg class="animate-spin h-8 w-8 text-indigo-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>

              <div v-else class="space-y-6">
                <!-- Resource Usage Cards -->
                <div class="grid grid-cols-2 gap-4">
                  <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                    <div class="flex items-center">
                      <UsersIcon class="h-8 w-8 text-blue-600" />
                      <div class="ml-3">
                        <p class="text-sm text-blue-600 dark:text-blue-400">{{ t('tenants.userCount') }}</p>
                        <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ statsData?.user_count || 0 }}</p>
                      </div>
                    </div>
                    <p class="text-xs text-gray-500 mt-2">{{ t('tenants.limit') || 'Limit' }}: {{ statsData?.max_users || '∞' }}</p>
                  </div>
                  <div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                    <div class="flex items-center">
                      <ServerIcon class="h-8 w-8 text-green-600" />
                      <div class="ml-3">
                        <p class="text-sm text-green-600 dark:text-green-400">{{ t('tenants.proxyCount') }}</p>
                        <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ statsData?.proxy_count || 0 }}</p>
                      </div>
                    </div>
                    <p class="text-xs text-gray-500 mt-2">{{ t('tenants.limit') || 'Limit' }}: {{ statsData?.max_proxies || '∞' }}</p>
                  </div>
                  <div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                    <div class="flex items-center">
                      <CircleStackIcon class="h-8 w-8 text-purple-600" />
                      <div class="ml-3">
                        <p class="text-sm text-purple-600 dark:text-purple-400">{{ t('tenants.repositoryCount') }}</p>
                        <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ statsData?.repository_count || 0 }}</p>
                      </div>
                    </div>
                    <p class="text-xs text-gray-500 mt-2">{{ t('tenants.limit') || 'Limit' }}: {{ statsData?.max_repositories || '∞' }}</p>
                  </div>
                  <div class="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
                    <div class="flex items-center">
                      <CircleStackIcon class="h-8 w-8 text-orange-600" />
                      <div class="ml-3">
                        <p class="text-sm text-orange-600 dark:text-orange-400">{{ t('tenants.storageUsed') }}</p>
                        <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ formatBytes(statsData?.storage_used || 0) }}</p>
                      </div>
                    </div>
                    <p class="text-xs text-gray-500 mt-2">{{ t('tenants.limit') || 'Limit' }}: {{ statsData?.max_storage_gb ? `${statsData.max_storage_gb} GB` : '∞' }}</p>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Footer -->
            <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
              <button
                type="button"
                class="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                @click="closeStatsDrawer"
              >
                {{ t('common.close') || 'Close' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Users Management Drawer -->
    <Teleport to="body">
      <div v-if="showUsersDrawer" class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
        <div class="flex min-h-screen items-center justify-center p-4">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="closeUsersDrawer"></div>
          
          <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
            <!-- Header -->
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
                  {{ usersTenant?.name }} - {{ t('tenants.manageUsers') }}
                </h3>
                <p class="text-sm text-gray-500 dark:text-gray-400">
                  {{ t('tenants.userCount') }}: {{ tenantUsers.length }}
                </p>
              </div>
              <button @click="closeUsersDrawer" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <XMarkIcon class="h-5 w-5" />
              </button>
            </div>
            
            <!-- Content -->
            <div class="flex-1 overflow-y-auto px-6 py-4">
              <!-- Add User Section -->
              <div class="mb-6">
                <button 
                  @click="showAddUserForm = !showAddUserForm"
                  class="flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-500"
                >
                  <PlusIcon class="h-4 w-4" />
                  {{ t('tenants.addUser') }}
                </button>
                
                <div v-if="showAddUserForm" class="mt-3 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg space-y-3">
                  <div class="grid grid-cols-2 gap-3">
                    <div>
                      <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{{ t('users.email') }}</label>
                      <input v-model="newUserEmail" type="email" :placeholder="t('users.emailPlaceholder')" class="w-full rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-white px-3 py-2 text-sm" />
                    </div>
                    <div>
                      <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{{ t('users.role') }}</label>
                      <select v-model="newUserRole" class="w-full rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-white px-3 py-2 text-sm">
                        <option class="bg-white dark:bg-slate-700" value="admin">{{ t('users.roles.admin') }}</option>
                        <option class="bg-white dark:bg-slate-700" value="member">{{ t('users.roles.member') }}</option>
                      </select>
                    </div>
                  </div>
                  <div class="flex justify-end gap-2">
                    <button @click="showAddUserForm = false" class="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400">
                      {{ t('common.cancel') }}
                    </button>
                    <button @click="handleAddUser" :disabled="!newUserEmail" class="bg-indigo-600 text-white rounded-md px-3 py-1.5 text-sm hover:bg-indigo-500 disabled:opacity-50">
                      {{ t('common.add') }}
                    </button>
                  </div>
                </div>
              </div>
              
              <!-- Users List -->
              <div class="space-y-3">
                <div v-if="loadingUsers" class="text-center py-8">
                  <svg class="animate-spin h-6 w-6 text-indigo-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
                <div v-else-if="tenantUsers.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400">
                  {{ t('common.noData') }}
                </div>
                <div v-else v-for="user in tenantUsers" :key="user.id" class="flex items-center justify-between p-4 bg-white dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 hover:shadow-sm transition-shadow">
                  <div class="flex items-center gap-3">
                    <div class="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white font-medium text-sm">
                      {{ getInitials(user) }}
                    </div>
                    <div>
                      <p class="font-medium text-gray-900 dark:text-white">{{ getDisplayName(user) }}</p>
                      <p class="text-xs text-gray-500 dark:text-gray-400">{{ user.email }} · ID: {{ user.id }}</p>
                      <div v-if="user.tenant_role === 'admin' && !user.is_superuser" class="flex items-center gap-2 mt-1">
                        <span class="bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium">
                          {{ t('users.roles.admin') }}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <!-- Role Selector -->
                    <select 
                      :value="user.tenant_role" 
                      @change="updateUserRole(user.id, ($event.target as HTMLSelectElement).value, user.is_superuser)"
                      :disabled="user.is_superuser"
                      class="rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white px-2 py-1.5 text-sm disabled:opacity-50"
                    >
                      <option class="bg-white dark:bg-slate-700" value="admin">{{ t('users.roles.admin') }}</option>
                      <option class="bg-white dark:bg-slate-700" value="member">{{ t('users.roles.member') }}</option>
                    </select>
                    <!-- Remove Button -->
                    <button 
                      @click="confirmRemoveUser(user)"
                      :disabled="user.is_superuser || user.id === currentUserId"
                      class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md disabled:opacity-30 disabled:cursor-not-allowed"
                      :title="user.is_superuser ? t('tenants.cannotRemoveSuperuser') : user.id === currentUserId ? t('tenants.cannotRemoveSelf') : t('common.remove')"
                    >
                      <UserMinusIcon class="h-5 w-5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Footer -->
            <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
              <button
                type="button"
                class="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                @click="closeUsersDrawer"
              >
                {{ t('common.close') || 'Close' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Remove User Confirmation -->
    <TransitionRoot appear :show="showRemoveUserConfirm" as="template">
      <Dialog as="div" class="relative z-[60]" @close="showRemoveUserConfirm = false">
        <TransitionChild as="template" enter="duration-300 ease-out" enter-from="opacity-0" enter-to="opacity-100" leave="duration-200 ease-in" leave-from="opacity-100" leave-to="opacity-0">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </TransitionChild>

        <div class="fixed inset-0 z-[60] overflow-y-auto">
          <div class="flex min-h-full items-center justify-center p-4">
            <TransitionChild as="template" enter="duration-300 ease-out" enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95" enter-to="opacity-100 translate-y-0 sm:scale-100" leave="duration-200 ease-in" leave-from="opacity-100 translate-y-0 sm:scale-100" leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95">
              <DialogPanel class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-sm sm:p-6">
                <div>
                  <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                    <ExclamationTriangleIcon class="h-6 w-6 text-red-600" aria-hidden="true" />
                  </div>
                  <div class="mt-3 text-center sm:mt-5">
                    <DialogTitle as="h3" class="text-base font-semibold leading-6 text-gray-900 dark:text-white">
                      {{ t('tenants.confirmRemoveUser') }}
                    </DialogTitle>
                    <div class="mt-2">
                      <p class="text-sm text-gray-500 dark:text-gray-400">
                        {{ t('tenants.confirmRemoveUserDesc', { email: removingUser?.email }) }}
                      </p>
                    </div>
                  </div>
                </div>
                <div class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                  <button type="button" class="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600" @click="showRemoveUserConfirm = false">
                    {{ t('common.cancel') }}
                  </button>
                  <button type="button" class="inline-flex w-full justify-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500" @click="executeRemoveUser">
                    {{ t('common.remove') }}
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>

    <!-- Delete Confirmation -->
    <TransitionRoot appear :show="showDeleteConfirm" as="template">
      <Dialog as="div" class="relative z-10" @close="showDeleteConfirm = false">
        <TransitionChild as="template" enter="duration-300 ease-out" enter-from="opacity-0" enter-to="opacity-100" leave="duration-200 ease-in" leave-from="opacity-100" leave-to="opacity-0">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </TransitionChild>

        <div class="fixed inset-0 z-10 overflow-y-auto">
          <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <TransitionChild as="template" enter="duration-300 ease-out" enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95" enter-to="opacity-100 translate-y-0 sm:scale-100" leave="duration-200 ease-in" leave-from="opacity-100 translate-y-0 sm:scale-100" leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95">
              <DialogPanel class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
                <div class="sm:flex sm:items-start">
                  <div class="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
                    <ExclamationTriangleIcon class="h-6 w-6 text-red-600" aria-hidden="true" />
                  </div>
                  <div class="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                    <DialogTitle as="h3" class="text-base font-semibold leading-6 text-gray-900 dark:text-white">
                      {{ t('common.confirmDelete') }}
                    </DialogTitle>
                    <div class="mt-2">
                      <p class="text-sm text-gray-500 dark:text-gray-400">
                        {{ t('tenants.confirmDelete', { name: deletingTenant?.name }) }}
                      </p>
                    </div>
                  </div>
                </div>
                <div class="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                  <button type="button" :disabled="deleting" class="inline-flex w-full justify-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500 sm:ml-3 sm:w-auto disabled:opacity-50" @click="deleteTenant">
                    {{ deleting ? t('common.deleting') : t('common.delete') }}
                  </button>
                  <button type="button" class="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 sm:w-auto dark:bg-gray-700 dark:text-white" @click="showDeleteConfirm = false">
                    {{ t('common.cancel') }}
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Dialog, DialogPanel, DialogTitle, Menu, MenuButton, MenuItem, MenuItems, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { BuildingOffice2Icon, ChevronLeftIcon, ChevronRightIcon, EllipsisVerticalIcon, ExclamationTriangleIcon, MagnifyingGlassIcon, PlusIcon, ServerIcon, UsersIcon, XMarkIcon, CircleStackIcon, UserMinusIcon } from '@heroicons/vue/24/outline'
import { tenantsApi } from '@/api'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import type { Tenant } from '@/types/tenant'

const { t } = useI18n()
const { showToast } = useToast()
const authStore = useAuthStore()

// State
const tenants = ref<Tenant[]>([])
const loading = ref(true)
const saving = ref(false)
const deleting = ref(false)
const showDialog = ref(false)
const showDeleteConfirm = ref(false)
const showStatsDrawer = ref(false)
const showUsersDrawer = ref(false)
const loadingStats = ref(false)
const loadingUsers = ref(false)
const editingTenant = ref<Tenant | null>(null)
const deletingTenant = ref<Tenant | null>(null)
const statsTenant = ref<Tenant | null>(null)
const statsData = ref<any>(null)
const usersTenant = ref<Tenant | null>(null)
const tenantUsers = ref<any[]>([])
const searchQuery = ref('')
const statusFilter = ref('')
const searchTimeout = ref<number | null>(null)

const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

const formData = ref({
  name: '',
  slug: '',
  description: '',
  max_users: null as number | null,
  max_proxies: null as number | null,
  max_repositories: null as number | null,
  max_storage_gb: null as number | null
})

// Computed
const totalPages = computed(() => Math.ceil(pagination.value.total / pagination.value.pageSize))
const displayedPages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, pagination.value.page - 2)
  const end = Math.min(totalPages.value, pagination.value.page + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

// Methods
const fetchTenants = async () => {
  loading.value = true
  try {
    const response = await tenantsApi.list({
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
      search: searchQuery.value || undefined,
      status: statusFilter.value || undefined
    })
    tenants.value = response.data.results || response.data
    pagination.value.total = response.data.count || tenants.value.length
  } catch (error) {
    console.error('Failed to fetch tenants:', error)
    showToast(t('common.error'), 'error')
  } finally {
    loading.value = false
  }
}

const debouncedSearch = () => {
  if (searchTimeout.value) clearTimeout(searchTimeout.value)
  searchTimeout.value = window.setTimeout(() => {
    pagination.value.page = 1
    fetchTenants()
  }, 300)
}

const prevPage = () => {
  if (pagination.value.page > 1) {
    pagination.value.page--
    fetchTenants()
  }
}

const nextPage = () => {
  if (pagination.value.page < totalPages.value) {
    pagination.value.page++
    fetchTenants()
  }
}

const goToPage = (page: number) => {
  pagination.value.page = page
  fetchTenants()
}

const openCreateDialog = () => {
  editingTenant.value = null
  formData.value = { name: '', slug: '', description: '', max_users: null, max_proxies: null, max_repositories: null, max_storage_gb: null }
  showDialog.value = true
}

const openEditDialog = (tenant: Tenant) => {
  editingTenant.value = tenant
  formData.value = {
    name: tenant.name,
    slug: tenant.slug,
    description: tenant.description || '',
    max_users: tenant.max_users,
    max_proxies: tenant.max_proxies,
    max_repositories: tenant.max_repositories,
    max_storage_gb: tenant.max_storage_gb
  }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
  editingTenant.value = null
}

const saveTenant = async () => {
  saving.value = true
  try {
    if (editingTenant.value) {
      await tenantsApi.update(editingTenant.value.id, formData.value)
      showToast(t('common.saved'), 'success')
    } else {
      await tenantsApi.create(formData.value)
      showToast(t('common.created'), 'success')
    }
    closeDialog()
    fetchTenants()
  } catch (error: any) {
    console.error('Failed to save tenant:', error)
    showToast(error.response?.data?.detail || t('common.error'), 'error')
  } finally {
    saving.value = false
  }
}

const confirmDeleteTenant = (tenant: Tenant) => {
  deletingTenant.value = tenant
  showDeleteConfirm.value = true
}

const deleteTenant = async () => {
  if (!deletingTenant.value) return
  deleting.value = true
  try {
    await tenantsApi.delete(deletingTenant.value.id)
    showToast(t('common.deleted'), 'success')
    showDeleteConfirm.value = false
    fetchTenants()
  } catch (error: any) {
    showToast(error.response?.data?.detail || t('common.error'), 'error')
  } finally {
    deleting.value = false
    deletingTenant.value = null
  }
}

const viewTenantStats = async (tenant: Tenant) => {
  statsTenant.value = tenant
  showStatsDrawer.value = true
  loadingStats.value = true
  try {
    const response = await tenantsApi.stats(tenant.id)
    statsData.value = response.data
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  } finally {
    loadingStats.value = false
  }
}

const closeStatsDrawer = () => {
  showStatsDrawer.value = false
  statsTenant.value = null
  statsData.value = null
}

const openUsersDialog = async (tenant: Tenant) => {
  usersTenant.value = tenant
  showUsersDrawer.value = true
  await fetchTenantUsers(tenant.id)
}

const fetchTenantUsers = async (tenantId: string) => {
  loadingUsers.value = true
  try {
    const response = await tenantsApi.users(tenantId)
    tenantUsers.value = response.data.results || response.data
  } catch (error) {
    console.error('Failed to fetch tenant users:', error)
    showToast(t('common.error'), 'error')
  } finally {
    loadingUsers.value = false
  }
}

// Helper functions for user display
const getInitials = (user: any): string => {
  if (user.first_name && user.last_name) {
    return (user.first_name[0] + user.last_name[0]).toUpperCase()
  }
  if (user.first_name) {
    return user.first_name.slice(0, 2).toUpperCase()
  }
  return (user.email || 'U').slice(0, 2).toUpperCase()
}

const getDisplayName = (user: any): string => {
  if (user.first_name && user.last_name) {
    return `${user.first_name} ${user.last_name}`
  }
  if (user.first_name) {
    return user.first_name
  }
  return user.email?.split('@')[0] || 'Unknown User'
}

const closeUsersDrawer = () => {
  showUsersDrawer.value = false
  usersTenant.value = null
  tenantUsers.value = []
}

const updateUserRole = async (userId: string, role: string, isSuperuser: boolean) => {
  if (!usersTenant.value) return
  try {
    await tenantsApi.updateUser(usersTenant.value.id, userId, { role, is_superuser: isSuperuser })
    showToast(t('common.saved'), 'success')
    await fetchTenantUsers(usersTenant.value.id)
  } catch (error: any) {
    showToast(error.response?.data?.detail || t('common.error'), 'error')
  }
}

const confirmRemoveUser = (user: any) => {
  removingUser.value = user
  showRemoveUserConfirm.value = true
}

const executeRemoveUser = async () => {
  if (!removingUser.value || !usersTenant.value) return
  try {
    await tenantsApi.removeUser(usersTenant.value.id, removingUser.value.id)
    showToast(t('common.deleted'), 'success')
    showRemoveUserConfirm.value = false
    removingUser.value = null
    await fetchTenantUsers(usersTenant.value.id)
  } catch (error: any) {
    showToast(error.response?.data?.error || error.response?.data?.detail || t('common.error'), 'error')
  }
}

// New user form state
const newUserEmail = ref('')
const newUserRole = ref('member')
const showAddUserForm = ref(false)
const showRemoveUserConfirm = ref(false)
const removingUser = ref<any>(null)

// Current user ID for self-check
const currentUserId = ref<string | null>(null)

const handleAddUser = async () => {
  if (!newUserEmail.value || !usersTenant.value) return
  try {
    await tenantsApi.addUser(usersTenant.value.id, {
      email: newUserEmail.value,
      role: newUserRole.value,
      is_superuser: false
    })
    showToast(t('common.success'), 'success')
    newUserEmail.value = ''
    newUserRole.value = 'member'
    showAddUserForm.value = false
    await fetchTenantUsers(usersTenant.value.id)
  } catch (error: any) {
    showToast(error.response?.data?.error || error.response?.data?.detail || t('common.error'), 'error')
  }
}

const activateTenant = async (tenant: Tenant) => {
  try {
    await tenantsApi.activate(tenant.id)
    showToast(t('common.success'), 'success')
    fetchTenants()
  } catch (error) {
    showToast(t('common.error'), 'error')
  }
}

const deactivateTenant = async (tenant: Tenant) => {
  try {
    await tenantsApi.deactivate(tenant.id)
    showToast(t('common.success'), 'success')
    fetchTenants()
  } catch (error) {
    showToast(t('common.error'), 'error')
  }
}

const getStatusClass = (status: string) => {
  switch (status) {
    case 'active': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
    case 'inactive': return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
    case 'suspended': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
    default: return 'bg-gray-100 text-gray-800'
  }
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString()
}

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

onMounted(() => {
  fetchTenants()
  // Get current user ID from auth store
  currentUserId.value = authStore.user?.id || null
})
</script>
