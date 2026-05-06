<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { gatewaysApi } from '@/api'
import Pagination from '@/components/Pagination.vue'
import {
  ServerIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  CpuChipIcon,
  CircleStackIcon,
  CheckCircleIcon,
  XMarkIcon,
  ClipboardDocumentIcon,
  PlayIcon,
  PauseIcon,
  TrashIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()

// Types
interface Gateway {
  id: string
  name: string
  description: string
  hostname: string
  internal_ip: string
  ssh_port: number
  status: string
  os_version: string
  version: string
  kopia_version: string
  cpu_cores: number
  memory_total: number
  disk_total: number
  cpu_usage: number
  memory_usage: number
  disk_usage: number
  active_mounts: number
  mount_base_path: string
  max_concurrent_mounts: number
  ai_enabled: boolean
  indexer_status: string
  last_index_time: string
  last_heartbeat: string
  is_online: boolean
  tags: Record<string, string>
  labels: string[]
  created_at: string
  updated_at: string
  registered_at: string
  installed_at: string
}

interface GatewayStats {
  total: number
  active: number
  offline: number
  pending: number
  error: number
  total_mounts: number
}

// State
const isLoading = ref(true)
const gateways = ref<Gateway[]>([])
const stats = ref<GatewayStats | null>(null)
const searchQuery = ref('')
const selectedStatus = ref<string>('all')

// Pagination
const currentPage = ref(1)
const pageSize = ref(10)
const totalItems = ref(0)

// Create Modal
const showCreateModal = ref(false)
const isCreating = ref(false)
const newGateway = ref({
  name: '',
  description: '',
  ssh_port: 22,
  mount_base_path: '/mnt/kopia',
  max_concurrent_mounts: 10,
  ai_enabled: true
})

// Detail Drawer
const showDetailDrawer = ref(false)
const selectedGateway = ref<Gateway | null>(null)
const detailTab = ref<'overview' | 'install' | 'mounts'>('overview')
const installCommand = ref('')
const isLoadingCommand = ref(false)
const commandCopied = ref(false)

// Status colors
const statusColors: Record<string, string> = {
  pending: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
  installing: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  inactive: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
  offline: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  error: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  maintenance: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
}

// Computed
const filteredGateways = computed(() => {
  let result = gateways.value
  
  if (selectedStatus.value !== 'all') {
    result = result.filter(g => g.status === selectedStatus.value)
  }
  
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(g => 
      g.name.toLowerCase().includes(query) ||
      g.hostname?.toLowerCase().includes(query) ||
      g.internal_ip?.toLowerCase().includes(query)
    )
  }
  
  return result
})

// Methods
async function fetchGateways() {
  isLoading.value = true
  try {
    const [listRes, statsRes] = await Promise.all([
      gatewaysApi.list({ page: currentPage.value, page_size: pageSize.value }),
      gatewaysApi.stats()
    ])
    gateways.value = listRes.data.results || listRes.data
    totalItems.value = listRes.data.count || gateways.value.length
    stats.value = statsRes.data
  } catch (error) {
    console.error('Failed to fetch gateways:', error)
  } finally {
    isLoading.value = false
  }
}

async function createGateway() {
  if (!newGateway.value.name.trim()) return
  
  isCreating.value = true
  try {
    await gatewaysApi.create(newGateway.value)
    showCreateModal.value = false
    resetNewGateway()
    await fetchGateways()
  } catch (error) {
    console.error('Failed to create gateway:', error)
  } finally {
    isCreating.value = false
  }
}

function resetNewGateway() {
  newGateway.value = {
    name: '',
    description: '',
    ssh_port: 22,
    mount_base_path: '/mnt/kopia',
    max_concurrent_mounts: 10,
    ai_enabled: true
  }
}

async function viewGatewayDetail(gateway: Gateway) {
  selectedGateway.value = gateway
  detailTab.value = 'overview'
  showDetailDrawer.value = true
  installCommand.value = ''
}

