<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex justify-between items-center">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
          {{ t('auditLog.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {{ t('auditLog.description') }}
        </p>
      </div>
      <div class="flex gap-2">
        <button
          @click="exportLogs('json')"
          class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-700"
        >
          <ArrowDownTrayIcon class="h-4 w-4 mr-2" />
          {{ t('auditLog.export') }}
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <!-- Date Range -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {{ t('auditLog.startDate') }}
          </label>
          <input
            v-model="filters.start_date"
            type="date"
            class="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {{ t('auditLog.endDate') }}
          </label>
          <input
            v-model="filters.end_date"
            type="date"
            class="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
        </div>
        <!-- Action Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {{ t('auditLog.action') }}
          </label>
          <select
            v-model="filters.action"
            class="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          >
            <option value="">{{ t('common.all') }}</option>
            <option value="create">{{ t('auditLog.actions.create') }}</option>
            <option value="update">{{ t('auditLog.actions.update') }}</option>
            <option value="delete">{{ t('auditLog.actions.delete') }}</option>
            <option value="login">{{ t('auditLog.actions.login') }}</option>
            <option value="logout">{{ t('auditLog.actions.logout') }}</option>
            <option value="enable">{{ t('auditLog.actions.enable') }}</option>
            <option value="disable">{{ t('auditLog.actions.disable') }}</option>
          </select>
        </div>
        <!-- Resource Type Filter -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {{ t('auditLog.resourceType') }}
          </label>
          <select
            v-model="filters.resource_type"
            class="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          >
            <option value="">{{ t('common.all') }}</option>
            <option value="user">{{ t('auditLog.resourceTypes.user') }}</option>
            <option value="tenant">{{ t('auditLog.resourceTypes.tenant') }}</option>
            <option value="proxy">{{ t('auditLog.resourceTypes.proxy') }}</option>
            <option value="license">{{ t('auditLog.resourceTypes.license') }}</option>
            <option value="session">{{ t('auditLog.resourceTypes.session') }}</option>
          </select>
        </div>
      </div>
      <div class="mt-4 flex justify-end">
        <button
          @click="fetchLogs"
          class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
        >
          {{ t('common.search') }}
        </button>
      </div>
    </div>

    <!-- Statistics Cards -->
    <div v-if="statistics" class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div class="text-sm text-gray-500 dark:text-gray-400">{{ t('auditLog.totalLogs') }}</div>
        <div class="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
          {{ statistics.total_count }}
        </div>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div class="text-sm text-gray-500 dark:text-gray-400">{{ t('auditLog.todayLogs') }}</div>
        <div class="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
          {{ statistics.today_count }}
        </div>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div class="text-sm text-gray-500 dark:text-gray-400">{{ t('auditLog.successRate') }}</div>
        <div class="mt-1 text-2xl font-semibold text-green-600 dark:text-green-400">
          {{ successRate }}%
        </div>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div class="text-sm text-gray-500 dark:text-gray-400">{{ t('auditLog.failureCount') }}</div>
        <div class="mt-1 text-2xl font-semibold text-red-600 dark:text-red-400">
          {{ statistics.result_stats?.failure || 0 }}
        </div>
      </div>
    </div>

    <!-- Logs Table -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                {{ t('auditLog.timestamp') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                {{ t('auditLog.user') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                {{ t('auditLog.action') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                {{ t('auditLog.resource') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                {{ t('auditLog.result') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                {{ t('auditLog.ipAddress') }}
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                {{ t('common.actions') }}
              </th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-if="loading">
              <td colspan="7" class="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                {{ t('common.loading') }}
              </td>
            </tr>
            <tr v-else-if="logs.length === 0">
              <td colspan="7" class="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                {{ t('common.noData') }}
              </td>
            </tr>
            <tr v-for="log in logs" :key="log.id" class="hover:bg-gray-50 dark:hover:bg-gray-700">
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                {{ formatDateTime(log.timestamp) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900 dark:text-white">
                  {{ log.user_display || 'System' }}
                </div>
                <div class="text-sm text-gray-500 dark:text-gray-400">
                  {{ log.user_email || '-' }}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="getActionBadgeClass(log.action)" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium">
                  {{ log.action_display || t(`auditLog.actions.${log.action}`) }}
                </span>
              </td>
              <td class="px-6 py-4">
                <div class="text-sm text-gray-900 dark:text-white">
                  {{ log.resource_name || log.resource_id || '-' }}
                </div>
                <div class="text-sm text-gray-500 dark:text-gray-400">
                  {{ log.resource_type_display || t(`auditLog.resourceTypes.${log.resource_type}`) }}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="getResultBadgeClass(log.result)" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium">
                  {{ log.result_display || t(`auditLog.results.${log.result}`) }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                {{ log.ip_address || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm">
                <button
                  @click="showDetail(log)"
                  class="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300"
                >
                  {{ t('common.detail') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="pagination.count > 0" class="bg-white dark:bg-gray-800 px-4 py-3 flex items-center justify-between border-t border-gray-200 dark:border-gray-700 sm:px-6">
        <div class="flex-1 flex justify-between sm:hidden">
          <button
            :disabled="pagination.page <= 1"
            @click="changePage(pagination.page - 1)"
            class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            {{ t('common.previous') }}
          </button>
          <button
            :disabled="pagination.page >= totalPages"
            @click="changePage(pagination.page + 1)"
            class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            {{ t('common.next') }}
          </button>
        </div>
        <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
          <div>
            <p class="text-sm text-gray-700 dark:text-gray-300">
              {{ t('common.showing') }} {{ (pagination.page - 1) * pageSize + 1 }}
              {{ t('common.to') }} {{ Math.min(pagination.page * pageSize, pagination.count) }}
              {{ t('common.of') }} {{ pagination.count }} {{ t('common.results') }}
            </p>
          </div>
          <div>
            <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
              <button
                :disabled="pagination.page <= 1"
                @click="changePage(pagination.page - 1)"
                class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
              >
                {{ t('common.previous') }}
              </button>
              <button
                v-for="page in visiblePages"
                :key="page"
                @click="changePage(page)"
                :class="[
                  page === pagination.page
                    ? 'z-10 bg-indigo-50 dark:bg-indigo-900 border-indigo-500 text-indigo-600 dark:text-indigo-300'
                    : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700',
                  'relative inline-flex items-center px-4 py-2 border text-sm font-medium'
                ]"
              >
                {{ page }}
              </button>
              <button
                :disabled="pagination.page >= totalPages"
                @click="changePage(pagination.page + 1)"
                class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
              >
                {{ t('common.next') }}
              </button>
            </nav>
          </div>
        </div>
      </div>
    </div>

    <!-- Detail Modal -->
    <div v-if="showDetailModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-center justify-center min-h-screen px-4">
        <div class="fixed inset-0 bg-black bg-opacity-50" @click="showDetailModal = false"></div>
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">
              {{ t('auditLog.detail') }}
            </h3>
            <button @click="showDetailModal = false" class="text-gray-400 hover:text-gray-500">
              <XMarkIcon class="h-6 w-6" />
            </button>
          </div>
          <div v-if="selectedLog" class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-500 dark:text-gray-400">
                  {{ t('auditLog.timestamp') }}
                </label>
                <div class="mt-1 text-sm text-gray-900 dark:text-white">
                  {{ formatDateTime(selectedLog.timestamp) }}
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-500 dark:text-gray-400">
                  {{ t('auditLog.user') }}
                </label>
                <div class="mt-1 text-sm text-gray-900 dark:text-white">
                  {{ selectedLog.user_display || 'System' }}
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-500 dark:text-gray-400">
                  {{ t('auditLog.action') }}
                </label>
                <div class="mt-1 text-sm text-gray-900 dark:text-white">
                  {{ selectedLog.action_display }}
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-500 dark:text-gray-400">
                  {{ t('auditLog.resource') }}
                </label>
                <div class="mt-1 text-sm text-gray-900 dark:text-white">
                  {{ selectedLog.resource_type_display }}: {{ selectedLog.resource_name || selectedLog.resource_id }}
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-500 dark:text-gray-400">
                  {{ t('auditLog.ipAddress') }}
                </label>
                <div class="mt-1 text-sm text-gray-900 dark:text-white">
                  {{ selectedLog.ip_address || '-' }}
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-500 dark:text-gray-400">
                  {{ t('auditLog.result') }}
                </label>
                <div class="mt-1">
                  <span :class="getResultBadgeClass(selectedLog.result)" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium">
                    {{ selectedLog.result_display }}
                  </span>
                </div>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-500 dark:text-gray-400">
                {{ t('auditLog.description') }}
              </label>
              <div class="mt-1 text-sm text-gray-900 dark:text-white">
                {{ selectedLog.details || '-' }}
              </div>
            </div>
            <div v-if="selectedLog.error_message">
              <label class="block text-sm font-medium text-red-500">
                {{ t('auditLog.errorMessage') }}
              </label>
              <div class="mt-1 text-sm text-red-600 dark:text-red-400">
                {{ selectedLog.error_message }}
              </div>
            </div>
            <div v-if="selectedLog.changes && Object.keys(selectedLog.changes).length > 0">
              <label class="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
                {{ t('auditLog.changes') }}
              </label>
              <pre class="bg-gray-50 dark:bg-gray-900 rounded p-3 text-xs overflow-auto max-h-60">{{ JSON.stringify(selectedLog.changes, null, 2) }}</pre>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-500 dark:text-gray-400">
                {{ t('auditLog.requestPath') }}
              </label>
              <div class="mt-1 text-sm text-gray-900 dark:text-white">
                {{ selectedLog.request_method }} {{ selectedLog.request_path }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowDownTrayIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { auditLogApi } from '@/api'
import { useAppStore } from '@/stores/app'

const { t } = useI18n()
const appStore = useAppStore()

interface AuditLogItem {
  id: string
  timestamp: string
  user: string | null
  user_display: string
  user_email: string
  action: string
  action_display: string
  resource_type: string
  resource_type_display: string
  resource_id: string
  resource_name: string
  result: string
  result_display: string
  ip_address: string
  details: string
  error_message: string
  request_method: string
  request_path: string
  changes: Record<string, unknown>
}

interface Statistics {
  total_count: number
  today_count: number
  action_stats: Record<string, number>
  resource_stats: Record<string, number>
  result_stats: Record<string, number>
}

const logs = ref<AuditLogItem[]>([])
const loading = ref(false)
const statistics = ref<Statistics | null>(null)
const showDetailModal = ref(false)
const selectedLog = ref<AuditLogItem | null>(null)

const filters = ref({
  start_date: '',
  end_date: '',
  action: '',
  resource_type: '',
})

const pagination = ref({
  page: 1,
  count: 0,
})

const pageSize = 20

const totalPages = computed(() => Math.ceil(pagination.value.count / pageSize))

const visiblePages = computed(() => {
  const pages: number[] = []
  const start = Math.max(1, pagination.value.page - 2)
  const end = Math.min(totalPages.value, pagination.value.page + 2)
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  return pages
})

const successRate = computed(() => {
  if (!statistics.value) return 0
  const total = statistics.value.total_count
  if (total === 0) return 0
  const success = statistics.value.result_stats?.success || 0
  return Math.round((success / total) * 100)
})

const fetchLogs = async () => {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: pagination.value.page,
      page_size: pageSize,
    }
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    if (filters.value.action) params.action = filters.value.action
    if (filters.value.resource_type) params.resource_type = filters.value.resource_type

    const response = await auditLogApi.list(params)
    logs.value = response.data.results || response.data
    pagination.value.count = response.data.count || logs.value.length
  } catch (error) {
    console.error('Failed to fetch audit logs:', error)
    appStore.showToast({ type: 'error', title: t('common.fetchFailed') })
  } finally {
    loading.value = false
  }
}

const fetchStatistics = async () => {
  try {
    const response = await auditLogApi.statistics()
    statistics.value = response.data
  } catch (error) {
    console.error('Failed to fetch statistics:', error)
  }
}

const changePage = (page: number) => {
  pagination.value.page = page
  fetchLogs()
}

const showDetail = (log: AuditLogItem) => {
  selectedLog.value = log
  showDetailModal.value = true
}

const exportLogs = async (format: 'json' | 'csv') => {
  try {
    const response = await auditLogApi.export(format)
    const blob = new Blob([response.data], { 
      type: format === 'csv' ? 'text/csv' : 'application/json' 
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `audit_logs.${format}`
    link.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Failed to export logs:', error)
    appStore.showToast({ type: 'error', title: t('common.exportFailed') })
  }
}

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString()
}

const getActionBadgeClass = (action: string) => {
  const classes: Record<string, string> = {
    create: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    update: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    delete: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    login: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
    logout: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
    enable: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    disable: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  }
  return classes[action] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
}

const getResultBadgeClass = (result: string) => {
  const classes: Record<string, string> = {
    success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    failure: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    partial: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  }
  return classes[result] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
}

onMounted(() => {
  fetchLogs()
  fetchStatistics()
})
</script>
