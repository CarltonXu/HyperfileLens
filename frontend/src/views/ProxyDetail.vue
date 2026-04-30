<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import type { ProxyNode, ProxyTask, ProxyHeartbeat } from '@/types/proxy'
import {
  ArrowLeftIcon,
  ComputerDesktopIcon,
  CircleStackIcon,
  CheckCircleIcon,
  XCircleIcon,
  WrenchScrewdriverIcon,
  ClockIcon,
  ServerIcon,
  ArrowPathIcon,
  PlayIcon,
  PauseIcon,
  TrashIcon,
  ClipboardDocumentIcon,
  KeyIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  CpuChipIcon,
  CircleStackIcon as DatabaseIcon,
  GlobeAltIcon,
  IdentificationIcon,
  TagIcon,
  DocumentTextIcon
} from '@heroicons/vue/24/outline'

const { t, te } = useI18n()
const route = useRoute()
const router = useRouter()

// Safe translation helper
const safeT = (key: string, fallback: string): string => {
  return te(key) ? t(key) : fallback
}

const proxyId = computed(() => route.params.id as string)
const proxy = ref<ProxyNode | null>(null)
const tasks = ref<ProxyTask[]>([])
const heartbeats = ref<ProxyHeartbeat[]>([])
const isLoading = ref(true)
const activeTab = ref<'overview' | 'install' | 'monitoring' | 'tasks' | 'heartbeats'>('overview')

// Install info for pending proxies
const installInfo = ref<{
  install_command: string
  api_token: string
  install_token: string
} | null>(null)

// Task statistics
const taskStats = computed(() => {
  const stats = { total: 0, completed: 0, failed: 0, running: 0 }
  tasks.value.forEach(task => {
    stats.total++
    if (task.status === 'completed') stats.completed++
    else if (task.status === 'failed') stats.failed++
    else if (task.status === 'running') stats.running++
  })
  return stats
})

// Heartbeat statistics
const heartbeatStats = computed(() => {
  if (heartbeats.value.length === 0) return { avgCpu: 0, avgMemory: 0, avgDisk: 0 }
  const total = heartbeats.value.length
  const sum = heartbeats.value.reduce((acc, hb) => ({
    cpu: acc.cpu + (hb.cpu_usage || 0),
    memory: acc.memory + (hb.memory_usage || 0),
    disk: acc.disk + (hb.disk_usage || 0)
  }), { cpu: 0, memory: 0, disk: 0 })
  return {
    avgCpu: sum.cpu / total,
    avgMemory: sum.memory / total,
    avgDisk: sum.disk / total
  }
})

// Polling
let pollInterval: number | null = null

async function fetchProxy() {
  try {
    const res = await api.get(`/api/v1/proxies/${proxyId.value}/`)
    proxy.value = res.data
    // If pending, show install tab by default
    if (proxy.value?.status === 'pending') {
      activeTab.value = 'install'
    }
  } catch (error) {
    console.error('Failed to fetch proxy:', error)
  }
}

async function fetchTasks() {
  try {
    const res = await api.get(`/api/v1/proxies/${proxyId.value}/tasks/?limit=50`)
    tasks.value = res.data.results || res.data
  } catch (error) {
    console.error('Failed to fetch tasks:', error)
  }
}

async function fetchHeartbeats() {
  try {
    const res = await api.get(`/api/v1/proxies/${proxyId.value}/heartbeats/?hours=24`)
    heartbeats.value = res.data.results || res.data
  } catch (error) {
    console.error('Failed to fetch heartbeats:', error)
  }
}

async function updateStatus(newStatus: string) {
  try {
    await api.post(`/api/v1/proxies/${proxyId.value}/set_status/`, { status: newStatus })
    await fetchProxy()
  } catch (error) {
    console.error('Failed to update status:', error)
  }
}

async function regenerateToken() {
  if (!confirm(t('proxies.actions.regenerateTokenConfirm'))) return
  try {
    const res = await api.post(`/api/v1/proxies/${proxyId.value}/regenerate_token/`)
    // Update install info from response
    installInfo.value = {
      install_command: res.data.install_command,
      api_token: res.data.api_token,
      install_token: res.data.install_token
    }
    await fetchProxy()
    // Switch to install tab to show new info
    activeTab.value = 'install'
  } catch (error) {
    console.error('Failed to regenerate token:', error)
  }
}

