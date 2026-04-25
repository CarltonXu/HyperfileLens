<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import type { Node, NodeStats, NodeCreateData, NodeHeartbeat } from '@/types/node'
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
  InformationCircleIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()

// State
const isLoading = ref(true)
const nodes = ref<Node[]>([])
const stats = ref<NodeStats | null>(null)
const selectedType = ref<string>('all')
const selectedStatus = ref<string>('all')
const searchQuery = ref('')

// Modals
const showAddModal = ref(false)
const showDetailModal = ref(false)
const showEditModal = ref(false)
const showDeleteConfirm = ref(false)
const selectedNode = ref<Node | null>(null)
const nodeHeartbeats = ref<NodeHeartbeat[]>([])

// Form data
const formData = ref<NodeCreateData>({
  name: '',
  node_type: 'source_proxy',
  hostname: '',
  port: 8080,
  protocol: 'https',
  operating_system: 'linux',
  heartbeat_interval: 30,
  tags: {},
  metadata: {}
})

// Dropdown menu
const openMenuId = ref<string | null>(null)

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

async function fetchNodeHeartbeats(nodeId: string) {
  try {
    const res = await api.get(`/api/v1/nodes/${nodeId}/heartbeats/?hours=24`)
    nodeHeartbeats.value = res.data
  } catch (error) {
    console.error('Failed to fetch heartbeats:', error)
    nodeHeartbeats.value = []
  }
}

function openAddModal() {
  formData.value = {
    name: '',
    node_type: 'source_proxy',
    hostname: '',
    port: 8080,
    protocol: 'https',
    operating_system: 'linux',
    heartbeat_interval: 30,
    tags: {},
    metadata: {}
  }
  showAddModal.value = true
}

async function createNode() {
  try {
    await api.post('/api/v1/nodes/', formData.value)
    showAddModal.value = false
    await fetchNodes()
  } catch (error) {
    console.error('Failed to create node:', error)
  }
}

function viewNodeDetail(node: Node) {
  selectedNode.value = node
  showDetailModal.value = true
  fetchNodeHeartbeats(node.node_id)
  openMenuId.value = null
}

function editNode(node: Node) {
  selectedNode.value = node
  formData.value = {
    name: node.name,
    node_type: node.node_type,
    hostname: node.hostname,
    port: node.port,
    protocol: node.protocol,
    operating_system: node.operating_system,
    heartbeat_interval: node.heartbeat_interval,
    tags: node.tags,
    metadata: node.metadata
  }
  showEditModal.value = true
  openMenuId.value = null
}

async function updateNode() {
  if (!selectedNode.value) return
  try {
    await api.patch(`/api/v1/nodes/${selectedNode.value.node_id}/`, formData.value)
    showEditModal.value = false
    await fetchNodes()
  } catch (error) {
    console.error('Failed to update node:', error)
  }
}

function confirmDeleteNode(node: Node) {
  selectedNode.value = node
  showDeleteConfirm.value = true
  openMenuId.value = null
}

async function deleteNode() {
  if (!selectedNode.value) return
  try {
    await api.delete(`/api/v1/nodes/${selectedNode.value.node_id}/`)
    showDeleteConfirm.value = false
    selectedNode.value = null
    await fetchNodes()
  } catch (error) {
    console.error('Failed to delete node:', error)
  }
}

async function updateNodeStatus(node: Node, newStatus: string) {
  try {
    await api.post(`/api/v1/nodes/${node.node_id}/set_status/`, { status: newStatus })
    await fetchNodes()
    openMenuId.value = null
  } catch (error) {
    console.error('Failed to update status:', error)
  }
}