async function loadInstallCommand() {
  if (!selectedGateway.value) return
  
  isLoadingCommand.value = true
  try {
    const res = await gatewaysApi.installCommand(selectedGateway.value.id)
    installCommand.value = res.data.install_command
  } catch (error) {
    console.error('Failed to get install command:', error)
  } finally {
    isLoadingCommand.value = false
  }
}

async function copyCommand() {
  if (!installCommand.value) return
  
  try {
    await navigator.clipboard.writeText(installCommand.value)
    commandCopied.value = true
    setTimeout(() => {
      commandCopied.value = false
    }, 2000)
  } catch (error) {
    console.error('Failed to copy:', error)
  }
}

async function activateGateway(gateway: Gateway) {
  try {
    await gatewaysApi.activate(gateway.id)
    await fetchGateways()
    if (selectedGateway.value?.id === gateway.id) {
      selectedGateway.value = { ...selectedGateway.value, status: 'active' }
    }
  } catch (error) {
    console.error('Failed to activate gateway:', error)
  }
}

async function deactivateGateway(gateway: Gateway) {
  try {
    await gatewaysApi.deactivate(gateway.id)
    await fetchGateways()
    if (selectedGateway.value?.id === gateway.id) {
      selectedGateway.value = { ...selectedGateway.value, status: 'inactive' }
    }
  } catch (error) {
    console.error('Failed to deactivate gateway:', error)
  }
}

async function deleteGateway(gateway: Gateway) {
  if (!confirm(t('gateways.confirmDelete'))) return
  
  try {
    await gatewaysApi.delete(gateway.id)
    showDetailDrawer.value = false
    await fetchGateways()
  } catch (error) {
    console.error('Failed to delete gateway:', error)
  }
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: t('gateways.statusPending'),
    installing: t('gateways.statusInstalling'),
    active: t('gateways.statusActive'),
    inactive: t('gateways.statusInactive'),
    offline: t('gateways.statusOffline'),
    error: t('gateways.statusError'),
    maintenance: t('gateways.statusMaintenance')
  }
  return labels[status] || status
}

