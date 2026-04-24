<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { recoveryTasksApi, backupTasksApi, nodesApi, repositoriesApi } from '@/api'
import type { RecoveryTask, RecoveryTaskCreateData, RecoveryTaskStats, SnapshotInfo } from '@/types/recovery'
import type { Node } from '@/types/backup'
import type { Repository } from '@/types/repository'

const { t } = useI18n()

// State
const isLoading = ref(true)
const tasks = ref<RecoveryTask[]>([])
const stats = ref<RecoveryTaskStats | null>(null)
const nodes = ref<Node[]>([])
const repositories = ref<Repository[]>([])
const snapshots = ref<SnapshotInfo[]>([])
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const selectedTask = ref<RecoveryTask | null>(null)

// Pagination
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = ref(20)

// Form state
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

// Stats computed
const recoveryStats = computed(() => stats.value || {
  total_tasks: 0,
  pending_tasks: 0,
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
    const response = await recoveryTasksApi.list({
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
    const response = await recoveryTasksApi.stats()
    stats.value = response.data
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  }
}

// Fetch nodes and repositories
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

// Fetch snapshots when repository selected
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

// Execute recovery task
async function executeRecovery(task: RecoveryTask) {
  try {
    await recoveryTasksApi.execute(task.id)
    await fetchTasks()
    await fetchStats()
  } catch (error) {
    console.error('Failed to execute recovery:', error)
  }
}

// Cancel recovery task
async function cancelRecovery(task: RecoveryTask) {
  try {
    await recoveryTasksApi.cancel(task.id)
    await fetchTasks()
  } catch (error) {
    console.error('Failed to cancel recovery:', error)
  }
}

// Create recovery task
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
        <h1 class="text-2xl font-bold text-gray-900">{{ t('recoveryTasks.title') }}</h1>
        <p class="text-gray-500 mt-1">{{ t('recoveryTasks.subtitle') }}</p>
      </div>
      <button @click="showCreateModal = true" class="btn-primary">
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
        {{ t('recoveryTasks.newRecovery') }}
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="card">
        <div class="text-sm text-gray-500">{{ t('recoveryTasks.totalTasks') }}</div>
        <div class="text-2xl font-bold">{{ recoveryStats.total_tasks }}</div>
      </div>
      <div class="card">
        <div class="text-sm text-gray-500">{{ t('recoveryTasks.pendingTasks') }}</div>
        <div class="text-2xl font-bold text-yellow-600">{{ recoveryStats.pending_tasks }}</div>
      </div>
      <div class="card">
        <div class="text-sm text-gray-500">{{ t('recoveryTasks.completedTasks') }}</div>
        <div class="text-2xl font-bold text-green-600">{{ recoveryStats.completed_tasks }}</div>
      </div>
      <div class="card">
        <div class="text-sm text-gray-500">{{ t('recoveryTasks.failedTasks') }}</div>
        <div class="text-2xl font-bold text-red-600">{{ recoveryStats.failed_tasks }}</div>
      </div>
    </div>

    <!-- Recovery Tasks Table -->
    <div class="card overflow-hidden">
      <table class="table">
        <thead>
          <tr>
            <th>{{ t('common.name') }}</th>
            <th>{{ t('recoveryTasks.snapshot') }}</th>
            <th>{{ t('recoveryTasks.type') }}</th>
            <th>{{ t('common.status') }}</th>
            <th>{{ t('recoveryTasks.progress') }}</th>
            <th>{{ t('recoveryTasks.createdAt') }}</th>
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
            <td class="font-mono text-sm">{{ task.snapshot_id.substring(0, 12) }}...</td>
            <td>
              <span :class="[
                'badge',
                task.recovery_type === 'original_location' ? 'badge-info' : 'badge-warning'
              ]">
                {{ t(`recoveryTasks.types.${task.recovery_type}`) }}
              </span>
            </td>
            <td>
              <span :class="['badge', getStatusColor(task.status)]">
                {{ t(`recoveryTasks.status.${task.status}`) }}
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
            <td>{{ new Date(task.created_at).toLocaleString() }}</td>
            <td>
              <div class="flex items-center gap-2">
                <button
                  v-if="task.status === 'pending'"
                  @click="executeRecovery(task)"
                  class="text-green-600 hover:text-green-700 text-sm"
                >
                  {{ t('recoveryTasks.start') }}
                </button>
                <button
                  v-if="task.status === 'running'"
                  @click="cancelRecovery(task)"
                  class="text-red-600 hover:text-red-700 text-sm"
                >
                  {{ t('recoveryTasks.cancel') }}
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
          <h2 class="text-xl font-bold">{{ t('recoveryTasks.newRecovery') }}</h2>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700">{{ t('common.name') }}</label>
            <input v-model="newRecovery.name" type="text" class="input mt-1" placeholder="My Recovery Task" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">{{ t('recoveryTasks.node') }}</label>
              <select v-model="newRecovery.node" class="input mt-1">
                <option value="0">Select Node</option>
                <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">{{ t('recoveryTasks.repository') }}</label>
              <select v-model="newRecovery.repository" @change="fetchSnapshots" class="input mt-1">
                <option value="0">Select Repository</option>
                <option v-for="repo in repositories" :key="repo.id" :value="repo.id">{{ repo.name }}</option>
              </select>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">{{ t('recoveryTasks.snapshot') }}</label>
            <select v-model="newRecovery.snapshot_id" class="input mt-1">
              <option value="">Select Snapshot</option>
              <option v-for="snap in snapshots" :key="snap.id" :value="snap.id">
                {{ snap.id.substring(0, 12) }}... - {{ snap.source_path }} ({{ new Date(snap.snapshot_time).toLocaleDateString() }})
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">{{ t('recoveryTasks.type') }}</label>
            <select v-model="newRecovery.recovery_type" class="input mt-1">
              <option value="original_location">{{ t('recoveryTasks.originalLocation') }}</option>
              <option value="new_location">{{ t('recoveryTasks.newLocation') }}</option>
            </select>
          </div>
          <div v-if="newRecovery.recovery_type === 'new_location'">
            <label class="block text-sm font-medium text-gray-700">{{ t('recoveryTasks.targetPath') }}</label>
            <input v-model="newRecovery.target_path" type="text" class="input mt-1" placeholder="/path/to/recover" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">{{ t('recoveryTasks.priority') }}</label>
            <select v-model="newRecovery.priority" class="input mt-1">
              <option value="low">{{ t('recoveryTasks.priorityLow') }}</option>
              <option value="normal">{{ t('recoveryTasks.priorityNormal') }}</option>
              <option value="high">{{ t('recoveryTasks.priorityHigh') }}</option>
              <option value="critical">{{ t('recoveryTasks.priorityCritical') }}</option>
            </select>
          </div>
        </div>
        <div class="p-6 border-t flex justify-end gap-3">
          <button @click="showCreateModal = false" class="btn-secondary">
            {{ t('common.cancel') }}
          </button>
          <button @click="createRecovery" class="btn-primary">
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
                {{ t(`recoveryTasks.status.${selectedTask.status}`) }}
              </div>
            </div>
            <div>
              <div class="text-sm text-gray-500">{{ t('recoveryTasks.type') }}</div>
              <div class="mt-1">{{ t(`recoveryTasks.types.${selectedTask.recovery_type}`) }}</div>
            </div>
          </div>
          <div>
            <div class="text-sm text-gray-500">{{ t('recoveryTasks.snapshot') }}</div>
            <div class="mt-1 font-mono text-sm">{{ selectedTask.snapshot_id }}</div>
          </div>
          <div>
            <div class="text-sm text-gray-500">{{ t('recoveryTasks.targetPath') }}</div>
            <div class="mt-1 font-mono text-sm">{{ selectedTask.target_path || '-' }}</div>
          </div>
          <div v-if="selectedTask.error_message" class="p-4 bg-red-50 rounded-lg">
            <div class="text-sm font-medium text-red-800">{{ t('recoveryTasks.error') }}</div>
            <div class="text-sm text-red-600 mt-1">{{ selectedTask.error_message }}</div>
          </div>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div class="text-gray-500">{{ t('recoveryTasks.createdAt') }}</div>
              <div>{{ new Date(selectedTask.created_at).toLocaleString() }}</div>
            </div>
            <div>
              <div class="text-gray-500">{{ t('recoveryTasks.completedAt') }}</div>
              <div>{{ selectedTask.completed_at ? new Date(selectedTask.completed_at).toLocaleString() : '-' }}</div>
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
