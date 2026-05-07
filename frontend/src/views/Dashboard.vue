<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  ServerIcon,
  CheckCircleIcon,
  CircleStackIcon,
  CloudArrowUpIcon,
  ArrowUturnLeftIcon,
  SparklesIcon,
  BoltIcon,
  ArrowRightIcon,
  DocumentIcon,
  PhotoIcon,
  FilmIcon,
  MusicalNoteIcon,
  ArchiveBoxIcon,
  MagnifyingGlassIcon,
  Squares2X2Icon,
  Bars3Icon,
  ArrowPathIcon,
  GlobeAltIcon
} from '@heroicons/vue/24/outline'
import { proxiesApi, gatewaysApi } from '@/api'

const router = useRouter()
const { t } = useI18n()

// View mode
const viewMode = ref<'card' | 'list'>('card')

// Loading states
const isLoading = ref(true)

// Stats
const stats = ref({
  total_nodes: 0,
  online_nodes: 0,
  total_proxies: 0,
  online_proxies: 0,
  total_gateways: 0,
  online_gateways: 0,
  active_tasks: 0,
  running_tasks: 0,
  pending_tasks: 0,
  storage_used: 0,
  storage_total: 1,
  success_rate: 0
})

// Proxies list
const proxies = ref<any[]>([])

// Gateways list
const gateways = ref<any[]>([])

// AI Insights
const lastSyncTime = ref('5分钟前')
const aiInsights = ref([
  { category: 'Documents', count: 1234, percentage: 45, icon: 'document' },
  { category: 'Images', count: 567, percentage: 21, icon: 'image' },
  { category: 'Videos', count: 234, percentage: 9, icon: 'video' },
  { category: 'Music', count: 123, percentage: 5, icon: 'music' },
  { category: 'Archives', count: 567, percentage: 20, icon: 'archive' }
])

// Pagination
const currentPage = ref(1)
const itemsPerPage = 9

// Search
const searchQuery = ref('')
const selectedStatus = ref('')

// Computed
const filteredProxies = computed(() => {
  let result = proxies.value
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p => 
      p.name.toLowerCase().includes(query) ||
      p.hostname?.toLowerCase().includes(query) ||
      p.ip_address?.includes(query)
    )
  }
  if (selectedStatus.value) {
    result = result.filter(p => p.status === selectedStatus.value)
  }
  return result
})

const filteredGateways = computed(() => {
  let result = gateways.value
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(g => 
      g.name.toLowerCase().includes(query) ||
      g.hostname?.toLowerCase().includes(query)
    )
  }
  if (selectedStatus.value) {
    result = result.filter(g => g.status === selectedStatus.value)
  }
  return result
})

const paginatedProxies = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  return filteredProxies.value.slice(start, start + itemsPerPage)
})

const paginatedGateways = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage
  return filteredGateways.value.slice(start, start + itemsPerPage)
})

// Methods
function formatBytes(bytes: number) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function getStatusColor(status: string) {
  const colors: Record<string, string> = {
    online: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    offline: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    maintenance: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    pending: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
  }
  return colors[status] || 'bg-slate-100 text-slate-700'
}

function getRoleColor(role: string) {
  const colors: Record<string, string> = {
    agent: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
    sync: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
  }
  return colors[role] || 'bg-slate-100 text-slate-700'
}

function viewProxyDetail(proxy: any) {
  router.push(`/proxies?id=${proxy.id}`)
}

function viewGatewayDetail(gateway: any) {
  router.push(`/gateways?id=${gateway.id}`)
}

