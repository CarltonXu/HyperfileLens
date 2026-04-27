<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import type { ProxyNode, ProxyStats, ProxyTask } from '@/types/proxy'
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
  WrenchScrewdriverIcon,
  ExclamationTriangleIcon,
  XMarkIcon,
  CpuChipIcon,
  TrashIcon,
  PencilIcon,
  PlayIcon,
  PauseIcon,
  InformationCircleIcon,
  ClipboardDocumentIcon,
  ArrowDownTrayIcon,
  DocumentDuplicateIcon,
  KeyIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()

// State
const isLoading = ref(true)
const proxies = ref<ProxyNode[]>([])
const stats = ref<ProxyStats | null>(null)
const selectedRole = ref<string>('all')
const selectedStatus = ref<string>('all')
const searchQuery = ref('')

// Installation Wizard
const showInstallWizard = ref(false)
const installStep = ref(1) // 1: select role, 2: config, 3: command, 4: waiting
const installData = ref({
  name: '',
  role: 'agent' as 'agent' | 'sync',
  os: 'linux',
  labels: [] as string[],
  newLabel: ''
})
const installResult = ref<{
  proxy_id: string
  name: string
  role: string
  install_token: string
  api_token: string
  install_command: string
  windows_command: string
  config_yaml: string
  expires_at: string
} | null>(null)
const isGeneratingInstall = ref(false)
const commandCopied = ref(false)

// Detail Modal
const showDetailModal = ref(false)
const selectedProxy = ref<ProxyNode | null>(null)
const proxyTasks = ref<ProxyTask[]>([])

// Edit Modal
const showEditModal = ref(false)
const editFormData = ref({
  name: '',
  hostname: '',
  heartbeat_interval: 10,
  tags: {} as Record<string, string>,
  labels: [] as string[]
})

// Delete Confirm
const showDeleteConfirm = ref(false)
const proxyToDelete = ref<ProxyNode | null>(null)

// Dropdown menu
const openMenuId = ref<string | null>(null)

// Polling for status updates
let pollInterval: number | null = null

const filteredProxies = computed(() => {
  let result = proxies.value

  if (selectedRole.value !== 'all') {
    result = result.filter(p => p.role === selectedRole.value)
  }

  if (selectedStatus.value !== 'all') {
    result = result.filter(p => p.status === selectedStatus.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p =>
      p.name.toLowerCase().includes(query) ||
      (p.hostname || '').toLowerCase().includes(query)
    )
  }

  return result
})

async function fetchProxies() {
  isLoading.value = true
  try {
    const [proxiesRes, statsRes] = await Promise.all([
      api.get('/api/v1/proxies/'),
      api.get('/api/v1/proxies/stats/')
    ])
    proxies.value = proxiesRes.data.results || proxiesRes.data || []
    stats.value = statsRes.data
  } catch (error) {
    console.error('Failed to fetch proxies:', error)
  } finally {
    isLoading.value = false
  }
}

async function fetchProxyTasks(proxyId: string) {
  try {
    const res = await api.get(`/api/v1/proxies/${proxyId}/tasks/?limit=10`)
    proxyTasks.value = res.data
  } catch (error) {
    console.error('Failed to fetch proxy tasks:', error)
    proxyTasks.value = []
  }
}

// Installation Wizard Functions
function openInstallWizard() {
  installStep.value = 1
  installData.value = {
    name: '',
    role: 'agent',
    os: 'linux',
    labels: [],
    newLabel: ''
  }
  installResult.value = null
  showInstallWizard.value = true
}

function addLabel() {
  if (installData.value.newLabel && !installData.value.labels.includes(installData.value.newLabel)) {
    installData.value.labels.push(installData.value.newLabel)
    installData.value.newLabel = ''
  }
}

function removeLabel(label: string) {
  installData.value.labels = installData.value.labels.filter(l => l !== label)
}

async function generateInstallCommand() {
  if (!installData.value.name) return

  isGeneratingInstall.value = true
  try {
    const res = await api.post('/api/v1/proxies/generate_install/', {
      name: installData.value.name,
      role: installData.value.role,
      os: installData.value.os,
      labels: installData.value.labels
    })
    installResult.value = res.data
    installStep.value = 3
  } catch (error: any) {
    console.error('Failed to generate install command:', error)
    alert(error.response?.data?.error || 'Failed to generate install command')
  } finally {
    isGeneratingInstall.value = false
  }
}

