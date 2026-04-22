<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'

const { t } = useI18n()

const isLoading = ref(true)
const tasks = ref<any[]>([])

async function fetchTasks() {
  isLoading.value = true
  try {
    const response = await api.get('/api/v1/recovery-tasks/')
    tasks.value = response.data.results || []
  } catch (error) {
    console.error('Failed to fetch tasks:', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchTasks()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">{{ t('recoveryTasks.title') }}</h1>
        <p class="text-gray-500 mt-1">{{ t('recoveryTasks.subtitle') }}</p>
      </div>
      <button class="btn-primary">
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
        {{ t('dashboard.actions.newRecovery') }}
      </button>
    </div>

    <div class="card overflow-hidden">
      <table class="table">
        <thead>
          <tr>
            <th>{{ t('common.name') }}</th>
            <th>{{ t('common.type') }}</th>
            <th>{{ t('common.status') }}</th>
            <th>{{ t('common.date') }}</th>
            <th>{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="isLoading">
            <td colspan="5" class="text-center py-8">
              <div class="spinner-md mx-auto"></div>
            </td>
          </tr>
          <tr v-else-if="tasks.length === 0">
            <td colspan="5" class="text-center py-8">
              <p class="text-gray-500">{{ t('common.noData') }}</p>
            </td>
          </tr>
          <tr v-for="task in tasks" :key="task.id">
            <td class="font-medium">{{ task.name }}</td>
            <td>
              <span class="badge-info">{{ t(`recoveryTasks.types.${task.recovery_type}`) }}</span>
            </td>
            <td>
              <span :class="[
                'badge',
                task.status === 'completed' ? 'badge-success' :
                task.status === 'running' ? 'badge-info' :
                task.status === 'failed' ? 'badge-danger' : 'badge-gray'
              ]">
                {{ t(`backupTasks.status.${task.status}`) }}
              </span>
            </td>
            <td>{{ new Date(task.created_at).toLocaleString() }}</td>
            <td>
              <button class="text-primary-600 hover:text-primary-700">
                {{ t('common.details') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