async function fetchDashboardData() {
  isLoading.value = true
  try {
    // Fetch proxies stats
    const proxiesStatsRes = await proxiesApi.stats()
    if (proxiesStatsRes.data) {
      stats.value.total_proxies = proxiesStatsRes.data.total || 0
      stats.value.online_proxies = proxiesStatsRes.data.online || 0
    }
    
    // Fetch proxies list
    const proxiesRes = await proxiesApi.list()
    if (proxiesRes.data?.results) {
      proxies.value = proxiesRes.data.results
    }
    
    // Fetch gateways stats
    const gatewaysStatsRes = await gatewaysApi.stats()
    if (gatewaysStatsRes.data) {
      stats.value.total_gateways = gatewaysStatsRes.data.total || 0
      stats.value.online_gateways = gatewaysStatsRes.data.online || 0
    }
    
    // Fetch gateways list
    const gatewaysRes = await gatewaysApi.list()
    if (gatewaysRes.data?.results) {
      gateways.value = gatewaysRes.data.results
    }
    
    // Update nodes count from proxies + gateways
    stats.value.total_nodes = stats.value.total_proxies + stats.value.total_gateways
    stats.value.online_nodes = stats.value.online_proxies + stats.value.online_gateways
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  } finally {
    isLoading.value = false
  }
}

// Lifecycle
let refreshInterval: number | null = null

