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
  TrashIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const proxyId = computed(() => route.params.id as string)
const proxy = ref<ProxyNode | null>(null)
const tasks = ref<ProxyTask[]>([])
const heartbeats = ref<ProxyHeartbeat[]>([])
const isLoading = ref(true)
const activeTab = ref<'overview' | 'tasks' | 'heartbeats'>('overview')

// Polling
let pollInterval: number | null = null

async function fetchProxy() {
  try {
    const res = await api.get(`/api/v1/proxies/${proxyId.value}/`)
    proxy.value = res.data
  } catch (error) {
    console.error('Failed to fetch proxy:', error)
  }
}

async function fetchTasks() {
  try {
    const res = await api.get(`/api/v1/proxies/${proxyId.value}/tasks/?limit=20`)
    tasks.value = res.data
  } catch (error) {
    console.error('Failed to fetch tasks:', error)
  }
}

async function fetchHeartbeats() {
  try {
    const res = await api.get(`/api/v1/proxies/${proxyId.value}/heartbeats/?hours=24`)
    heartbeats.value = res.data
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
    await api.post(`/api/v1/proxies/${proxyId.value}/regenerate_token/`)
    await fetchProxy()
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

function getStatusIcon(status: string) {
  const icons: Record<string, any> = {
    active: CheckCircleIcon,
    inactive: XCircleIcon,
    offline: XCircleIcon,
    error: XCircleIcon,
    maintenance: WrenchScrewdriverIcon
  }
  return icons[status] || ServerIcon
}

function getRoleColor(role: string): string {
  return role === 'agent'
    ? 'bg-indigo-100 text-indigo-700'
    : 'bg-purple-100 text-purple-700'
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
          class="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
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
              <h1 class="text-2xl font-bold text-slate-800">{{ proxy.name }}</h1>
              <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', getRoleColor(proxy.role)]">
                {{ t(`proxies.roles.${proxy.role}`) }}
              </span>
            </div>
          </div>
        </div>
      </div>
      <div v-if="proxy" class="flex items-center gap-2">
        <button
          v-if="proxy.status === 'active'"
          @click="updateStatus('maintenance')"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-amber-600 border border-amber-200 rounded-lg hover:bg-amber-50"
        >
          <PauseIcon class="w-4 h-4" />
          {{ t('proxies.actions.setMaintenance') }}
        </button>
        <button
          v-else-if="proxy.status === 'maintenance'"
          @click="updateStatus('active')"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-emerald-600 border border-emerald-200 rounded-lg hover:bg-emerald-50"
        >
          <PlayIcon class="w-4 h-4" />
          {{ t('proxies.actions.activate') }}
        </button>
        <button
          @click="regenerateToken"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t('proxies.actions.regenerateToken') }}
        </button>
        <button
          @click="deleteProxy"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50"
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
        proxy.status === 'active' ? 'bg-emerald-50 border-emerald-200' :
        proxy.status === 'error' ? 'bg-red-50 border-red-200' :
        proxy.status === 'maintenance' ? 'bg-amber-50 border-amber-200' :
        'bg-slate-50 border-slate-200'
      ]">
        <component
          :is="getStatusIcon(proxy.status)"
          :class="[
            'w-6 h-6',
            proxy.status === 'active' ? 'text-emerald-500' :
            proxy.status === 'error' ? 'text-red-500' : 'text-amber-500'
          ]"
        />
        <div class="flex-1">
          <p class="font-medium" :class="proxy.status === 'active' ? 'text-emerald-800' : proxy.status === 'error' ? 'text-red-800' : 'text-amber-800'">
            {{ t(`proxies.status.${proxy.status}`) }}
          </p>
          <p class="text-sm" :class="proxy.status === 'active' ? 'text-emerald-600' : proxy.status === 'error' ? 'text-red-600' : 'text-amber-600'">
            {{ proxy.is_online ? t('proxies.detail.currentlyOnline') : t('proxies.detail.currentlyOffline') }}
          </p>
        </div>
        <div class="text-right">
          <p class="text-sm text-slate-500">{{ t('proxies.detail.uptime') }}</p>
          <p class="font-medium text-slate-800">{{ formatUptime(proxy.uptime_seconds) }}</p>
        </div>
      </div>

      <!-- Tabs -->
      <div class="border-b border-slate-200">
        <nav class="flex gap-8">
          <button
            v-for="tab in ['overview', 'tasks', 'heartbeats']"
            :key="tab"
            @click="activeTab = tab as any"
            :class="[
              'py-3 px-1 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            ]"
          >
            {{ t(`proxies.detail.tabs.${tab}`) }}
          </button>
        </nav>
      </div>

      <!-- Overview Tab -->
      <div v-if="activeTab === 'overview'" class="space-y-6">
        <!-- Resource Usage -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="bg-white rounded-xl border border-slate-200 p-5">
            <div class="flex items-center justify-between mb-3">
              <span class="text-sm font-medium text-slate-600">CPU Usage</span>
              <span class="text-2xl font-bold text-slate-800">{{ proxy.cpu_usage?.toFixed(1) || 0 }}%</span>
            </div>
            <div class="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all"
                :style="{ width: `${proxy.cpu_usage || 0}%` }"
              />
            </div>
            <p class="text-xs text-slate-500 mt-2">{{ proxy.cpu_cores || 'N/A' }} cores</p>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-5">
            <div class="flex items-center justify-between mb-3">
              <span class="text-sm font-medium text-slate-600">Memory Usage</span>
              <span class="text-2xl font-bold text-slate-800">{{ proxy.memory_usage?.toFixed(1) || 0 }}%</span>
            </div>
            <div class="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all"
                :style="{ width: `${proxy.memory_usage || 0}%` }"
              />
            </div>
            <p class="text-xs text-slate-500 mt-2">{{ formatBytes(proxy.total_memory) }} total</p>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-5">
            <div class="flex items-center justify-between mb-3">
              <span class="text-sm font-medium text-slate-600">Disk Usage</span>
              <span class="text-2xl font-bold text-slate-800">{{ proxy.disk_usage?.toFixed(1) || 0 }}%</span>
            </div>
            <div class="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full transition-all"
                :style="{ width: `${proxy.disk_usage || 0}%` }"
              />
            </div>
            <p class="text-xs text-slate-500 mt-2">{{ formatBytes(proxy.total_disk) }} total</p>
          </div>
        </div>

        <!-- System Info -->
        <div class="bg-white rounded-xl border border-slate-200 p-5">
          <h3 class="text-sm font-medium text-slate-700 mb-4">{{ t('proxies.detail.systemInfo') }}</h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p class="text-xs text-slate-500">{{ t('proxies.detail.hostname') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ proxy.hostname || '-' }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500">{{ t('proxies.detail.internalIp') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ proxy.internal_ip || '-' }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500">{{ t('proxies.detail.operatingSystem') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ proxy.operating_system || '-' }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500">{{ t('proxies.detail.version') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ proxy.version || '-' }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500">{{ t('proxies.detail.kopiaVersion') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ proxy.kopia_version || '-' }}</p>
            </div>
            <div>
              <p class="text-xs text-slate-500">{{ t('proxies.detail.lastHeartbeat') }}</p>
              <p class="text-sm font-medium text-slate-800">
                {{ proxy.last_heartbeat ? new Date(proxy.last_heartbeat).toLocaleString() : '-' }}
              </p>
            </div>
            <div>
              <p class="text-xs text-slate-500">{{ t('proxies.detail.registeredAt') }}</p>
              <p class="text-sm font-medium text-slate-800">
                {{ proxy.registered_at ? new Date(proxy.registered_at).toLocaleString() : '-' }}
              </p>
            </div>
            <div>
              <p class="text-xs text-slate-500">{{ t('proxies.detail.heartbeatInterval') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ proxy.heartbeat_interval }}s</p>
            </div>
          </div>
        </div>

        <!-- Capabilities -->
        <div v-if="proxy.capabilities && Object.keys(proxy.capabilities).length > 0" class="bg-white rounded-xl border border-slate-200 p-5">
          <h3 class="text-sm font-medium text-slate-700 mb-4">{{ t('proxies.detail.capabilities') }}</h3>
          <div class="flex flex-wrap gap-3">
            <span
              v-for="(value, key) in proxy.capabilities"
              :key="key"
              :class="[
                'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
                value ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-50 text-slate-500 border border-slate-200'
              ]"
            >
              <CheckCircleIcon v-if="value" class="w-4 h-4" />
              <XCircleIcon v-else class="w-4 h-4" />
              {{ key }}
            </span>
          </div>
        </div>

        <!-- Labels -->
        <div v-if="proxy.labels && proxy.labels.length > 0" class="bg-white rounded-xl border border-slate-200 p-5">
          <h3 class="text-sm font-medium text-slate-700 mb-4">{{ t('proxies.detail.labels') }}</h3>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="label in proxy.labels"
              :key="label"
              class="inline-flex items-center px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full text-sm font-medium"
            >
              {{ label }}
            </span>
          </div>
        </div>
      </div>

      <!-- Tasks Tab -->
      <div v-if="activeTab === 'tasks'" class="space-y-4">
        <div v-if="tasks.length === 0" class="bg-white rounded-xl border border-slate-200 p-8 text-center">
          <ClockIcon class="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p class="text-slate-500">{{ t('proxies.detail.noTasks') }}</p>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="task in tasks"
            :key="task.id"
            class="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-4"
          >
            <div :class="[
              'w-10 h-10 rounded-lg flex items-center justify-center',
              task.status === 'completed' ? 'bg-emerald-100' :
              task.status === 'failed' ? 'bg-red-100' :
              task.status === 'running' ? 'bg-indigo-100' : 'bg-slate-100'
            ]">
              <component
                :is="task.status === 'completed' ? CheckCircleIcon : task.status === 'failed' ? XCircleIcon : ClockIcon"
                :class="[
                  'w-5 h-5',
                  task.status === 'completed' ? 'text-emerald-600' :
                  task.status === 'failed' ? 'text-red-600' :
                  task.status === 'running' ? 'text-indigo-600' : 'text-slate-400'
                ]"
              />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <p class="font-medium text-slate-800">{{ task.task_type }}</p>
                <span :class="[
                  'px-2 py-0.5 rounded text-xs font-medium',
                  task.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                  task.status === 'failed' ? 'bg-red-100 text-red-700' :
                  task.status === 'running' ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'
                ]">
                  {{ task.status }}
                </span>
              </div>
              <p class="text-sm text-slate-500">
                {{ new Date(task.created_at).toLocaleString() }}
                <span v-if="task.duration_seconds"> · {{ task.duration_seconds.toFixed(0) }}s</span>
              </p>
              <p v-if="task.error_message" class="text-sm text-red-500 mt-1">{{ task.error_message }}</p>
            </div>
            <div class="text-right">
              <p class="text-lg font-bold text-slate-800">{{ task.progress }}%</p>
              <div class="w-20 h-2 bg-slate-100 rounded-full overflow-hidden mt-1">
                <div
                  :class="[
                    'h-full rounded-full',
                    task.status === 'failed' ? 'bg-red-500' : 'bg-indigo-500'
                  ]"
                  :style="{ width: `${task.progress}%` }"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Heartbeats Tab -->
      <div v-if="activeTab === 'heartbeats'" class="space-y-4">
        <div v-if="heartbeats.length === 0" class="bg-white rounded-xl border border-slate-200 p-8 text-center">
          <ServerIcon class="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p class="text-slate-500">{{ t('proxies.detail.noHeartbeats') }}</p>
        </div>

        <div v-else class="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table class="min-w-full divide-y divide-slate-200">
            <thead class="bg-slate-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Time</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">CPU</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Memory</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Disk</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Uptime</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Tasks</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200">
              <tr v-for="hb in heartbeats" :key="hb.id">
                <td class="px-4 py-3 text-sm text-slate-800">
                  {{ new Date(hb.created_at).toLocaleString() }}
                </td>
                <td class="px-4 py-3 text-sm text-slate-600">
                  {{ hb.cpu_usage?.toFixed(1) || '-' }}%
                </td>
                <td class="px-4 py-3 text-sm text-slate-600">
                  {{ hb.memory_usage?.toFixed(1) || '-' }}%
                </td>
                <td class="px-4 py-3 text-sm text-slate-600">
                  {{ hb.disk_usage?.toFixed(1) || '-' }}%
                </td>
                <td class="px-4 py-3 text-sm text-slate-600">
                  {{ formatUptime(hb.uptime_seconds) }}
                </td>
                <td class="px-4 py-3 text-sm text-slate-600">
                  {{ hb.active_tasks }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
