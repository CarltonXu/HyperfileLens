<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { backupTasksApi, nodesApi, repositoriesApi } from '@/api'
import type { BackupTask, BackupTaskCreateData, BackupTaskStats } from '@/types/backup'
import type { Node } from '@/types/node'
import type { Repository } from '@/types/repository'

const { t } = useI18n()

// State
const isLoading = ref(true)
const tasks = ref<BackupTask[]>([])
const stats = ref<BackupTaskStats | null>(null)
const nodes = ref<Node[]>([])
const repositories = ref<Repository[]>([])
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const selectedTask = ref<BackupTask | null>(null)

// Pagination
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = ref(20)

// Form state
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

// Stats computed
const taskStats = computed(() => stats.value || {
  total_tasks: 0,
  active_tasks: 0,
  running_tasks: 0,
  completed_tasks: 0,
  failed_tasks: 0,
  total_size_bytes: 0,
  total_files: 0
})

// Fetch tasks
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

// Fetch stats
async function fetchStats() {
  try {
    const response = await backupTasksApi.stats()
    stats.value = response.data
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  }
}

// Fetch nodes and repositories for dropdown
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

// Execute backup task
async function executeTask(task: BackupTask) {
  try {
    await backupTasksApi.execute(task.id)
    await fetchTasks()
    await fetchStats()
  } catch (error) {
    console.error('Failed to execute task:', error)
  }
}

// Cancel backup task
async function cancelTask(task: BackupTask) {
  try {
    await backupTasksApi.cancel(task.id)
    await fetchTasks()
  } catch (error) {
    console.error('Failed to cancel task:', error)
  }
}

// Create task
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

// Format bytes
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Get status color
function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    cancelled: 'bg-yellow-100 text-yellow-800'
  }
  return colors[status] || 'bg-gray-100 text-gray-800'
}

// Add path to task
function addPath() {
  if (!newTask.value.paths) {
    newTask.value.paths = []
  }
  newTask.value.paths.push({ path: '' })
}

