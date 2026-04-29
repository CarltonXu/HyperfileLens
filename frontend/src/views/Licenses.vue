<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="sm:flex sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900 dark:text-white">{{ t('licenses.title') }}</h1>
        <p class="mt-2 text-sm text-gray-700 dark:text-gray-300">
          {{ t('licenses.description') || 'Manage product licenses and authorization' }}
        </p>
      </div>
      <div class="mt-4 sm:mt-0 flex gap-2">
        <button
          type="button"
          class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
          @click="validateAllLicenses"
        >
          <CheckCircleIcon class="-ml-0.5 mr-1.5 h-5 w-5 text-gray-400" aria-hidden="true" />
          {{ t('licenses.validateAll') }}
        </button>
        <button
          type="button"
          class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
          @click="openImportDialog"
        >
          <KeyIcon class="-ml-0.5 mr-1.5 h-5 w-5 text-gray-400" aria-hidden="true" />
          {{ t('licenses.importLicense') || 'Import License' }}
        </button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      <div class="overflow-hidden rounded-lg bg-white dark:bg-gray-800 shadow">
        <div class="p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <DocumentTextIcon class="h-6 w-6 text-gray-400" />
            </div>
            <div class="ml-5 w-0 flex-1">
              <dl>
                <dt class="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">{{ t('licenses.totalLicenses') }}</dt>
                <dd class="text-2xl font-semibold text-gray-900 dark:text-white">{{ stats.total || 0 }}</dd>
              </dl>
            </div>
          </div>
        </div>
      </div>
      <div class="overflow-hidden rounded-lg bg-white dark:bg-gray-800 shadow">
        <div class="p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <CheckCircleIcon class="h-6 w-6 text-green-400" />
            </div>
            <div class="ml-5 w-0 flex-1">
              <dl>
                <dt class="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">{{ t('licenses.validLicenses') }}</dt>
                <dd class="text-2xl font-semibold text-gray-900 dark:text-white">{{ stats.valid || 0 }}</dd>
              </dl>
            </div>
          </div>
        </div>
      </div>
      <div class="overflow-hidden rounded-lg bg-white dark:bg-gray-800 shadow">
        <div class="p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <ExclamationCircleIcon class="h-6 w-6 text-red-400" />
            </div>
            <div class="ml-5 w-0 flex-1">
              <dl>
                <dt class="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">{{ t('licenses.expiredLicenses') }}</dt>
                <dd class="text-2xl font-semibold text-gray-900 dark:text-white">{{ stats.expired || 0 }}</dd>
              </dl>
            </div>
          </div>
        </div>
      </div>
      <div class="overflow-hidden rounded-lg bg-white dark:bg-gray-800 shadow">
        <div class="p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <SparklesIcon class="h-6 w-6 text-purple-400" />
            </div>
            <div class="ml-5 w-0 flex-1">
              <dl>
                <dt class="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">{{ t('licenses.activeFeatures') }}</dt>
                <dd class="text-2xl font-semibold text-gray-900 dark:text-white">{{ stats.active_features || 0 }}</dd>
              </dl>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white dark:bg-gray-800 shadow rounded-lg p-4">
      <div class="flex flex-wrap gap-4">
        <div class="flex items-center gap-2">
          <select
            v-model="statusFilter"
            class="rounded-md border-0 py-1.5 pl-3 pr-8 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
            @change="fetchLicenses"
          >
            <option value="">{{ t('common.all') || 'All Status' }}</option>
            <option value="valid">{{ t('licenses.valid') }}</option>
            <option value="expired">{{ t('licenses.expired') }}</option>
            <option value="invalid">{{ t('licenses.invalid') }}</option>
            <option value="revoked">{{ t('licenses.revoked') }}</option>
          </select>
        </div>
        <div class="flex items-center gap-2">
          <select
            v-model="typeFilter"
            class="rounded-md border-0 py-1.5 pl-3 pr-8 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
            @change="fetchLicenses"
          >
            <option value="">{{ t('common.all') || 'All Types' }}</option>
            <option value="trial">{{ t('licenses.trial') }}</option>
            <option value="standard">{{ t('licenses.standard') }}</option>
            <option value="professional">{{ t('licenses.professional') }}</option>
            <option value="enterprise">{{ t('licenses.enterprise') }}</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Licenses Table -->
    <div class="bg-white dark:bg-gray-800 shadow rounded-lg overflow-visible">
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
            <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 dark:text-white sm:pl-6">{{ t('licenses.licenseName') }}</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('licenses.licenseType') }}</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('licenses.status') }}</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('licenses.tenant') }}</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('licenses.expiresAt') }}</th>
            <th scope="col" class="relative py-3.5 pl-3 pr-4 sm:pr-6">
              <span class="sr-only">{{ t('common.actions') }}</span>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
          <tr v-for="license in licenses" :key="license.id" class="hover:bg-gray-50 dark:hover:bg-gray-700/50">
            <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm sm:pl-6">
              <div class="flex items-center">
                <div class="h-10 w-10 flex-shrink-0 rounded-lg bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center">
                  <KeyIcon class="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div class="ml-4">
                  <div class="font-medium text-gray-900 dark:text-white">{{ license.name }}</div>
                  <div class="text-gray-500 dark:text-gray-400 truncate max-w-xs">{{ license.license_key?.substring(0, 20) }}...</div>
                </div>
              </div>
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm">
              <span :class="getTypeClass(license.edition)" class="inline-flex rounded-full px-2 py-1 text-xs font-semibold">
                {{ t(`licenses.${license.edition}`) }}
              </span>
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm">
              <span :class="getStatusClass(license.status)" class="inline-flex rounded-full px-2 py-1 text-xs font-semibold">
                {{ t(`licenses.${license.status}`) }}
              </span>
              <p v-if="license.status === 'valid' && license.days_remaining !== undefined" class="text-xs text-gray-500 mt-1">
                {{ t('licenses.daysRemaining', { n: license.days_remaining }) }}
              </p>
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
              {{ license.tenant_name || '-' }}
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
              {{ license.expires_at ? formatDate(license.expires_at) : t('common.unlimited') || 'Unlimited' }}
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
                      <button @click="validateLicense(license)" :class="[active ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300', 'block w-full px-4 py-2 text-left text-sm']">
                        {{ t('licenses.validate') }}
                      </button>
                    </MenuItem>
                    <MenuItem v-slot="{ active }">
                      <button @click="viewLicenseDetail(license)" :class="[active ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300', 'block w-full px-4 py-2 text-left text-sm']">
                        {{ t('common.viewDetails') || 'View Details' }}
                      </button>
                    </MenuItem>
                    <MenuItem v-slot="{ active }">
                      <button @click="confirmDeleteLicense(license)" :class="[active ? 'bg-red-100 text-red-900' : 'text-red-700', 'block w-full px-4 py-2 text-left text-sm']">
                        {{ t('common.delete') }}
                      </button>
                    </MenuItem>
                  </MenuItems>
                </transition>
              </Menu>
            </td>
          </tr>
          <tr v-if="licenses.length === 0">
            <td colspan="6" class="px-6 py-12 text-center text-sm text-gray-500 dark:text-gray-400">
              {{ t('common.noData') || 'No licenses found' }}
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

    <!-- Create Dialog -->
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
                      {{ t('licenses.createLicense') }}
                    </DialogTitle>
                    <form @submit.prevent="saveLicense" class="mt-4 space-y-4">
                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('licenses.licenseName') }} *</label>
                        <input v-model="formData.name" type="text" required class="mt-1 block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6" />
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('licenses.licenseKey') }} *</label>
                        <textarea v-model="formData.license_key" rows="4" required class="mt-1 block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6 font-mono text-xs" />
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

    <!-- Detail Modal -->
    <TransitionRoot appear :show="showDetailDrawer" as="template">
      <Dialog as="div" class="relative z-10" @close="closeDetailDrawer">
        <TransitionChild as="template" enter="duration-300 ease-out" enter-from="opacity-0" enter-to="opacity-100" leave="duration-200 ease-in" leave-from="opacity-100" leave-to="opacity-0">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </TransitionChild>

        <div class="fixed inset-0 z-10 overflow-y-auto">
          <div class="flex min-h-full items-center justify-center p-4">
            <TransitionChild as="template" enter="duration-300 ease-out" enter-from="opacity-0 scale-95" enter-to="opacity-100 scale-100" leave="duration-200 ease-in" leave-from="opacity-100 scale-100" leave-to="opacity-0 scale-95">
              <DialogPanel class="w-full max-w-2xl bg-white dark:bg-gray-800 shadow-xl rounded-xl max-h-[90vh] overflow-y-auto">
                <div class="p-6">
                  <div class="flex items-center justify-between mb-6">
                    <DialogTitle class="text-lg font-semibold text-gray-900 dark:text-white">
                      {{ t('licenses.licenseName') }}: {{ detailLicense?.name }}
                    </DialogTitle>
                    <button type="button" class="rounded-md text-gray-400 hover:text-gray-500" @click="closeDetailDrawer">
                      <XMarkIcon class="h-6 w-6" aria-hidden="true" />
                    </button>
                  </div>
                  
                  <div v-if="detailLicense" class="space-y-6">
                    <!-- Status -->
                    <div class="flex items-center gap-4 p-4 rounded-lg" :class="getStatusBgClass(detailLicense.status)">
                      <component :is="getStatusIcon(detailLicense.status)" class="h-8 w-8" />
                      <div>
                        <p class="text-lg font-semibold" :class="getStatusTextClass(detailLicense.status)">
                          {{ t(`licenses.${detailLicense.status}`) }}
                        </p>
                        <p v-if="detailLicense.status === 'valid' && detailLicense.days_remaining !== undefined" class="text-sm text-gray-500">
                          {{ t('licenses.daysRemaining', { n: detailLicense.days_remaining }) }}
                        </p>
                      </div>
                    </div>

                    <!-- License Info -->
                    <div class="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-3">
                      <h4 class="font-medium text-gray-900 dark:text-white">{{ t('licenses.licenseKey') }}</h4>
                      <pre class="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap break-all bg-gray-100 dark:bg-gray-800 p-3 rounded">{{ detailLicense.license_key }}</pre>
                    </div>

                    <!-- Limits -->
                    <div class="grid grid-cols-2 gap-4">
                      <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                        <p class="text-sm text-blue-600 dark:text-blue-400">{{ t('licenses.maxUsers') }}</p>
                        <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ detailLicense.max_users || '∞' }}</p>
                      </div>
                      <div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                        <p class="text-sm text-green-600 dark:text-green-400">{{ t('licenses.maxProxies') }}</p>
                        <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ detailLicense.max_proxies || '∞' }}</p>
                      </div>
                      <div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                        <p class="text-sm text-purple-600 dark:text-purple-400">{{ t('licenses.maxRepositories') }}</p>
                        <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ detailLicense.max_repositories || '∞' }}</p>
                      </div>
                      <div class="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
                        <p class="text-sm text-orange-600 dark:text-orange-400">{{ t('licenses.maxStorageGb') }}</p>
                        <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ detailLicense.max_storage_gb || '∞' }} GB</p>
                      </div>
                    </div>

                    <!-- Features -->
                    <div v-if="detailLicense.features && (Array.isArray(detailLicense.features) ? detailLicense.features.length > 0 : Object.keys(detailLicense.features).length > 0)">
                      <h4 class="font-medium text-gray-900 dark:text-white mb-3">{{ t('licenses.features') }}</h4>
                      <div class="flex flex-wrap gap-2">
                        <template v-if="Array.isArray(detailLicense.features)">
                          <span v-for="feature in detailLicense.features" :key="feature" class="inline-flex items-center rounded-full bg-indigo-100 dark:bg-indigo-900 px-3 py-1 text-xs font-medium text-indigo-700 dark:text-indigo-300">
                            {{ feature }}
                          </span>
                        </template>
                        <template v-else>
                          <span v-for="(enabled, feature) in detailLicense.features" :key="feature" class="inline-flex items-center rounded-full bg-indigo-100 dark:bg-indigo-900 px-3 py-1 text-xs font-medium text-indigo-700 dark:text-indigo-300">
                            {{ feature }} {{ enabled ? '✓' : '✗' }}
                          </span>
                        </template>
                      </div>
                    </div>

                    <!-- Dates -->
                    <div class="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p class="text-gray-500 dark:text-gray-400">{{ t('licenses.issuedAt') }}</p>
                        <p class="text-gray-900 dark:text-white">{{ detailLicense.issued_at ? formatDate(detailLicense.issued_at) : '-' }}</p>
                      </div>
                      <div>
                        <p class="text-gray-500 dark:text-gray-400">{{ t('licenses.expiresAt') }}</p>
                        <p class="text-gray-900 dark:text-white">{{ detailLicense.expires_at ? formatDate(detailLicense.expires_at) : t('common.unlimited') || 'Unlimited' }}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>

    <!-- Import License Dialog -->
    <TransitionRoot appear :show="showImportDialog" as="template">
      <Dialog as="div" class="relative z-10" @close="showImportDialog = false">
        <TransitionChild as="template" enter="duration-300 ease-out" enter-from="opacity-0" enter-to="opacity-100" leave="duration-200 ease-in" leave-from="opacity-100" leave-to="opacity-0">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </TransitionChild>

        <div class="fixed inset-0 z-10 overflow-y-auto">
          <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <TransitionChild as="template" enter="duration-300 ease-out" enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95" enter-to="opacity-100 translate-y-0 sm:scale-100" leave="duration-200 ease-in" leave-from="opacity-100 translate-y-0 sm:scale-100" leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95">
              <DialogPanel class="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6 dark:bg-gray-800">
                <div class="absolute right-0 top-0 pr-4 pt-4">
                  <button type="button" class="rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none dark:bg-gray-800 dark:hover:text-gray-300" @click="showImportDialog = false">
                    <span class="sr-only">Close</span>
                    <XMarkIcon class="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>
                <div class="sm:flex sm:items-start">
                  <div class="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-indigo-100 sm:mx-0 sm:h-10 sm:w-10 dark:bg-indigo-900">
                    <KeyIcon class="h-6 w-6 text-indigo-600 dark:text-indigo-300" aria-hidden="true" />
                  </div>
                  <div class="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full">
                    <DialogTitle as="h3" class="text-base font-semibold leading-6 text-gray-900 dark:text-white">
                      {{ t('licenses.importLicense') || 'Import License' }}
                    </DialogTitle>
                    <div class="mt-4">
                      <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">
                        {{ t('licenses.importDescription') || 'Paste the license string you received from sales team' }}
                      </p>
                      <textarea
                        v-model="importLicenseString"
                        rows="6"
                        class="block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6 dark:bg-gray-700 dark:text-white dark:ring-gray-600"
                        :placeholder="t('licenses.importPlaceholder') || 'HFL-LICENSE-...'"
                      />
                    </div>
                  </div>
                </div>
                <div class="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                  <button type="button" :disabled="importing || !importLicenseString.trim()" class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 sm:ml-3 sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed" @click="importLicense">
                    {{ importing ? (t('licenses.importing') || 'Importing...') : (t('licenses.import') || 'Import') }}
                  </button>
                  <button type="button" class="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 sm:w-auto dark:bg-gray-700 dark:text-white" @click="showImportDialog = false">
                    {{ t('common.cancel') }}
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
                        {{ t('licenses.confirmDelete', { name: deletingLicense?.name }) }}
                      </p>
                    </div>
                  </div>
                </div>
                <div class="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                  <button type="button" :disabled="deleting" class="inline-flex w-full justify-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500 sm:ml-3 sm:w-auto disabled:opacity-50" @click="deleteLicense">
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
import { CheckCircleIcon, ChevronLeftIcon, ChevronRightIcon, DocumentTextIcon, EllipsisVerticalIcon, ExclamationCircleIcon, ExclamationTriangleIcon, KeyIcon, SparklesIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { licensesApi } from '@/api'
import { useToast } from '@/composables/useToast'
import type { License } from '@/types/license'

const { t } = useI18n()
const { showToast } = useToast()

// State
const licenses = ref<License[]>([])
const stats = ref({ total: 0, valid: 0, expired: 0, active_features: 0 })
const loading = ref(true)
const saving = ref(false)
const deleting = ref(false)
const showDialog = ref(false)
const showDeleteConfirm = ref(false)
const showDetailDrawer = ref(false)
const showImportDialog = ref(false)
const importing = ref(false)
const importLicenseString = ref('')
const deletingLicense = ref<License | null>(null)
const detailLicense = ref<License | null>(null)
const statusFilter = ref('')
const typeFilter = ref('')

const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

const formData = ref({
  name: '',
  license_key: ''
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
const fetchLicenses = async () => {
  loading.value = true
  try {
    const response = await licensesApi.list({
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
      status: statusFilter.value || undefined,
      license_type: typeFilter.value || undefined
    })
    licenses.value = response.data.results || response.data
    pagination.value.total = response.data.count || licenses.value.length
  } catch (error) {
    console.error('Failed to fetch licenses:', error)
    showToast(t('common.error'), 'error')
  } finally {
    loading.value = false
  }
}

const fetchStats = async () => {
  try {
    const response = await licensesApi.stats()
    stats.value = response.data
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  }
}

const prevPage = () => {
  if (pagination.value.page > 1) {
    pagination.value.page--
    fetchLicenses()
  }
}

const nextPage = () => {
  if (pagination.value.page < totalPages.value) {
    pagination.value.page++
    fetchLicenses()
  }
}

const goToPage = (page: number) => {
  pagination.value.page = page
  fetchLicenses()
}

const closeDialog = () => {
  showDialog.value = false
}

const openImportDialog = () => {
  importLicenseString.value = ''
  showImportDialog.value = true
}

const importLicense = async () => {
  if (!importLicenseString.value.trim()) return
  
  importing.value = true
  try {
    await licensesApi.importLicense({ encoded_license: importLicenseString.value.trim() })
    showToast(t('licenses.importSuccess') || 'License imported successfully', 'success')
    showImportDialog.value = false
    importLicenseString.value = ''
    fetchLicenses()
    fetchStats()
  } catch (error: any) {
    console.error('Failed to import license:', error)
    showToast(error.response?.data?.error || error.response?.data?.detail || t('licenses.importFailed') || 'Failed to import license', 'error')
  } finally {
    importing.value = false
  }
}

const saveLicense = async () => {
  saving.value = true
  try {
    await licensesApi.create(formData.value)
    showToast(t('common.created'), 'success')
    closeDialog()
    fetchLicenses()
    fetchStats()
  } catch (error: any) {
    console.error('Failed to save license:', error)
    showToast(error.response?.data?.detail || t('common.error'), 'error')
  } finally {
    saving.value = false
  }
}

const validateLicense = async (license: License) => {
  try {
    const response = await licensesApi.validate(license.id)
    if (response.data.valid) {
      showToast(t('licenses.valid'), 'success')
    } else {
      showToast(response.data.message || t('licenses.invalid'), 'error')
    }
    fetchLicenses()
    fetchStats()
  } catch (error: any) {
    showToast(error.response?.data?.message || t('common.error'), 'error')
  }
}

const validateAllLicenses = async () => {
  try {
    await licensesApi.validateAll()
    showToast(t('common.success'), 'success')
    fetchLicenses()
    fetchStats()
  } catch (error) {
    showToast(t('common.error'), 'error')
  }
}

const viewLicenseDetail = (license: License) => {
  detailLicense.value = license
  showDetailDrawer.value = true
}

const closeDetailDrawer = () => {
  showDetailDrawer.value = false
  detailLicense.value = null
}

const confirmDeleteLicense = (license: License) => {
  deletingLicense.value = license
  showDeleteConfirm.value = true
}

const deleteLicense = async () => {
  if (!deletingLicense.value) return
  deleting.value = true
  try {
    await licensesApi.delete(deletingLicense.value.id)
    showToast(t('common.deleted'), 'success')
    showDeleteConfirm.value = false
    fetchLicenses()
    fetchStats()
  } catch (error: any) {
    showToast(error.response?.data?.detail || t('common.error'), 'error')
  } finally {
    deleting.value = false
    deletingLicense.value = null
  }
}

const getStatusClass = (status: string) => {
  switch (status) {
    case 'valid': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
    case 'expired': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
    case 'invalid': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300'
    case 'revoked': return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
    default: return 'bg-gray-100 text-gray-800'
  }
}

const getStatusBgClass = (status: string) => {
  switch (status) {
    case 'valid': return 'bg-green-50 dark:bg-green-900/20'
    case 'expired': return 'bg-red-50 dark:bg-red-900/20'
    case 'invalid': return 'bg-yellow-50 dark:bg-yellow-900/20'
    default: return 'bg-gray-50 dark:bg-gray-900'
  }
}

const getStatusTextClass = (status: string) => {
  switch (status) {
    case 'valid': return 'text-green-700 dark:text-green-400'
    case 'expired': return 'text-red-700 dark:text-red-400'
    case 'invalid': return 'text-yellow-700 dark:text-yellow-400'
    default: return 'text-gray-700 dark:text-gray-400'
  }
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'valid': return CheckCircleIcon
    case 'expired': return ExclamationCircleIcon
    case 'invalid': return ExclamationTriangleIcon
    default: return KeyIcon
  }
}

const getTypeClass = (type: string) => {
  switch (type) {
    case 'trial': return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
    case 'standard': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
    case 'professional': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300'
    case 'enterprise': return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300'
    default: return 'bg-gray-100 text-gray-800'
  }
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString()
}

onMounted(() => {
  fetchLicenses()
  fetchStats()
})
</script>
