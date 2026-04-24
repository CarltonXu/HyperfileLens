<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { repositoriesApi } from '@/api'
import type { Repository } from '@/types/repository'
import {
  ServerStackIcon,
  PlusIcon,
  CircleStackIcon,
  CloudIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  Cog6ToothIcon,
  TrashIcon,
  CheckCircleIcon,
  ExclamationCircleIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()

const isLoading = ref(true)
const repositories = ref<Repository[]>([])
const searchQuery = ref('')
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const selectedRepo = ref<Repository | null>(null)

const newRepo = ref({
  name: '',
  repository_type: 's3' as 'local' | 's3' | 'azure' | 'gcs' | 'nfs' | 'smb',
  path: '',
  description: '',
  config: {
    endpoint: '',
    bucket: '',
    region: '',
    access_key: '',
    secret_key: ''
  }
})

const filteredRepos = computed(() => {
  if (!searchQuery.value) return repositories.value
  const query = searchQuery.value.toLowerCase()
  return repositories.value.filter(r => 
    r.name.toLowerCase().includes(query) ||
    r.repository_type?.toLowerCase().includes(query)
  )
})

const totalCapacity = computed(() => {
  return repositories.value.reduce((sum, r) => sum + (r.capacity_bytes || 0), 0)
})

const totalUsed = computed(() => {
  return repositories.value.reduce((sum, r) => sum + (r.used_bytes || 0), 0)
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

async function createRepository() {
  try {
    await repositoriesApi.create(newRepo.value)
    showCreateModal.value = false
    newRepo.value = {
      name: '',
      repository_type: 's3',
      path: '',
      description: '',
      config: { endpoint: '', bucket: '', region: '', access_key: '', secret_key: '' }
    }
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
    smb: ServerStackIcon,
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
    smb: 'bg-emerald-100 text-emerald-600',
    azure: 'bg-sky-100 text-sky-600',
    gcs: 'bg-red-100 text-red-600'
  }
  return colors[type] || 'bg-slate-100 text-slate-600'
}

onMounted(() => {
  fetchRepositories()
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
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('repository.stats.total') }}</p>
        <p class="text-xl font-bold text-slate-800 mt-1">{{ repositories.length }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('repository.stats.totalCapacity') }}</p>
        <p class="text-xl font-bold text-slate-800 mt-1">{{ formatBytes(totalCapacity) }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('repository.stats.usedSpace') }}</p>
        <p class="text-xl font-bold text-blue-600 mt-1">{{ formatBytes(totalUsed) }}</p>
      </div>
    </div>

    <!-- Search -->
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
        v-for="repo in filteredRepos"
        :key="repo.id"
        class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between mb-4">
          <div :class="['w-10 h-10 rounded-lg flex items-center justify-center', getRepoTypeColor(repo.repository_type)]">
            <component :is="getRepoTypeIcon(repo.repository_type)" class="w-5 h-5" />
          </div>
          <div class="flex items-center gap-1">
            <span :class="[
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
              repo.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'
            ]">
              <CheckCircleIcon v-if="repo.status === 'active'" class="w-3 h-3" />
              <ExclamationCircleIcon v-else class="w-3 h-3" />
              {{ repo.status === 'active' ? t('common.active') : t('common.inactive') }}
            </span>
          </div>
        </div>
        
        <h3 class="text-base font-semibold text-slate-800 mb-1">{{ repo.name }}</h3>
        <p class="text-sm text-slate-500 mb-4">{{ repo.description || repo.repository_type?.toUpperCase() }}</p>
        
        <div class="mb-4">
          <div class="flex items-center justify-between text-xs text-slate-500 mb-1">
            <span>{{ t('repository.stats.usedSpace') }}</span>
            <span>{{ formatBytes(repo.used_bytes || 0) }} / {{ formatBytes(repo.capacity_bytes || 0) }}</span>
          </div>
          <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              class="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all"
              :style="{ width: `${repo.capacity_bytes ? ((repo.used_bytes || 0) / repo.capacity_bytes) * 100 : 0}%` }"
            />
          </div>
        </div>
        
        <div class="flex items-center justify-between pt-3 border-t border-slate-100">
          <span class="text-xs text-slate-400 uppercase">{{ repo.repository_type }}</span>
          <div class="flex items-center gap-2">
            <button
              @click="selectedRepo = repo; showDetailModal = true"
              class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              :title="t('common.settings')"
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

    <!-- Create Modal -->
    <Teleport to="body">
      <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showCreateModal = false" />
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-lg">
          <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-slate-800">{{ t('repository.form.addRepository') }}</h2>
            <button @click="showCreateModal = false" class="p-1 hover:bg-slate-100 rounded-lg">
              <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="p-6 space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('common.name') }}</label>
              <input v-model="newRepo.name" type="text" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.form.repositoryType') }}</label>
              <select v-model="newRepo.repository_type" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="s3">Amazon S3</option>
                <option value="local">Local Filesystem</option>
                <option value="nfs">NFS</option>
                <option value="azure">Azure Blob</option>
                <option value="gcs">Google Cloud Storage</option>
              </select>
            </div>
            <div v-if="newRepo.repository_type === 's3'" class="space-y-3">
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">Endpoint</label>
                  <input v-model="newRepo.config.endpoint" type="text" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">Bucket</label>
                  <input v-model="newRepo.config.bucket" type="text" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">Region</label>
                <input v-model="newRepo.config.region" type="text" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>
            <div v-else>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('repository.form.path') }}</label>
              <input v-model="newRepo.path" type="text" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <div class="px-6 py-4 border-t border-slate-100 flex justify-end gap-3">
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
                <p class="font-semibold text-slate-800">{{ formatBytes(selectedRepo.capacity_bytes || 0) }}</p>
              </div>
              <div class="bg-slate-50 rounded-lg p-3">
                <p class="text-xs text-slate-500">{{ t('repository.stats.usedSpace') }}</p>
                <p class="font-semibold text-slate-800">{{ formatBytes(selectedRepo.used_bytes || 0) }}</p>
              </div>
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
