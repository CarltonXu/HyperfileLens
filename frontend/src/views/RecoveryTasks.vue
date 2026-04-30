<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { recoveryTasksApi, backupTasksApi, nodesApi, repositoriesApi } from '@/api'
import type { RecoveryTask, RecoveryTaskCreateData, RecoveryTaskStatsBackend, SnapshotInfo } from '@/types/recovery'
import type { ProxyNode } from '@/types/proxy'
import type { Repository } from '@/types/repository'
import Pagination from '@/components/Pagination.vue'
import {
  ArrowDownTrayIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  PlayIcon,
  StopIcon,
  EyeIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  BoltIcon,
  PauseIcon,
  XCircleIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()

const isLoading = ref(true)
const tasks = ref<RecoveryTask[]>([])
const stats = ref<RecoveryTaskStatsBackend | null>(null)
const nodes = ref<ProxyNode[]>([])
const repositories = ref<Repository[]>([])
const snapshots = ref<SnapshotInfo[]>([])
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const selectedTask = ref<RecoveryTask | null>(null)
const selectedStatus = ref<string>('all')
const searchQuery = ref('')

// Pagination
const currentPage = ref(1)
const pageSize = ref(10)

const newRecovery = ref<RecoveryTaskCreateData>({
  name: '',
  node: 0,
  repository: 0,
  snapshot_id: '',
  recovery_type: 'original_location',
  target_path: '',
  priority: 'normal',
  metadata: {}
})

const recoveryStats = computed(() => {
  if (!stats.value) {
    return {
      total_tasks: 0,
      pending_tasks: 0,
      running_tasks: 0,
      completed_tasks: 0,
      failed_tasks: 0,
      total_files: 0,
      total_size_bytes: 0
    }
  }
  return {
    total_tasks: stats.value.total || 0,
    pending_tasks: stats.value.pending || 0,
    running_tasks: stats.value.running || 0,
    completed_tasks: stats.value.completed || 0,
    failed_tasks: stats.value.failed || 0,
    total_files: stats.value.total_files || 0,
    total_size_bytes: stats.value.total_size || 0
  }
})

const filteredTasks = computed(() => {
  let result = tasks.value
  if (selectedStatus.value !== 'all') {
    result = result.filter(t => t.status === selectedStatus.value)
  }
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(t => t.name.toLowerCase().includes(query))
  }
  return result
})

// Paginated tasks for display
const paginatedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredTasks.value.slice(start, end)
})

// Reset page when filters change
watch([selectedStatus, searchQuery], () => {
  currentPage.value = 1
})

async function fetchTasks() {
  isLoading.value = true
  try {
    const response = await recoveryTasksApi.list()
    tasks.value = response.data.results || response.data
  } catch (error) {
    console.error('Failed to fetch tasks:', error)
  } finally {
    isLoading.value = false
  }
}

async function fetchStats() {
  try {
    const response = await recoveryTasksApi.stats()
    stats.value = response.data
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  }
}

async function fetchNodesAndRepos() {
  try {
    const [nodesRes, reposRes] = await Promise.all([
      nodesApi.list({ page_size: 100 }),
      repositoriesApi.list({ page_size: 100 })
    ])
    nodes.value = nodesRes.data.results || nodesRes.data
    repositories.value = reposRes.data.results || reposRes.data
  } catch (error) {
    console.error('Failed to fetch nodes/repos:', error)
  }
}

async function fetchSnapshots() {
  if (!newRecovery.value.repository) return
  try {
    const response = await backupTasksApi.listSnapshots({
      repository: newRecovery.value.repository,
      page_size: 50
    })
    snapshots.value = response.data.results || response.data
  } catch (error) {
    console.error('Failed to fetch snapshots:', error)
  }
}

watch(() => newRecovery.value.repository, fetchSnapshots)

async function executeRecovery(task: RecoveryTask) {
  try {
    await recoveryTasksApi.execute(task.id)
    await fetchTasks()
    await fetchStats()
  } catch (error) {
    console.error('Failed to execute recovery:', error)
  }
}

async function cancelRecovery(task: RecoveryTask) {
  try {
    await recoveryTasksApi.cancel(task.id)
    await fetchTasks()
  } catch (error) {
    console.error('Failed to cancel recovery:', error)
  }
}