// Remove path
function removePath(index: number) {
  newTask.value.paths?.splice(index, 1)
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
        <h1 class="text-2xl font-bold text-gray-900">{{ t('backupTasks.title') }}</h1>
        <p class="text-gray-500 mt-1">{{ t('backupTasks.subtitle') }}</p>
      </div>
      <button @click="showCreateModal = true" class="btn-primary">
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
        {{ t('backupTasks.createTask') }}
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="card">
        <div class="text-sm text-gray-500">{{ t('backupTasks.totalTasks') }}</div>
        <div class="text-2xl font-bold">{{ taskStats.total_tasks }}</div>
      </div>
      <div class="card">
        <div class="text-sm text-gray-500">{{ t('backupTasks.runningTasks') }}</div>
        <div class="text-2xl font-bold text-blue-600">{{ taskStats.running_tasks }}</div>
      </div>
      <div class="card">
        <div class="text-sm text-gray-500">{{ t('backupTasks.completedTasks') }}</div>
        <div class="text-2xl font-bold text-green-600">{{ taskStats.completed_tasks }}</div>
      </div>
      <div class="card">
        <div class="text-sm text-gray-500">{{ t('backupTasks.totalSize') }}</div>
        <div class="text-2xl font-bold">{{ formatBytes(taskStats.total_size_bytes) }}</div>
      </div>
    </div>

    <!-- Tasks Table -->
    <div class="card overflow-hidden">
      <table class="table">
        <thead>
          <tr>
            <th>{{ t('common.name') }}</th>
            <th>{{ t('backupTasks.node') }}</th>
            <th>{{ t('backupTasks.type') }}</th>
            <th>{{ t('common.status') }}</th>
            <th>{{ t('backupTasks.progress') }}</th>
            <th>{{ t('backupTasks.lastRun') }}</th>
            <th>{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="isLoading">
            <td colspan="7" class="text-center py-8">
              <div class="spinner-md mx-auto"></div>
            </td>
          </tr>
          <tr v-else-if="tasks.length === 0">
            <td colspan="7" class="text-center py-8">
              <p class="text-gray-500">{{ t('common.noData') }}</p>
            </td>
          </tr>
          <tr v-for="task in tasks" :key="task.id" class="hover:bg-gray-50">
            <td class="font-medium">{{ task.name }}</td>
            <td>{{ task.node_name || task.node }}</td>
            <td>
              <span class="badge-info">{{ (task.task_type || 'MANUAL').toUpperCase() }}</span>
            </td>
            <td>
              <span :class="['badge', getStatusColor(task.status)]">
                {{ t(`backupTasks.status.${task.status}`) }}
              </span>
            </td>
            <td>
              <div v-if="task.status === 'running'" class="w-24">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: `${task.progress_percent || 0}%` }"></div>
                </div>
                <span class="text-xs text-gray-500">{{ task.progress_percent || 0 }}%</span>
              </div>
              <span v-else class="text-gray-500">-</span>
            </td>
            <td>{{ task.last_run_at ? new Date(task.last_run_at).toLocaleString() : '-' }}</td>
            <td>
              <div class="flex items-center gap-2">
                <button
                  v-if="task.status === 'pending' || task.status === 'failed'"
                  @click="executeTask(task)"
                  class="text-green-600 hover:text-green-700 text-sm"
                >
                  {{ t('backupTasks.run') }}
                </button>
                <button
                  v-if="task.status === 'running'"
                  @click="cancelTask(task)"
                  class="text-red-600 hover:text-red-700 text-sm"
                >
                  {{ t('backupTasks.cancel') }}
                </button>
                <button
                  @click="selectedTask = task; showDetailModal = true"
                  class="text-primary-600 hover:text-primary-700 text-sm"
                >
                  {{ t('common.details') }}
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div class="flex items-center justify-between px-4 py-3 border-t">
        <div class="text-sm text-gray-500">
          {{ t('common.page') }} {{ currentPage }} / {{ totalPages }}
        </div>
        <div class="flex gap-2">
          <button
            @click="currentPage--; fetchTasks()"
            :disabled="currentPage === 1"
            class="btn-secondary"
          >
            {{ t('common.previous') }}
          </button>
          <button
            @click="currentPage++; fetchTasks()"
            :disabled="currentPage === totalPages"
            class="btn-secondary"
          >
            {{ t('common.next') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div class="p-6 border-b">
          <h2 class="text-xl font-bold">{{ t('backupTasks.createTask') }}</h2>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700">{{ t('common.name') }}</label>
            <input v-model="newTask.name" type="text" class="input mt-1" placeholder="My Backup Task" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">{{ t('backupTasks.node') }}</label>
              <select v-model="newTask.node" class="input mt-1">
                <option value="0">Select Node</option>
                <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">{{ t('backupTasks.repository') }}</label>
              <select v-model="newTask.repository" class="input mt-1">
                <option value="0">Select Repository</option>
                <option v-for="repo in repositories" :key="repo.id" :value="repo.id">{{ repo.name }}</option>
              </select>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">{{ t('backupTasks.paths') }}</label>
            <div class="space-y-2 mt-1">
              <div v-for="(_, index) in (newTask.paths || [])" :key="index" class="flex gap-2">
                <input v-model="newTask.paths![index].path" type="text" class="input flex-1" placeholder="/path/to/backup" />
                <button @click="removePath(index)" class="btn-secondary text-red-600">X</button>
              </div>
              <button @click="addPath" class="btn-secondary text-sm">+ {{ t('backupTasks.addPath') }}</button>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">{{ t('backupTasks.taskType') }}</label>
              <select v-model="newTask.task_type" class="input mt-1">
                <option value="full">{{ t('backupTasks.full') }}</option>
                <option value="incremental">{{ t('backupTasks.incremental') }}</option>
                <option value="differential">{{ t('backupTasks.differential') }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">{{ t('backupTasks.schedule') }}</label>
              <select v-model="newTask.schedule_type" class="input mt-1">
                <option value="manual">{{ t('backupTasks.manual') }}</option>
                <option value="scheduled">{{ t('backupTasks.scheduled') }}</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">{{ t('backupTasks.retention') }}</label>
              <input v-model.number="newTask.retention_days" type="number" class="input mt-1" min="1" />
            </div>
          </div>
          <div class="flex gap-4">
            <label class="flex items-center">
              <input v-model="newTask.compression_enabled" type="checkbox" class="mr-2" />
              {{ t('backupTasks.compression') }}
            </label>
            <label class="flex items-center">
              <input v-model="newTask.encryption_enabled" type="checkbox" class="mr-2" />
              {{ t('backupTasks.encryption') }}
            </label>
          </div>
        </div>
        <div class="p-6 border-t flex justify-end gap-3">
          <button @click="showCreateModal = false" class="btn-secondary">
            {{ t('common.cancel') }}
          </button>
          <button @click="createTask" class="btn-primary">
            {{ t('common.create') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Detail Modal -->
    <div v-if="showDetailModal && selectedTask" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl">
        <div class="p-6 border-b">
          <h2 class="text-xl font-bold">{{ selectedTask.name }}</h2>
        </div>
        <div class="p-6 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <div class="text-sm text-gray-500">{{ t('common.status') }}</div>
              <div :class="['badge mt-1', getStatusColor(selectedTask.status)]">
                {{ t(`backupTasks.status.${selectedTask.status}`) }}
              </div>
            </div>
            <div>
              <div class="text-sm text-gray-500">{{ t('backupTasks.taskType') }}</div>
              <div class="mt-1">{{ (selectedTask.task_type || 'MANUAL').toUpperCase() }}</div>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <div class="text-sm text-gray-500">{{ t('backupTasks.node') }}</div>
              <div class="mt-1">{{ selectedTask.node_name || selectedTask.node }}</div>
            </div>
            <div>
              <div class="text-sm text-gray-500">{{ t('backupTasks.repository') }}</div>
              <div class="mt-1">{{ selectedTask.repository_name || selectedTask.repository }}</div>
            </div>
          </div>
          <div v-if="selectedTask.paths && selectedTask.paths.length > 0">
            <div class="text-sm text-gray-500">{{ t('backupTasks.paths') }}</div>
            <div class="mt-1 space-y-1">
              <div v-for="(path, index) in selectedTask.paths" :key="index" class="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                {{ path }}
              </div>
            </div>
          </div>
          <div v-if="selectedTask.error_message" class="p-4 bg-red-50 rounded-lg">
            <div class="text-sm font-medium text-red-800">{{ t('backupTasks.error') }}</div>
            <div class="text-sm text-red-600 mt-1">{{ selectedTask.error_message }}</div>
          </div>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div class="text-gray-500">{{ t('backupTasks.createdAt') }}</div>
              <div>{{ new Date(selectedTask.created_at).toLocaleString() }}</div>
            </div>
            <div>
              <div class="text-gray-500">{{ t('backupTasks.lastRun') }}</div>
              <div>{{ selectedTask.last_run_at ? new Date(selectedTask.last_run_at).toLocaleString() : '-' }}</div>
            </div>
          </div>
        </div>
        <div class="p-6 border-t flex justify-end">
          <button @click="showDetailModal = false" class="btn-secondary">
            {{ t('common.close') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