function toggleMenu(nodeId: string) {
  openMenuId.value = openMenuId.value === nodeId ? null : nodeId
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

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

// Close menu when clicking outside
function closeMenu() {
  openMenuId.value = null
}

onMounted(() => {
  fetchNodes()
  document.addEventListener('click', closeMenu)
})
</script>

<template>
  <div class="space-y-6" @click.stop>
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">{{ t('nodes.title') }}</h1>
        <p class="text-slate-500 mt-1">{{ t('nodes.subtitle') }}</p>
      </div>
      <button
        @click="openAddModal"
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
          <option value="maintenance">{{ t('nodes.status.maintenance') }}</option>
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
      <button
        @click="openAddModal"
        class="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t('nodes.addNode') }}
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <div
        v-for="node in filteredNodes"
        :key="node.id"
        class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md hover:border-slate-300 transition-all group"
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
          <div class="relative" @click.stop>
            <button
              @click="toggleMenu(node.node_id)"
              class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <EllipsisHorizontalIcon class="w-5 h-5" />
            </button>
            <!-- Dropdown Menu -->
            <div
              v-if="openMenuId === node.node_id"
              class="absolute right-0 top-8 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-50"
            >
              <button
                @click="viewNodeDetail(node)"
                class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
              >
                <InformationCircleIcon class="w-4 h-4" />
                {{ t('nodes.actions.viewDetails') }}
              </button>
              <button
                @click="editNode(node)"
                class="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2"
              >
                <PencilIcon class="w-4 h-4" />
                {{ t('nodes.actions.edit') }}
              </button>
              <hr class="my-1 border-slate-100" />
              <button
                v-if="node.status === 'active'"
                @click="updateNodeStatus(node, 'maintenance')"
                class="w-full px-4 py-2 text-left text-sm text-amber-600 hover:bg-amber-50 flex items-center gap-2"
              >
                <PauseIcon class="w-4 h-4" />
                {{ t('nodes.actions.setMaintenance') }}
              </button>
              <button
                v-else-if="node.status === 'maintenance' || node.status === 'inactive'"
                @click="updateNodeStatus(node, 'active')"
                class="w-full px-4 py-2 text-left text-sm text-emerald-600 hover:bg-emerald-50 flex items-center gap-2"
              >
                <PlayIcon class="w-4 h-4" />
                {{ t('nodes.actions.activate') }}
              </button>
              <hr class="my-1 border-slate-100" />
              <button
                @click="confirmDeleteNode(node)"
                class="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
              >
                <TrashIcon class="w-4 h-4" />
                {{ t('nodes.actions.delete') }}
              </button>
            </div>
          </div>
        </div>

        <div class="space-y-3 text-sm">
          <div class="flex items-center gap-2 text-slate-500">
            <MapPinIcon class="w-4 h-4 flex-shrink-0" />
            <span class="truncate">{{ node.protocol }}://{{ node.hostname }}:{{ node.port }}</span>
          </div>
          <div class="flex items-center gap-2 text-slate-500">
            <ClockIcon class="w-4 h-4 flex-shrink-0" />
            <span>{{ node.last_heartbeat ? new Date(node.last_heartbeat).toLocaleString() : t('nodes.neverConnected') }}</span>
          </div>
          <div class="flex items-center gap-2 text-slate-500">
            <CpuChipIcon class="w-4 h-4 flex-shrink-0" />
            <span>{{ node.operating_system }} {{ node.cpu_cores ? `(${node.cpu_cores} cores)` : '' }}</span>
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
          <button
            @click="viewNodeDetail(node)"
            class="text-sm font-medium text-indigo-600 hover:text-indigo-700"
          >
            {{ t('nodes.actions.viewDetails') }} →
          </button>
        </div>
      </div>
    </div>

    <!-- Add Node Modal -->
    <div v-if="showAddModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between p-5 border-b border-slate-100">
          <h2 class="text-lg font-semibold text-slate-800">{{ t('nodes.addNode') }}</h2>
          <button @click="showAddModal = false" class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg">
            <XMarkIcon class="w-5 h-5" />
          </button>
        </div>
        <form @submit.prevent="createNode" class="p-5 space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('nodes.form.name') }}</label>
            <input
              v-model="formData.name"
              type="text"
              required
              :placeholder="t('nodes.form.namePlaceholder')"
              class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('nodes.form.type') }}</label>
            <select
              v-model="formData.node_type"
              class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="source_proxy">{{ t('nodes.types.source_proxy') }}</option>
              <option value="target_gateway">{{ t('nodes.types.target_gateway') }}</option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('nodes.form.hostname') }}</label>
              <input
                v-model="formData.hostname"
                type="text"
                required
                placeholder="192.168.1.100"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('nodes.form.port') }}</label>
              <input
                v-model.number="formData.port"
                type="number"
                required
                placeholder="8080"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('nodes.form.protocol') }}</label>
              <select
                v-model="formData.protocol"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="https">HTTPS</option>
                <option value="http">HTTP</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('nodes.form.os') }}</label>
              <select
                v-model="formData.operating_system"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="linux">Linux</option>
                <option value="windows">Windows</option>
                <option value="macos">macOS</option>
              </select>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('nodes.form.heartbeatInterval') }}</label>
            <input
              v-model.number="formData.heartbeat_interval"
              type="number"
              min="10"
              max="300"
              class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div class="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              @click="showAddModal = false"
              class="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              type="submit"
              class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
            >
              {{ t('common.create') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Node Detail Modal -->
    <div v-if="showDetailModal && selectedNode" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between p-5 border-b border-slate-100">
          <div class="flex items-center gap-3">
            <div :class="[
              'w-10 h-10 rounded-xl flex items-center justify-center',
              selectedNode.status === 'active' ? 'bg-gradient-to-br from-emerald-500 to-teal-600' :
              selectedNode.status === 'error' ? 'bg-gradient-to-br from-red-500 to-rose-600' :
              'bg-gradient-to-br from-slate-400 to-slate-500'
            ]">
              <ServerIcon class="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 class="text-lg font-semibold text-slate-800">{{ selectedNode.name }}</h2>
              <span :class="['inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', getTypeColor(selectedNode.node_type)]">
                {{ t(`nodes.types.${selectedNode.node_type}`) }}
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
              :is="getStatusIcon(selectedNode.status)"
              :class="[
                'w-5 h-5',
                selectedNode.status === 'active' ? 'text-emerald-500' :
                selectedNode.status === 'error' ? 'text-red-500' : 'text-slate-400'
              ]"
            />
            <span :class="['px-3 py-1 rounded-full text-sm font-medium', getStatusColor(selectedNode.status)]">
              {{ t(`nodes.status.${selectedNode.status}`) }}
            </span>
            <span v-if="selectedNode.is_online" class="px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full text-sm font-medium">
              {{ t('nodes.online') }}
            </span>
          </div>

          <!-- Info Grid -->
          <div class="grid grid-cols-2 gap-4">
            <div class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('nodes.detail.connection') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ selectedNode.protocol }}://{{ selectedNode.hostname }}:{{ selectedNode.port }}</p>
            </div>
            <div class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('nodes.detail.operatingSystem') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ selectedNode.operating_system }}</p>
            </div>
            <div class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('nodes.detail.lastHeartbeat') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ selectedNode.last_heartbeat ? new Date(selectedNode.last_heartbeat).toLocaleString() : '-' }}</p>
            </div>
            <div class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('nodes.detail.uptime') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ selectedNode.uptime_seconds ? formatUptime(selectedNode.uptime_seconds) : '-' }}</p>
            </div>
            <div v-if="selectedNode.cpu_cores" class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('nodes.detail.cpuCores') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ selectedNode.cpu_cores }}</p>
            </div>
            <div v-if="selectedNode.memory_total" class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('nodes.detail.memory') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ formatBytes(selectedNode.memory_total) }}</p>
            </div>
            <div v-if="selectedNode.disk_total" class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('nodes.detail.disk') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ formatBytes(selectedNode.disk_total) }}</p>
            </div>
            <div v-if="selectedNode.version" class="bg-slate-50 rounded-lg p-4">
              <p class="text-xs text-slate-500 mb-1">{{ t('nodes.detail.version') }}</p>
              <p class="text-sm font-medium text-slate-800">{{ selectedNode.version }}</p>
            </div>
          </div>

          <!-- Node ID & API Key -->
          <div class="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <p class="text-sm font-medium text-amber-800 mb-2">{{ t('nodes.detail.credentials') }}</p>
            <div class="space-y-2 text-sm">
              <div class="flex items-center justify-between">
                <span class="text-amber-700">Node ID:</span>
                <code class="bg-amber-100 px-2 py-0.5 rounded text-amber-900 font-mono text-xs">{{ selectedNode.node_id }}</code>
              </div>
              <p class="text-xs text-amber-600">{{ t('nodes.detail.credentialsHint') }}</p>
            </div>
          </div>

          <!-- Recent Heartbeats -->
          <div v-if="nodeHeartbeats.length > 0">
            <h3 class="text-sm font-medium text-slate-700 mb-3">{{ t('nodes.detail.recentHeartbeats') }}</h3>
            <div class="bg-slate-50 rounded-lg overflow-hidden">
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b border-slate-200">
                    <th class="px-4 py-2 text-left text-xs text-slate-500">{{ t('nodes.heartbeat.time') }}</th>
                    <th class="px-4 py-2 text-left text-xs text-slate-500">{{ t('nodes.heartbeat.cpu') }}</th>
                    <th class="px-4 py-2 text-left text-xs text-slate-500">{{ t('nodes.heartbeat.memory') }}</th>
                    <th class="px-4 py-2 text-left text-xs text-slate-500">{{ t('nodes.heartbeat.disk') }}</th>
                    <th class="px-4 py-2 text-left text-xs text-slate-500">{{ t('nodes.heartbeat.tasks') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="hb in nodeHeartbeats.slice(0, 5)" :key="hb.id" class="border-b border-slate-100 last:border-0">
                    <td class="px-4 py-2 text-slate-600">{{ new Date(hb.timestamp).toLocaleTimeString() }}</td>
                    <td class="px-4 py-2 text-slate-600">{{ hb.cpu_usage?.toFixed(1) || '-' }}%</td>
                    <td class="px-4 py-2 text-slate-600">{{ hb.memory_usage?.toFixed(1) || '-' }}%</td>
                    <td class="px-4 py-2 text-slate-600">{{ hb.disk_usage?.toFixed(1) || '-' }}%</td>
                    <td class="px-4 py-2 text-slate-600">{{ hb.active_tasks }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex justify-between pt-4 border-t border-slate-100">
            <button
              @click="confirmDeleteNode(selectedNode); showDetailModal = false"
              class="inline-flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <TrashIcon class="w-4 h-4" />
              {{ t('nodes.actions.delete') }}
            </button>
            <div class="flex gap-2">
              <button
                @click="showDetailModal = false; editNode(selectedNode)"
                class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
              >
                <PencilIcon class="w-4 h-4" />
                {{ t('nodes.actions.edit') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Node Modal -->
    <div v-if="showEditModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between p-5 border-b border-slate-100">
          <h2 class="text-lg font-semibold text-slate-800">{{ t('nodes.actions.edit') }}</h2>
          <button @click="showEditModal = false" class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg">
            <XMarkIcon class="w-5 h-5" />
          </button>
        </div>
        <form @submit.prevent="updateNode" class="p-5 space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('nodes.form.name') }}</label>
            <input
              v-model="formData.name"
              type="text"
              required
              class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('nodes.form.hostname') }}</label>
              <input
                v-model="formData.hostname"
                type="text"
                required
                class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('nodes.form.port') }}</label>
              <input
                v-model.number="formData.port"
                type="number"
                required
                class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('nodes.form.protocol') }}</label>
              <select
                v-model="formData.protocol"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="https">HTTPS</option>
                <option value="http">HTTP</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('nodes.form.heartbeatInterval') }}</label>
              <input
                v-model.number="formData.heartbeat_interval"
                type="number"
                min="10"
                max="300"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
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

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteConfirm && selectedNode" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl max-w-md w-full">
        <div class="p-5 text-center">
          <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <ExclamationTriangleIcon class="w-6 h-6 text-red-600" />
          </div>
          <h3 class="text-lg font-semibold text-slate-800 mb-2">{{ t('nodes.deleteConfirm.title') }}</h3>
          <p class="text-slate-500 mb-6">{{ t('nodes.deleteConfirm.message', { name: selectedNode.name }) }}</p>
          <div class="flex justify-center gap-3">
            <button
              @click="showDeleteConfirm = false"
              class="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              @click="deleteNode"
              class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
            >
              {{ t('common.delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