async function createRecovery() {
  try {
    await recoveryTasksApi.create(newRecovery.value)
    showCreateModal.value = false
    newRecovery.value = {
      name: '',
      node: 0,
      repository: 0,
      snapshot_id: '',
      recovery_type: 'original_location',
      target_path: '',
      priority: 'normal',
      metadata: {}
    }
    await fetchTasks()
    await fetchStats()
  } catch (error) {
    console.error('Failed to create recovery:', error)
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
    queued: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    running: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400',
    paused: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
    completed: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
    failed: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
    cancelled: 'bg-slate-100 dark:bg-slate-700 text-slate-600'
  }
  return colors[status] || 'bg-slate-100 dark:bg-slate-700 text-slate-600'
}

function getStatusIcon(status: string) {
  const icons: Record<string, any> = {
    pending: ClockIcon,
    running: BoltIcon,
    completed: CheckCircleIcon,
    failed: ExclamationTriangleIcon,
    paused: PauseIcon,
    cancelled: XCircleIcon
  }
  return icons[status] || ClockIcon
}

onMounted(() => {
  fetchTasks()
  fetchStats()
  fetchNodesAndRepos()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800 dark:text-white">{{ t('recoveryTasks.title') }}</h1>
        <p class="text-slate-500 mt-1">{{ t('recoveryTasks.subtitle') }}</p>
      </div>
      <button
        @click="showCreateModal = true"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-emerald-500 to-teal-600 rounded-lg hover:from-emerald-600 hover:to-teal-700 transition-all shadow-md hover:shadow-lg"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t('recoveryTasks.createTask') }}
      </button>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
        <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('common.total') }}</p>
        <p class="text-xl font-bold text-slate-800 dark:text-white mt-1">{{ recoveryStats.total_tasks }}</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
        <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('recoveryTasks.status.running') }}</p>
        <p class="text-xl font-bold text-indigo-600 mt-1">{{ recoveryStats.running_tasks }}</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
        <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('recoveryTasks.status.completed') }}</p>
        <p class="text-xl font-bold text-emerald-600 mt-1">{{ recoveryStats.completed_tasks }}</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
        <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('recoveryTasks.status.failed') }}</p>
        <p class="text-xl font-bold text-red-600 mt-1">{{ recoveryStats.failed_tasks }}</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
        <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('recoveryTasks.progress.files') }}</p>
        <p class="text-xl font-bold text-slate-800 dark:text-white mt-1">{{ recoveryStats.total_files }}</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
      <div class="flex flex-wrap items-center gap-3">
        <div class="relative flex-1 min-w-[200px]">
          <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('common.search')"
            class="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>
        <select
          v-model="selectedStatus"
          class="px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          <option class="bg-white dark:bg-slate-700" value="all">{{ t('common.status') }}: {{ t('common.all') }}</option>
          <option class="bg-white dark:bg-slate-700" value="pending">{{ t('recoveryTasks.status.pending') }}</option>
          <option class="bg-white dark:bg-slate-700" value="running">{{ t('recoveryTasks.status.running') }}</option>
          <option class="bg-white dark:bg-slate-700" value="completed">{{ t('recoveryTasks.status.completed') }}</option>
          <option class="bg-white dark:bg-slate-700" value="failed">{{ t('recoveryTasks.status.failed') }}</option>
        </select>
        <button
          @click="fetchTasks"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm text-slate-600 dark:text-slate-300 dark:text-slate-300 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Tasks List -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <div class="w-8 h-8 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin" />
    </div>

    <div v-else-if="filteredTasks.length === 0" class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-12 text-center">
      <div class="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
        <ArrowDownTrayIcon class="w-8 h-8 text-slate-400" />
      </div>
      <h3 class="text-lg font-medium text-slate-800 mb-1">{{ t('recoveryTasks.empty.title') }}</h3>
      <p class="text-slate-500 dark:text-slate-400">{{ t('recoveryTasks.empty.description') }}</p>
    </div>

    <div v-else class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
      <table class="w-full">
        <thead class="bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-700 dark:border-slate-700">
          <tr>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('common.name') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('recoveryTasks.form.type') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('common.status') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('recoveryTasks.progress.progress') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('common.date') }}</th>
            <th class="text-right text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 dark:divide-slate-700 dark:divide-slate-700">
          <tr v-for="task in paginatedTasks" :key="task.id" class="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
            <td class="px-6 py-4">
              <div class="flex items-center gap-3">
                <div :class="[
                  'w-9 h-9 rounded-lg flex items-center justify-center',
                  task.status === 'running' ? 'bg-emerald-100' :
                  task.status === 'completed' ? 'bg-emerald-100' :
                  task.status === 'failed' ? 'bg-red-100' : 'bg-slate-100'
                ]">
                  <ArrowDownTrayIcon :class="[
                    'w-5 h-5',
                    task.status === 'running' ? 'text-emerald-600' :
                    task.status === 'completed' ? 'text-emerald-600' :
                    task.status === 'failed' ? 'text-red-600' : 'text-slate-400'
                  ]" />
                </div>
                <div>
                  <p class="text-sm font-medium text-slate-800 dark:text-white">{{ task.name }}</p>
                  <p class="text-xs text-slate-500 dark:text-slate-400">{{ task.target_node_name || 'Node' }}</p>
                </div>
              </div>
            </td>
            <td class="px-6 py-4">
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200">
                {{ t(`recoveryTasks.types.${task.recovery_type || 'original_location'}`) }}
              </span>
            </td>
            <td class="px-6 py-4">
              <span :class="['inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium', getStatusColor(task.status)]">
                <component :is="getStatusIcon(task.status)" class="w-3.5 h-3.5" />
                {{ t(`recoveryTasks.status.${task.status}`) }}
              </span>
            </td>
            <td class="px-6 py-4">
              <div v-if="task.status === 'running' || task.progress" class="w-32">
                <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span>{{ task.progress || 0 }}%</span>
                </div>
                <div class="h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    class="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-300"
                    :style="{ width: `${task.progress || 0}%` }"
                  />
                </div>
              </div>
              <span v-else class="text-sm text-slate-400">-</span>
            </td>
            <td class="px-6 py-4 text-sm text-slate-500 dark:text-slate-400 dark:text-slate-400">
              {{ task.created_at ? new Date(task.created_at).toLocaleDateString() : '-' }}
            </td>
            <td class="px-6 py-4 text-right">
              <div class="flex items-center justify-end gap-2">
                <button
                  v-if="task.status === 'pending' || task.status === 'failed'"
                  @click="executeRecovery(task)"
                  class="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                  :title="t('recoveryTasks.actions.start')"
                >
                  <PlayIcon class="w-4 h-4" />
                </button>
                <button
                  v-if="task.status === 'running'"
                  @click="cancelRecovery(task)"
                  class="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  :title="t('recoveryTasks.actions.cancel')"
                >
                  <StopIcon class="w-4 h-4" />
                </button>
                <button
                  @click="selectedTask = task; showDetailModal = true"
                  class="p-1.5 text-slate-500 hover:bg-slate-100 dark:bg-slate-700 rounded-lg transition-colors"
                  :title="t('common.details')"
                >
                  <EyeIcon class="w-4 h-4" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <Pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total-items="filteredTasks.length"
      />
    </div>

    <!-- Create Modal -->
    <Teleport to="body">
      <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showCreateModal = false" />
        <div class="relative bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
          <div class="sticky top-0 bg-white dark:bg-slate-800 px-6 py-4 border-b border-slate-100 dark:border-slate-700 dark:border-slate-700 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-slate-800 dark:text-white dark:text-white">{{ t('recoveryTasks.createTask') }}</h2>
            <button @click="showCreateModal = false" class="p-1 hover:bg-slate-100 dark:bg-slate-700 rounded-lg">
              <XCircleIcon class="w-5 h-5 text-slate-400" />
            </button>
          </div>
          <div class="p-6 space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('common.name') }}</label>
              <input v-model="newRecovery.name" type="text" class="w-full px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500" />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('recoveryTasks.form.targetNode') }}</label>
                <select v-model="newRecovery.node" class="w-full px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500">
                  <option class="bg-white dark:bg-slate-700" :value="0">Select</option>
                  <option class="bg-white dark:bg-slate-700" v-for="node in nodes" :key="node.id" :value="node.id">{{ node.name }}</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('recoveryTasks.form.repository') }}</label>
                <select v-model="newRecovery.repository" class="w-full px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500">
                  <option class="bg-white dark:bg-slate-700" :value="0">Select</option>
                  <option class="bg-white dark:bg-slate-700" v-for="repo in repositories" :key="repo.id" :value="repo.id">{{ repo.name }}</option>
                </select>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('recoveryTasks.form.snapshot') }}</label>
              <select v-model="newRecovery.snapshot_id" class="w-full px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500">
                <option class="bg-white dark:bg-slate-700" value="">Select Snapshot</option>
                <option class="bg-white dark:bg-slate-700" v-for="snap in snapshots" :key="snap.id" :value="snap.id">{{ snap.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('recoveryTasks.form.type') }}</label>
              <select v-model="newRecovery.recovery_type" class="w-full px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500">
                <option class="bg-white dark:bg-slate-700" value="original_location">{{ t('recoveryTasks.types.original_location') }}</option>
                <option class="bg-white dark:bg-slate-700" value="new_location">{{ t('recoveryTasks.types.new_location') }}</option>
              </select>
            </div>
            <div v-if="newRecovery.recovery_type === 'new_location'">
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 dark:text-slate-300 mb-1">{{ t('recoveryTasks.form.targetPath') }}</label>
              <input v-model="newRecovery.target_path" type="text" class="w-full px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500" />
            </div>
          </div>
          <div class="sticky bottom-0 bg-white dark:bg-slate-800 px-6 py-4 border-t border-slate-100 dark:border-slate-700 dark:border-slate-700 flex justify-end gap-3">
            <button @click="showCreateModal = false" class="px-4 py-2 text-sm text-slate-600 dark:text-slate-300 dark:text-slate-300 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700">
              {{ t('common.cancel') }}
            </button>
            <button @click="createRecovery" class="px-4 py-2 text-sm text-white bg-emerald-600 rounded-lg hover:bg-emerald-700">
              {{ t('common.create') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Detail Modal -->
    <Teleport to="body">
      <div v-if="showDetailModal && selectedTask" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showDetailModal = false" />
        <div class="relative bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-lg">
          <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-slate-800 dark:text-white dark:text-white">{{ selectedTask.name }}</h2>
            <button @click="showDetailModal = false" class="p-1 hover:bg-slate-100 dark:bg-slate-700 rounded-lg">
              <XCircleIcon class="w-5 h-5 text-slate-400" />
            </button>
          </div>
          <div class="p-6 space-y-4">
            <div class="flex items-center gap-4">
              <span :class="['inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium', getStatusColor(selectedTask.status)]">
                <component :is="getStatusIcon(selectedTask.status)" class="w-4 h-4" />
                {{ t(`recoveryTasks.status.${selectedTask.status}`) }}
              </span>
              <span class="text-sm text-slate-500 dark:text-slate-400 dark:text-slate-400">{{ t(`recoveryTasks.types.${selectedTask.recovery_type || 'original_location'}`) }}</span>
            </div>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div class="bg-slate-50 rounded-lg p-3">
                <p class="text-slate-500 dark:text-slate-400">{{ t('recoveryTasks.form.targetNode') }}</p>
                <p class="font-medium text-slate-800 mt-1">{{ selectedTask.target_node_name || 'N/A' }}</p>
              </div>
              <div class="bg-slate-50 rounded-lg p-3">
                <p class="text-slate-500 dark:text-slate-400">{{ t('recoveryTasks.form.targetPath') }}</p>
                <p class="font-medium text-slate-800 mt-1 font-mono text-xs">{{ selectedTask.target_path || 'Original Location' }}</p>
              </div>
            </div>
            <div v-if="selectedTask.file_patterns?.length" class="bg-slate-50 rounded-lg p-3">
              <p class="text-sm text-slate-500 dark:text-slate-400 mb-2">{{ t('recoveryTasks.form.filePatterns') }}</p>
              <div class="flex flex-wrap gap-1">
                <span v-for="(pattern, i) in selectedTask.file_patterns" :key="i" class="px-2 py-0.5 bg-white text-xs text-slate-600 rounded border border-slate-200 dark:border-slate-700">
                  {{ pattern }}
                </span>
              </div>
            </div>
            <div v-if="selectedTask.progress" class="bg-slate-50 rounded-lg p-3">
              <div class="flex justify-between text-sm mb-2">
                <span class="text-slate-500 dark:text-slate-400">{{ t('recoveryTasks.progress.progress') }}</span>
                <span class="font-medium text-slate-800 dark:text-white">{{ selectedTask.progress }}%</span>
              </div>
              <div class="h-2 bg-slate-200 rounded-full overflow-hidden">
                <div
                  class="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full"
                  :style="{ width: `${selectedTask.progress}%` }"
                />
              </div>
              <div class="flex justify-between text-xs text-slate-500 mt-2">
                <span>{{ selectedTask.restored_files || 0 }} / {{ selectedTask.total_files || 0 }} {{ t('recoveryTasks.progress.files') }}</span>
                <span>{{ formatBytes(selectedTask.restored_size || 0) }}</span>
              </div>
            </div>
          </div>
          <div class="px-6 py-4 border-t border-slate-100 dark:border-slate-700 flex justify-end">
            <button @click="showDetailModal = false" class="px-4 py-2 text-sm text-slate-600 dark:text-slate-300 dark:text-slate-300 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700">
              {{ t('common.cancel') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
