<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '@/api'

const router = useRouter()
const { t } = useI18n()

interface Stats {
  total_nodes: number
  online_nodes: number
  active_tasks: number
  storage_used: number
  total_backups: number
  success_rate: number
}

const isLoading = ref(true)
const stats = ref<Stats>({
  total_nodes: 0,
  online_nodes: 0,
  active_tasks: 0,
  storage_used: 0,
  total_backups: 0,
  success_rate: 0
})

const recentTasks = ref<any[]>([])
const systemHealth = ref<any>({
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

async function fetchDashboardData() {
  isLoading.value = true
  try {
    // Fetch node stats and backup tasks
    const [nodesRes, tasksRes] = await Promise.all([
      api.get('/api/v1/nodes/stats/'),
      api.get('/api/v1/backup-tasks/tasks/?ordering=-created_at&page_size=5')
    ])

    stats.value = {
      total_nodes: nodesRes.data.total_nodes || 0,
      online_nodes: nodesRes.data.online_nodes || 0,
      active_tasks: tasksRes.data.count || 0,
      storage_used: 0,
      total_backups: 0,
      success_rate: 95
    }

    recentTasks.value = tasksRes.data.results || []
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
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">{{ t('dashboard.title') }}</h1>
        <p class="text-gray-500 mt-1">{{ t('dashboard.subtitle') }}</p>
      </div>
      <div class="flex items-center gap-3">
        <button class="btn-outline" @click="fetchDashboardData">
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- Total Nodes -->
      <div class="card">
        <div class="card-body">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">{{ t('dashboard.stats.totalNodes') }}</p>
              <p class="text-3xl font-bold text-gray-900 mt-2">{{ stats.total_nodes }}</p>
            </div>
            <div class="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
              <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" />
              </svg>
            </div>
          </div>
          <div class="mt-4 flex items-center text-sm">
            <span class="text-success-600 flex items-center">
              <span class="status-online mr-1"></span>
              {{ stats.online_nodes }} {{ t('common.active') }}
            </span>
          </div>
        </div>
      </div>

      <!-- Active Tasks -->
      <div class="card">
        <div class="card-body">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">{{ t('dashboard.stats.activeTasks') }}</p>
              <p class="text-3xl font-bold text-gray-900 mt-2">{{ stats.active_tasks }}</p>
            </div>
            <div class="w-12 h-12 bg-warning-100 rounded-xl flex items-center justify-center">
              <svg class="w-6 h-6 text-warning-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
          </div>
          <div class="mt-4">
            <div class="progress-bar">
              <div class="progress-bar-fill bg-warning-500" style="width: 45%"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Storage Used -->
      <div class="card">
        <div class="card-body">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">{{ t('dashboard.stats.storageUsed') }}</p>
              <p class="text-3xl font-bold text-gray-900 mt-2">{{ formatBytes(stats.storage_used) }}</p>
            </div>
            <div class="w-12 h-12 bg-success-100 rounded-xl flex items-center justify-center">
              <svg class="w-6 h-6 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
            </div>
          </div>
          <div class="mt-4">
            <div class="progress-bar">
              <div class="progress-bar-fill bg-success-500" style="width: 35%"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Success Rate -->
      <div class="card">
        <div class="card-body">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-500">{{ t('dashboard.stats.successRate') }}</p>
              <p class="text-3xl font-bold text-gray-900 mt-2">{{ stats.success_rate }}%</p>
            </div>
            <div class="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
              <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div class="mt-4 flex items-center text-sm text-success-600">
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
            2.5% {{ t('time.daysAgo').replace('{n}', '') }}
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Recent Tasks -->
      <div class="lg:col-span-2">
        <div class="card">
          <div class="card-header flex items-center justify-between">
            <h3 class="text-lg font-semibold text-gray-900">{{ t('dashboard.recentActivity') }}</h3>
            <router-link to="/backup-tasks" class="text-sm text-primary-600 hover:text-primary-700">
              {{ t('common.all') }}
            </router-link>
          </div>
          <div class="divide-y divide-gray-200">
            <div v-if="recentTasks.length === 0" class="empty-state py-8">
              <p class="text-gray-500">{{ t('common.noData') }}</p>
            </div>
            <div v-for="task in recentTasks" :key="task.id" class="px-6 py-4 hover:bg-gray-50">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div :class="[
                    'w-8 h-8 rounded-lg flex items-center justify-center',
                    task.status === 'completed' ? 'bg-success-100' :
                    task.status === 'running' ? 'bg-primary-100' :
                    task.status === 'failed' ? 'bg-danger-100' : 'bg-gray-100'
                  ]">
                    <svg v-if="task.status === 'completed'" class="w-4 h-4 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                    <svg v-else-if="task.status === 'running'" class="w-4 h-4 text-primary-600 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <svg v-else class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <p class="text-sm font-medium text-gray-900">{{ task.name }}</p>
                    <p class="text-xs text-gray-500">{{ task.task_type }}</p>
                  </div>
                </div>
                <div class="text-right">
                  <p :class="[
                    'badge',
                    task.status === 'completed' ? 'badge-success' :
                    task.status === 'running' ? 'badge-info' :
                    task.status === 'failed' ? 'badge-danger' : 'badge-gray'
                  ]">
                    {{ t(`backupTasks.status.${task.status}`) }}
                  </p>
                  <p class="text-xs text-gray-500 mt-1">
                    {{ new Date(task.created_at).toLocaleString() }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Actions & System Status -->
      <div class="space-y-6">
        <!-- Quick Actions -->
        <div class="card">
          <div class="card-header">
            <h3 class="text-lg font-semibold text-gray-900">{{ t('dashboard.quickActions') }}</h3>
          </div>
          <div class="card-body space-y-3">
            <button class="btn-primary w-full justify-start" @click="router.push('/backup-tasks')">
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              {{ t('dashboard.actions.newBackup') }}
            </button>
            <button class="btn-outline w-full justify-start" @click="router.push('/recovery-tasks')">
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {{ t('dashboard.actions.newRecovery') }}
            </button>
            <button class="btn-outline w-full justify-start" @click="router.push('/nodes')">
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              {{ t('dashboard.actions.viewNodes') }}
            </button>
          </div>
        </div>

        <!-- System Status -->
        <div class="card">
          <div class="card-header">
            <h3 class="text-lg font-semibold text-gray-900">{{ t('dashboard.systemStatus') }}</h3>
          </div>
          <div class="card-body space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600">API</span>
              <span class="badge-success flex items-center gap-1">
                <span class="status-online"></span>
                {{ systemHealth.api }}
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600">Database</span>
              <span class="badge-success flex items-center gap-1">
                <span class="status-online"></span>
                {{ systemHealth.database }}
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600">Storage</span>
              <span class="badge-success flex items-center gap-1">
                <span class="status-online"></span>
                {{ systemHealth.storage }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
