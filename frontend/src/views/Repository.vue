<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { repositoriesApi, nodesApi } from '@/api'
import { useAppStore } from '@/stores/app'
import type { Repository } from '@/types/repository'
import type { ProxyNode } from '@/types/proxy'
import Pagination from '@/components/Pagination.vue'
import {
  PlusIcon,
  CircleStackIcon,
  CloudIcon,
  ServerIcon,
  FolderIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  Cog6ToothIcon,
  TrashIcon,
  CheckCircleIcon,
  LinkIcon,
  PlayIcon,
  ChevronRightIcon,
  ExclamationCircleIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()

const isLoading = ref(true)
const repositories = ref<Repository[]>([])
const nodes = ref<ProxyNode[]>([])
const searchQuery = ref('')
const typeFilter = ref('')
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const selectedRepo = ref<Repository | null>(null)

// Pagination
const currentPage = ref(1)
const pageSize = ref(10)

// Repository type selection
const repoTypes = [
  { value: 's3', label: 'S3 对象存储', icon: CloudIcon, color: 'orange' },
  { value: 'nas', label: 'NAS/NFS/CIFS', icon: ServerIcon, color: 'purple' },
  { value: 'local', label: '本地文件系统', icon: FolderIcon, color: 'blue' }
]

// New repository form
const newRepo = ref({
  name: '',
  repo_type: 's3' as 's3' | 'nas' | 'local',
  description: '',
  bound_node: '' as string | null,
  // S3 config
  s3_config: {
    endpoint: '',
    bucket: '',
    region: '',
    prefix: '',
    access_key: '',
    secret_key: ''
  },
  // NAS config
  nas_config: {
    server: '',
    export_path: '',
    mount_type: 'nfs' as 'nfs' | 'cifs',
    mount_options: '',
    username: '',
    password: ''
  },
  // Local config
  local_config: {
    path: ''
  }
})

// Form validation errors
const formErrors = ref<Record<string, string>>({})

// Validate form before submission
function validateForm(): boolean {
  formErrors.value = {}
  
  // Name is required
  if (!newRepo.value.name.trim()) {
    formErrors.value.name = t('repository.validation.nameRequired')
  }
  
  // Validate based on repository type
  if (newRepo.value.repo_type === 's3') {
    if (!newRepo.value.s3_config.endpoint.trim()) {
      formErrors.value.endpoint = t('repository.validation.endpointRequired')
    }
    if (!newRepo.value.s3_config.bucket.trim()) {
      formErrors.value.bucket = t('repository.validation.bucketRequired')
    }
    if (!newRepo.value.s3_config.access_key.trim()) {
      formErrors.value.access_key = t('repository.validation.accessKeyRequired')
    }
    if (!newRepo.value.s3_config.secret_key.trim()) {
      formErrors.value.secret_key = t('repository.validation.secretKeyRequired')
    }
  } else if (newRepo.value.repo_type === 'nas') {
    if (!newRepo.value.nas_config.server.trim()) {
      formErrors.value.server = t('repository.validation.serverRequired')
    }
    if (!newRepo.value.nas_config.export_path.trim()) {
      formErrors.value.export_path = t('repository.validation.exportPathRequired')
    }
    if (newRepo.value.nas_config.mount_type === 'cifs') {
      if (!newRepo.value.nas_config.username.trim()) {
        formErrors.value.username = t('repository.validation.usernameRequired')
      }
      if (!newRepo.value.nas_config.password.trim()) {
        formErrors.value.password = t('repository.validation.passwordRequired')
      }
    }
    if (!newRepo.value.bound_node) {
      formErrors.value.bound_node = t('repository.validation.proxyRequired')
    }
  } else if (newRepo.value.repo_type === 'local') {
    if (!newRepo.value.bound_node) {
      formErrors.value.bound_node = t('repository.validation.proxyRequired')
    }
    if (!newRepo.value.local_config.path.trim()) {
      formErrors.value.path = t('repository.validation.pathRequired')
    }
  }
  
  return Object.keys(formErrors.value).length === 0
}

// Clear error for a field
function clearError(field: string) {
  delete formErrors.value[field]
}

// Available Sync Proxies (online + sync role)
const availableSyncProxies = computed(() => {
  return nodes.value.filter(node => 
    node.role === 'sync' && node.status === 'active'
  )
})

// Selected proxy for local filesystem
const selectedProxy = ref<ProxyNode | null>(null)
const proxyDirectories = ref<string[]>([])
const isLoadingDirectories = ref(false)
const currentPath = ref('')

// Fetch Sync Proxy directories
async function fetchProxyDirectories(proxyId: string, path: string = '/') {
  if (!proxyId) return
  isLoadingDirectories.value = true
  try {
    const response = await nodesApi.getDirectories(proxyId, path)
    proxyDirectories.value = response.data.directories || []
    currentPath.value = path
  } catch (error) {
    console.error('Failed to fetch directories:', error)
    proxyDirectories.value = []
  } finally {
    isLoadingDirectories.value = false
  }
}

// Handle proxy selection for local type
function handleProxySelect(proxyId: string) {
  newRepo.value.bound_node = proxyId
  selectedProxy.value = availableSyncProxies.value.find(p => p.id === proxyId) || null
  if (proxyId) {
    fetchProxyDirectories(proxyId, '/')
  } else {
    proxyDirectories.value = []
    currentPath.value = ''
  }
}

// Navigate to subdirectory
function navigateToDirectory(dir: string) {
  const newPath = currentPath.value === '/' ? `/${dir}` : `${currentPath.value}/${dir}`
  fetchProxyDirectories(newRepo.value.bound_node!, newPath)
}

// Navigate up
function navigateUp() {
  if (currentPath.value === '/' || !currentPath.value) return
  const parts = currentPath.value.split('/').filter(Boolean)
  parts.pop()
  const newPath = parts.length === 0 ? '/' : '/' + parts.join('/')
  fetchProxyDirectories(newRepo.value.bound_node!, newPath)
}

// Select current directory as backup path
function selectCurrentPath() {
  newRepo.value.local_config.path = currentPath.value
}

const filteredRepos = computed(() => {
  let result = repositories.value
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(r => 
      r.name.toLowerCase().includes(query) ||
      r.repository_type?.toLowerCase().includes(query)
    )
  }
  if (typeFilter.value) {
    result = result.filter(r => r.repository_type === typeFilter.value)
  }
  return result
})