onMounted(() => {
  fetchDashboardData()
  refreshInterval = window.setInterval(fetchDashboardData, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800 dark:text-white">{{ t('dashboard.title') }}</h1>
        <p class="text-slate-500 dark:text-slate-400 mt-1">{{ t('dashboard.subtitle') }}</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="fetchDashboardData"
          class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 hover:border-slate-300 dark:hover:border-slate-500 transition-colors shadow-sm"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Stats Cards - Proxies Style -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Total Nodes -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-700 dark:to-slate-600 rounded-lg flex items-center justify-center">
            <ServerIcon class="w-5 h-5 text-slate-600 dark:text-slate-300" />
          </div>
          <div>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('dashboard.stats.totalNodes') }}</p>
            <p class="text-xl font-bold text-slate-800 dark:text-white">{{ stats.total_nodes }}</p>
          </div>
        </div>
      </div>
      
      <!-- Online Nodes -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg flex items-center justify-center">
            <CheckCircleIcon class="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('dashboard.stats.onlineNodes') }}</p>
            <p class="text-xl font-bold text-emerald-600 dark:text-emerald-400">{{ stats.online_nodes }}</p>
          </div>
        </div>
      </div>
      
      <!-- Active Tasks -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-amber-100 dark:bg-amber-900/30 rounded-lg flex items-center justify-center">
            <BoltIcon class="w-5 h-5 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('dashboard.stats.activeTasks') }}</p>
            <p class="text-xl font-bold text-slate-800 dark:text-white">{{ stats.active_tasks }}</p>
          </div>
        </div>
      </div>
      
      <!-- Storage Used -->
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
            <CircleStackIcon class="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('dashboard.stats.storageUsed') }}</p>
            <p class="text-xl font-bold text-slate-800 dark:text-white">{{ formatBytes(stats.storage_used) }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Nodes Section (Proxies + Gateways) -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Filters - Proxies Style -->
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shadow-sm">
          <div class="flex flex-wrap items-center gap-3">
            <div class="relative flex-1 min-w-[200px]">
              <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 dark:text-slate-500" />
              <input
                v-model="searchQuery"
                type="text"
                :placeholder="t('common.search')"
                class="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
            <select
              v-model="selectedStatus"
              class="px-3 py-2 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">{{ t('common.allStatus') }}</option>
              <option value="online">{{ t('common.online') }}</option>
              <option value="offline">{{ t('common.offline') }}</option>
            </select>
            <!-- View Toggle -->
            <div class="flex items-center gap-1 bg-slate-100 dark:bg-slate-700 rounded-lg p-1">
              <button
                @click="viewMode = 'card'"
                :class="[
                  'p-1.5 rounded-md transition-colors',
                  viewMode === 'card' ? 'bg-white dark:bg-slate-600 text-indigo-600 dark:text-indigo-400 shadow-sm' : 'text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:text-slate-300'
                ]"
                :title="t('proxies.viewModes.card')"
              >
                <Squares2X2Icon class="w-4 h-4" />
              </button>
              <button
                @click="viewMode = 'list'"
                :class="[
                  'p-1.5 rounded-md transition-colors',
                  viewMode === 'list' ? 'bg-white dark:bg-slate-600 text-indigo-600 dark:text-indigo-400 shadow-sm' : 'text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:text-slate-300'
                ]"
                :title="t('proxies.viewModes.list')"
              >
                <Bars3Icon class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <!-- Nodes Card View -->
        <template v-if="viewMode === 'card'">
          <div v-if="isLoading" class="flex items-center justify-center py-12">
            <div class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
          </div>

          <div v-else-if="filteredProxies.length === 0 && filteredGateways.length === 0" class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-12 text-center">
            <div class="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
              <ServerIcon class="w-8 h-8 text-slate-400 dark:text-slate-500" />
            </div>
            <h3 class="text-lg font-medium text-slate-800 dark:text-white mb-1">{{ t('dashboard.nodes.empty') }}</h3>
            <p class="text-slate-500 dark:text-slate-400">{{ t('dashboard.nodes.emptyDesc') }}</p>
          </div>

          <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Proxy Cards -->
            <div
              v-for="proxy in paginatedProxies"
              :key="'proxy-' + proxy.id"
              class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600 transition-all group cursor-pointer"
              @click="viewProxyDetail(proxy)"
            >
              <div class="flex items-start justify-between mb-3">
                <div class="flex items-center gap-3">
                  <div :class="[
                    'w-10 h-10 rounded-lg flex items-center justify-center',
                    proxy.role === 'agent'
                      ? 'bg-gradient-to-br from-indigo-500 to-blue-600'
                      : 'bg-gradient-to-br from-purple-500 to-violet-600'
                  ]">
                    <ServerIcon class="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 class="font-semibold text-slate-800 dark:text-white group-hover:text-indigo-600 transition-colors">{{ proxy.name }}</h3>
                    <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', getRoleColor(proxy.role)]">
                      {{ proxy.role === 'agent' ? 'Agent' : 'Sync' }}
                    </span>
                  </div>
                </div>
                <span :class="['inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', getStatusColor(proxy.is_online ? 'online' : 'offline')]">
                  {{ proxy.is_online ? t('common.online') : t('common.offline') }}
                </span>
              </div>
              <div class="space-y-2 text-sm">
                <div class="flex items-center justify-between text-slate-600 dark:text-slate-400">
                  <span>{{ t('proxies.list.hostname') }}</span>
                  <span class="font-medium text-slate-800 dark:text-white">{{ proxy.hostname || '-' }}</span>
                </div>
                <div class="flex items-center justify-between text-slate-600 dark:text-slate-400">
                  <span>{{ t('proxies.list.ip') }}</span>
                  <span class="font-medium text-slate-800 dark:text-white">{{ proxy.ip_address || '-' }}</span>
                </div>
              </div>
            </div>

            <!-- Gateway Cards -->
            <div
              v-for="gateway in paginatedGateways"
              :key="'gateway-' + gateway.id"
              class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600 transition-all group cursor-pointer"
              @click="viewGatewayDetail(gateway)"
            >
              <div class="flex items-start justify-between mb-3">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 bg-gradient-to-br from-teal-500 to-emerald-600 rounded-lg flex items-center justify-center">
                    <GlobeAltIcon class="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 class="font-semibold text-slate-800 dark:text-white group-hover:text-indigo-600 transition-colors">{{ gateway.name }}</h3>
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400">
                      Gateway
                    </span>
                  </div>
                </div>
                <span :class="['inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', getStatusColor(gateway.is_online ? 'online' : 'offline')]">
                  {{ gateway.is_online ? t('common.online') : t('common.offline') }}
                </span>
              </div>
              <div class="space-y-2 text-sm">
                <div class="flex items-center justify-between text-slate-600 dark:text-slate-400">
                  <span>{{ t('gateways.list.hostname') }}</span>
                  <span class="font-medium text-slate-800 dark:text-white">{{ gateway.hostname || '-' }}</span>
                </div>
                <div class="flex items-center justify-between text-slate-600 dark:text-slate-400">
                  <span>{{ t('gateways.list.mounts') }}</span>
                  <span class="font-medium text-slate-800 dark:text-white">{{ gateway.active_mounts || 0 }} / {{ gateway.max_mounts || 10 }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- Nodes List View -->
        <template v-else>
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
            <table class="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
              <thead class="bg-slate-50 dark:bg-slate-900/50">
                <tr>
                  <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">{{ t('common.name') }}</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">{{ t('common.type') }}</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">{{ t('common.status') }}</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">{{ t('proxies.list.hostname') }}</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">{{ t('proxies.list.ip') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-200 dark:divide-slate-700">
                <tr v-for="proxy in paginatedProxies" :key="'proxy-' + proxy.id" class="hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer" @click="viewProxyDetail(proxy)">
                  <td class="px-4 py-3 whitespace-nowrap">
                    <div class="flex items-center gap-2">
                      <div :class="['w-8 h-8 rounded-lg flex items-center justify-center', proxy.role === 'agent' ? 'bg-indigo-100 dark:bg-indigo-900/30' : 'bg-purple-100 dark:bg-purple-900/30']">
                        <ServerIcon :class="['w-4 h-4', proxy.role === 'agent' ? 'text-indigo-600' : 'text-purple-600']" />
                      </div>
                      <span class="font-medium text-slate-800 dark:text-white">{{ proxy.name }}</span>
                    </div>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap">
                    <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', getRoleColor(proxy.role)]">
                      {{ proxy.role === 'agent' ? 'Agent' : 'Sync' }}
                    </span>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap">
                    <span :class="['inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', getStatusColor(proxy.is_online ? 'online' : 'offline')]">
                      {{ proxy.is_online ? t('common.online') : t('common.offline') }}
                    </span>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-600 dark:text-slate-300">{{ proxy.hostname || '-' }}</td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-600 dark:text-slate-300">{{ proxy.ip_address || '-' }}</td>
                </tr>
                <tr v-for="gateway in paginatedGateways" :key="'gateway-' + gateway.id" class="hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer" @click="viewGatewayDetail(gateway)">
                  <td class="px-4 py-3 whitespace-nowrap">
                    <div class="flex items-center gap-2">
                      <div class="w-8 h-8 bg-teal-100 dark:bg-teal-900/30 rounded-lg flex items-center justify-center">
                        <GlobeAltIcon class="w-4 h-4 text-teal-600" />
                      </div>
                      <span class="font-medium text-slate-800 dark:text-white">{{ gateway.name }}</span>
                    </div>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400">
                      Gateway
                    </span>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap">
                    <span :class="['inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', getStatusColor(gateway.is_online ? 'online' : 'offline')]">
                      {{ gateway.is_online ? t('common.online') : t('common.offline') }}
                    </span>
                  </td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-600 dark:text-slate-300">{{ gateway.hostname || '-' }}</td>
                  <td class="px-4 py-3 whitespace-nowrap text-sm text-slate-600 dark:text-slate-300">{{ gateway.ip_address || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- Quick Actions - Proxies Style -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button
            @click="router.push('/backup-tasks')"
            class="flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
          >
            <CloudArrowUpIcon class="w-5 h-5" />
            {{ t('dashboard.actions.newBackup') }}
          </button>
          <button
            @click="router.push('/recovery-tasks')"
            class="flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
          >
            <ArrowUturnLeftIcon class="w-5 h-5 text-slate-500 dark:text-slate-400" />
            {{ t('dashboard.actions.newRecovery') }}
          </button>
          <button
            @click="router.push('/ai-insights')"
            class="flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
          >
            <SparklesIcon class="w-5 h-5 text-purple-500" />
            {{ t('dashboard.actions.aiInsights') }}
          </button>
          <button
            @click="router.push('/gateways')"
            class="flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
          >
            <GlobeAltIcon class="w-5 h-5 text-teal-500" />
            {{ t('dashboard.actions.manageGateways') }}
          </button>
        </div>
      </div>

      <!-- Right Sidebar -->
      <div class="space-y-6">
        <!-- AI Insights Section -->
        <div class="bg-gradient-to-r from-indigo-50 via-purple-50 to-pink-50 dark:from-indigo-950/30 dark:via-purple-950/30 dark:to-pink-950/30 rounded-xl border border-indigo-100 dark:border-indigo-900/50 overflow-hidden">
          <div class="px-5 py-4 flex items-center justify-between border-b border-indigo-100 dark:border-indigo-900/50 bg-white/50 dark:bg-slate-900/30">
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-md">
                <SparklesIcon class="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 class="text-base font-semibold text-slate-800 dark:text-white">{{ t('dashboard.aiInsights.title') }}</h2>
                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('dashboard.aiInsights.syncTime', { time: lastSyncTime }) }}</p>
              </div>
            </div>
          </div>
          
          <div class="p-4 space-y-2 bg-white dark:bg-slate-800">
            <div v-for="item in aiInsights" :key="item.category" class="flex items-center justify-between py-2">
              <div class="flex items-center gap-2">
                <DocumentIcon v-if="item.icon === 'document'" class="w-4 h-4 text-blue-500" />
                <PhotoIcon v-else-if="item.icon === 'image'" class="w-4 h-4 text-green-500" />
                <FilmIcon v-else-if="item.icon === 'video'" class="w-4 h-4 text-purple-500" />
                <MusicalNoteIcon v-else-if="item.icon === 'music'" class="w-4 h-4 text-pink-500" />
                <ArchiveBoxIcon v-else class="w-4 h-4 text-amber-500" />
                <span class="text-sm text-slate-700 dark:text-slate-300">{{ item.category }}</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-slate-800 dark:text-white">{{ item.count.toLocaleString() }}</span>
                <div class="w-16 h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div class="h-full bg-indigo-500 rounded-full" :style="{ width: `${item.percentage}%` }" />
                </div>
              </div>
            </div>
          </div>
          
          <div class="px-4 py-3 bg-white/50 dark:bg-slate-900/30 border-t border-indigo-100 dark:border-indigo-900/50">
            <button
              @click="router.push('/ai-insights')"
              class="w-full flex items-center justify-center gap-1.5 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300"
            >
              {{ t('dashboard.aiInsights.viewDetails') }}
              <ArrowRightIcon class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Compliance & License -->
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
          <div class="px-5 py-4 border-b border-slate-100 dark:border-slate-700">
            <div class="flex items-center gap-2">
              <CheckCircleIcon class="w-5 h-5 text-emerald-500" />
              <h2 class="text-base font-semibold text-slate-800 dark:text-white">{{ t('dashboard.compliance.title') }}</h2>
            </div>
          </div>
          <div class="p-4 space-y-2">
            <div class="flex items-center justify-between px-3 py-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-900/50">
              <span class="text-sm text-slate-600 dark:text-slate-400">{{ t('dashboard.compliance.licenseStatus') }}</span>
              <span class="flex items-center gap-1.5 text-sm font-medium text-emerald-600 dark:text-emerald-400">
                <CheckCircleIcon class="w-4 h-4" />
                {{ t('dashboard.compliance.normal') }}
              </span>
            </div>
            <div class="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-700/50">
              <span class="text-sm text-slate-600 dark:text-slate-400">{{ t('dashboard.compliance.storageQuota') }}</span>
              <span class="text-sm font-medium text-slate-800 dark:text-white">{{ t('dashboard.compliance.quotaRemaining', { amount: '1.2 TB' }) }}</span>
            </div>
            <div class="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-700/50">
              <span class="text-sm text-slate-600 dark:text-slate-400">{{ t('dashboard.compliance.expiryDate') }}</span>
              <span class="text-sm font-medium text-slate-800 dark:text-white">2027-01-01</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
