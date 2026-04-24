<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { auditLogApi } from '@/api'

const { t } = useI18n()

const isLoading = ref(true)
const logs = ref<any[]>([])

async function fetchLogs() {
  isLoading.value = true
  try {
    const response = await auditLogApi.list()
    logs.value = response.data.results || []
  } catch (error) {
    console.error('Failed to fetch audit logs:', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">{{ t('auditLog.title') }}</h1>
        <p class="text-gray-500 mt-1">{{ t('auditLog.subtitle') }}</p>
      </div>
      <button class="btn-outline">
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        {{ t('auditLog.actions.export') }}
      </button>
    </div>

    <div class="card overflow-hidden">
      <table class="table">
        <thead>
          <tr>
            <th>{{ t('auditLog.columns.timestamp') }}</th>
            <th>{{ t('auditLog.columns.user') }}</th>
            <th>{{ t('auditLog.columns.action') }}</th>
            <th>{{ t('auditLog.columns.resourceType') }}</th>
            <th>{{ t('auditLog.columns.details') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="isLoading">
            <td colspan="5" class="text-center py-8">
              <div class="spinner-md mx-auto"></div>
            </td>
          </tr>
          <tr v-else-if="logs.length === 0">
            <td colspan="5" class="text-center py-8">
              <p class="text-gray-500">{{ t('common.noData') }}</p>
            </td>
          </tr>
          <tr v-for="log in logs" :key="log.id">
            <td class="text-gray-500">{{ new Date(log.timestamp).toLocaleString() }}</td>
            <td>{{ log.user?.email || 'System' }}</td>
            <td>{{ log.action }}</td>
            <td>{{ log.resource_type }}</td>
            <td class="text-gray-500 truncate max-w-xs">{{ log.details }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
