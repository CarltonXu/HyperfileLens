<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { backupTasksApi, nodesApi, repositoriesApi } from '@/api'
import type { BackupTask, BackupTaskCreateData, BackupTaskStats } from '@/types/backup'
import type { ProxyNode } from '@/types/proxy'
import type { Repository } from '@/types/repository'
import {
  CloudArrowUpIcon,
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
const tasks = ref<BackupTask[]>([])
const stats = ref<BackupTaskStats | null>(null)
const nodes = ref<ProxyNode[]>([])
const repositories = ref<Repository[]>([])
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const selectedTask = ref<BackupTask | null>(null)
const selectedStatus = ref<string>('all')
const searchQuery = ref('')

const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = ref(20)

const newTask = ref<BackupTaskCreateData>({
  name: '',
  node: 0,
  repository: 0,
  source_path: '',
  paths: [],
  backup_type: 'full',
  task_type: 'manual',
  schedule_type: 'once',
  priority: 'normal',
  retention_days: 30,
  compression_enabled: true,
  encryption_enabled: false,
  metadata: {}
})

const taskStats = computed(() => stats.value || {
  total_tasks: 0,
  active_tasks: 0,
  running_tasks: 0,
  completed_tasks: 0,
  failed_tasks: 0,
  total_size_bytes: 0,
  total_files: 0
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

async function fetchTasks() {
  isLoading.value = true
  try {
    const response = await backupTasksApi.list({
      page: currentPage.value,
      page_size: pageSize.value
    })
    tasks.value = response.data.results || response.data
    totalPages.value = Math.ceil((response.data.count || 0) / pageSize.value)
  } catch (error) {
    console.error('Failed to fetch tasks:', error)
  } finally {
    isLoading.value = false
  }
}

async function fetchStats() {
  try {
    const response = await backupTasksApi.stats()
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

async function executeTask(task: BackupTask) {
  try {
    await backupTasksApi.execute(task.id)
    await fetchTasks()
    await fetchStats()
  } catch (error) {
    console.error('Failed to execute task:', error)
  }
}

async function cancelTask(task: BackupTask) {
  try {
    await backupTasksApi.cancel(task.id)
    await fetchTasks()
  } catch (error) {
    console.error('Failed to cancel task:', error)
  }
}

async function createTask() {
  try {
    await backupTasksApi.create(newTask.value)
    showCreateModal.value = false
    newTask.value = {
      name: '',
      node: 0,
      repository: 0,
      source_path: '',
      paths: [],
      backup_type: 'full',
      task_type: 'manual',
      schedule_type: 'once',
      priority: 'normal',
      retention_days: 30,
      compression_enabled: true,
      encryption_enabled: false,
      metadata: {}
    }
    await fetchTasks()
    await fetchStats()
  } catch (error) {
    console.error('Failed to create task:', error)
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
    pending: 'bg-amber-100 text-amber-700',
    queued: 'bg-blue-100 text-blue-700',
    running: 'bg-indigo-100 text-indigo-700',
    paused: 'bg-purple-100 text-purple-700',
    completed: 'bg-emerald-100 text-emerald-700',
    failed: 'bg-red-100 text-red-700',
    cancelled: 'bg-slate-100 text-slate-600'
  }
  return colors[status] || 'bg-slate-100 text-slate-600'
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
        <h1 class="text-2xl font-bold text-slate-800">{{ t('backupTasks.title') }}</h1>
        <p class="text-slate-500 mt-1">{{ t('backupTasks.subtitle') }}</p>
      </div>
      <button
        @click="showCreateModal = true"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t('backupTasks.createTask') }}
      </button>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('common.total') }}</p>
        <p class="text-xl font-bold text-slate-800 mt-1">{{ taskStats.total_tasks }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('backupTasks.status.running') }}</p>
        <p class="text-xl font-bold text-indigo-600 mt-1">{{ taskStats.running_tasks }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('backupTasks.status.completed') }}</p>
        <p class="text-xl font-bold text-emerald-600 mt-1">{{ taskStats.completed_tasks }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('backupTasks.status.failed') }}</p>
        <p class="text-xl font-bold text-red-600 mt-1">{{ taskStats.failed_tasks }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('backupTasks.progress.size') }}</p>
        <p class="text-xl font-bold text-slate-800 mt-1">{{ formatBytes(taskStats.total_size_bytes) }}</p>
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
            class="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <select
          v-model="selectedStatus"
          class="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">{{ t('common.status') }}: {{ t('common.all') }}</option>
          <option value="pending">{{ t('backupTasks.status.pending') }}</option>
          <option value="running">{{ t('backupTasks.status.running') }}</option>
          <option value="completed">{{ t('backupTasks.status.completed') }}</option>
          <option value="failed">{{ t('backupTasks.status.failed') }}</option>
        </select>
        <button
          @click="fetchTasks"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Tasks List -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <div class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
    </div>

    <div v-else-if="filteredTasks.length === 0" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
      <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <CloudArrowUpIcon class="w-8 h-8 text-slate-400" />
      </div>
      <h3 class="text-lg font-medium text-slate-800 mb-1">{{ t('backupTasks.empty.title') }}</h3>
      <p class="text-slate-500">{{ t('backupTasks.empty.description') }}</p>
    </div>

    <div v-else class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <table class="w-full">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('common.name') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('common.type') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('common.status') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('backupTasks.progress.progress') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('common.date') }}</th>
            <th class="text-right text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="task in filteredTasks" :key="task.id" class="hover:bg-slate-50 transition-colors">
            <td class="px-6 py-4">
              <div class="flex items-center gap-3">
                <div :class="[
                  'w-9 h-9 rounded-lg flex items-center justify-center',
                  task.status === 'running' ? 'bg-indigo-100' :
                  task.status === 'completed' ? 'bg-emerald-100' :
                  task.status === 'failed' ? 'bg-red-100' : 'bg-slate-100'
                ]">
                  <CloudArrowUpIcon :class="[
                    'w-5 h-5',
                    task.status === 'running' ? 'text-indigo-600' :
                    task.status === 'completed' ? 'text-emerald-600' :
                    task.status === 'failed' ? 'text-red-600' : 'text-slate-400'
                  ]" />
                </div>
                <div>
                  <p class="text-sm font-medium text-slate-800">{{ task.name }}</p>
                  <p class="text-xs text-slate-500">{{ task.node_name || 'Node' }}</p>
                </div>
              </div>
            </td>
            <td class="px-6 py-4">
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                {{ t(`backupTasks.types.${task.task_type || 'full'}`) }}
              </span>
            </td>
            <td class="px-6 py-4">
              <span :class="['inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium', getStatusColor(task.status)]">
                <component :is="getStatusIcon(task.status)" class="w-3.5 h-3.5" />
                {{ t(`backupTasks.status.${task.status}`) }}
              </span>
            </td>
            <td class="px-6 py-4">
              <div v-if="task.status === 'running' || task.progress_percent" class="w-32">
                <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
                  <span>{{ task.progress_percent || 0 }}%</span>
                </div>
                <div class="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    class="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-300"
                    :style="{ width: `${task.progress_percent || 0}%` }"
                  />
                </div>
              </div>
              <span v-else class="text-sm text-slate-400">-</span>
            </td>
            <td class="px-6 py-4 text-sm text-slate-500">
              {{ task.created_at ? new Date(task.created_at).toLocaleDateString() : '-' }}
            </td>
            <td class="px-6 py-4 text-right">
              <div class="flex items-center justify-end gap-2">
                <button
                  v-if="task.status === 'pending' || task.status === 'failed'"
                  @click="executeTask(task)"
                  class="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                  :title="t('backupTasks.actions.start')"
                >
                  <PlayIcon class="w-4 h-4" />
                </button>
                <button
                  v-if="task.status === 'running'"
                  @click="cancelTask(task)"
                  class="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  :title="t('backupTasks.actions.cancel')"
                >
                  <StopIcon class="w-4 h-4" />
                </button>
                <button
                  @click="selectedTask = task; showDetailModal = true"
                  class="p-1.5 text-slate-500 hover:bg-slate-100 rounded-lg transition-colors"
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
      <div class="flex items-center justify-between px-6 py-3 border-t border-slate-100">
        <p class="text-sm text-slate-500">{{ t('common.total') }}: {{ tasks.length }}</p>
        <div class="flex gap-2">
          <button
            @click="currentPage--; fetchTasks()"
            :disabled="currentPage === 1"
            class="px-3 py-1.5 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t('common.previous') }}
          </button>
          <button
            @click="currentPage++; fetchTasks()"
            :disabled="currentPage >= totalPages"
            class="px-3 py-1.5 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t('common.next') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <Teleport to="body">
      <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showCreateModal = false" />
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
          <div class="sticky top-0 bg-white px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-slate-800">{{ t('backupTasks.createTask') }}</h2>
            <button @click="showCreateModal = false" class="p-1 hover:bg-slate-100 rounded-lg">
              <XCircleIcon class="w-5 h-5 text-slate-400" />
            </button>
          </div>
          <div class="p-6 space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('common.name') }}</label>
              <input v-model="newTask.name" type="text" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('backupTasks.form.sourceNode') }}</label>
                <select v-model="newTask.node" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  <option :value="0">Select</option>
                  <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.name }}</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('backupTasks.form.repository') }}</label>
                <select v-model="newTask.repository" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  <option :value="0">Select</option>
                  <option v-for="repo in repositories" :key="repo.id" :value="repo.id">{{ repo.name }}</option>
                </select>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('backupTasks.form.taskType') }}</label>
              <select v-model="newTask.task_type" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
                <option value="full">{{ t('backupTasks.types.full') }}</option>
                <option value="incremental">{{ t('backupTasks.types.incremental') }}</option>
              </select>
            </div>
          </div>
          <div class="sticky bottom-0 bg-white px-6 py-4 border-t border-slate-100 flex justify-end gap-3">
            <button @click="showCreateModal = false" class="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50">
              {{ t('common.cancel') }}
            </button>
            <button @click="createTask" class="px-4 py-2 text-sm text-white bg-indigo-600 rounded-lg hover:bg-indigo-700">
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
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-lg">
          <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-slate-800">{{ selectedTask.name }}</h2>
            <button @click="showDetailModal = false" class="p-1 hover:bg-slate-100 rounded-lg">
              <XCircleIcon class="w-5 h-5 text-slate-400" />
            </button>
          </div>
          <div class="p-6 space-y-4">
            <div class="flex items-center gap-4">
              <span :class="['inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium', getStatusColor(selectedTask.status)]">
                <component :is="getStatusIcon(selectedTask.status)" class="w-4 h-4" />
                {{ t(`backupTasks.status.${selectedTask.status}`) }}
              </span>
              <span class="text-sm text-slate-500">{{ t(`backupTasks.types.${selectedTask.task_type || 'full'}`) }}</span>
            </div>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div class="bg-slate-50 rounded-lg p-3">
                <p class="text-slate-500">{{ t('backupTasks.form.sourceNode') }}</p>
                <p class="font-medium text-slate-800 mt-1">{{ selectedTask.node_name || 'N/A' }}</p>
              </div>
              <div class="bg-slate-50 rounded-lg p-3">
                <p class="text-slate-500">{{ t('backupTasks.form.repository') }}</p>
                <p class="font-medium text-slate-800 mt-1">{{ selectedTask.repository_name || 'N/A' }}</p>
              </div>
            </div>
            <div v-if="selectedTask.paths?.length" class="bg-slate-50 rounded-lg p-3">
              <p class="text-sm text-slate-500 mb-2">{{ t('backupTasks.form.sourcePaths') }}</p>
              <div class="space-y-1">
                <p v-for="(path, i) in selectedTask.paths" :key="i" class="text-sm font-mono text-slate-700 bg-white px-2 py-1 rounded">{{ path }}</p>
              </div>
            </div>
          </div>
          <div class="px-6 py-4 border-t border-slate-100 flex justify-end">
            <button @click="showDetailModal = false" class="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50">
              {{ t('common.cancel') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
