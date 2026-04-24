<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { auditLogApi } from '@/api'
import {
  ClipboardDocumentListIcon,
  ArrowDownTrayIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  UserCircleIcon,
  ServerIcon,
  CloudArrowUpIcon,
  Cog6ToothIcon,
  InformationCircleIcon,
  ArrowUturnLeftIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()

interface AuditLog {
  id: string | number
  timestamp: string
  user?: { email: string; name?: string }
  action: string
  resource_type: string
  resource_id?: string
  details?: string
  ip_address?: string
  status?: 'success' | 'failure' | 'warning'
}

const isLoading = ref(true)
const logs = ref<AuditLog[]>([])
const searchQuery = ref('')
const selectedAction = ref('all')
const selectedResourceType = ref('all')
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = ref(20)

const filteredLogs = computed(() => {
  let result = logs.value
  if (selectedAction.value !== 'all') {
    result = result.filter(l => l.action === selectedAction.value)
  }
  if (selectedResourceType.value !== 'all') {
    result = result.filter(l => l.resource_type === selectedResourceType.value)
  }
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(l => 
      l.action?.toLowerCase().includes(query) ||
      l.details?.toLowerCase().includes(query) ||
      l.user?.email?.toLowerCase().includes(query)
    )
  }
  return result
})

const stats = computed(() => ({
  total: logs.value.length,
  success: logs.value.filter(l => l.status === 'success' || !l.status).length,
  warning: logs.value.filter(l => l.status === 'warning').length,
  failure: logs.value.filter(l => l.status === 'failure').length
}))

async function fetchLogs() {
  isLoading.value = true
  try {
    const response = await auditLogApi.list({
      page: currentPage.value,
      page_size: pageSize.value
    })
    logs.value = response.data.results || response.data
    totalPages.value = Math.ceil((response.data.count || 0) / pageSize.value)
  } catch (error) {
    console.error('Failed to fetch audit logs:', error)
  } finally {
    isLoading.value = false
  }
}