// Paginated repos for display
const paginatedRepos = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredRepos.value.slice(start, end)
})

// Reset page when filters change
watch([searchQuery, typeFilter], () => {
  currentPage.value = 1
})

// Reset form when repo type changes
watch(() => newRepo.value.repo_type, () => {
  // Reset bound_node when switching away from local
  if (newRepo.value.repo_type !== 'local') {
    newRepo.value.bound_node = null
    selectedProxy.value = null
    proxyDirectories.value = []
    currentPath.value = ''
  }
})

const stats = computed(() => {
  const total = repositories.value.length
  const active = repositories.value.filter(r => r.status === 'active').length
  const initialized = repositories.value.filter(r => r.kopia_initialized).length
  const totalCapacity = repositories.value.reduce((sum, r) => sum + (r.capacity || 0), 0)
  const totalUsed = repositories.value.reduce((sum, r) => sum + (r.used_space || 0), 0)
  return { total, active, initialized, totalCapacity, totalUsed }
})

async function fetchRepositories() {
  isLoading.value = true
  try {
    const response = await repositoriesApi.list()
    repositories.value = response.data.results || response.data
  } catch (error) {
    console.error('Failed to fetch repositories:', error)
  } finally {
    isLoading.value = false
  }
}

async function fetchNodes() {
  try {
    const response = await nodesApi.list()
    nodes.value = response.data.results || response.data
  } catch (error) {
    console.error('Failed to fetch nodes:', error)
  }
}

// Get app store for toast
const appStore = useAppStore()

