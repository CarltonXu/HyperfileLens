<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  ServerIcon,
  FolderIcon,
  CloudIcon,
  ComputerDesktopIcon,
  PlusIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  LinkIcon,
  EyeIcon,
  PencilIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'
import { sourceResourcesApi, nodesApi } from '../api'
import type { SourceResource, ResourceType, SourceResourceStats } from '../types/sourceResource'
import Pagination from '@/components/Pagination.vue'

const { t } = useI18n()

// State
const resources = ref<SourceResource[]>([])
const stats = ref<SourceResourceStats | null>(null)
const nodes = ref<any[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// Filters
const searchQuery = ref('')
const typeFilter = ref('')
const statusFilter = ref('')

// Pagination
const currentPage = ref(1)
const pageSize = ref(10)

// Modals
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const selectedResource = ref<SourceResource | null>(null)

// Form data
const formData = ref({
  name: '',
  description: '',
  resource_type: 'nfs' as ResourceType,
  config: {} as Record<string, any>,
  credentials: {} as Record<string, any>,
  bound_node_id: null as string | null
})

// Computed
const filteredResources = computed(() => {
  return resources.value.filter(r => {
    const matchesSearch = !searchQuery.value || 
      r.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesType = !typeFilter.value || r.resource_type === typeFilter.value
    const matchesStatus = !statusFilter.value || r.status === statusFilter.value
    return matchesSearch && matchesType && matchesStatus
  })
})

// Paginated resources for display
const paginatedResources = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredResources.value.slice(start, end)
})

// Reset page when filters change
watch([searchQuery, typeFilter, statusFilter], () => {
  currentPage.value = 1
})

// Resource type options
const resourceTypes: { value: ResourceType; label: string }[] = [
  { value: 'nas', label: 'NAS Storage' },
  { value: 'nfs', label: 'NFS Share' },
  { value: 'cifs', label: 'CIFS/SMB Share' },
  { value: 's3', label: 'Amazon S3' },
  { value: 'azure', label: 'Azure Blob' },
  { value: 'gcs', label: 'Google Cloud Storage' },
  { value: 'local', label: 'Local Filesystem' }
]