async function exportLogs() {
  try {
    const response = await auditLogApi.export({})
    // Handle download
    const blob = new Blob([response.data], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Failed to export logs:', error)
  }
}

function getActionIcon(action: string) {
  const icons: Record<string, any> = {
    login: UserCircleIcon,
    logout: UserCircleIcon,
    backup_create: CloudArrowUpIcon,
    backup_execute: CloudArrowUpIcon,
    backup_delete: CloudArrowUpIcon,
    recovery_create: ArrowUturnLeftIcon,
    recovery_execute: ArrowUturnLeftIcon,
    node_create: ServerIcon,
    node_delete: ServerIcon,
    config_change: Cog6ToothIcon,
    user_create: UserCircleIcon,
    user_delete: UserCircleIcon
  }
  return icons[action] || InformationCircleIcon
}

function getActionColor(action: string): string {
  const colors: Record<string, string> = {
    login: 'bg-blue-100 text-blue-600',
    logout: 'bg-slate-100 text-slate-600',
    backup_create: 'bg-indigo-100 text-indigo-600',
    backup_execute: 'bg-indigo-100 text-indigo-600',
    backup_delete: 'bg-red-100 text-red-600',
    recovery_create: 'bg-emerald-100 text-emerald-600',
    recovery_execute: 'bg-emerald-100 text-emerald-600',
    node_create: 'bg-purple-100 text-purple-600',
    node_delete: 'bg-red-100 text-red-600',
    config_change: 'bg-amber-100 text-amber-600'
  }
  return colors[action] || 'bg-slate-100 text-slate-600'
}

function formatAction(action: string): string {
  return action?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || action
}

onMounted(() => {
  fetchLogs()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">{{ t('auditLog.title') }}</h1>
        <p class="text-slate-500 mt-1">{{ t('auditLog.subtitle') }}</p>
      </div>
      <button
        @click="exportLogs"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
      >
        <ArrowDownTrayIcon class="w-4 h-4" />
        {{ t('auditLog.actions.export') }}
      </button>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('common.total') }}</p>
        <p class="text-xl font-bold text-slate-800 mt-1">{{ stats.total }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('auditLog.stats.success') }}</p>
        <p class="text-xl font-bold text-emerald-600 mt-1">{{ stats.success }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('auditLog.stats.warning') }}</p>
        <p class="text-xl font-bold text-amber-600 mt-1">{{ stats.warning }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('auditLog.stats.failure') }}</p>
        <p class="text-xl font-bold text-red-600 mt-1">{{ stats.failure }}</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <div class="flex flex-wrap items-center gap-3">
        <div class="relative flex-1 min-w-[200px]">
          <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('common.search')"
            class="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          v-model="selectedAction"
          class="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">{{ t('auditLog.columns.action') }}: {{ t('common.all') }}</option>
          <option value="login">Login</option>
          <option value="backup_create">{{ t('auditLog.actions.backupCreate') }}</option>
          <option value="backup_execute">{{ t('auditLog.actions.backupExecute') }}</option>
          <option value="recovery_create">{{ t('auditLog.actions.recoveryCreate') }}</option>
        </select>
        <select
          v-model="selectedResourceType"
          class="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">{{ t('auditLog.columns.resourceType') }}: {{ t('common.all') }}</option>
          <option value="backup_task">Backup Task</option>
          <option value="recovery_task">Recovery Task</option>
          <option value="node">Node</option>
          <option value="user">User</option>
        </select>
        <button
          @click="fetchLogs"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Logs List -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <div class="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
    </div>

    <div v-else-if="filteredLogs.length === 0" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
      <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <ClipboardDocumentListIcon class="w-8 h-8 text-slate-400" />
      </div>
      <h3 class="text-lg font-medium text-slate-800 mb-1">{{ t('auditLog.empty.title') }}</h3>
      <p class="text-slate-500">{{ t('auditLog.empty.description') }}</p>
    </div>

    <div v-else class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <table class="w-full">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('auditLog.columns.timestamp') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('auditLog.columns.user') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('auditLog.columns.action') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('auditLog.columns.resourceType') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('auditLog.columns.details') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="log in filteredLogs" :key="log.id" class="hover:bg-slate-50 transition-colors">
            <td class="px-6 py-4">
              <span class="text-sm text-slate-600 font-mono">
                {{ log.timestamp ? new Date(log.timestamp).toLocaleString() : '-' }}
              </span>
            </td>
            <td class="px-6 py-4">
              <div class="flex items-center gap-2">
                <div class="w-7 h-7 bg-slate-100 rounded-full flex items-center justify-center">
                  <UserCircleIcon class="w-4 h-4 text-slate-400" />
                </div>
                <span class="text-sm text-slate-700">{{ log.user?.email || 'System' }}</span>
              </div>
            </td>
            <td class="px-6 py-4">
              <div class="flex items-center gap-2">
                <div :class="['w-7 h-7 rounded-lg flex items-center justify-center', getActionColor(log.action)]">
                  <component :is="getActionIcon(log.action)" class="w-4 h-4" />
                </div>
                <span class="text-sm text-slate-700">{{ formatAction(log.action) }}</span>
              </div>
            </td>
            <td class="px-6 py-4">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">
                {{ log.resource_type }}
              </span>
            </td>
            <td class="px-6 py-4">
              <p class="text-sm text-slate-500 truncate max-w-xs">{{ log.details || '-' }}</p>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div class="flex items-center justify-between px-6 py-3 border-t border-slate-100">
        <p class="text-sm text-slate-500">{{ t('common.total') }}: {{ filteredLogs.length }}</p>
        <div class="flex gap-2">
          <button
            @click="currentPage--; fetchLogs()"
            :disabled="currentPage === 1"
            class="px-3 py-1.5 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t('common.previous') }}
          </button>
          <button
            @click="currentPage++; fetchLogs()"
            :disabled="currentPage >= totalPages"
            class="px-3 py-1.5 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t('common.next') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