async function createRepository() {
  // Validate form first
  if (!validateForm()) {
    appStore.error(t('repository.validation.formInvalid'), t('repository.validation.checkFields'))
    return
  }
  
  try {
    let payload: any = {
      name: newRepo.value.name,
      repo_type: newRepo.value.repo_type,
      description: newRepo.value.description,
      bound_node: newRepo.value.bound_node || null
    }

    // Build config based on type
    if (newRepo.value.repo_type === 's3') {
      payload.config = {
        endpoint: newRepo.value.s3_config.endpoint,
        bucket: newRepo.value.s3_config.bucket,
        region: newRepo.value.s3_config.region,
        prefix: newRepo.value.s3_config.prefix
      }
      payload.credentials = {
        access_key: newRepo.value.s3_config.access_key,
        secret_key: newRepo.value.s3_config.secret_key
      }
    } else if (newRepo.value.repo_type === 'nas') {
      payload.config = {
        server: newRepo.value.nas_config.server,
        export_path: newRepo.value.nas_config.export_path,
        mount_type: newRepo.value.nas_config.mount_type,
        mount_options: newRepo.value.nas_config.mount_options
      }
      if (newRepo.value.nas_config.mount_type === 'cifs') {
        payload.credentials = {
          username: newRepo.value.nas_config.username,
          password: newRepo.value.nas_config.password
        }
      }
    } else if (newRepo.value.repo_type === 'local') {
      payload.config = {
        path: newRepo.value.local_config.path
      }
    }

    await repositoriesApi.create(payload)
    showCreateModal.value = false
    resetForm()
    await fetchRepositories()
    appStore.success(t('repository.createSuccess'))
  } catch (error: any) {
    console.error('Failed to create repository:', error)
    // Handle backend validation errors
    const errorData = error?.response?.data
    if (errorData) {
      if (errorData.name) {
        formErrors.value.name = errorData.name[0] || errorData.name
      }
      if (errorData.config) {
        // Map config errors to specific fields
        const configError = errorData.config
        if (typeof configError === 'string') {
          appStore.error(t('repository.validation.configError'), configError)
        }
      }
      if (errorData.credentials) {
        appStore.error(t('repository.validation.credentialsError'), errorData.credentials)
      }
      if (errorData.detail || errorData.non_field_errors) {
        appStore.error(t('common.error'), errorData.detail || errorData.non_field_errors)
      }
    } else {
      appStore.error(t('repository.createFailed'))
    }
  }
}

async function deleteRepository(repo: Repository) {
  if (!confirm(t('repository.confirmDelete'))) return
  try {
    await repositoriesApi.delete(repo.id)
    await fetchRepositories()
  } catch (error) {
    console.error('Failed to delete repository:', error)
  }
}

async function testConnection(repo: Repository) {
  try {
    await repositoriesApi.testConnection(repo.id)
    alert(t('common.connectionSuccess'))
  } catch (error) {
    console.error('Connection test failed:', error)
    alert(t('common.connectionFailed'))
  }
}

async function initKopia(repo: Repository) {
  try {
    await repositoriesApi.initKopia(repo.id)
    alert(t('repository.kopiaInitialized'))
    await fetchRepositories()
  } catch (error) {
    console.error('Failed to initialize Kopia:', error)
    alert(t('common.operationFailed'))
  }
}

function resetForm() {
  newRepo.value = {
    name: '',
    repo_type: 's3',
    description: '',
    bound_node: null,
    s3_config: {
      endpoint: '',
      bucket: '',
      region: '',
      prefix: '',
      access_key: '',
      secret_key: ''
    },
    nas_config: {
      server: '',
      export_path: '',
      mount_type: 'nfs',
      mount_options: '',
      username: '',
      password: ''
    },
    local_config: {
      path: ''
    }
  }
  formErrors.value = {}
  selectedProxy.value = null
  proxyDirectories.value = []
  currentPath.value = ''
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function getRepoTypeIcon(type: string) {
  const icons: Record<string, any> = {
    s3: CloudIcon,
    local: FolderIcon,
    nas: ServerIcon,
    nfs: ServerIcon,
    azure: CloudIcon,
    gcs: CloudIcon
  }
  return icons[type] || CircleStackIcon
}

function getRepoTypeColor(type: string): string {
  const colors: Record<string, string> = {
    s3: 'bg-orange-100 text-orange-600',
    local: 'bg-blue-100 text-blue-600',
    nas: 'bg-purple-100 text-purple-600',
    nfs: 'bg-purple-100 text-purple-600',
    azure: 'bg-sky-100 text-sky-600',
    gcs: 'bg-red-100 text-red-600'
  }
  return colors[type] || 'bg-slate-100 text-slate-600'
}

function getRepoTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    s3: 'S3',
    local: t('repository.types.local'),
    nas: 'NAS',
    nfs: 'NFS',
    azure: 'Azure',
    gcs: 'GCS'
  }
  return labels[type] || type.toUpperCase()
}

function getNodeName(nodeId: string | null | undefined): string {
  if (!nodeId) return t('sourceResources.noBoundNode')
  const node = nodes.value.find((n: ProxyNode) => String(n.id) === nodeId)
  return node?.name || nodeId
}