async function copyCommand(command: string) {
  try {
    await navigator.clipboard.writeText(command)
    commandCopied.value = true
    setTimeout(() => {
      commandCopied.value = false
    }, 2000)
  } catch (error) {
    console.error('Failed to copy:', error)
  }
}

function downloadConfig() {
  if (!installResult.value) return

  const blob = new Blob([installResult.value.config_yaml], { type: 'text/yaml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `hyperfilelens-proxy-${installData.value.name}.yaml`
  a.click()
  URL.revokeObjectURL(url)
}

function getCommandForOS(): string {
  if (!installResult.value) return ''
  return installData.value.os === 'windows'
    ? installResult.value.windows_command
    : installResult.value.install_command
}

// Proxy Actions
function viewProxyDetail(proxy: ProxyNode) {
  selectedProxy.value = proxy
  showDetailModal.value = true
  fetchProxyTasks(proxy.id)
  openMenuId.value = null
}

function editProxy(proxy: ProxyNode) {
  selectedProxy.value = proxy
  editFormData.value = {
    name: proxy.name,
    hostname: proxy.hostname || '',
    heartbeat_interval: proxy.heartbeat_interval,
    tags: proxy.tags || {},
    labels: proxy.labels || []
  }
  showEditModal.value = true
  openMenuId.value = null
}

async function updateProxy() {
  if (!selectedProxy.value) return
  try {
    await api.patch(`/api/v1/proxies/${selectedProxy.value.id}/`, editFormData.value)
    showEditModal.value = false
    await fetchProxies()
  } catch (error) {
    console.error('Failed to update proxy:', error)
  }
}

function confirmDeleteProxy(proxy: ProxyNode) {
  proxyToDelete.value = proxy
  showDeleteConfirm.value = true
  openMenuId.value = null
}

async function deleteProxy() {
  if (!proxyToDelete.value) return
  try {
    await api.delete(`/api/v1/proxies/${proxyToDelete.value.id}/`)
    showDeleteConfirm.value = false
    proxyToDelete.value = null
    await fetchProxies()
  } catch (error) {
    console.error('Failed to delete proxy:', error)
  }
}

async function updateProxyStatus(proxy: ProxyNode, newStatus: string) {
  try {
    await api.post(`/api/v1/proxies/${proxy.id}/set_status/`, { status: newStatus })
    await fetchProxies()
    openMenuId.value = null
  } catch (error) {
    console.error('Failed to update status:', error)
  }
}

async function regenerateToken(proxy: ProxyNode) {
  if (!confirm(t('proxies.actions.regenerateTokenConfirm'))) return
  try {
    await api.post(`/api/v1/proxies/${proxy.id}/regenerate_token/`)
    await fetchProxies()
    openMenuId.value = null
  } catch (error) {
    console.error('Failed to regenerate token:', error)
  }
}

function toggleMenu(proxyId: string) {
  openMenuId.value = openMenuId.value === proxyId ? null : proxyId
}

// Status helpers
function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    active: 'bg-emerald-100 text-emerald-700',
    inactive: 'bg-slate-100 text-slate-600',
    offline: 'bg-slate-100 text-slate-600',
    error: 'bg-red-100 text-red-700',
    maintenance: 'bg-amber-100 text-amber-700',
    pending: 'bg-blue-100 text-blue-700',
    installing: 'bg-indigo-100 text-indigo-700'
  }
  return colors[status] || 'bg-slate-100 text-slate-600'
}

function getStatusIcon(status: string) {
  const icons: Record<string, any> = {
    active: CheckCircleIcon,
    inactive: XCircleIcon,
    offline: XCircleIcon,
    error: XCircleIcon,
    maintenance: WrenchScrewdriverIcon,
    pending: ClockIcon,
    installing: ArrowPathIcon
  }
  return icons[status] || CircleStackIcon
}

function getRoleColor(role: string): string {
  return role === 'agent'
    ? 'bg-indigo-100 text-indigo-700'
    : 'bg-purple-100 text-purple-700'
}

function formatUptime(seconds: number | null): string {
  if (!seconds) return 'N/A'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

function timeSince(date: string | null): string {
  if (!date) return t('common.never')
  const seconds = Math.floor((new Date().getTime() - new Date(date).getTime()) / 1000)
  if (seconds < 60) return t('common.justNow')
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}${t('common.minutesAgo')}`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}${t('common.hoursAgo')}`
  const days = Math.floor(hours / 24)
  return `${days}${t('common.daysAgo')}`
}

// Close menu when clicking outside
function closeMenu() {
  openMenuId.value = null
}

// Role icons
const AgentIcon = ComputerDesktopIcon
const SyncIcon = CircleStackIcon

