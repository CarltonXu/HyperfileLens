<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import type { Node, NodeStats } from '@/types/node'

const { t } = useI18n()

const isLoading = ref(true)
const nodes = ref<Node[]>([])
const stats = ref<NodeStats | null>(null)
const selectedType = ref<string>('all')
const searchQuery = ref('')

const filteredNodes = computed(() => {
  let result = nodes.value

  if (selectedType.value !== 'all') {
    result = result.filter(n => n.node_type === selectedType.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(n =>
      n.name.toLowerCase().includes(query) ||
      n.hostname.toLowerCase().includes(query)
    )
  }

  return result
})

async function fetchNodes() {
  isLoading.value = true
  try {
    const [nodesRes, statsRes] = await Promise.all([
      api.get('/api/v1/nodes/'),
      api.get('/api/v1/nodes/stats/')
    ])
    nodes.value = nodesRes.data.results || []
    stats.value = statsRes.data
  } catch (error) {
    console.error('Failed to fetch nodes:', error)
  } finally {
    isLoading.value = false
  }
}

function getStatusClass(status: string) {
  switch (status) {
    case 'active': return 'badge-success'
    case 'inactive': return 'badge-gray'
    case 'error': return 'badge-danger'
    case 'maintenance': return 'badge-warning'
    default: return 'badge-gray'
  }
}

function getStatusDot(status: string) {
  switch (status) {
    case 'active': return 'status-online'
    case 'inactive': return 'status-offline'
    case 'error': return 'status-error'
    default: return 'status-offline'
  }
}

onMounted(() => {
  fetchNodes()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">{{ t('nodes.title') }}</h1>
        <p class="text-gray-500 mt-1">{{ t('nodes.subtitle') }}</p>
      </div>
      <button class="btn-primary">
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
        {{ t('nodes.addNode') }}
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="card p-4">
        <p class="text-sm text-gray-500">{{ t('dashboard.stats.totalNodes') }}</p>
        <p class="text-2xl font-bold text-gray-900 mt-1">{{ stats?.total_nodes || 0 }}</p>
      </div>
      <div class="card p-4">
        <p class="text-sm text-gray-500">{{ t('dashboard.stats.onlineNodes') }}</p>
        <p class="text-2xl font-bold text-success-600 mt-1">{{ stats?.online_nodes || 0 }}</p>
      </div>
      <div class="card p-4">
        <p class="text-sm text-gray-500">{{ t('nodes.types.source_proxy') }}</p>
        <p class="text-2xl font-bold text-gray-900 mt-1">{{ stats?.nodes_by_type?.source_proxy || 0 }}</p>
      </div>
      <div class="card p-4">
        <p class="text-sm text-gray-500">{{ t('nodes.types.target_gateway') }}</p>
        <p class="text-2xl font-bold text-gray-900 mt-1">{{ stats?.nodes_by_type?.target_gateway || 0 }}</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex items-center justify-between gap-4">
      <div class="flex items-center gap-4">
        <select v-model="selectedType" class="input w-48">
          <option value="all">{{ t('common.all') }}</option>
          <option value="source_proxy">{{ t('nodes.types.source_proxy') }}</option>
          <option value="target_gateway">{{ t('nodes.types.target_gateway') }}</option>
        </select>
        <div class="relative">
          <input
            v-model="searchQuery"
            type="text"
            class="input pl-10"
            :placeholder="t('common.search')"
          />
          <svg class="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>
      <button class="btn-outline" @click="fetchNodes">
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        {{ t('common.refresh') }}
      </button>
    </div>

    <!-- Nodes Table -->
    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="table">
          <thead>
            <tr>
              <th>{{ t('common.name') }}</th>
              <th>{{ t('common.type') }}</th>
              <th>{{ t('common.status') }}</th>
              <th>{{ t('nodes.details.hostname') }}</th>
              <th>{{ t('nodes.details.lastHeartbeat') }}</th>
              <th>{{ t('common.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="isLoading">
              <td colspan="6" class="text-center py-8">
                <div class="spinner-md mx-auto"></div>
              </td>
            </tr>
            <tr v-else-if="filteredNodes.length === 0">
              <td colspan="6" class="text-center py-8">
                <p class="text-gray-500">{{ t('common.noData') }}</p>
              </td>
            </tr>
            <tr v-for="node in filteredNodes" :key="node.id" class="hover:bg-gray-50">
              <td>
                <div class="flex items-center gap-3">
                  <div :class="['status-dot', getStatusDot(node.status)]"></div>
                  <span class="font-medium">{{ node.name }}</span>
                </div>
              </td>
              <td>
                <span class="badge-info">
                  {{ t(`nodes.types.${node.node_type}`) }}
                </span>
              </td>
              <td>
                <span :class="['badge', getStatusClass(node.status)]">
                  {{ t(`nodes.status.${node.status}`) }}
                </span>
              </td>
              <td>{{ node.hostname }}:{{ node.port }}</td>
              <td>
                {{ node.last_heartbeat ? new Date(node.last_heartbeat).toLocaleString() : '-' }}
              </td>
              <td>
                <router-link :to="`/nodes/${node.node_id}`" class="text-primary-600 hover:text-primary-700">
                  {{ t('nodes.actions.viewDetails') }}
                </router-link>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
