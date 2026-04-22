<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'

const { t } = useI18n()

const isLoading = ref(true)
const repositories = ref<any[]>([])

async function fetchRepositories() {
  isLoading.value = true
  try {
    const response = await api.get('/api/v1/repository/')
    repositories.value = response.data.results || []
  } catch (error) {
    console.error('Failed to fetch repositories:', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchRepositories()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">{{ t('repository.title') }}</h1>
        <p class="text-gray-500 mt-1">{{ t('repository.subtitle') }}</p>
      </div>
      <button class="btn-primary">
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
        {{ t('repository.form.addRepository') }}
      </button>
    </div>

    <div class="card overflow-hidden">
      <table class="table">
        <thead>
          <tr>
            <th>{{ t('common.name') }}</th>
            <th>{{ t('repository.form.repositoryType') }}</th>
            <th>{{ t('common.status') }}</th>
            <th>{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="isLoading">
            <td colspan="4" class="text-center py-8">
              <div class="spinner-md mx-auto"></div>
            </td>
          </tr>
          <tr v-else-if="repositories.length === 0">
            <td colspan="4" class="text-center py-8">
              <p class="text-gray-500">{{ t('common.noData') }}</p>
            </td>
          </tr>
          <tr v-for="repo in repositories" :key="repo.id">
            <td class="font-medium">{{ repo.name }}</td>
            <td>{{ repo.type }}</td>
            <td>
              <span class="badge-success">{{ t('common.active') }}</span>
            </td>
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