async function deleteProxy() {
  if (!confirm(t('proxies.delete.confirm'))) return
  try {
    await api.delete(`/api/v1/proxies/${proxyId.value}/`)
    router.push('/proxies')
  } catch (error) {
    console.error('Failed to delete proxy:', error)
  }
}

async function copyToClipboard(text: string, label: string) {
  try {
    await navigator.clipboard.writeText(text)
    alert(`${label} copied!`)
  } catch (error) {
    console.error('Failed to copy:', error)
  }
}

function getStatusIcon(status: string) {
  const icons: Record<string, any> = {
    active: CheckCircleIcon,
    inactive: XCircleIcon,
    offline: XCircleIcon,
    error: XCircleIcon,
    maintenance: WrenchScrewdriverIcon,
    pending: ClockIcon
  }
  return icons[status] || ServerIcon
}

function getRoleColor(role: string): string {
  return role === 'agent'
    ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400'
    : 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400'
}

function formatBytes(bytes: number | null): string {
  if (!bytes) return 'N/A'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

async function fetchData() {
  isLoading.value = true
  try {
    await Promise.all([fetchProxy(), fetchTasks(), fetchHeartbeats()])
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchData()
  pollInterval = window.setInterval(fetchProxy, 30000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <button
          @click="router.push('/proxies')"
          class="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:bg-slate-700 rounded-lg transition-colors"
        >
          <ArrowLeftIcon class="w-5 h-5" />
        </button>
        <div v-if="proxy">
          <div class="flex items-center gap-3">
            <div :class="[
              'w-12 h-12 rounded-xl flex items-center justify-center',
              proxy.role === 'agent'
                ? 'bg-gradient-to-br from-indigo-500 to-blue-600'
                : 'bg-gradient-to-br from-purple-500 to-violet-600'
            ]">
              <component :is="proxy.role === 'agent' ? ComputerDesktopIcon : CircleStackIcon" class="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 class="text-2xl font-bold text-slate-800 dark:text-white">{{ proxy.name }}</h1>
              <div class="flex items-center gap-2 mt-1">
                <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', getRoleColor(proxy.role)]">
                  {{ safeT(`proxies.roles.${proxy.role}`, proxy.role) }}
                </span>
                <span :class="[
                  'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
                  proxy.status === 'active' ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' :
                  proxy.status === 'error' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400' :
                  proxy.status === 'pending' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400' :
                  'bg-slate-100 dark:bg-slate-700 text-slate-600'
                ]">
                  {{ safeT(`proxies.status.${proxy.status}`, proxy.status) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="proxy" class="flex items-center gap-2">
        <button
          v-if="proxy.status === 'active'"
          @click="updateStatus('maintenance')"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-amber-600 dark:text-amber-400 border border-amber-200 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-900/30"
        >
          <PauseIcon class="w-4 h-4" />
          {{ t('proxies.actions.setMaintenance') }}
        </button>
        <button
          v-else-if="proxy.status === 'maintenance'"
          @click="updateStatus('active')"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-emerald-600 dark:text-emerald-400 border border-emerald-200 rounded-lg hover:bg-emerald-50 dark:hover:bg-emerald-900/30"
        >
          <PlayIcon class="w-4 h-4" />
          {{ t('proxies.actions.activate') }}
        </button>
        <button
          @click="regenerateToken"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 dark:bg-slate-700/50"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t('proxies.actions.regenerateToken') }}
        </button>
        <button
          @click="deleteProxy"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400 border border-red-200 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/30"
        >
          <TrashIcon class="w-4 h-4" />
          {{ t('proxies.actions.delete') }}
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <div class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
    </div>

    <template v-else-if="proxy">
      <!-- Status Banner -->
      <div :class="[
        'rounded-xl border p-4 flex items-center gap-4',
        proxy.status === 'active' ? 'bg-emerald-50 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800' :
        proxy.status === 'error' ? 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800' :
        proxy.status === 'pending' ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800' :
        proxy.status === 'maintenance' ? 'bg-amber-50 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800' :
        'bg-slate-50 border-slate-200'
      ]">
        <component
          :is="getStatusIcon(proxy.status)"
          :class="[
            'w-6 h-6',
            proxy.status === 'active' ? 'text-emerald-500' :
            proxy.status === 'error' ? 'text-red-500' :
            proxy.status === 'pending' ? 'text-blue-500' : 'text-amber-500'
          ]"
        />
        <div class="flex-1">
          <p class="font-medium" :class="proxy.status === 'active' ? 'text-emerald-800 dark:text-emerald-200' : proxy.status === 'error' ? 'text-red-800 dark:text-red-200' : proxy.status === 'pending' ? 'text-blue-800 dark:text-blue-200' : 'text-amber-800 dark:text-amber-200'">
            {{ safeT(`proxies.status.${proxy.status}`, proxy.status) }}
            <span v-if="proxy.status === 'pending'">- {{ t('proxies.detail.pendingHint') }}</span>
          </p>
          <p class="text-sm" :class="proxy.status === 'active' ? 'text-emerald-600 dark:text-emerald-400' : proxy.status === 'error' ? 'text-red-600 dark:text-red-400' : proxy.status === 'pending' ? 'text-blue-600 dark:text-blue-400' : 'text-amber-600 dark:text-amber-400'">
            {{ proxy.is_online ? t('proxies.detail.currentlyOnline') : t('proxies.detail.currentlyOffline') }}
          </p>
        </div>
        <div class="text-right">
          <p class="text-sm text-slate-500 dark:text-slate-400">{{ t('proxies.detail.uptime') }}</p>
          <p class="font-medium text-slate-800 dark:text-white">{{ formatUptime(proxy.uptime_seconds) }}</p>
        </div>
      </div>

      <!-- Tabs -->
      <div class="border-b border-slate-200 dark:border-slate-700">
        <nav class="flex gap-8">
          <!-- Install tab - only show for pending status -->
          <button
            v-if="proxy.status === 'pending'"
            @click="activeTab = 'install'"
            :class="[
              'py-3 px-1 text-sm font-medium border-b-2 transition-colors',
              activeTab === 'install'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            ]"
          >
            {{ t('proxies.detail.tabs.install') }}
          </button>
          <button
            v-for="tab in ['overview', 'monitoring', 'tasks', 'heartbeats']"
            :key="tab"
            @click="activeTab = tab as any"
            :class="[
              'py-3 px-1 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            ]"
          >
            {{ safeT(`proxies.detail.tabs.${tab}`, tab) }}
          </button>
        </nav>
      </div>

      <!-- ==================== Install Tab ==================== -->
      <div v-if="activeTab === 'install' && proxy.status === 'pending'" class="space-y-6">
        <!-- Warning -->
        <div class="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div class="flex items-start gap-3">
            <ExclamationTriangleIcon class="w-5 h-5 text-amber-500 mt-0.5" />
            <div>
              <h4 class="font-medium text-amber-800 dark:text-amber-200">{{ t('proxies.install.warningTitle') }}</h4>
              <p class="text-sm text-amber-700 mt-1">{{ t('proxies.install.warningText') }}</p>
            </div>
          </div>
        </div>

        <!-- Step 1: Install Command -->
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <div class="flex items-center gap-2 mb-3">
            <span class="w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 text-sm font-medium flex items-center justify-center">1</span>
            <h3 class="font-medium text-slate-800 dark:text-white">{{ t('proxies.install.step1Title') }}</h3>
          </div>
          <p class="text-sm text-slate-600 dark:text-slate-300 mb-4">{{ t('proxies.install.step1Text') }}</p>
          
          <div class="relative">
            <pre class="bg-slate-900 text-slate-100 p-4 rounded-lg text-sm overflow-x-auto pr-24">{{ installInfo?.install_command || proxy.install_command || 'Click "Regenerate Token" to get install command' }}</pre>
            <button
              v-if="installInfo?.install_command || proxy.install_command"
              @click="copyToClipboard(installInfo?.install_command || proxy.install_command || '', 'Install command')"
              class="absolute top-3 right-3 p-2 bg-slate-700 hover:bg-slate-600 rounded text-white transition-colors"
              :title="t('common.copy')"
            >
              <ClipboardDocumentIcon class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Step 2: Credentials -->
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <div class="flex items-center gap-2 mb-4">
            <KeyIcon class="w-5 h-5 text-indigo-500" />
            <h3 class="font-medium text-slate-800 dark:text-white">{{ t('proxies.install.credentialsTitle') }}</h3>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Proxy ID -->
            <div class="p-4 bg-slate-50 dark:bg-slate-700 rounded-lg">
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.install.proxyIdLabel') }}</p>
              <div class="flex items-center justify-between gap-2">
                <code class="text-sm text-slate-800 break-all">{{ proxy.id }}</code>
                <button
                  @click="copyToClipboard(String(proxy.id), 'Proxy ID')"
                  class="p-1.5 hover:bg-slate-200 rounded transition-colors"
                  :title="t('common.copy')"
                >
                  <ClipboardDocumentIcon class="w-4 h-4 text-slate-500 dark:text-slate-400" />
                </button>
              </div>
              <p class="text-xs text-slate-400 mt-2">{{ t('proxies.install.proxyIdDesc') }}</p>
            </div>

            <!-- API Token -->
            <div class="p-4 bg-slate-50 dark:bg-slate-700 rounded-lg">
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.install.apiTokenLabel') }}</p>
              <div class="flex items-center justify-between gap-2">
                <code class="text-sm text-slate-800 break-all">{{ installInfo?.api_token || proxy.api_token || 'N/A' }}</code>
                <button
                  v-if="installInfo?.api_token || proxy.api_token"
                  @click="copyToClipboard(installInfo?.api_token || proxy.api_token || '', 'API Token')"
                  class="p-1.5 hover:bg-slate-200 rounded transition-colors"
                  :title="t('common.copy')"
                >
                  <ClipboardDocumentIcon class="w-4 h-4 text-slate-500 dark:text-slate-400" />
                </button>
              </div>
              <p class="text-xs text-slate-400 mt-2">{{ t('proxies.install.apiTokenDesc') }}</p>
            </div>
          </div>
        </div>

        <!-- Help -->
        <div class="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <div class="flex items-start gap-3">
            <InformationCircleIcon class="w-5 h-5 text-blue-500 mt-0.5" />
            <div class="text-sm text-blue-700">
              <p><strong>{{ t('proxies.install.helpTitle') }}</strong></p>
              <ul class="mt-2 space-y-1 list-disc list-inside">
                <li>{{ t('proxies.install.help1') }}</li>
                <li>{{ t('proxies.install.help2') }}</li>
                <li>{{ t('proxies.install.help3') }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== Overview Tab ==================== -->
      <div v-if="activeTab === 'overview'" class="space-y-6">
        <!-- Basic Info Card -->
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h3 class="text-sm font-medium text-slate-700 mb-4 flex items-center gap-2">
            <IdentificationIcon class="w-4 h-4" />
            {{ t('proxies.detail.basicInfo') }}
          </h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p class="text-xs text-slate-500 mb-1">Proxy ID</p>
              <div class="flex items-center gap-2">
                <code class="text-sm font-medium text-slate-800 dark:text-white">{{ String(proxy.id).substring(0, 8) }}...</code>
                <button @click="copyToClipboard(String(proxy.id), 'Proxy ID')" class="p-1 hover:bg-slate-100 dark:bg-slate-700 rounded">
                  <ClipboardDocumentIcon class="w-3.5 h-3.5 text-slate-400" />
                </button>
              </div>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.role') }}</p>
              <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', getRoleColor(proxy.role)]">
                {{ safeT(`proxies.roles.${proxy.role}`, proxy.role) }}
              </span>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.status') }}</p>
              <span :class="[
                'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
                proxy.status === 'active' ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' :
                proxy.status === 'error' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400' :
                'bg-slate-100 dark:bg-slate-700 text-slate-600'
              ]">
                {{ safeT(`proxies.status.${proxy.status}`, proxy.status) }}
              </span>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.owner') }}</p>
              <p class="text-sm font-medium text-slate-800 dark:text-white">{{ proxy.owner_name || '-' }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.createdAt') }}</p>
              <p class="text-sm text-slate-800 dark:text-white">{{ formatDate(proxy.created_at) }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.registeredAt') }}</p>
              <p class="text-sm text-slate-800 dark:text-white">{{ formatDate(proxy.registered_at) }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.lastHeartbeat') }}</p>
              <p class="text-sm text-slate-800 dark:text-white">{{ formatDate(proxy.last_heartbeat) }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.heartbeatInterval') }}</p>
              <p class="text-sm text-slate-800 dark:text-white">{{ proxy.heartbeat_interval || 10 }}s</p>
            </div>
          </div>
        </div>

        <!-- Resource Usage Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <div class="flex items-center gap-3 mb-3">
              <div class="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center">
                <CpuChipIcon class="w-5 h-5 text-indigo-600" />
              </div>
              <div>
                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('proxies.detail.cpuUsage') }}</p>
                <p class="text-2xl font-bold text-slate-800 dark:text-white">{{ proxy.cpu_usage?.toFixed(1) || 0 }}%</p>
              </div>
            </div>
            <div class="w-full h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                class="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all"
                :style="{ width: `${Math.min(proxy.cpu_usage || 0, 100)}%` }"
              />
            </div>
            <p class="text-xs text-slate-500 mt-2">{{ proxy.cpu_cores || 'N/A' }} cores</p>
          </div>

          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <div class="flex items-center gap-3 mb-3">
              <div class="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
                <DatabaseIcon class="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('proxies.detail.memoryUsage') }}</p>
                <p class="text-2xl font-bold text-slate-800 dark:text-white">{{ proxy.memory_usage?.toFixed(1) || 0 }}%</p>
              </div>
            </div>
            <div class="w-full h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                class="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all"
                :style="{ width: `${Math.min(proxy.memory_usage || 0, 100)}%` }"
              />
            </div>
            <p class="text-xs text-slate-500 mt-2">{{ formatBytes(proxy.total_memory) }} {{ t('proxies.detail.total') }}</p>
          </div>

          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
            <div class="flex items-center gap-3 mb-3">
              <div class="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center">
                <CircleStackIcon class="w-5 h-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p class="text-xs text-slate-500 dark:text-slate-400">{{ t('proxies.detail.diskUsage') }}</p>
                <p class="text-2xl font-bold text-slate-800 dark:text-white">{{ proxy.disk_usage?.toFixed(1) || 0 }}%</p>
              </div>
            </div>
            <div class="w-full h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                class="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full transition-all"
                :style="{ width: `${Math.min(proxy.disk_usage || 0, 100)}%` }"
              />
            </div>
            <p class="text-xs text-slate-500 mt-2">{{ formatBytes(proxy.total_disk) }} {{ t('proxies.detail.total') }}</p>
          </div>
        </div>

        <!-- System Info -->
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h3 class="text-sm font-medium text-slate-700 mb-4 flex items-center gap-2">
            <ServerIcon class="w-4 h-4" />
            {{ t('proxies.detail.systemInfo') }}
          </h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.hostname') }}</p>
              <p class="text-sm font-medium text-slate-800 dark:text-white">{{ proxy.hostname || '-' }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.internalIp') }}</p>
              <div class="flex items-center gap-2">
                <GlobeAltIcon class="w-4 h-4 text-slate-400" />
                <p class="text-sm font-medium text-slate-800 dark:text-white">{{ proxy.internal_ip || '-' }}</p>
              </div>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.operatingSystem') }}</p>
              <p class="text-sm font-medium text-slate-800 dark:text-white">{{ proxy.os || '-' }} {{ proxy.os_version || '' }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.version') }}</p>
              <p class="text-sm font-medium text-slate-800 dark:text-white">v{{ proxy.version || '-' }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.kopiaVersion') }}</p>
              <p class="text-sm font-medium text-slate-800 dark:text-white">{{ proxy.kopia_version || '-' }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.uptime') }}</p>
              <p class="text-sm font-medium text-slate-800 dark:text-white">{{ formatUptime(proxy.uptime_seconds) }}</p>
            </div>
          </div>
        </div>

        <!-- Capabilities -->
        <div v-if="proxy.capabilities && Object.keys(proxy.capabilities).length > 0" class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h3 class="text-sm font-medium text-slate-700 mb-4 flex items-center gap-2">
            <CheckCircleIcon class="w-4 h-4" />
            {{ t('proxies.detail.capabilities') }}
          </h3>
          <div class="flex flex-wrap gap-3">
            <span
              v-for="(value, key) in proxy.capabilities"
              :key="key"
              :class="[
                'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
                value ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800' : 'bg-slate-50 dark:bg-slate-700 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-600'
              ]"
            >
              <CheckCircleIcon v-if="value" class="w-4 h-4" />
              <XCircleIcon v-else class="w-4 h-4" />
              {{ key }}
            </span>
          </div>
        </div>

        <!-- Labels -->
        <div v-if="proxy.labels && proxy.labels.length > 0" class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h3 class="text-sm font-medium text-slate-700 mb-4 flex items-center gap-2">
            <TagIcon class="w-4 h-4" />
            {{ t('proxies.detail.labels') }}
          </h3>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="label in proxy.labels"
              :key="label"
              class="inline-flex items-center px-3 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 rounded-full text-sm font-medium"
            >
              {{ label }}
            </span>
          </div>
        </div>
      </div>

      <!-- ==================== Monitoring Tab ==================== -->
      <div v-if="activeTab === 'monitoring'" class="space-y-6">
        <!-- Quick Stats -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <p class="text-xs text-slate-500 mb-1">{{ t('proxies.monitoring.24hHeartbeats') }}</p>
            <p class="text-2xl font-bold text-slate-800 dark:text-white">{{ heartbeats.length }}</p>
          </div>
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <p class="text-xs text-slate-500 mb-1">{{ t('proxies.monitoring.avgCpu') }}</p>
            <p class="text-2xl font-bold text-indigo-600">{{ heartbeatStats.avgCpu.toFixed(1) }}%</p>
          </div>
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <p class="text-xs text-slate-500 mb-1">{{ t('proxies.monitoring.avgMemory') }}</p>
            <p class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{{ heartbeatStats.avgMemory.toFixed(1) }}%</p>
          </div>
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <p class="text-xs text-slate-500 mb-1">{{ t('proxies.monitoring.avgDisk') }}</p>
            <p class="text-2xl font-bold text-amber-600 dark:text-amber-400">{{ heartbeatStats.avgDisk.toFixed(1) }}%</p>
          </div>
        </div>

        <!-- Real-time Status -->
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h3 class="text-sm font-medium text-slate-700 mb-4">{{ t('proxies.monitoring.realtimeStatus') }}</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="text-center">
              <div class="relative w-32 h-32 mx-auto">
                <svg class="w-full h-full transform -rotate-90">
                  <circle cx="64" cy="64" r="56" stroke="#e2e8f0" class="dark:stroke-slate-700" stroke-width="12" fill="none" />
                  <circle 
                    cx="64" cy="64" r="56" 
                    stroke="url(#cpuGradient)" 
                    stroke-width="12" 
                    fill="none"
                    :stroke-dasharray="352"
                    :stroke-dashoffset="352 - (352 * (proxy.cpu_usage || 0) / 100)"
                    stroke-linecap="round"
                  />
                  <defs>
                    <linearGradient id="cpuGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stop-color="#6366f1" />
                      <stop offset="100%" stop-color="#a855f7" />
                    </linearGradient>
                  </defs>
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold text-slate-800 dark:text-white">{{ proxy.cpu_usage?.toFixed(0) || 0 }}%</span>
                </div>
              </div>
              <p class="text-sm text-slate-600 dark:text-slate-300 mt-2">{{ t('proxies.detail.cpuUsage') }}</p>
            </div>
            <div class="text-center">
              <div class="relative w-32 h-32 mx-auto">
                <svg class="w-full h-full transform -rotate-90">
                  <circle cx="64" cy="64" r="56" stroke="#e2e8f0" class="dark:stroke-slate-700" stroke-width="12" fill="none" />
                  <circle 
                    cx="64" cy="64" r="56" 
                    stroke="url(#memGradient)" 
                    stroke-width="12" 
                    fill="none"
                    :stroke-dasharray="352"
                    :stroke-dashoffset="352 - (352 * (proxy.memory_usage || 0) / 100)"
                    stroke-linecap="round"
                  />
                  <defs>
                    <linearGradient id="memGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stop-color="#10b981" />
                      <stop offset="100%" stop-color="#14b8a6" />
                    </linearGradient>
                  </defs>
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold text-slate-800 dark:text-white">{{ proxy.memory_usage?.toFixed(0) || 0 }}%</span>
                </div>
              </div>
              <p class="text-sm text-slate-600 dark:text-slate-300 mt-2">{{ t('proxies.detail.memoryUsage') }}</p>
            </div>
            <div class="text-center">
              <div class="relative w-32 h-32 mx-auto">
                <svg class="w-full h-full transform -rotate-90">
                  <circle cx="64" cy="64" r="56" stroke="#e2e8f0" class="dark:stroke-slate-700" stroke-width="12" fill="none" />
                  <circle 
                    cx="64" cy="64" r="56" 
                    stroke="url(#diskGradient)" 
                    stroke-width="12" 
                    fill="none"
                    :stroke-dasharray="352"
                    :stroke-dashoffset="352 - (352 * (proxy.disk_usage || 0) / 100)"
                    stroke-linecap="round"
                  />
                  <defs>
                    <linearGradient id="diskGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stop-color="#f59e0b" />
                      <stop offset="100%" stop-color="#f97316" />
                    </linearGradient>
                  </defs>
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold text-slate-800 dark:text-white">{{ proxy.disk_usage?.toFixed(0) || 0 }}%</span>
                </div>
              </div>
              <p class="text-sm text-slate-600 dark:text-slate-300 mt-2">{{ t('proxies.detail.diskUsage') }}</p>
            </div>
          </div>
        </div>

        <!-- Connection Info -->
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h3 class="text-sm font-medium text-slate-700 mb-4">{{ t('proxies.monitoring.connectionInfo') }}</h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.monitoring.websocketStatus') }}</p>
              <span :class="[
                'inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium',
                proxy.is_online ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' : 'bg-slate-100 dark:bg-slate-700 text-slate-600'
              ]">
                <span :class="['w-2 h-2 rounded-full', proxy.is_online ? 'bg-emerald-500' : 'bg-slate-400']" />
                {{ proxy.is_online ? t('proxies.monitoring.connected') : t('proxies.monitoring.disconnected') }}
              </span>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.lastHeartbeat') }}</p>
              <p class="text-sm text-slate-800 dark:text-white">{{ formatDate(proxy.last_heartbeat) }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.detail.uptime') }}</p>
              <p class="text-sm text-slate-800 dark:text-white">{{ formatUptime(proxy.uptime_seconds) }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500 mb-1">{{ t('proxies.monitoring.heartbeatInterval') }}</p>
              <p class="text-sm text-slate-800 dark:text-white">{{ proxy.heartbeat_interval || 10 }}s</p>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== Tasks Tab ==================== -->
      <div v-if="activeTab === 'tasks'" class="space-y-6">
        <!-- Task Stats -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <p class="text-xs text-slate-500 mb-1">{{ t('proxies.tasks.total') }}</p>
            <p class="text-2xl font-bold text-slate-800 dark:text-white">{{ taskStats.total }}</p>
          </div>
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <p class="text-xs text-slate-500 mb-1">{{ t('proxies.tasks.completed') }}</p>
            <p class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{{ taskStats.completed }}</p>
          </div>
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <p class="text-xs text-slate-500 mb-1">{{ t('proxies.tasks.failed') }}</p>
            <p class="text-2xl font-bold text-red-600 dark:text-red-400">{{ taskStats.failed }}</p>
          </div>
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <p class="text-xs text-slate-500 mb-1">{{ t('proxies.tasks.running') }}</p>
            <p class="text-2xl font-bold text-indigo-600">{{ taskStats.running }}</p>
          </div>
        </div>

        <!-- Task List -->
        <div v-if="tasks.length === 0" class="bg-white rounded-xl border border-slate-200 p-8 text-center">
          <DocumentTextIcon class="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p class="text-slate-500 dark:text-slate-400">{{ t('proxies.detail.noTasks') }}</p>
        </div>

        <div v-else class="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table class="min-w-full divide-y divide-slate-200">
            <thead class="bg-slate-50 dark:bg-slate-700/50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">{{ t('proxies.tasks.taskId') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">{{ t('proxies.tasks.type') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">{{ t('proxies.tasks.status') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">{{ t('proxies.tasks.progress') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">{{ t('proxies.tasks.startTime') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">{{ t('proxies.tasks.duration') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200">
              <tr v-for="task in tasks" :key="task.id" class="hover:bg-slate-50 dark:bg-slate-700/50">
                <td class="px-4 py-3 text-sm text-slate-800 font-mono">{{ String(task.id).substring(0, 8) }}</td>
                <td class="px-4 py-3">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200">
                    {{ task.task_type }}
                  </span>
                </td>
                <td class="px-4 py-3">
                  <span :class="[
                    'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
                    task.status === 'completed' ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' :
                    task.status === 'failed' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400' :
                    task.status === 'running' ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400' : 'bg-slate-100 dark:bg-slate-700 text-slate-600'
                  ]">
                    {{ task.status }}
                  </span>
                </td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <div class="w-20 h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div
                        :class="['h-full rounded-full', task.status === 'failed' ? 'bg-red-500' : 'bg-indigo-500']"
                        :style="{ width: `${task.progress}%` }"
                      />
                    </div>
                    <span class="text-sm text-slate-600 dark:text-slate-300">{{ task.progress }}%</span>
                  </div>
                </td>
                <td class="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{{ formatDate(task.created_at) }}</td>
                <td class="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
                  {{ task.duration_seconds ? `${task.duration_seconds.toFixed(0)}s` : '-' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ==================== Heartbeats Tab ==================== -->
      <div v-if="activeTab === 'heartbeats'" class="space-y-6">
        <!-- Heartbeat Stats -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <p class="text-xs text-slate-500 mb-1">{{ t('proxies.heartbeats.24hCount') }}</p>
            <p class="text-2xl font-bold text-slate-800 dark:text-white">{{ heartbeats.length }}</p>
          </div>
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <p class="text-xs text-slate-500 mb-1">{{ t('proxies.heartbeats.avgCpu') }}</p>
            <p class="text-2xl font-bold text-indigo-600">{{ heartbeatStats.avgCpu.toFixed(1) }}%</p>
          </div>
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <p class="text-xs text-slate-500 mb-1">{{ t('proxies.heartbeats.avgMemory') }}</p>
            <p class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{{ heartbeatStats.avgMemory.toFixed(1) }}%</p>
          </div>
          <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <p class="text-xs text-slate-500 mb-1">{{ t('proxies.heartbeats.avgDisk') }}</p>
            <p class="text-2xl font-bold text-amber-600 dark:text-amber-400">{{ heartbeatStats.avgDisk.toFixed(1) }}%</p>
          </div>
        </div>

        <!-- Heartbeats List -->
        <div v-if="heartbeats.length === 0" class="bg-white rounded-xl border border-slate-200 p-8 text-center">
          <ServerIcon class="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p class="text-slate-500 dark:text-slate-400">{{ t('proxies.detail.noHeartbeats') }}</p>
        </div>

        <div v-else class="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table class="min-w-full divide-y divide-slate-200">
            <thead class="bg-slate-50 dark:bg-slate-700/50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">{{ t('proxies.heartbeats.time') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">{{ t('proxies.heartbeats.cpu') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">{{ t('proxies.heartbeats.memory') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">{{ t('proxies.heartbeats.disk') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">{{ t('proxies.heartbeats.uptime') }}</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">{{ t('proxies.heartbeats.activeTasks') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200">
              <tr v-for="hb in heartbeats" :key="hb.id" class="hover:bg-slate-50 dark:bg-slate-700/50">
                <td class="px-4 py-3 text-sm text-slate-800 dark:text-white">{{ formatDate(hb.created_at) }}</td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <div class="w-16 h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div class="h-full bg-indigo-500 rounded-full" :style="{ width: `${hb.cpu_usage || 0}%` }" />
                    </div>
                    <span class="text-sm text-slate-600 dark:text-slate-300">{{ hb.cpu_usage?.toFixed(1) || '-' }}%</span>
                  </div>
                </td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <div class="w-16 h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div class="h-full bg-emerald-500 rounded-full" :style="{ width: `${hb.memory_usage || 0}%` }" />
                    </div>
                    <span class="text-sm text-slate-600 dark:text-slate-300">{{ hb.memory_usage?.toFixed(1) || '-' }}%</span>
                  </div>
                </td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <div class="w-16 h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div class="h-full bg-amber-500 rounded-full" :style="{ width: `${hb.disk_usage || 0}%` }" />
                    </div>
                    <span class="text-sm text-slate-600 dark:text-slate-300">{{ hb.disk_usage?.toFixed(1) || '-' }}%</span>
                  </div>
                </td>
                <td class="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{{ formatUptime(hb.uptime_seconds) }}</td>
                <td class="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">{{ hb.active_tasks || 0 }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
