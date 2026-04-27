<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { repositoriesApi, nodesApi } from '@/api'
import type { Repository } from '@/types/repository'
import type { ProxyNode } from '@/types/proxy'
import Pagination from '@/components/Pagination.vue'
import {
  PlusIcon,
  CircleStackIcon,
  CloudIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  Cog6ToothIcon,
  TrashIcon,
  CheckCircleIcon,
  LinkIcon,
  PlayIcon
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

const newRepo = ref({
  name: '',
  repository_type: 's3' as 'local' | 's3' | 'azure' | 'gcs' | 'nfs',
  description: '',
  bound_node: '' as string | null,
  config: {
    endpoint: '',
    bucket: '',
    region: '',
    path: ''
  },
  credentials: {
    access_key: '',
    secret_key: ''
  }
})

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

async function createRepository() {
  try {
    const payload = {
      name: newRepo.value.name,
      repository_type: newRepo.value.repository_type,
      description: newRepo.value.description,
      bound_node: newRepo.value.bound_node || null,
      config: newRepo.value.config,
      credentials: newRepo.value.credentials
    }
    await repositoriesApi.create(payload)
    showCreateModal.value = false
    resetForm()
    await fetchRepositories()
  } catch (error) {
    console.error('Failed to create repository:', error)
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
    repository_type: 's3',
    description: '',
    bound_node: '',
    config: { endpoint: '', bucket: '', region: '', path: '' },
    credentials: { access_key: '', secret_key: '' }
  }
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
    local: CircleStackIcon,
    nfs: CircleStackIcon,
    azure: CloudIcon,
    gcs: CloudIcon
  }
  return icons[type] || CircleStackIcon
}

function getRepoTypeColor(type: string): string {
  const colors: Record<string, string> = {
    s3: 'bg-orange-100 text-orange-600',
    local: 'bg-blue-100 text-blue-600',
    nfs: 'bg-purple-100 text-purple-600',
    azure: 'bg-sky-100 text-sky-600',
    gcs: 'bg-red-100 text-red-600'
  }
  return colors[type] || 'bg-slate-100 text-slate-600'
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
          <option value="local">Local</option>
          <option value="nfs">NFS</option>
          <option value="azure">Azure</option>
          <option value="gcs">GCS</option>
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
        <p class="text-sm text-slate-500 mb-3">{{ repo.description || repo.repository_type?.toUpperCase() }}</p>
        
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
          <span class="text-xs text-slate-400 uppercase">{{ repo.repository_type }}</span>
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
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
          <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white">
            <h2 class="text-lg font-semibold text-slate-800">{{ t('repository.form.addRepository') }}</h2>
            <button @click="showCreateModal = false" class="p-1 hover:bg-slate-100 rounded-lg">
              <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="p-6 space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('common.name') }} *</label>
              <input v-model="newRepo.name" type="text" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.form.repositoryType') }}</label>
              <select v-model="newRepo.repository_type" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="s3">Amazon S3 / S3 Compatible</option>
                <option value="local">Local Filesystem</option>
                <option value="nfs">NFS</option>
                <option value="azure">Azure Blob</option>
                <option value="gcs">Google Cloud Storage</option>
              </select>
            </div>
            
            <!-- S3 Configuration -->
            <div v-if="newRepo.repository_type === 's3'" class="space-y-3 p-3 bg-slate-50 rounded-lg">
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('sourceResources.form.endpoint') }}</label>
                <input v-model="newRepo.config.endpoint" type="text" placeholder="https://s3.amazonaws.com" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('sourceResources.form.bucket') }}</label>
                  <input v-model="newRepo.config.bucket" type="text" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('sourceResources.form.region') }}</label>
                  <input v-model="newRepo.config.region" type="text" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('sourceResources.form.accessKey') }}</label>
                  <input v-model="newRepo.credentials.access_key" type="text" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('sourceResources.form.secretKey') }}</label>
                  <input v-model="newRepo.credentials.secret_key" type="password" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
            </div>
            
            <!-- Local/NFS Configuration -->
            <div v-else-if="newRepo.repository_type === 'local' || newRepo.repository_type === 'nfs'" class="space-y-3 p-3 bg-slate-50 rounded-lg">
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('sourceResources.form.path') }}</label>
                <input v-model="newRepo.config.path" type="text" placeholder="/backup/hyperfilelens" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>
            
            <!-- Bound Node -->
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('sourceResources.form.boundNode') }}</label>
              <select v-model="newRepo.bound_node" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">{{ t('sourceResources.selectNode') }}</option>
                <option v-for="node in nodes" :key="node.id" :value="node.id">{{ node.name }}</option>
              </select>
              <p class="text-xs text-slate-500 mt-1">{{ t('repository.boundNodeHint') }}</p>
            </div>
            
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('common.description') }}</label>
              <textarea v-model="newRepo.description" rows="2" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <div class="px-6 py-4 border-t border-slate-100 flex justify-end gap-3 sticky bottom-0 bg-white">
            <button @click="showCreateModal = false" class="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50">
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
                <p class="font-medium text-slate-800">{{ selectedRepo.repository_type?.toUpperCase() }}</p>
                <p class="text-sm text-slate-500">{{ selectedRepo.config?.path || selectedRepo.config?.bucket }}</p>
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