onMounted(() => {
  fetchRepositories()
  fetchNodes()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">{{ t('repository.title') }}</h1>
        <p class="text-slate-500 mt-1">{{ t('repository.subtitle') }}</p>
      </div>
      <button
        @click="showCreateModal = true"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-blue-500 to-cyan-600 rounded-lg hover:from-blue-600 hover:to-cyan-700 transition-all shadow-md hover:shadow-lg"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t('repository.form.addRepository') }}
      </button>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('repository.stats.total') }}</p>
        <p class="text-xl font-bold text-slate-800 mt-1">{{ stats.total }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('repository.stats.active') }}</p>
        <p class="text-xl font-bold text-emerald-600 mt-1">{{ stats.active }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('repository.stats.totalCapacity') }}</p>
        <p class="text-xl font-bold text-slate-800 mt-1">{{ formatBytes(stats.totalCapacity) }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('repository.stats.usedSpace') }}</p>
        <p class="text-xl font-bold text-blue-600 mt-1">{{ formatBytes(stats.totalUsed) }}</p>
      </div>
    </div>

    <!-- Search & Filters -->
    <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <div class="flex flex-wrap items-center gap-3">
        <div class="relative flex-1 min-w-[200px]">
          <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('common.search')"
            class="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          v-model="typeFilter"
          class="px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">{{ t('sourceResources.allTypes') }}</option>
          <option value="s3">S3</option>
          <option value="local">{{ t('repository.types.local') }}</option>
          <option value="nas">NAS/NFS</option>
        </select>
        <button
          @click="fetchRepositories"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Repositories Grid -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <div class="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
    </div>

    <div v-else-if="filteredRepos.length === 0" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
      <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <CircleStackIcon class="w-8 h-8 text-slate-400" />
      </div>
      <h3 class="text-lg font-medium text-slate-800 mb-1">{{ t('repository.empty.title') }}</h3>
      <p class="text-slate-500">{{ t('repository.empty.description') }}</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="repo in paginatedRepos"
        :key="repo.id"
        class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between mb-4">
          <div :class="['w-10 h-10 rounded-lg flex items-center justify-center', getRepoTypeColor(repo.repository_type)]">
            <component :is="getRepoTypeIcon(repo.repository_type)" class="w-5 h-5" />
          </div>
          <div class="flex items-center gap-2">
            <span v-if="repo.kopia_initialized" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
              <CheckCircleIcon class="w-3 h-3" />
              Kopia
            </span>
            <span :class="[
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
              repo.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'
            ]">
              {{ repo.status === 'active' ? t('common.active') : t('common.inactive') }}
            </span>
          </div>
        </div>
        
        <h3 class="text-base font-semibold text-slate-800 mb-1">{{ repo.name }}</h3>
        <p class="text-sm text-slate-500 mb-3">{{ repo.description || getRepoTypeLabel(repo.repository_type) }}</p>
        
        <!-- Bound Node -->
        <div class="flex items-center gap-2 text-sm text-slate-600 mb-3">
          <LinkIcon class="w-4 h-4" />
          <span>{{ getNodeName(repo.bound_node) }}</span>
        </div>
        
        <!-- Storage Progress -->
        <div class="mb-4">
          <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span>{{ t('repository.stats.usedSpace') }}</span>
            <span>{{ formatBytes(repo.used_space || 0) }} / {{ formatBytes(repo.capacity || 0) }}</span>
          </div>
          <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              class="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all"
              :style="{ width: `${repo.capacity ? ((repo.used_space || 0) / repo.capacity) * 100 : 0}%` }"
            />
          </div>
        </div>
        
        <div class="flex items-center justify-between pt-3 border-t border-slate-100">
          <span class="text-xs text-slate-400 uppercase">{{ getRepoTypeLabel(repo.repository_type) }}</span>
          <div class="flex items-center gap-1">
            <button
              v-if="!repo.kopia_initialized && repo.bound_node"
              @click="initKopia(repo)"
              class="p-1.5 text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
              :title="t('repository.initKopia')"
            >
              <PlayIcon class="w-4 h-4" />
            </button>
            <button
              v-if="repo.bound_node"
              @click="testConnection(repo)"
              class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              :title="t('sourceResources.testConnection')"
            >
              <LinkIcon class="w-4 h-4" />
            </button>
            <button
              @click="selectedRepo = repo; showDetailModal = true"
              class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              :title="t('common.details')"
            >
              <Cog6ToothIcon class="w-4 h-4" />
            </button>
            <button
              @click="deleteRepository(repo)"
              class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              :title="t('common.delete')"
            >
              <TrashIcon class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <Pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total-items="filteredRepos.length"
    />

    <!-- Create Modal -->
    <Teleport to="body">
      <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showCreateModal = false" />
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
          <!-- Fixed Header -->
          <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between flex-shrink-0">
            <h2 class="text-lg font-semibold text-slate-800">{{ t('repository.form.addRepository') }}</h2>
            <button @click="showCreateModal = false" class="p-1 hover:bg-slate-100 rounded-lg">
              <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <!-- Fixed Repository Type Selection -->
          <div class="px-6 py-4 border-b border-slate-100 bg-slate-50 flex-shrink-0">
            <label class="block text-sm font-medium text-slate-700 mb-3">{{ t('repository.form.repositoryType') }}</label>
            <div class="grid grid-cols-3 gap-3">
              <button
                v-for="type in repoTypes"
                :key="type.value"
                @click="newRepo.repo_type = type.value as any"
                :class="[
                  'flex flex-col items-center gap-2 p-3 rounded-xl border-2 transition-all',
                  newRepo.repo_type === type.value 
                    ? 'border-blue-500 bg-white shadow-sm' 
                    : 'border-slate-200 bg-white hover:border-slate-300'
                ]"
              >
                <div :class="[
                  'w-9 h-9 rounded-lg flex items-center justify-center',
                  type.color === 'orange' ? 'bg-orange-100 text-orange-600' :
                  type.color === 'purple' ? 'bg-purple-100 text-purple-600' :
                  'bg-blue-100 text-blue-600'
                ]">
                  <component :is="type.icon" class="w-5 h-5" />
                </div>
                <span class="text-xs font-medium text-slate-700">{{ type.label }}</span>
              </button>
            </div>
          </div>

          <!-- Scrollable Content Area -->
          <div class="flex-1 overflow-y-auto p-6 space-y-4">

            <!-- Basic Info -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('common.name') }} *</label>
                <input 
                  v-model="newRepo.name" 
                  type="text" 
                  :placeholder="t('repository.form.namePlaceholder')" 
                  :class="['w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2', 
                    formErrors.name ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 focus:ring-blue-500']"
                  @input="clearError('name')"
                />
                <p v-if="formErrors.name" class="mt-1 text-xs text-red-500">{{ formErrors.name }}</p>
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('common.description') }}</label>
                <input v-model="newRepo.description" type="text" :placeholder="t('repository.form.descPlaceholder')" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>

            <!-- S3 Configuration -->
            <div v-if="newRepo.repo_type === 's3'" class="space-y-4 p-4 bg-orange-50 rounded-xl border border-orange-100">
              <div class="flex items-start gap-2 text-sm text-orange-700 bg-orange-100 rounded-lg p-3">
                <ExclamationCircleIcon class="w-5 h-5 flex-shrink-0 mt-0.5" />
                <div>
                  <p class="font-medium">{{ t('repository.s3.hint') }}</p>
                  <p class="mt-1 text-xs text-orange-600">{{ t('repository.s3.hintDetail') }}</p>
                </div>
              </div>
              
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.s3.endpoint') }}</label>
                <input 
                  v-model="newRepo.s3_config.endpoint" 
                  type="text" 
                  placeholder="https://s3.amazonaws.com" 
                  :class="['w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2',
                    formErrors.endpoint ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 focus:ring-blue-500']"
                  @input="clearError('endpoint')"
                />
                <p class="text-xs text-slate-500 mt-1">{{ t('repository.s3.endpointHint') }}</p>
                <p v-if="formErrors.endpoint" class="mt-1 text-xs text-red-500">{{ formErrors.endpoint }}</p>
              </div>
              
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.s3.bucket') }} *</label>
                  <input 
                    v-model="newRepo.s3_config.bucket" 
                    type="text" 
                    placeholder="my-backup-bucket" 
                    :class="['w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2',
                      formErrors.bucket ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 focus:ring-blue-500']"
                    @input="clearError('bucket')"
                  />
                  <p v-if="formErrors.bucket" class="mt-1 text-xs text-red-500">{{ formErrors.bucket }}</p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.s3.region') }}</label>
                  <input v-model="newRepo.s3_config.region" type="text" placeholder="us-east-1" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.s3.prefix') }}</label>
                <input v-model="newRepo.s3_config.prefix" type="text" placeholder="backups/hyperfilelens" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                <p class="text-xs text-slate-500 mt-1">{{ t('repository.s3.prefixHint') }}</p>
              </div>
              
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.s3.accessKey') }} *</label>
                  <input 
                    v-model="newRepo.s3_config.access_key" 
                    type="text" 
                    placeholder="AKIAIOSFODNN7EXAMPLE" 
                    :class="['w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2',
                      formErrors.access_key ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 focus:ring-blue-500']"
                    @input="clearError('access_key')"
                  />
                  <p v-if="formErrors.access_key" class="mt-1 text-xs text-red-500">{{ formErrors.access_key }}</p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.s3.secretKey') }} *</label>
                  <input 
                    v-model="newRepo.s3_config.secret_key" 
                    type="password" 
                    placeholder="••••••••••••••••" 
                    :class="['w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2',
                      formErrors.secret_key ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 focus:ring-blue-500']"
                    @input="clearError('secret_key')"
                  />
                  <p v-if="formErrors.secret_key" class="mt-1 text-xs text-red-500">{{ formErrors.secret_key }}</p>
                </div>
              </div>
            </div>

            <!-- NAS Configuration -->
            <div v-if="newRepo.repo_type === 'nas'" class="space-y-4 p-4 bg-purple-50 rounded-xl border border-purple-100">
              <div class="flex items-start gap-2 text-sm text-purple-700 bg-purple-100 rounded-lg p-3">
                <ExclamationCircleIcon class="w-5 h-5 flex-shrink-0 mt-0.5" />
                <div>
                  <p class="font-medium">{{ t('repository.nas.hint') }}</p>
                  <p class="mt-1 text-xs text-purple-600">{{ t('repository.nas.hintDetail') }}</p>
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.nas.mountType') }}</label>
                <div class="grid grid-cols-2 gap-3">
                  <button
                    @click="newRepo.nas_config.mount_type = 'nfs'"
                    :class="[
                      'flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all text-sm font-medium',
                      newRepo.nas_config.mount_type === 'nfs' 
                        ? 'border-purple-500 bg-purple-100 text-purple-700' 
                        : 'border-slate-200 text-slate-600 hover:border-slate-300'
                    ]"
                  >
                    NFS
                  </button>
                  <button
                    @click="newRepo.nas_config.mount_type = 'cifs'"
                    :class="[
                      'flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all text-sm font-medium',
                      newRepo.nas_config.mount_type === 'cifs' 
                        ? 'border-purple-500 bg-purple-100 text-purple-700' 
                        : 'border-slate-200 text-slate-600 hover:border-slate-300'
                    ]"
                  >
                    CIFS/SMB
                  </button>
                </div>
              </div>
              
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.nas.server') }} *</label>
                  <input 
                    v-model="newRepo.nas_config.server" 
                    type="text" 
                    placeholder="192.168.1.100 或 nas.example.com" 
                    :class="['w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2',
                      formErrors.server ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 focus:ring-blue-500']"
                    @input="clearError('server')"
                  />
                  <p v-if="formErrors.server" class="mt-1 text-xs text-red-500">{{ formErrors.server }}</p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.nas.exportPath') }} *</label>
                  <input 
                    v-model="newRepo.nas_config.export_path" 
                    type="text" 
                    :placeholder="newRepo.nas_config.mount_type === 'nfs' ? '/export/backup' : '/share/backup'" 
                    :class="['w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2',
                      formErrors.export_path ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 focus:ring-blue-500']"
                    @input="clearError('export_path')"
                  />
                  <p v-if="formErrors.export_path" class="mt-1 text-xs text-red-500">{{ formErrors.export_path }}</p>
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.nas.mountOptions') }}</label>
                <input v-model="newRepo.nas_config.mount_options" type="text" :placeholder="newRepo.nas_config.mount_type === 'nfs' ? 'rw,hard,intr' : 'vers=3.0,iocharset=utf8'" class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                <p class="text-xs text-slate-500 mt-1">{{ t('repository.nas.mountOptionsHint') }}</p>
              </div>

              <!-- CIFS credentials -->
              <div v-if="newRepo.nas_config.mount_type === 'cifs'" class="grid grid-cols-2 gap-4 p-3 bg-white rounded-lg">
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.nas.username') }} *</label>
                  <input 
                    v-model="newRepo.nas_config.username" 
                    type="text" 
                    placeholder="username" 
                    :class="['w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2',
                      formErrors.username ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 focus:ring-blue-500']"
                    @input="clearError('username')"
                  />
                  <p v-if="formErrors.username" class="mt-1 text-xs text-red-500">{{ formErrors.username }}</p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.nas.password') }} *</label>
                  <input 
                    v-model="newRepo.nas_config.password" 
                    type="password" 
                    placeholder="••••••••" 
                    :class="['w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2',
                      formErrors.password ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 focus:ring-blue-500']"
                    @input="clearError('password')"
                  />
                  <p v-if="formErrors.password" class="mt-1 text-xs text-red-500">{{ formErrors.password }}</p>
                </div>
              </div>

              <!-- Bound Sync Proxy for NAS -->
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.boundSyncProxy') }} *</label>
                <select 
                  v-model="newRepo.bound_node" 
                  :class="['w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2',
                    formErrors.bound_node ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 focus:ring-blue-500']"
                  @change="clearError('bound_node')"
                >
                  <option value="">{{ t('repository.selectSyncProxy') }}</option>
                  <option v-for="proxy in availableSyncProxies" :key="proxy.id" :value="proxy.id">
                    {{ proxy.name }} ({{ proxy.hostname || proxy.id }})
                  </option>
                </select>
                <p v-if="formErrors.bound_node" class="mt-1 text-xs text-red-500">{{ formErrors.bound_node }}</p>
                <p class="text-xs text-slate-500 mt-1">{{ t('repository.boundSyncProxyHint') }}</p>
              </div>
            </div>

            <!-- Local Filesystem Configuration -->
            <div v-if="newRepo.repo_type === 'local'" class="space-y-4 p-4 bg-blue-50 rounded-xl border border-blue-100">
              <div class="flex items-start gap-2 text-sm text-blue-700 bg-blue-100 rounded-lg p-3">
                <ExclamationCircleIcon class="w-5 h-5 flex-shrink-0 mt-0.5" />
                <div>
                  <p class="font-medium">{{ t('repository.local.hint') }}</p>
                  <p class="mt-1 text-xs text-blue-600">{{ t('repository.local.hintDetail') }}</p>
                </div>
              </div>

              <!-- Select Sync Proxy -->
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.boundSyncProxy') }} *</label>
                <select 
                  :value="newRepo.bound_node || ''" 
                  @change="handleProxySelect(($event.target as HTMLSelectElement).value)"
                  :class="['w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2',
                    formErrors.bound_node ? 'border-red-300 focus:ring-red-500' : 'border-slate-200 focus:ring-blue-500']"
                >
                  <option value="">{{ t('repository.selectSyncProxy') }}</option>
                  <option v-for="proxy in availableSyncProxies" :key="proxy.id" :value="proxy.id">
                    {{ proxy.name }} ({{ proxy.hostname || proxy.id }})
                  </option>
                </select>
                <p v-if="formErrors.bound_node" class="mt-1 text-xs text-red-500">{{ formErrors.bound_node }}</p>
                <p class="text-xs text-slate-500 mt-1">{{ t('repository.boundSyncProxyHint') }}</p>
              </div>

              <!-- Directory Browser -->
              <div v-if="newRepo.bound_node" class="bg-white rounded-lg border border-slate-200">
                <div class="px-3 py-2 border-b border-slate-100 flex items-center justify-between">
                  <div class="flex items-center gap-2 text-sm">
                    <FolderIcon class="w-4 h-4 text-slate-400" />
                    <span class="text-slate-600">{{ t('repository.local.selectDirectory') }}</span>
                  </div>
                  <button
                    v-if="currentPath !== '/'"
                    @click="navigateUp"
                    class="text-xs text-blue-600 hover:text-blue-700"
                  >
                    {{ t('repository.local.goUp') }}
                  </button>
                </div>
                
                <!-- Current Path -->
                <div class="px-3 py-2 bg-slate-50 border-b border-slate-100">
                  <code class="text-sm text-slate-700">{{ currentPath || '/' }}</code>
                </div>

                <!-- Loading -->
                <div v-if="isLoadingDirectories" class="flex items-center justify-center py-8">
                  <div class="w-6 h-6 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
                </div>

                <!-- Directory List -->
                <div v-else class="max-h-48 overflow-y-auto">
                  <div v-if="proxyDirectories.length === 0" class="py-6 text-center text-sm text-slate-500">
                    {{ t('repository.local.noSubdirectories') }}
                  </div>
                  <button
                    v-for="dir in proxyDirectories"
                    :key="dir"
                    @click="navigateToDirectory(dir)"
                    class="w-full px-3 py-2 flex items-center gap-2 hover:bg-slate-50 text-left text-sm"
                  >
                    <FolderIcon class="w-4 h-4 text-yellow-500" />
                    <span class="text-slate-700">{{ dir }}</span>
                    <ChevronRightIcon class="w-4 h-4 text-slate-400 ml-auto" />
                  </button>
                </div>

                <!-- Select Current Path -->
                <div class="px-3 py-2 border-t border-slate-100">
                  <button
                    @click="selectCurrentPath"
                    class="w-full py-2 text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    {{ t('repository.local.useCurrentPath') }}
                  </button>
                </div>
              </div>
              
              <!-- Selected Path Display -->
              <div v-if="newRepo.local_config.path" class="flex items-center gap-2 p-3 bg-green-50 rounded-lg">
                <CheckCircleIcon class="w-5 h-5 text-green-600" />
                <span class="text-sm text-green-700">{{ t('repository.local.selectedPath') }}: <code class="bg-green-100 px-1 rounded">{{ newRepo.local_config.path }}</code></span>
              </div>
              
              <!-- Path Error -->
              <p v-if="formErrors.path" class="text-xs text-red-500">{{ formErrors.path }}</p>

              <!-- No Sync Proxy Available Warning -->
              <div v-if="availableSyncProxies.length === 0" class="flex items-start gap-2 p-3 bg-amber-50 rounded-lg border border-amber-200">
                <ExclamationCircleIcon class="w-5 h-5 text-amber-600 flex-shrink-0" />
                <div>
                  <p class="text-sm font-medium text-amber-700">{{ t('repository.local.noSyncProxy') }}</p>
                  <p class="text-xs text-amber-600 mt-1">{{ t('repository.local.noSyncProxyHint') }}</p>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Fixed Footer -->
          <div class="px-6 py-4 border-t border-slate-100 flex justify-end gap-3 flex-shrink-0 bg-white">
            <button @click="showCreateModal = false; resetForm()" class="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50">
              {{ t('common.cancel') }}
            </button>
            <button @click="createRepository" class="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700">
              {{ t('common.create') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Detail Modal -->
    <Teleport to="body">
      <div v-if="showDetailModal && selectedRepo" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showDetailModal = false" />
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-lg">
          <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-slate-800">{{ selectedRepo.name }}</h2>
            <button @click="showDetailModal = false" class="p-1 hover:bg-slate-100 rounded-lg">
              <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="p-6 space-y-4">
            <div class="flex items-center gap-3">
              <div :class="['w-12 h-12 rounded-lg flex items-center justify-center', getRepoTypeColor(selectedRepo.repository_type)]">
                <component :is="getRepoTypeIcon(selectedRepo.repository_type)" class="w-6 h-6" />
              </div>
              <div>
                <p class="font-medium text-slate-800">{{ getRepoTypeLabel(selectedRepo.repository_type) }}</p>
                <p class="text-sm text-slate-500">{{ selectedRepo.config?.path || selectedRepo.config?.bucket || selectedRepo.config?.server }}</p>
              </div>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
              <div class="bg-slate-50 rounded-lg p-3">
                <p class="text-xs text-slate-500">{{ t('repository.stats.totalCapacity') }}</p>
                <p class="font-semibold text-slate-800">{{ formatBytes(selectedRepo.capacity || 0) }}</p>
              </div>
              <div class="bg-slate-50 rounded-lg p-3">
                <p class="text-xs text-slate-500">{{ t('repository.stats.usedSpace') }}</p>
                <p class="font-semibold text-slate-800">{{ formatBytes(selectedRepo.used_space || 0) }}</p>
              </div>
            </div>
            
            <div class="bg-slate-50 rounded-lg p-3">
              <p class="text-xs text-slate-500 mb-1">{{ t('sourceResources.boundNode') }}</p>
              <p class="text-sm text-slate-700">{{ getNodeName(selectedRepo.bound_node) }}</p>
            </div>
            
            <div class="flex items-center gap-2">
              <span :class="[
                'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                selectedRepo.kopia_initialized ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'
              ]">
                <CheckCircleIcon v-if="selectedRepo.kopia_initialized" class="w-3 h-3" />
                {{ selectedRepo.kopia_initialized ? t('repository.kopiaInitialized') : t('repository.kopiaNotInitialized') }}
              </span>
            </div>
            
            <div v-if="selectedRepo.description" class="bg-slate-50 rounded-lg p-3">
              <p class="text-xs text-slate-500 mb-1">{{ t('common.description') }}</p>
              <p class="text-sm text-slate-700">{{ selectedRepo.description }}</p>
            </div>
          </div>
          <div class="px-6 py-4 border-t border-slate-100 flex justify-end">
            <button @click="showDetailModal = false" class="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50">
              {{ t('common.cancel') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
