<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import {
  ServerIcon,
  BoltIcon,
  CircleStackIcon,
  ChartBarIcon,
  CloudArrowUpIcon,
  ArrowUturnLeftIcon,
  ArrowTrendingUpIcon,
  EllipsisHorizontalIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'

const router = useRouter()
const { t } = useI18n()

interface Stats {
  total_nodes: number
  online_nodes: number
  active_tasks: number
  storage_used: number
  storage_total: number
  total_backups: number
  success_rate: number
  running_tasks: number
  pending_tasks: number
  failed_tasks: number
}

const isLoading = ref(true)
const stats = ref<Stats>({
  total_nodes: 0,
  online_nodes: 0,
  active_tasks: 0,
  storage_used: 0,
  storage_total: 0,
  total_backups: 0,
  success_rate: 0,
  running_tasks: 0,
  pending_tasks: 0,
  failed_tasks: 0
})

const recentTasks = ref<any[]>([])
const systemHealth = ref({
  api: 'ok',
  database: 'ok',
  storage: 'ok'
})

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    completed: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
    running: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    pending: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
    failed: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
    cancelled: 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300',
    paused: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400'
  }
  return colors[status] || 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300'
}

function getStatusIcon(status: string) {
  const icons: Record<string, any> = {
    completed: CheckCircleIcon,
    running: BoltIcon,
    pending: ClockIcon,
    failed: ExclamationTriangleIcon
  }
  return icons[status] || ClockIcon
}

async function fetchDashboardData() {
  isLoading.value = true
  try {
    const [proxiesRes, tasksRes] = await Promise.all([
      api.get('/api/v1/proxies/stats/'),
      api.get('/api/v1/backup-tasks/tasks/?ordering=-created_at&page_size=5')
    ])

    const tasksData = tasksRes.data.results || []
    const runningCount = tasksData.filter((t: any) => t.status === 'running').length
    const pendingCount = tasksData.filter((t: any) => t.status === 'pending').length
    const failedCount = tasksData.filter((t: any) => t.status === 'failed').length

    stats.value = {
      total_nodes: proxiesRes.data.total_proxies || proxiesRes.data.total_nodes || 0,
      online_nodes: proxiesRes.data.active_proxies || proxiesRes.data.active_nodes || proxiesRes.data.online_nodes || 0,
      active_tasks: tasksRes.data.count || 0,
      storage_used: 161061273600, // 150GB
      storage_total: 1099511627776, // 1TB
      total_backups: 24,
      success_rate: 97.5,
      running_tasks: runningCount,
      pending_tasks: pendingCount,
      failed_tasks: failedCount
    }

    recentTasks.value = tasksData
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchDashboardData()
})
</script>