onMounted(() => {
  fetchProxies()
  document.addEventListener('click', closeMenu)

  // Poll for updates every 30 seconds
  pollInterval = window.setInterval(fetchProxies, 30000)
})

onUnmounted(() => {
  document.removeEventListener('click', closeMenu)
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<template>
  <div class="space-y-6" @click.stop>
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">{{ t('proxies.title') }}</h1>
        <p class="text-slate-500 mt-1">{{ t('proxies.subtitle') }}</p>
      </div>
      <button
        @click="openInstallWizard"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t('proxies.installProxy') }}
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
            <p class="text-xs text-slate-500">{{ t('proxies.stats.total') }}</p>
            <p class="text-xl font-bold text-slate-800">{{ stats?.total_proxies || 0 }}</p>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
            <CheckCircleIcon class="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <p class="text-xs text-slate-500">{{ t('proxies.stats.online') }}</p>
            <p class="text-xl font-bold text-emerald-600">{{ stats?.online_proxies || 0 }}</p>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
            <ComputerDesktopIcon class="w-5 h-5 text-indigo-600" />
          </div>
          <div>
            <p class="text-xs text-slate-500">{{ t('proxies.roles.agent') }}</p>
            <p class="text-xl font-bold text-slate-800">{{ stats?.agent_proxies || 0 }}</p>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
            <CircleStackIcon class="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <p class="text-xs text-slate-500">{{ t('proxies.roles.sync') }}</p>
            <p class="text-xl font-bold text-slate-800">{{ stats?.sync_proxies || 0 }}</p>
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
          v-model="selectedRole"
          class="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">{{ t('common.role') }}: {{ t('common.all') }}</option>
          <option value="agent">{{ t('proxies.roles.agent') }}</option>
          <option value="sync">{{ t('proxies.roles.sync') }}</option>
        </select>
        <select
          v-model="selectedStatus"
          class="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">{{ t('common.status') }}: {{ t('common.all') }}</option>
          <option value="active">{{ t('proxies.status.active') }}</option>
          <option value="pending">{{ t('proxies.status.pending') }}</option>
          <option value="offline">{{ t('proxies.status.offline') }}</option>
          <option value="error">{{ t('proxies.status.error') }}</option>
          <option value="maintenance">{{ t('proxies.status.maintenance') }}</option>
        </select>
        <button
          @click="fetchProxies"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Proxies Grid -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <div class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
    </div>

    <div v-else-if="filteredProxies.length === 0" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
      <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <ServerIcon class="w-8 h-8 text-slate-400" />
      </div>
      <h3 class="text-lg font-medium text-slate-800 mb-1">{{ t('proxies.empty.title') }}</h3>
      <p class="text-slate-500">{{ t('proxies.empty.description') }}</p>
      <button
        @click="openInstallWizard"
        class="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t('proxies.installProxy') }}
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div
        v-for="proxy in filteredProxies"
        :key="proxy.id"
        class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md hover:border-slate-300 transition-all group"
      >
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-3">
            <div :class="[
              'w-11 h-11 rounded-xl flex items-center justify-center',
              proxy.role === 'agent'
                ? 'bg-gradient-to-br from-indigo-500 to-blue-600'
                : 'bg-gradient-to-br from-purple-500 to-violet-600'
            ]">
              <component :is="proxy.role === 'agent' ? AgentIcon : SyncIcon" class="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 class="font-semibold text-slate-800 group-hover:text-indigo-600 transition-colors">{{ proxy.name }}</h3>
              <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium mt-1', getRoleColor(proxy.role)]">
                {{ t(`proxies.roles.${proxy.role}`) }}
              </span>
            </div>
          </div>
          <div class="relative" @click.stop>
            <button
              @click="toggleMenu(proxy.id)"
              class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <EllipsisHorizontalIcon class="w-5 h-5" />
            </button>
            <!-- Dropdown Menu -->
            <div
              v-if="openMenuId === proxy.id"
              class="absolute right-0 top-8 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-50"
            >
              <button
                @click="viewProxyDetail(proxy)"
                class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
              >
                <InformationCircleIcon class="w-4 h-4" />
                {{ t('proxies.actions.viewDetails') }}
              </button>
              <button
                @click="editProxy(proxy)"
                class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
              >
                <PencilIcon class="w-4 h-4" />
                {{ t('proxies.actions.edit') }}
              </button>
              <button
                @click="regenerateToken(proxy)"
                class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
              >
                <ArrowPathIcon class="w-4 h-4" />
                {{ t('proxies.actions.regenerateToken') }}
              </button>
              <hr class="my-1 border-slate-100" />
              <button
                v-if="proxy.status === 'active'"
                @click="updateProxyStatus(proxy, 'maintenance')"
                class="w-full px-4 py-2 text-left text-sm text-amber-600 hover:bg-amber-50 flex items-center gap-2"
              >
                <PauseIcon class="w-4 h-4" />
                {{ t('proxies.actions.setMaintenance') }}
              </button>
              <button
                v-else-if="proxy.status === 'maintenance'"
                @click="updateProxyStatus(proxy, 'active')"
                class="w-full px-4 py-2 text-left text-sm text-emerald-600 hover:bg-emerald-50 flex items-center gap-2"
              >
                <PlayIcon class="w-4 h-4" />
                {{ t('proxies.actions.activate') }}
              </button>
              <hr class="my-1 border-slate-100" />
              <button
                @click="confirmDeleteProxy(proxy)"
                class="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
              >
                <TrashIcon class="w-4 h-4" />
                {{ t('proxies.actions.delete') }}
              </button>
            </div>
          </div>
        </div>

        <div class="space-y-3 text-sm">
          <div class="flex items-center gap-2 text-slate-500">
            <MapPinIcon class="w-4 h-4 flex-shrink-0" />
            <span class="truncate">{{ proxy.hostname || proxy.internal_ip || t('proxies.noConnection') }}</span>
          </div>
          <div class="flex items-center gap-2 text-slate-500">
            <ClockIcon class="w-4 h-4 flex-shrink-0" />
            <span>{{ timeSince(proxy.last_heartbeat) }}</span>
          </div>
          <div class="flex items-center gap-2 text-slate-500">
            <CpuChipIcon class="w-4 h-4 flex-shrink-0" />
            <span>
              {{ proxy.operating_system || 'Unknown' }}
              {{ proxy.cpu_cores ? `(${proxy.cpu_cores} cores)` : '' }}
            </span>
          </div>
        </div>

        <!-- Resource Usage -->
        <div v-if="proxy.cpu_usage !== null" class="mt-4 grid grid-cols-3 gap-2 text-center">
          <div class="bg-slate-50 rounded-lg p-2">
            <p class="text-xs text-slate-500">CPU</p>
            <p class="text-sm font-medium text-slate-800">{{ proxy.cpu_usage?.toFixed(1) }}%</p>
          </div>
          <div class="bg-slate-50 rounded-lg p-2">
            <p class="text-xs text-slate-500">Memory</p>
            <p class="text-sm font-medium text-slate-800">{{ proxy.memory_usage?.toFixed(1) }}%</p>
          </div>
          <div class="bg-slate-50 rounded-lg p-2">
            <p class="text-xs text-slate-500">Disk</p>
            <p class="text-sm font-medium text-slate-800">{{ proxy.disk_usage?.toFixed(1) }}%</p>
          </div>
        </div>

        <div class="flex items-center justify-between mt-4 pt-4 border-t border-slate-100">
          <div class="flex items-center gap-1.5">
            <component
              :is="getStatusIcon(proxy.status)"
              :class="[
                'w-4 h-4',
                proxy.status === 'active' ? 'text-emerald-500' :
                proxy.status === 'error' ? 'text-red-500' : 'text-slate-400'
              ]"
            />
            <span :class="['text-xs font-medium', getStatusColor(proxy.status).split(' ').slice(1).join(' ')]">
              {{ t(`proxies.status.${proxy.status}`) }}
            </span>
          </div>
          <button
            @click="viewProxyDetail(proxy)"
            class="text-sm font-medium text-indigo-600 hover:text-indigo-700"
          >
            {{ t('proxies.actions.viewDetails') }} →
          </button>
        </div>
      </div>
    </div>

    <!-- Install Wizard Modal -->
    <div v-if="showInstallWizard" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div class="bg-white rounded-2xl shadow-xl max-w-2xl w-full my-8">
        <!-- Header -->
        <div class="flex items-center justify-between p-5 border-b border-slate-100">
          <div>
            <h2 class="text-lg font-semibold text-slate-800">{{ t('proxies.install.title') }}</h2>
            <p class="text-sm text-slate-500 mt-1">{{ t('proxies.install.subtitle') }}</p>
          </div>
          <button @click="showInstallWizard = false" class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg">
            <XMarkIcon class="w-5 h-5" />
          </button>
        </div>

        <!-- Steps -->
        <div class="p-5">
          <!-- Step 1: Select Role -->
          <div v-if="installStep === 1" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Agent Proxy -->
              <button
                @click="installData.role = 'agent'; installStep = 2"
                :class="[
                  'p-6 rounded-xl border-2 text-left transition-all',
                  installData.role === 'agent'
                    ? 'border-indigo-500 bg-indigo-50'
                    : 'border-slate-200 hover:border-slate-300'
                ]"
              >
                <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center mb-4">
                  <ComputerDesktopIcon class="w-6 h-6 text-white" />
                </div>
                <h3 class="font-semibold text-slate-800">{{ t('proxies.roles.agent') }}</h3>
                <p class="text-sm text-slate-500 mt-2">{{ t('proxies.install.agentDescription') }}</p>
                
                <!-- Agent Requirements -->
                <div class="mt-4 pt-4 border-t border-slate-200">
                  <p class="text-xs font-medium text-slate-600 mb-2">{{ t('proxies.install.requirements') }}</p>
                  <div class="space-y-1.5 text-xs text-slate-500">
                    <div class="flex items-center gap-2">
                      <ComputerDesktopIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.agentOS') }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <CpuChipIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.agentCPU') }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <CircleStackIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.agentMemory') }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <ServerIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.agentDisk') }}</span>
                    </div>
                  </div>
                </div>
              </button>

              <!-- Sync Proxy -->
              <button
                @click="installData.role = 'sync'; installData.os = 'linux'; installStep = 2"
                :class="[
                  'p-6 rounded-xl border-2 text-left transition-all',
                  installData.role === 'sync'
                    ? 'border-purple-500 bg-purple-50'
                    : 'border-slate-200 hover:border-slate-300'
                ]"
              >
                <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center mb-4">
                  <CircleStackIcon class="w-6 h-6 text-white" />
                </div>
                <h3 class="font-semibold text-slate-800">{{ t('proxies.roles.sync') }}</h3>
                <p class="text-sm text-slate-500 mt-2">{{ t('proxies.install.syncDescription') }}</p>
                
                <!-- Sync Requirements -->
                <div class="mt-4 pt-4 border-t border-slate-200">
                  <p class="text-xs font-medium text-slate-600 mb-2">{{ t('proxies.install.requirements') }}</p>
                  <div class="space-y-1.5 text-xs text-slate-500">
                    <div class="flex items-center gap-2">
                      <ComputerDesktopIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.syncOS') }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <CpuChipIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.syncCPU') }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <CircleStackIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.syncMemory') }}</span>
                    </div>
                    <div class="flex items-center gap-2">
                      <ServerIcon class="w-3.5 h-3.5 text-slate-400" />
                      <span>{{ t('proxies.install.syncDisk') }}</span>
                    </div>
                  </div>
                </div>
              </button>
            </div>
            
            <!-- Info Banner -->
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
              <InformationCircleIcon class="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
              <div class="text-sm text-blue-700">
                <p class="font-medium">{{ t('proxies.install.infoTitle') }}</p>
                <p class="mt-1">{{ t('proxies.install.infoDescription') }}</p>
              </div>
            </div>
          </div>

          <!-- Step 2: Configuration -->
          <div v-if="installStep === 2" class="space-y-5">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">
                {{ t('proxies.install.proxyName') }}
              </label>
              <input
                v-model="installData.name"
                type="text"
                required
                :placeholder="t('proxies.install.namePlaceholder')"
                class="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <!-- OS Selection - Only for Agent Proxy -->
            <div v-if="installData.role === 'agent'">
              <label class="block text-sm font-medium text-slate-700 mb-1">
                {{ t('proxies.install.targetOS') }}
              </label>
              <div class="grid grid-cols-3 gap-3">
                <button
                  v-for="os in ['linux', 'windows', 'macos']"
                  :key="os"
                  @click="installData.os = os"
                  :class="[
                    'px-4 py-3 rounded-lg border-2 text-sm font-medium transition-all',
                    installData.os === os
                      ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  ]"
                >
                  {{ t(`proxies.install.os.${os}`) }}
                </button>
              </div>
            </div>

            <!-- Sync Proxy - Fixed OS Info -->
            <div v-else class="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <ComputerDesktopIcon class="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p class="text-sm font-medium text-purple-800">{{ t('proxies.install.syncFixedOS') }}</p>
                  <p class="text-xs text-purple-600">{{ t('proxies.install.syncFixedOSNote') }}</p>
                </div>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">
                {{ t('proxies.install.labels') }}
              </label>
              <div class="flex gap-2 mb-2">
                <input
                  v-model="installData.newLabel"
                  type="text"
                  :placeholder="t('proxies.install.labelPlaceholder')"
                  class="flex-1 px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  @keyup.enter="addLabel"
                />
                <button
                  @click="addLabel"
                  class="px-4 py-2 text-sm font-medium text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50"
                >
                  {{ t('common.add') }}
                </button>
              </div>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="label in installData.labels"
                  :key="label"
                  class="inline-flex items-center gap-1 px-3 py-1 bg-slate-100 text-slate-600 rounded-full text-sm"
                >
                  {{ label }}
                  <button @click="removeLabel(label)" class="hover:text-red-500">
                    <XMarkIcon class="w-3.5 h-3.5" />
                  </button>
                </span>
              </div>
            </div>

            <div class="flex justify-between pt-4">
              <button
                @click="installStep = 1"
                class="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
              >
                {{ t('common.back') }}
              </button>
              <button
                @click="generateInstallCommand"
                :disabled="!installData.name || isGeneratingInstall"
                class="px-6 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ isGeneratingInstall ? t('proxies.install.generating') : t('proxies.install.generateCommand') }}
              </button>
            </div>
          </div>

          <!-- Step 3: Install Command -->
          <div v-if="installStep === 3 && installResult" class="space-y-5">
            <div class="bg-emerald-50 border border-emerald-200 rounded-lg p-4 flex items-start gap-3">
              <CheckCircleIcon class="w-5 h-5 text-emerald-500 mt-0.5" />
              <div>
                <p class="text-sm font-medium text-emerald-800">{{ t('proxies.install.ready') }}</p>
                <p class="text-sm text-emerald-600 mt-1">{{ t('proxies.install.readyDescription') }}</p>
              </div>
            </div>

            <!-- Installation Instructions -->
            <div class="space-y-4">
              <!-- Step 1: Run Command -->
              <div class="bg-slate-50 rounded-lg p-4">
                <div class="flex items-center gap-2 mb-3">
                  <span class="w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 text-xs font-bold flex items-center justify-center">1</span>
                  <span class="text-sm font-medium text-slate-700">{{ t('proxies.install.step1Title') }}</span>
                </div>
                <p class="text-xs text-slate-500 mb-3">{{ t('proxies.install.step1Desc') }}</p>
                <div class="relative">
                  <pre class="bg-slate-900 text-slate-100 p-4 rounded-lg text-sm overflow-x-auto whitespace-pre-wrap font-mono">{{ getCommandForOS() }}</pre>
                  <div class="absolute top-2 right-2 flex gap-2">
                    <button
                      @click="downloadConfig"
                      class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-700 rounded-lg hover:bg-slate-600"
                    >
                      <ArrowDownTrayIcon class="w-3.5 h-3.5" />
                      {{ t('proxies.install.downloadConfig') }}
                    </button>
                    <button
                      @click="copyCommand(getCommandForOS())"
                      class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500"
                    >
                      <ClipboardDocumentIcon class="w-3.5 h-3.5" />
                      {{ commandCopied ? t('common.copied') : t('common.copy') }}
                    </button>
                  </div>
                </div>
              </div>

              <!-- Step 2: Keep Credentials -->
              <div class="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <div class="flex items-start gap-3">
                  <ExclamationTriangleIcon class="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
                  <div class="flex-1">
                    <p class="text-sm font-medium text-amber-800">{{ t('proxies.install.credentialsTitle') }}</p>
                    <p class="text-xs text-amber-600 mt-1">{{ t('proxies.install.credentialsDesc') }}</p>
                  </div>
                </div>
              </div>

              <!-- Credentials -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-white border border-slate-200 rounded-lg p-4">
                  <div class="flex items-center gap-2 mb-2">
                    <span class="w-6 h-6 rounded-full bg-slate-100 text-slate-600 text-xs font-bold flex items-center justify-center">ID</span>
                    <span class="text-sm font-medium text-slate-700">{{ t('proxies.install.proxyId') }}</span>
                  </div>
                  <p class="text-xs text-slate-500 mb-2">{{ t('proxies.install.proxyIdDesc') }}</p>
                  <div class="flex items-center gap-2 bg-slate-50 rounded px-3 py-2">
                    <p class="text-sm font-mono text-slate-800 flex-1 truncate">{{ installResult.proxy_id }}</p>
                    <button @click="copyCommand(installResult.proxy_id)" class="text-slate-400 hover:text-slate-600">
                      <DocumentDuplicateIcon class="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div class="bg-white border border-slate-200 rounded-lg p-4">
                  <div class="flex items-center gap-2 mb-2">
                    <span class="w-6 h-6 rounded-full bg-slate-100 text-slate-600 text-xs font-bold flex items-center justify-center">
                      <KeyIcon class="w-3.5 h-3.5" />
                    </span>
                    <span class="text-sm font-medium text-slate-700">{{ t('proxies.install.apiToken') }}</span>
                  </div>
                  <p class="text-xs text-slate-500 mb-2">{{ t('proxies.install.apiTokenDesc') }}</p>
                  <div class="flex items-center gap-2 bg-slate-50 rounded px-3 py-2">
                    <p class="text-sm font-mono text-slate-800 flex-1 break-all">{{ installResult.api_token || 'N/A' }}</p>
                    <button @click="copyCommand(installResult.api_token)" class="text-slate-400 hover:text-slate-600 flex-shrink-0">
                      <DocumentDuplicateIcon class="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div class="flex justify-between pt-4">
              <button
                @click="installStep = 2"
                class="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
              >
                {{ t('common.back') }}
              </button>
              <button
                @click="showInstallWizard = false; fetchProxies()"
                class="px-6 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
              >
                {{ t('proxies.install.done') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Proxy Detail Modal -->
    <div v-if="showDetailModal && selectedProxy" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div class="bg-white rounded-2xl shadow-xl max-w-3xl w-full my-8 max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between p-5 border-b border-slate-100 sticky top-0 bg-white z-10">
          <div class="flex items-center gap-3">
            <div :class="[
              'w-10 h-10 rounded-xl flex items-center justify-center',
              selectedProxy.role === 'agent'
                ? 'bg-gradient-to-br from-indigo-500 to-blue-600'
                : 'bg-gradient-to-br from-purple-500 to-violet-600'
            ]">
              <component :is="selectedProxy.role === 'agent' ? AgentIcon : SyncIcon" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 class="text-lg font-semibold text-slate-800">{{ selectedProxy.name }}</h2>
              <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', getRoleColor(selectedProxy.role)]">
                {{ t(`proxies.roles.${selectedProxy.role}`) }}
              </span>
            </div>
          </div>
          <button @click="showDetailModal = false" class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg">
            <XMarkIcon class="w-5 h-5" />
          </button>
        </div>

        <div class="p-5 space-y-6">
          <!-- Status -->
          <div class="flex items-center gap-3">
            <component
              :is="getStatusIcon(selectedProxy.status)"
              :class="[
                'w-5 h-5',
                selectedProxy.status === 'active' ? 'text-emerald-500' :
                selectedProxy.status === 'error' ? 'text-red-500' : 'text-slate-400'
              ]"
            />
            <span :class="['px-3 py-1 rounded-full text-sm font-medium', getStatusColor(selectedProxy.status)]">
              {{ t(`proxies.status.${selectedProxy.status}`) }}
            </span>
            <span v-if="selectedProxy.is_online" class="px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full text-sm font-medium">
              {{ t('proxies.online') }}
            </span>
          </div>

          <!-- Info Grid -->
          <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.hostname') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ selectedProxy.hostname || '-' }}</p>
            </div>
            <div class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.internalIp') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ selectedProxy.internal_ip || '-' }}</p>
            </div>
            <div class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.operatingSystem') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ selectedProxy.operating_system || '-' }}</p>
            </div>
            <div class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.version') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ selectedProxy.version || '-' }}</p>
            </div>
            <div class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.kopiaVersion') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ selectedProxy.kopia_version || '-' }}</p>
            </div>
            <div class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.uptime') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ formatUptime(selectedProxy.uptime_seconds) }}</p>
            </div>
          </div>

          <!-- Resource Usage -->
          <div v-if="selectedProxy.cpu_usage !== null" class="grid grid-cols-3 gap-4">
            <div class="bg-slate-50 rounded-lg p-4 text-center">
              <p class="text-xs text-slate-500 mb-1">CPU</p>
              <p class="text-2xl font-bold text-slate-800">{{ selectedProxy.cpu_usage?.toFixed(1) }}%</p>
              <div class="w-full h-2 bg-slate-200 rounded-full mt-2">
                <div class="h-full bg-indigo-500 rounded-full" :style="{ width: `${selectedProxy.cpu_usage || 0}%` }" />
              </div>
            </div>
            <div class="bg-slate-50 rounded-lg p-4 text-center">
              <p class="text-xs text-slate-500 mb-1">Memory</p>
              <p class="text-2xl font-bold text-slate-800">{{ selectedProxy.memory_usage?.toFixed(1) }}%</p>
              <div class="w-full h-2 bg-slate-200 rounded-full mt-2">
                <div class="h-full bg-emerald-500 rounded-full" :style="{ width: `${selectedProxy.memory_usage || 0}%` }" />
              </div>
            </div>
            <div class="bg-slate-50 rounded-lg p-4 text-center">
              <p class="text-xs text-slate-500 mb-1">Disk</p>
              <p class="text-2xl font-bold text-slate-800">{{ selectedProxy.disk_usage?.toFixed(1) }}%</p>
              <div class="w-full h-2 bg-slate-200 rounded-full mt-2">
                <div class="h-full bg-amber-500 rounded-full" :style="{ width: `${selectedProxy.disk_usage || 0}%` }" />
              </div>
            </div>
          </div>

          <!-- Capabilities -->
          <div v-if="selectedProxy.capabilities && Object.keys(selectedProxy.capabilities).length > 0">
            <h3 class="text-sm font-medium text-slate-700 mb-3">{{ t('proxies.detail.capabilities') }}</h3>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="(value, key) in selectedProxy.capabilities"
                :key="key"
                :class="[
                  'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium',
                  value ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'
                ]"
              >
                {{ key }}
                <CheckCircleIcon v-if="value" class="w-3.5 h-3.5 ml-1" />
              </span>
            </div>
          </div>

          <!-- Recent Tasks -->
          <div v-if="proxyTasks.length > 0">
            <h3 class="text-sm font-medium text-slate-700 mb-3">{{ t('proxies.detail.recentTasks') }}</h3>
            <div class="space-y-2">
              <div
                v-for="task in proxyTasks"
                :key="task.id"
                class="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
              >
                <div class="flex items-center gap-3">
                  <div :class="[
                    'w-8 h-8 rounded-lg flex items-center justify-center',
                    task.status === 'completed' ? 'bg-emerald-100' :
                    task.status === 'failed' ? 'bg-red-100' : 'bg-slate-100'
                  ]">
                    <component
                      :is="task.status === 'completed' ? CheckCircleIcon : task.status === 'failed' ? XCircleIcon : ArrowPathIcon"
                      :class="[
                        'w-4 h-4',
                        task.status === 'completed' ? 'text-emerald-600' :
                        task.status === 'failed' ? 'text-red-600' : 'text-slate-400'
                      ]"
                    />
                  </div>
                  <div>
                    <p class="text-sm font-medium text-slate-800">{{ task.task_type }}</p>
                    <p class="text-xs text-slate-500">{{ new Date(task.created_at).toLocaleString() }}</p>
                  </div>
                </div>
                <div class="text-right">
                  <p class="text-xs text-slate-500">{{ task.progress }}%</p>
                  <p class="text-xs text-slate-400">{{ task.duration_seconds ? `${task.duration_seconds.toFixed(0)}s` : '-' }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <div v-if="showEditModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl max-w-lg w-full">
        <div class="flex items-center justify-between p-5 border-b border-slate-100">
          <h2 class="text-lg font-semibold text-slate-800">{{ t('proxies.edit.title') }}</h2>
          <button @click="showEditModal = false" class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg">
            <XMarkIcon class="w-5 h-5" />
          </button>
        </div>
        <form @submit.prevent="updateProxy" class="p-5 space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('proxies.form.name') }}</label>
            <input
              v-model="editFormData.name"
              type="text"
              required
              class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('proxies.form.hostname') }}</label>
            <input
              v-model="editFormData.hostname"
              type="text"
              class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('proxies.form.heartbeatInterval') }}</label>
            <input
              v-model.number="editFormData.heartbeat_interval"
              type="number"
              min="5"
              max="300"
              class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div class="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              @click="showEditModal = false"
              class="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              type="submit"
              class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
            >
              {{ t('common.save') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete Confirm -->
    <div v-if="showDeleteConfirm && proxyToDelete" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl max-w-md w-full">
        <div class="p-6">
          <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <ExclamationTriangleIcon class="w-6 h-6 text-red-600" />
          </div>
          <h3 class="text-lg font-semibold text-slate-800 text-center mb-2">{{ t('proxies.delete.title') }}</h3>
          <p class="text-sm text-slate-500 text-center">{{ t('proxies.delete.description', { name: proxyToDelete.name }) }}</p>
        </div>
        <div class="flex justify-center gap-3 p-5 border-t border-slate-100">
          <button
            @click="showDeleteConfirm = false; proxyToDelete = null"
            class="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            @click="deleteProxy"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
          >
            {{ t('common.delete') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
