<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import type { Node, NodeStats } from '@/types/node'
import {
  ServerIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  ComputerDesktopIcon,
  CircleStackIcon,
  EllipsisHorizontalIcon,
  MapPinIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  WrenchScrewdriverIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()

const isLoading = ref(true)
const nodes = ref<Node[]>([])
const stats = ref<NodeStats | null>(null)
const selectedType = ref<string>('all')
const selectedStatus = ref<string>('all')
const searchQuery = ref('')

const filteredNodes = computed(() => {
  let result = nodes.value

  if (selectedType.value !== 'all') {
    result = result.filter(n => n.node_type === selectedType.value)
  }

  if (selectedStatus.value !== 'all') {
    result = result.filter(n => n.status === selectedStatus.value)
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

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    active: 'bg-emerald-100 text-emerald-700',
    inactive: 'bg-slate-100 text-slate-600',
    error: 'bg-red-100 text-red-700',
    maintenance: 'bg-amber-100 text-amber-700',
    pending: 'bg-blue-100 text-blue-700'
  }
  return colors[status] || 'bg-slate-100 text-slate-600'
}

function getStatusIcon(status: string) {
  const icons: Record<string, any> = {
    active: CheckCircleIcon,
    inactive: XCircleIcon,
    error: XCircleIcon,
    maintenance: WrenchScrewdriverIcon
  }
  return icons[status] || CircleStackIcon
}

function getTypeColor(type: string): string {
  return type === 'source_proxy'
    ? 'bg-indigo-100 text-indigo-700'
    : 'bg-purple-100 text-purple-700'
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
        <h1 class="text-2xl font-bold text-slate-800">{{ t('nodes.title') }}</h1>
        <p class="text-slate-500 mt-1">{{ t('nodes.subtitle') }}</p>
      </div>
      <button
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t('nodes.addNode') }}
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-gradient-to-br from-slate-100 to-slate-200 rounded-lg flex items-center justify-center">
            <ServerIcon class="w-5 h-5 text-slate-600" />
          </div>
          <div>
            <p class="text-xs text-slate-500">{{ t('dashboard.stats.totalNodes') }}</p>
            <p class="text-xl font-bold text-slate-800">{{ stats?.total_nodes || 0 }}</p>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
            <CheckCircleIcon class="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <p class="text-xs text-slate-500">{{ t('dashboard.stats.onlineNodes') }}</p>
            <p class="text-xl font-bold text-emerald-600">{{ stats?.online_nodes || 0 }}</p>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
            <ComputerDesktopIcon class="w-5 h-5 text-indigo-600" />
          </div>
          <div>
            <p class="text-xs text-slate-500">{{ t('nodes.types.source_proxy') }}</p>
            <p class="text-xl font-bold text-slate-800">{{ stats?.nodes_by_type?.source_proxy || 0 }}</p>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
            <CircleStackIcon class="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <p class="text-xs text-slate-500">{{ t('nodes.types.target_gateway') }}</p>
            <p class="text-xl font-bold text-slate-800">{{ stats?.nodes_by_type?.target_gateway || 0 }}</p>
          </div>
        </div>
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
            class="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>
        <select
          v-model="selectedType"
          class="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">{{ t('common.type') }}: {{ t('common.all') }}</option>
          <option value="source_proxy">{{ t('nodes.types.source_proxy') }}</option>
          <option value="target_gateway">{{ t('nodes.types.target_gateway') }}</option>
        </select>
        <select
          v-model="selectedStatus"
          class="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">{{ t('common.status') }}: {{ t('common.all') }}</option>
          <option value="active">{{ t('nodes.status.active') }}</option>
          <option value="inactive">{{ t('nodes.status.inactive') }}</option>
          <option value="error">{{ t('nodes.status.error') }}</option>
        </select>
        <button
          @click="fetchNodes"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Nodes Grid -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <div class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
    </div>

    <div v-else-if="filteredNodes.length === 0" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
      <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <ServerIcon class="w-8 h-8 text-slate-400" />
      </div>
      <h3 class="text-lg font-medium text-slate-800 mb-1">{{ t('nodes.empty.title') }}</h3>
      <p class="text-slate-500">{{ t('nodes.empty.description') }}</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div
        v-for="node in filteredNodes"
        :key="node.id"
        class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md hover:border-slate-300 transition-all cursor-pointer group"
      >
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-3">
            <div :class="[
              'w-11 h-11 rounded-xl flex items-center justify-center',
              node.status === 'active' ? 'bg-gradient-to-br from-emerald-500 to-teal-600' :
              node.status === 'error' ? 'bg-gradient-to-br from-red-500 to-rose-600' :
              'bg-gradient-to-br from-slate-400 to-slate-500'
            ]">
              <ServerIcon class="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 class="font-semibold text-slate-800 group-hover:text-indigo-600 transition-colors">{{ node.name }}</h3>
              <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium mt-1', getTypeColor(node.node_type)]">
                {{ t(`nodes.types.${node.node_type}`) }}
              </span>
            </div>
          </div>
          <button class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors">
            <EllipsisHorizontalIcon class="w-5 h-5" />
          </button>
        </div>

        <div class="space-y-3 text-sm">
          <div class="flex items-center gap-2 text-slate-500">
            <MapPinIcon class="w-4 h-4 flex-shrink-0" />
            <span class="truncate">{{ node.hostname }}:{{ node.port }}</span>
          </div>
          <div class="flex items-center gap-2 text-slate-500">
            <ClockIcon class="w-4 h-4 flex-shrink-0" />
            <span>{{ node.last_heartbeat ? new Date(node.last_heartbeat).toLocaleString() : '-' }}</span>
          </div>
        </div>

        <div class="flex items-center justify-between mt-4 pt-4 border-t border-slate-100">
          <div class="flex items-center gap-1.5">
            <component
              :is="getStatusIcon(node.status)"
              :class="[
                'w-4 h-4',
                node.status === 'active' ? 'text-emerald-500' :
                node.status === 'error' ? 'text-red-500' : 'text-slate-400'
              ]"
            />
            <span :class="['text-xs font-medium', getStatusColor(node.status).split(' ').slice(1).join(' ')]">
              {{ t(`nodes.status.${node.status}`) }}
            </span>
          </div>
          <router-link
            :to="`/nodes/${node.node_id}`"
            class="text-sm font-medium text-indigo-600 hover:text-indigo-700"
          >
            {{ t('nodes.actions.viewDetails') }} →
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