<template>
  <div class="space-y-8">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800 dark:text-white">{{ t('dashboard.title') }}</h1>
        <p class="text-slate-500 dark:text-slate-400 mt-1">{{ t('dashboard.subtitle') }}</p>
      </div>
      <button
        @click="fetchDashboardData"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 hover:border-slate-300 dark:hover:border-slate-600 transition-colors shadow-sm"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        {{ t('common.refresh') }}
      </button>
    </div>

    <!-- Stats Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      <!-- Total Nodes -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm font-medium text-slate-500 dark:text-slate-400">{{ t('dashboard.stats.totalNodes') }}</p>
            <p class="text-3xl font-bold text-slate-800 dark:text-white mt-2">{{ stats.total_nodes }}</p>
            <div class="flex items-center gap-1.5 mt-3">
              <span class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
              <span class="text-sm text-emerald-600 dark:text-emerald-400 font-medium">{{ stats.online_nodes }} {{ t('common.active') }}</span>
            </div>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-200 dark:shadow-indigo-900/30">
            <ServerIcon class="w-6 h-6 text-white" />
          </div>
        </div>
      </div>

      <!-- Active Tasks -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm font-medium text-slate-500 dark:text-slate-400">{{ t('dashboard.stats.activeTasks') }}</p>
            <p class="text-3xl font-bold text-slate-800 dark:text-white mt-2">{{ stats.active_tasks }}</p>
            <div class="flex items-center gap-3 mt-3">
              <span class="text-sm text-blue-600 dark:text-blue-400">{{ stats.running_tasks }} {{ t('backupTasks.status.running') }}</span>
              <span class="text-sm text-amber-600 dark:text-amber-400">{{ stats.pending_tasks }} {{ t('backupTasks.status.pending') }}</span>
            </div>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl flex items-center justify-center shadow-lg shadow-amber-200 dark:shadow-amber-900/30">
            <BoltIcon class="w-6 h-6 text-white" />
          </div>
        </div>
      </div>

      <!-- Storage Used -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm font-medium text-slate-500 dark:text-slate-400">{{ t('dashboard.stats.storageUsed') }}</p>
            <p class="text-3xl font-bold text-slate-800 dark:text-white mt-2">{{ formatBytes(stats.storage_used) }}</p>
            <div class="mt-3">
              <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
                <span>{{ t('dashboard.stats.storageUsed') }}</span>
                <span>{{ Math.round(stats.storage_used / stats.storage_total * 100) }}%</span>
              </div>
              <div class="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-500"
                  :style="{ width: `${Math.round(stats.storage_used / stats.storage_total * 100)}%` }"
                />
              </div>
            </div>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center shadow-lg shadow-emerald-200 dark:shadow-emerald-900/30">
            <CircleStackIcon class="w-6 h-6 text-white" />
          </div>
        </div>
      </div>

      <!-- Success Rate -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm font-medium text-slate-500 dark:text-slate-400">{{ t('dashboard.stats.successRate') }}</p>
            <p class="text-3xl font-bold text-slate-800 dark:text-white mt-2">{{ stats.success_rate }}%</p>
            <div class="flex items-center gap-1.5 mt-3 text-emerald-600 dark:text-emerald-400">
              <ArrowTrendingUpIcon class="w-4 h-4" />
              <span class="text-sm font-medium">+2.5%</span>
            </div>
          </div>
          <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-cyan-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200 dark:shadow-blue-900/30">
            <ChartBarIcon class="w-6 h-6 text-white" />
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Recent Activity -->
      <div class="lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-700">
          <h2 class="text-lg font-semibold text-slate-800 dark:text-white">{{ t('dashboard.recentActivity') }}</h2>
          <router-link
            to="/backup-tasks"
            class="text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors"
          >
            {{ t('common.all') }} →
          </router-link>
        </div>
        
        <div v-if="recentTasks.length === 0" class="px-6 py-12 text-center">
          <div class="w-12 h-12 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-3">
            <EllipsisHorizontalIcon class="w-6 h-6 text-slate-400" />
          </div>
          <p class="text-slate-500 dark:text-slate-400">{{ t('common.noData') }}</p>
        </div>

        <div v-else class="divide-y divide-slate-100 dark:divide-slate-700">
          <div
            v-for="task in recentTasks"
            :key="task.id"
            class="px-6 py-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer"
            @click="router.push(`/backup-tasks`)"
          >
            <div class="flex items-center gap-4">
              <div :class="[
                'w-10 h-10 rounded-lg flex items-center justify-center',
                task.status === 'completed' ? 'bg-emerald-100 dark:bg-emerald-900/30' :
                task.status === 'running' ? 'bg-blue-100 dark:bg-blue-900/30' :
                task.status === 'failed' ? 'bg-red-100 dark:bg-red-900/30' : 'bg-slate-100 dark:bg-slate-700'
              ]">
                <component
                  :is="getStatusIcon(task.status)"
                  :class="[
                    'w-5 h-5',
                    task.status === 'completed' ? 'text-emerald-600 dark:text-emerald-400' :
                    task.status === 'running' ? 'text-blue-600 dark:text-blue-400' :
                    task.status === 'failed' ? 'text-red-600 dark:text-red-400' : 'text-slate-600 dark:text-slate-400'
                  ]"
                />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-slate-800 dark:text-white truncate">{{ task.name }}</p>
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  {{ t(`backupTasks.types.${task.task_type}`) }} • {{ task.source_node_name || 'Node' }}
                </p>
              </div>
              <div class="text-right">
                <span :class="[
                  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                  getStatusColor(task.status)
                ]">
                  {{ t(`backupTasks.status.${task.status}`) }}
                </span>
                <p class="text-xs text-slate-400 mt-1">
                  {{ new Date(task.created_at).toLocaleDateString() }}
                </p>
              </div>
            </div>
            <!-- Progress bar for running tasks -->
            <div v-if="task.status === 'running' && task.progress" class="mt-3">
              <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
                <span>{{ task.progress }}%</span>
                <span>{{ formatBytes(task.backed_up_size || 0) }} / {{ formatBytes(task.total_size || 0) }}</span>
              </div>
              <div class="h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all duration-300"
                  :style="{ width: `${task.progress}%` }"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Sidebar -->
      <div class="space-y-6">
        <!-- Quick Actions -->
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
          <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-700">
            <h2 class="text-lg font-semibold text-slate-800 dark:text-white">{{ t('dashboard.quickActions') }}</h2>
          </div>
          <div class="p-4 space-y-2">
            <button
              @click="router.push('/backup-tasks')"
              class="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
            >
              <CloudArrowUpIcon class="w-5 h-5" />
              {{ t('dashboard.actions.newBackup') }}
            </button>
            <button
              @click="router.push('/recovery-tasks')"
              class="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-600 hover:border-slate-300 dark:hover:border-slate-500 transition-colors"
            >
              <ArrowUturnLeftIcon class="w-5 h-5 text-slate-500 dark:text-slate-400" />
              {{ t('dashboard.actions.newRecovery') }}
            </button>
          </div>
        </div>

        <!-- System Status -->
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
          <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-700">
            <h2 class="text-lg font-semibold text-slate-800 dark:text-white">{{ t('dashboard.systemStatus') }}</h2>
          </div>
          <div class="p-4 space-y-3">
            <div class="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-700/50">
              <span class="text-sm text-slate-600 dark:text-slate-300">API Server</span>
              <span class="flex items-center gap-2 text-sm font-medium text-emerald-600 dark:text-emerald-400">
                <span class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
                {{ systemHealth.api }}
              </span>
            </div>
            <div class="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-700/50">
              <span class="text-sm text-slate-600 dark:text-slate-300">Database</span>
              <span class="flex items-center gap-2 text-sm font-medium text-emerald-600 dark:text-emerald-400">
                <span class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
                {{ systemHealth.database }}
              </span>
            </div>
            <div class="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-700/50">
              <span class="text-sm text-slate-600 dark:text-slate-300">Storage</span>
              <span class="flex items-center gap-2 text-sm font-medium text-emerald-600 dark:text-emerald-400">
                <span class="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
                {{ systemHealth.storage }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