function formatBytes(bytes: number): string {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

// Watch tab changes
watch(detailTab, (newTab) => {
  if (newTab === 'install' && selectedGateway.value?.status === 'pending') {
    loadInstallCommand()
  }
})

// Lifecycle
onMounted(() => {
  fetchGateways()
})
</script>

<template>
  <div class="p-6">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-800 dark:text-white">{{ t('gateways.title') }}</h1>
        <p class="text-slate-500 dark:text-slate-400 mt-1">{{ t('gateways.subtitle') }}</p>
      </div>
      <button
        @click="showCreateModal = true"
        class="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors"
      >
        <PlusIcon class="w-5 h-5" />
        {{ t('gateways.createGateway') }}
      </button>
    </div>

    <!-- Stats Cards -->
    <div v-if="stats" class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <p class="text-sm text-slate-500 dark:text-slate-400">{{ t('gateways.statsTotal') }}</p>
        <p class="text-2xl font-bold text-slate-800 dark:text-white mt-1">{{ stats.total }}</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <p class="text-sm text-slate-500 dark:text-slate-400">{{ t('gateways.statsActive') }}</p>
        <p class="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{{ stats.active }}</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <p class="text-sm text-slate-500 dark:text-slate-400">{{ t('gateways.statsOffline') }}</p>
        <p class="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">{{ stats.offline }}</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <p class="text-sm text-slate-500 dark:text-slate-400">{{ t('gateways.statsPending') }}</p>
        <p class="text-2xl font-bold text-slate-600 dark:text-slate-400 mt-1">{{ stats.pending }}</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <p class="text-sm text-slate-500 dark:text-slate-400">{{ t('gateways.statsError') }}</p>
        <p class="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">{{ stats.error }}</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <p class="text-sm text-slate-500 dark:text-slate-400">{{ t('gateways.statsMounts') }}</p>
        <p class="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">{{ stats.total_mounts }}</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex items-center gap-4 mb-6">
      <div class="flex-1 relative">
        <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="t('gateways.searchPlaceholder')"
          class="w-full pl-10 pr-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500"
        />
      </div>
      <select
        v-model="selectedStatus"
        class="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
      >
        <option value="all">{{ t('gateways.allStatus') }}</option>
        <option value="active">{{ t('gateways.statusActive') }}</option>
        <option value="offline">{{ t('gateways.statusOffline') }}</option>
        <option value="pending">{{ t('gateways.statusPending') }}</option>
        <option value="error">{{ t('gateways.statusError') }}</option>
      </select>
      <button
        @click="fetchGateways"
        class="p-2 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
      >
        <ArrowPathIcon class="w-5 h-5" />
      </button>
    </div>

    <!-- Gateway List -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <ArrowPathIcon class="w-8 h-8 text-slate-400 animate-spin" />
    </div>

    <div v-else-if="filteredGateways.length === 0" class="text-center py-12">
      <ServerIcon class="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
      <p class="text-slate-500 dark:text-slate-400">{{ t('gateways.noGateways') }}</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="gateway in filteredGateways"
        :key="gateway.id"
        class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 hover:border-violet-300 dark:hover:border-violet-700 cursor-pointer transition-all"
        @click="viewGatewayDetail(gateway)"
      >
        <!-- Header -->
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-3">
            <div :class="['w-10 h-10 rounded-lg flex items-center justify-center', gateway.is_online ? 'bg-emerald-100 dark:bg-emerald-900/30' : 'bg-slate-100 dark:bg-slate-700']">
              <ServerIcon :class="['w-5 h-5', gateway.is_online ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400']" />
            </div>
            <div>
              <h3 class="font-semibold text-slate-800 dark:text-white">{{ gateway.name }}</h3>
              <p class="text-sm text-slate-500 dark:text-slate-400">{{ gateway.hostname || gateway.internal_ip || '-' }}</p>
            </div>
          </div>
          <span :class="['px-2 py-1 text-xs font-medium rounded-full', statusColors[gateway.status]]">
            {{ getStatusLabel(gateway.status) }}
          </span>
        </div>

        <!-- Info -->
        <div class="space-y-2 text-sm">
          <div class="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span>{{ t('gateways.activeMounts') }}</span>
            <span class="font-medium text-slate-700 dark:text-slate-300">{{ gateway.active_mounts }}</span>
          </div>
          <div class="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span>{{ t('gateways.cpuCores') }}</span>
            <span class="font-medium text-slate-700 dark:text-slate-300">{{ gateway.cpu_cores || '-' }}</span>
          </div>
          <div v-if="gateway.kopia_version" class="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span>{{ t('gateways.kopiaVersion') }}</span>
            <span class="font-medium text-slate-700 dark:text-slate-300">{{ gateway.kopia_version }}</span>
          </div>
        </div>

        <!-- AI Status -->
        <div v-if="gateway.ai_enabled" class="mt-4 pt-4 border-t border-slate-100 dark:border-slate-700">
          <div class="flex items-center gap-2 text-sm text-violet-600 dark:text-violet-400">
            <ChatBubbleLeftRightIcon class="w-4 h-4" />
            <span>{{ t('gateways.aiEnabled') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="totalItems > pageSize" class="mt-6">
      <Pagination
        :current-page="currentPage"
        :total-items="totalItems"
        :page-size="pageSize"
        @page-change="currentPage = $event; fetchGateways()"
      />
    </div>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="bg-white dark:bg-slate-800 rounded-xl w-full max-w-lg p-6">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-semibold text-slate-800 dark:text-white">{{ t('gateways.createGateway') }}</h2>
          <button @click="showCreateModal = false" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
            <XMarkIcon class="w-6 h-6" />
          </button>
        </div>

        <form @submit.prevent="createGateway" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {{ t('gateways.gatewayName') }} <span class="text-red-500">*</span>
            </label>
            <input
              v-model="newGateway.name"
              type="text"
              required
              class="w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {{ t('gateways.description') }}
            </label>
            <textarea
              v-model="newGateway.description"
              rows="2"
              class="w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {{ t('gateways.sshPort') }}
              </label>
              <input
                v-model.number="newGateway.ssh_port"
                type="number"
                class="w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {{ t('gateways.maxMounts') }}
              </label>
              <input
                v-model.number="newGateway.max_concurrent_mounts"
                type="number"
                class="w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {{ t('gateways.mountBasePath') }}
            </label>
            <input
              v-model="newGateway.mount_base_path"
              type="text"
              class="w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
          </div>

          <div class="flex items-center gap-2">
            <input
              v-model="newGateway.ai_enabled"
              type="checkbox"
              id="ai_enabled"
              class="w-4 h-4 rounded border-slate-300 text-violet-600 focus:ring-violet-500"
            />
            <label for="ai_enabled" class="text-sm text-slate-700 dark:text-slate-300">
              {{ t('gateways.enableAI') }}
            </label>
          </div>

          <div class="flex justify-end gap-3 pt-4">
            <button
              type="button"
              @click="showCreateModal = false"
              class="px-4 py-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              type="submit"
              :disabled="isCreating || !newGateway.name.trim()"
              class="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ isCreating ? t('common.loading') : t('common.create') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Detail Drawer -->
    <div v-if="showDetailDrawer && selectedGateway" class="fixed inset-0 z-50">
      <div class="absolute inset-0 bg-black/50" @click="showDetailDrawer = false" />
      <div class="absolute right-0 top-0 bottom-0 w-full max-w-2xl bg-white dark:bg-slate-800 shadow-xl overflow-y-auto">
        <!-- Drawer Header -->
        <div class="sticky top-0 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div :class="['w-10 h-10 rounded-lg flex items-center justify-center', selectedGateway.is_online ? 'bg-emerald-100 dark:bg-emerald-900/30' : 'bg-slate-100 dark:bg-slate-700']">
                <ServerIcon :class="['w-5 h-5', selectedGateway.is_online ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400']" />
              </div>
              <div>
                <h2 class="text-lg font-semibold text-slate-800 dark:text-white">{{ selectedGateway.name }}</h2>
                <p class="text-sm text-slate-500 dark:text-slate-400">{{ selectedGateway.hostname || selectedGateway.internal_ip || '-' }}</p>
              </div>
            </div>
            <button @click="showDetailDrawer = false" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
              <XMarkIcon class="w-6 h-6" />
            </button>
          </div>
        </div>

        <!-- Tabs -->
        <div class="border-b border-slate-200 dark:border-slate-700">
          <div class="flex px-6">
            <button
              v-for="tab in (['overview', 'install', 'mounts'] as const)"
              :key="tab"
              @click="detailTab = tab"
              :class="['px-4 py-3 text-sm font-medium border-b-2 -mb-px', detailTab === tab ? 'border-violet-500 text-violet-600 dark:text-violet-400' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300']"
            >
              {{ t(`gateways.tabs.${tab}`) }}
            </button>
          </div>
        </div>

        <!-- Tab Content -->
        <div class="p-6">
          <!-- Overview Tab -->
          <div v-if="detailTab === 'overview'" class="space-y-6">
            <!-- Status -->
            <div class="flex items-center gap-3">
              <span :class="['px-3 py-1 text-sm font-medium rounded-full', statusColors[selectedGateway.status]]">
                {{ getStatusLabel(selectedGateway.status) }}
              </span>
              <span v-if="selectedGateway.is_online" class="text-sm text-emerald-600 dark:text-emerald-400">
                {{ t('gateways.online') }}
              </span>
              <span v-else class="text-sm text-red-600 dark:text-red-400">
                {{ t('gateways.offline') }}
              </span>
            </div>

            <!-- Info Grid -->
            <div class="grid grid-cols-2 gap-4">
              <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                <p class="text-sm text-slate-500 dark:text-slate-400">{{ t('gateways.hostname') }}</p>
                <p class="text-base font-medium text-slate-800 dark:text-white mt-1">{{ selectedGateway.hostname || '-' }}</p>
              </div>
              <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                <p class="text-sm text-slate-500 dark:text-slate-400">{{ t('gateways.internalIp') }}</p>
                <p class="text-base font-medium text-slate-800 dark:text-white mt-1">{{ selectedGateway.internal_ip || '-' }}</p>
              </div>
              <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                <p class="text-sm text-slate-500 dark:text-slate-400">{{ t('gateways.osVersion') }}</p>
                <p class="text-base font-medium text-slate-800 dark:text-white mt-1">{{ selectedGateway.os_version || 'Ubuntu 22.04' }}</p>
              </div>
              <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                <p class="text-sm text-slate-500 dark:text-slate-400">{{ t('gateways.kopiaVersion') }}</p>
                <p class="text-base font-medium text-slate-800 dark:text-white mt-1">{{ selectedGateway.kopia_version || '-' }}</p>
              </div>
            </div>

            <!-- Resources -->
            <div>
              <h3 class="text-sm font-semibold text-slate-800 dark:text-white mb-3">{{ t('gateways.resources') }}</h3>
              <div class="grid grid-cols-3 gap-4">
                <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                  <div class="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
                    <CpuChipIcon class="w-4 h-4" />
                    <span class="text-sm">{{ t('gateways.cpu') }}</span>
                  </div>
                  <p class="text-lg font-semibold text-slate-800 dark:text-white">{{ selectedGateway.cpu_cores || '-' }} {{ t('gateways.cores') }}</p>
                  <p v-if="selectedGateway.cpu_usage" class="text-sm text-slate-500 dark:text-slate-400">{{ selectedGateway.cpu_usage }}% {{ t('gateways.used') }}</p>
                </div>
                <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                  <div class="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
                    <CircleStackIcon class="w-4 h-4" />
                    <span class="text-sm">{{ t('gateways.memory') }}</span>
                  </div>
                  <p class="text-lg font-semibold text-slate-800 dark:text-white">{{ selectedGateway.memory_total ? formatBytes(selectedGateway.memory_total) : '-' }}</p>
                  <p v-if="selectedGateway.memory_usage" class="text-sm text-slate-500 dark:text-slate-400">{{ selectedGateway.memory_usage }}% {{ t('gateways.used') }}</p>
                </div>
                <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                  <div class="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
                    <CircleStackIcon class="w-4 h-4" />
                    <span class="text-sm">{{ t('gateways.disk') }}</span>
                  </div>
                  <p class="text-lg font-semibold text-slate-800 dark:text-white">{{ selectedGateway.disk_total ? formatBytes(selectedGateway.disk_total) : '-' }}</p>
                  <p v-if="selectedGateway.disk_usage" class="text-sm text-slate-500 dark:text-slate-400">{{ selectedGateway.disk_usage }}% {{ t('gateways.used') }}</p>
                </div>
              </div>
            </div>

            <!-- Mount Info -->
            <div>
              <h3 class="text-sm font-semibold text-slate-800 dark:text-white mb-3">{{ t('gateways.mountInfo') }}</h3>
              <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-sm text-slate-500 dark:text-slate-400">{{ t('gateways.activeMounts') }}</span>
                  <span class="font-medium text-slate-800 dark:text-white">{{ selectedGateway.active_mounts }} / {{ selectedGateway.max_concurrent_mounts }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm text-slate-500 dark:text-slate-400">{{ t('gateways.mountBasePath') }}</span>
                  <span class="font-medium text-slate-800 dark:text-white">{{ selectedGateway.mount_base_path }}</span>
                </div>
              </div>
            </div>

            <!-- AI Insights Status -->
            <div v-if="selectedGateway.ai_enabled">
              <h3 class="text-sm font-semibold text-slate-800 dark:text-white mb-3">{{ t('gateways.aiInsights') }}</h3>
              <div class="bg-violet-50 dark:bg-violet-900/20 rounded-lg p-4">
                <div class="flex items-center gap-2 text-violet-600 dark:text-violet-400 mb-2">
                  <ChatBubbleLeftRightIcon class="w-5 h-5" />
                  <span class="font-medium">{{ t('gateways.aiEnabled') }}</span>
                </div>
                <p v-if="selectedGateway.last_index_time" class="text-sm text-slate-500 dark:text-slate-400">
                  {{ t('gateways.lastIndexTime') }}: {{ formatDate(selectedGateway.last_index_time) }}
                </p>
              </div>
            </div>

            <!-- Timestamps -->
            <div class="text-sm text-slate-500 dark:text-slate-400 space-y-1">
              <p>{{ t('gateways.createdAt') }}: {{ formatDate(selectedGateway.created_at) }}</p>
              <p v-if="selectedGateway.registered_at">{{ t('gateways.registeredAt') }}: {{ formatDate(selectedGateway.registered_at) }}</p>
              <p v-if="selectedGateway.last_heartbeat">{{ t('gateways.lastHeartbeat') }}: {{ formatDate(selectedGateway.last_heartbeat) }}</p>
            </div>

            <!-- Actions -->
            <div class="flex items-center gap-2 pt-4 border-t border-slate-200 dark:border-slate-700">
              <button
                v-if="selectedGateway.status !== 'active'"
                @click="activateGateway(selectedGateway)"
                class="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
              >
                <PlayIcon class="w-4 h-4" />
                {{ t('gateways.activate') }}
              </button>
              <button
                v-if="selectedGateway.status === 'active'"
                @click="deactivateGateway(selectedGateway)"
                class="flex items-center gap-2 px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700"
              >
                <PauseIcon class="w-4 h-4" />
                {{ t('gateways.deactivate') }}
              </button>
              <button
                @click="deleteGateway(selectedGateway)"
                class="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                <TrashIcon class="w-4 h-4" />
                {{ t('gateways.delete') }}
              </button>
            </div>
          </div>

          <!-- Install Tab -->
          <div v-if="detailTab === 'install'" class="space-y-6">
            <div v-if="selectedGateway.status === 'pending'" class="space-y-4">
              <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                <p class="text-sm text-blue-700 dark:text-blue-300">
                  {{ t('gateways.installInstructions') }}
                </p>
              </div>

              <div v-if="isLoadingCommand" class="flex items-center justify-center py-8">
                <ArrowPathIcon class="w-6 h-6 text-slate-400 animate-spin" />
              </div>

              <div v-else-if="installCommand" class="space-y-4">
                <div class="flex items-center justify-between">
                  <h3 class="text-sm font-semibold text-slate-800 dark:text-white">{{ t('gateways.installCommand') }}</h3>
                  <button
                    @click="copyCommand"
                    :class="['flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors', commandCopied ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600']"
                  >
                    <ClipboardDocumentIcon class="w-4 h-4" />
                    {{ commandCopied ? t('gateways.copied') : t('gateways.copyCommand') }}
                  </button>
                </div>
                <pre class="bg-slate-900 text-slate-100 p-4 rounded-lg text-sm overflow-x-auto whitespace-pre-wrap">{{ installCommand }}</pre>
              </div>

              <div class="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4">
                <p class="text-sm text-amber-700 dark:text-amber-300">
                  {{ t('gateways.installNote') }}
                </p>
              </div>
            </div>

            <div v-else class="text-center py-12 text-slate-500 dark:text-slate-400">
              <CheckCircleIcon class="w-16 h-16 mx-auto mb-4 text-emerald-500" />
              <p>{{ t('gateways.alreadyInstalled') }}</p>
            </div>
          </div>

          <!-- Mounts Tab -->
          <div v-if="detailTab === 'mounts'" class="space-y-6">
            <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
              <div class="flex items-center justify-between mb-4">
                <span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ t('gateways.mountStatus') }}</span>
                <span class="text-lg font-semibold text-slate-800 dark:text-white">{{ selectedGateway.active_mounts }} / {{ selectedGateway.max_concurrent_mounts }}</span>
              </div>
              <div class="h-2 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden">
                <div 
                  class="h-full bg-violet-500 rounded-full transition-all"
                  :style="{ width: `${(selectedGateway.active_mounts / selectedGateway.max_concurrent_mounts) * 100}%` }"
                />
              </div>
            </div>

            <div class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
              <p class="text-sm text-slate-500 dark:text-slate-400 mb-2">{{ t('gateways.mountBasePath') }}</p>
              <code class="text-sm font-mono text-slate-800 dark:text-white">{{ selectedGateway.mount_base_path }}</code>
            </div>

            <p class="text-sm text-slate-500 dark:text-slate-400 text-center">
              {{ t('gateways.mountDetailsNote') }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