// Methods
const fetchData = async () => {
  loading.value = true
  error.value = null
  try {
    const [resourcesRes, statsRes, nodesRes] = await Promise.all([
      sourceResourcesApi.list(),
      sourceResourcesApi.stats(),
      nodesApi.list({ page_size: 100 })
    ])
    resources.value = resourcesRes.data.results || resourcesRes.data
    stats.value = statsRes.data
    nodes.value = nodesRes.data.results || nodesRes.data
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const getResourceIcon = (type: ResourceType) => {
  switch (type) {
    case 'nas': return ServerIcon
    case 'nfs':
    case 'cifs': return FolderIcon
    case 's3':
    case 'azure':
    case 'gcs': return CloudIcon
    case 'local': return ComputerDesktopIcon
    default: return FolderIcon
  }
}

const openCreateModal = () => {
  formData.value = {
    name: '',
    description: '',
    resource_type: 'nfs',
    config: {},
    credentials: {},
    bound_node_id: null
  }
  showCreateModal.value = true
}

const openDetailModal = (resource: SourceResource) => {
  selectedResource.value = resource
  showDetailModal.value = true
}

const openEditModal = (resource: SourceResource) => {
  selectedResource.value = resource
  formData.value = {
    name: resource.name,
    description: resource.description,
    resource_type: resource.resource_type,
    config: resource.config,
    credentials: resource.credentials || {},
    bound_node_id: resource.bound_node?.id || null
  }
  showEditModal.value = true
}

const openDeleteModal = (resource: SourceResource) => {
  selectedResource.value = resource
  showDeleteModal.value = true
}

const createResource = async () => {
  try {
    await sourceResourcesApi.create(formData.value)
    showCreateModal.value = false
    fetchData()
  } catch (e: any) {
    error.value = e.message
  }
}

const updateResource = async () => {
  if (!selectedResource.value) return
  try {
    await sourceResourcesApi.update(selectedResource.value.id, formData.value)
    showEditModal.value = false
    fetchData()
  } catch (e: any) {
    error.value = e.message
  }
}

const deleteResource = async () => {
  if (!selectedResource.value) return
  try {
    await sourceResourcesApi.delete(selectedResource.value.id)
    showDeleteModal.value = false
    fetchData()
  } catch (e: any) {
    error.value = e.message
  }
}

const testConnection = async (resource: SourceResource) => {
  try {
    const res = await sourceResourcesApi.testConnection(resource.id)
    alert(res.data.success ? t('common.success') : res.data.message)
  } catch (e: any) {
    alert(t('common.error') + ': ' + e.message)
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">
          {{ t('sourceResources.title') }}
        </h1>
        <p class="mt-1 text-sm text-slate-500">
          {{ t('sourceResources.subtitle') }}
        </p>
      </div>
      <button
        @click="openCreateModal"
        class="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
      >
        <PlusIcon class="w-5 h-5" />
        {{ t('sourceResources.addResource') }}
      </button>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('sourceResources.stats.total') }}</p>
        <p class="text-xl font-bold text-slate-800 mt-1">{{ stats?.total_resources || 0 }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('sourceResources.stats.active') }}</p>
        <p class="text-xl font-bold text-emerald-600 mt-1">{{ stats?.active_resources || 0 }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('sourceResources.stats.mounted') }}</p>
        <p class="text-xl font-bold text-indigo-600 mt-1">{{ stats?.mounted_resources || 0 }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('sourceResources.stats.error') }}</p>
        <p class="text-xl font-bold text-red-600 mt-1">{{ stats?.error_resources || 0 }}</p>
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
            class="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <select
          v-model="typeFilter"
          class="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">{{ t('sourceResources.allTypes') }}</option>
          <option v-for="type in resourceTypes" :key="type.value" :value="type.value">
            {{ type.label }}
          </option>
        </select>
        <select
          v-model="statusFilter"
          class="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">{{ t('sourceResources.allStatus') }}</option>
          <option value="connected">{{ t('sourceResources.status.connected') }}</option>
          <option value="disconnected">{{ t('sourceResources.status.disconnected') }}</option>
          <option value="error">{{ t('sourceResources.status.error') }}</option>
        </select>
        <button
          @click="fetchData"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredResources.length === 0" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
      <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <ServerIcon class="w-8 h-8 text-slate-400" />
      </div>
      <h3 class="text-lg font-medium text-slate-800 mb-1">{{ t('sourceResources.noResources') }}</h3>
      <p class="text-slate-500">{{ t('sourceResources.noResourcesDesc') }}</p>
    </div>

    <!-- Resource List -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="resource in paginatedResources"
        :key="resource.id"
        class="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow"
      >
        <div class="p-4">
          <!-- Header -->
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg flex items-center justify-center" :class="[
                resource.status === 'connected' ? 'bg-emerald-100' :
                resource.status === 'error' ? 'bg-red-100' : 'bg-slate-100'
              ]">
                <component :is="getResourceIcon(resource.resource_type)" :class="[
                  'w-5 h-5',
                  resource.status === 'connected' ? 'text-emerald-600' :
                  resource.status === 'error' ? 'text-red-600' : 'text-slate-400'
                ]" />
              </div>
              <div>
                <h3 class="font-medium text-slate-800">{{ resource.name }}</h3>
                <p class="text-sm text-slate-500">{{ resource.resource_type_display }}</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span :class="[
                'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full',
                resource.status === 'connected' ? 'bg-emerald-100 text-emerald-700' :
                resource.status === 'error' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'
              ]">
                {{ resource.status }}
              </span>
            </div>
          </div>

          <!-- Connection Info -->
          <div class="mt-4 space-y-2 text-sm">
            <div v-if="resource.config.server" class="flex items-center gap-2 text-slate-600">
              <ServerIcon class="w-4 h-4 text-slate-400" />
              <span class="truncate">{{ resource.config.server }}{{ resource.config.export_path || resource.config.share || '' }}</span>
            </div>
            <div v-if="resource.config.endpoint" class="flex items-center gap-2 text-slate-600">
              <CloudIcon class="w-4 h-4 text-slate-400" />
              <span class="truncate">{{ resource.config.bucket }}</span>
            </div>
          </div>

          <!-- Bound Node -->
          <div class="mt-4 flex items-center gap-2">
            <LinkIcon class="w-4 h-4 text-slate-400" />
            <span v-if="resource.bound_node" class="text-sm text-slate-600">
              {{ resource.bound_node.name }}
            </span>
            <span v-else class="text-sm text-slate-400">{{ t('sourceResources.noBoundNode') }}</span>
          </div>

          <!-- Mount Status -->
          <div class="mt-2 flex items-center gap-2">
            <FolderIcon class="w-4 h-4 text-slate-400" />
            <span class="text-sm text-slate-600">
              {{ resource.mount_point || t('sourceResources.notMounted') }}
            </span>
          </div>

          <!-- Actions -->
          <div class="mt-4 flex items-center justify-between pt-4 border-t border-slate-100">
            <button
              @click="testConnection(resource)"
              class="px-3 py-1.5 text-sm text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
            >
              {{ t('sourceResources.testConnection') }}
            </button>
            <div class="flex gap-1">
              <button @click="openDetailModal(resource)" class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded" :title="t('common.view')">
                <EyeIcon class="w-4 h-4" />
              </button>
              <button @click="openEditModal(resource)" class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded" :title="t('common.edit')">
                <PencilIcon class="w-4 h-4" />
              </button>
              <button @click="openDeleteModal(resource)" class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded" :title="t('common.delete')">
                <TrashIcon class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <Pagination
      v-if="filteredResources.length > 0"
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total-items="filteredResources.length"
    />

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-full items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/50" @click="showCreateModal = false"></div>
        <div class="relative bg-white rounded-xl shadow-xl max-w-lg w-full">
          <div class="p-6">
            <h2 class="text-lg font-semibold text-slate-800 mb-4">
              {{ t('sourceResources.addResource') }}
            </h2>
            <form @submit.prevent="createResource" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.name') }}</label>
                <input v-model="formData.name" type="text" required class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.type') }}</label>
                <select v-model="formData.resource_type" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  <option v-for="type in resourceTypes" :key="type.value" :value="type.value">{{ type.label }}</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.boundNode') }}</label>
                <select v-model="formData.bound_node_id" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  <option :value="null">{{ t('sourceResources.form.selectNode') }}</option>
                  <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.name }}</option>
                </select>
              </div>
              <div v-if="['nfs', 'nas'].includes(formData.resource_type)">
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.server') }}</label>
                    <input v-model="formData.config.server" type="text" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.exportPath') }}</label>
                    <input v-model="formData.config.export_path" type="text" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </div>
                </div>
              </div>
              <div v-if="formData.resource_type === 'cifs'">
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.server') }}</label>
                    <input v-model="formData.config.server" type="text" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.share') }}</label>
                    <input v-model="formData.config.share" type="text" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </div>
                </div>
                <div class="grid grid-cols-2 gap-4 mt-4">
                  <div>
                    <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.username') }}</label>
                    <input v-model="formData.credentials.username" type="text" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.password') }}</label>
                    <input v-model="formData.credentials.password" type="password" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </div>
                </div>
              </div>
              <div v-if="formData.resource_type === 's3'">
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.endpoint') }}</label>
                    <input v-model="formData.config.endpoint" type="text" placeholder="https://s3.amazonaws.com" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.bucket') }}</label>
                    <input v-model="formData.config.bucket" type="text" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </div>
                </div>
                <div class="grid grid-cols-2 gap-4 mt-4">
                  <div>
                    <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.accessKey') }}</label>
                    <input v-model="formData.credentials.access_key" type="text" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.secretKey') }}</label>
                    <input v-model="formData.credentials.secret_key" type="password" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </div>
                </div>
              </div>
              <div class="flex justify-end gap-3 pt-4">
                <button type="button" @click="showCreateModal = false" class="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">
                  {{ t('common.cancel') }}
                </button>
                <button type="submit" class="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
                  {{ t('common.create') }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>

    <!-- Detail Modal -->
    <div v-if="showDetailModal && selectedResource" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-full items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/50" @click="showDetailModal = false"></div>
        <div class="relative bg-white rounded-xl shadow-xl max-w-lg w-full">
          <div class="p-6">
            <h2 class="text-lg font-semibold text-slate-800 mb-4">{{ selectedResource.name }}</h2>
            <div class="space-y-3">
              <div class="flex justify-between py-2 border-b border-slate-100">
                <span class="text-sm text-slate-500">{{ t('sourceResources.form.type') }}</span>
                <span class="text-sm text-slate-800">{{ selectedResource.resource_type_display }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-100">
                <span class="text-sm text-slate-500">{{ t('sourceResources.status.label') }}</span>
                <span :class="[
                  'text-sm font-medium',
                  selectedResource.status === 'connected' ? 'text-emerald-600' :
                  selectedResource.status === 'error' ? 'text-red-600' : 'text-slate-600'
                ]">{{ selectedResource.status }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-100">
                <span class="text-sm text-slate-500">{{ t('sourceResources.mountStatus') }}</span>
                <span class="text-sm text-slate-800">{{ selectedResource.mount_status }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-100">
                <span class="text-sm text-slate-500">{{ t('sourceResources.mountPoint') }}</span>
                <span class="text-sm text-slate-800">{{ selectedResource.mount_point || '-' }}</span>
              </div>
              <div class="flex justify-between py-2">
                <span class="text-sm text-slate-500">{{ t('sourceResources.boundNode') }}</span>
                <span class="text-sm text-slate-800">{{ selectedResource.bound_node?.name || '-' }}</span>
              </div>
            </div>
            <div class="flex justify-end mt-6">
              <button @click="showDetailModal = false" class="px-4 py-2 text-sm bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200">
                {{ t('common.close') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <div v-if="showEditModal && selectedResource" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-full items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/50" @click="showEditModal = false"></div>
        <div class="relative bg-white rounded-xl shadow-xl max-w-lg w-full">
          <div class="p-6">
            <h2 class="text-lg font-semibold text-slate-800 mb-4">
              {{ t('sourceResources.editResource') }}
            </h2>
            <form @submit.prevent="updateResource" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.name') }}</label>
                <input v-model="formData.name" type="text" required class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.type') }}</label>
                <select v-model="formData.resource_type" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  <option v-for="type in resourceTypes" :key="type.value" :value="type.value">{{ type.label }}</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700">{{ t('sourceResources.form.boundNode') }}</label>
                <select v-model="formData.bound_node_id" class="mt-1 w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  <option :value="null">{{ t('sourceResources.form.selectNode') }}</option>
                  <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.name }}</option>
                </select>
              </div>
              <div class="flex justify-end gap-3 pt-4">
                <button type="button" @click="showEditModal = false" class="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">{{ t('common.cancel') }}</button>
                <button type="submit" class="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">{{ t('common.save') }}</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Modal -->
    <div v-if="showDeleteModal && selectedResource" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-full items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/50" @click="showDeleteModal = false"></div>
        <div class="relative bg-white rounded-xl shadow-xl max-w-sm w-full">
          <div class="p-6">
            <h2 class="text-lg font-semibold text-slate-800 mb-2">{{ t('sourceResources.deleteConfirm') }}</h2>
            <p class="text-sm text-slate-500 mb-4">{{ t('sourceResources.deleteConfirmDesc', { name: selectedResource.name }) }}</p>
            <div class="flex justify-end gap-3">
              <button @click="showDeleteModal = false" class="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg">{{ t('common.cancel') }}</button>
              <button @click="deleteResource" class="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700">{{ t('common.delete') }}</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
