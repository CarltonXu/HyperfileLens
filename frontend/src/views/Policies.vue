<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { policiesApi, backupTasksApi } from '@/api'
import {
  DocumentTextIcon,
  PlusIcon,
  ClockIcon,
  CalendarIcon,
  PlayIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  Cog6ToothIcon,
  TrashIcon,
  BoltIcon,
  PauseIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()

interface Policy {
  id: string | number
  name: string
  description?: string
  backup_task?: string | number
  backup_task_name?: string
  schedule_type: string
  schedule_config: {
    cron?: string
    interval_hours?: number
    time?: string
    day_of_week?: number
  }
  retention_days?: number
  enabled: boolean
  last_run?: string
  next_run?: string
  status?: string
}

const isLoading = ref(true)
const policies = ref<Policy[]>([])
const backupTasks = ref<any[]>([])
const searchQuery = ref('')
const showCreateModal = ref(false)

const newPolicy = ref<Partial<Policy>>({
  name: '',
  description: '',
  backup_task: undefined,
  schedule_type: 'daily',
  schedule_config: {
    time: '02:00',
    interval_hours: 24
  },
  retention_days: 30,
  enabled: true
})

const filteredPolicies = computed(() => {
  if (!searchQuery.value) return policies.value
  const query = searchQuery.value.toLowerCase()
  return policies.value.filter(p => 
    p.name.toLowerCase().includes(query)
  )
})

async function fetchPolicies() {
  isLoading.value = true
  try {
    const response = await policiesApi.list()
    policies.value = response.data.results || response.data
  } catch (error) {
    console.error('Failed to fetch policies:', error)
  } finally {
    isLoading.value = false
  }
}

async function fetchBackupTasks() {
  try {
    const response = await backupTasksApi.list({ page_size: 100 })
    backupTasks.value = response.data.results || response.data
  } catch (error) {
    console.error('Failed to fetch backup tasks:', error)
  }
}

async function createPolicy() {
  try {
    await policiesApi.create(newPolicy.value)
    showCreateModal.value = false
    newPolicy.value = {
      name: '',
      description: '',
      backup_task: undefined,
      schedule_type: 'daily',
      schedule_config: { time: '02:00', interval_hours: 24 },
      retention_days: 30,
      enabled: true
    }
    await fetchPolicies()
  } catch (error) {
    console.error('Failed to create policy:', error)
  }
}

async function togglePolicy(policy: Policy) {
  try {
    await policiesApi.update(policy.id, { enabled: !policy.enabled })
    await fetchPolicies()
  } catch (error) {
    console.error('Failed to toggle policy:', error)
  }
}

async function deletePolicy(policy: Policy) {
  if (!confirm(t('policies.confirmDelete'))) return
  try {
    await policiesApi.delete(policy.id)
    await fetchPolicies()
  } catch (error) {
    console.error('Failed to delete policy:', error)
  }
}

function getScheduleTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    hourly: t('policies.scheduleTypes.hourly'),
    daily: t('policies.scheduleTypes.daily'),
    weekly: t('policies.scheduleTypes.weekly'),
    monthly: t('policies.scheduleTypes.monthly'),
    manual: t('policies.scheduleTypes.manual')
  }
  return labels[type] || type
}

function getScheduleTypeIcon(type: string) {
  const icons: Record<string, any> = {
    hourly: BoltIcon,
    daily: CalendarIcon,
    weekly: CalendarIcon,
    monthly: CalendarIcon,
    manual: PlayIcon
  }
  return icons[type] || ClockIcon
}

function getScheduleTypeColor(type: string): string {
  const colors: Record<string, string> = {
    hourly: 'bg-amber-100 text-amber-600',
    daily: 'bg-blue-100 text-blue-600',
    weekly: 'bg-purple-100 text-purple-600',
    monthly: 'bg-indigo-100 text-indigo-600',
    manual: 'bg-slate-100 text-slate-600'
  }
  return colors[type] || 'bg-slate-100 text-slate-600'
}

onMounted(() => {
  fetchPolicies()
  fetchBackupTasks()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">{{ t('policies.title') }}</h1>
        <p class="text-slate-500 mt-1">{{ t('policies.subtitle') }}</p>
      </div>
      <button
        @click="showCreateModal = true"
        class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-violet-500 to-purple-600 rounded-lg hover:from-violet-600 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
      >
        <PlusIcon class="w-4 h-4" />
        {{ t('policies.form.addPolicy') }}
      </button>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('policies.stats.total') }}</p>
        <p class="text-xl font-bold text-slate-800 mt-1">{{ policies.length }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('policies.stats.enabled') }}</p>
        <p class="text-xl font-bold text-emerald-600 mt-1">{{ policies.filter(p => p.enabled).length }}</p>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p class="text-xs text-slate-500">{{ t('policies.stats.disabled') }}</p>
        <p class="text-xl font-bold text-slate-400 mt-1">{{ policies.filter(p => !p.enabled).length }}</p>
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
            class="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
        <button
          @click="fetchPolicies"
          class="inline-flex items-center gap-2 px-3 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50"
        >
          <ArrowPathIcon class="w-4 h-4" />
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- Policies List -->
    <div v-if="isLoading" class="flex items-center justify-center py-12">
      <div class="w-8 h-8 border-4 border-violet-200 border-t-violet-600 rounded-full animate-spin" />
    </div>

    <div v-else-if="filteredPolicies.length === 0" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
      <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <DocumentTextIcon class="w-8 h-8 text-slate-400" />
      </div>
      <h3 class="text-lg font-medium text-slate-800 mb-1">{{ t('policies.empty.title') }}</h3>
      <p class="text-slate-500">{{ t('policies.empty.description') }}</p>
    </div>

    <div v-else class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <table class="w-full">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('common.name') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('policies.form.scheduleType') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('common.status') }}</th>
            <th class="text-left text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('policies.form.nextRun') }}</th>
            <th class="text-right text-xs font-medium text-slate-500 uppercase tracking-wider px-6 py-3">{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="policy in filteredPolicies" :key="policy.id" class="hover:bg-slate-50 transition-colors">
            <td class="px-6 py-4">
              <div class="flex items-center gap-3">
                <div :class="['w-9 h-9 rounded-lg flex items-center justify-center', getScheduleTypeColor(policy.schedule_type)]">
                  <component :is="getScheduleTypeIcon(policy.schedule_type)" class="w-5 h-5" />
                </div>
                <div>
                  <p class="text-sm font-medium text-slate-800">{{ policy.name }}</p>
                  <p class="text-xs text-slate-500">{{ policy.backup_task_name || 'Task' }}</p>
                </div>
              </div>
            </td>
            <td class="px-6 py-4">
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                {{ getScheduleTypeLabel(policy.schedule_type) }}
              </span>
            </td>
            <td class="px-6 py-4">
              <button
                @click="togglePolicy(policy)"
                :class="[
                  'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors',
                  policy.enabled ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'
                ]"
              >
                <CheckCircleIcon v-if="policy.enabled" class="w-3.5 h-3.5" />
                <PauseIcon v-else class="w-3.5 h-3.5" />
                {{ policy.enabled ? t('common.enabled') : t('common.disabled') }}
              </button>
            </td>
            <td class="px-6 py-4 text-sm text-slate-500">
              {{ policy.next_run ? new Date(policy.next_run).toLocaleString() : '-' }}
            </td>
            <td class="px-6 py-4 text-right">
              <div class="flex items-center justify-end gap-2">
                <button
                  class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                  :title="t('common.settings')"
                >
                  <Cog6ToothIcon class="w-4 h-4" />
                </button>
                <button
                  @click="deletePolicy(policy)"
                  class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  :title="t('common.delete')"
                >
                  <TrashIcon class="w-4 h-4" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create Modal -->
    <Teleport to="body">
      <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="showCreateModal = false" />
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-lg">
          <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-slate-800">{{ t('policies.form.addPolicy') }}</h2>
            <button @click="showCreateModal = false" class="p-1 hover:bg-slate-100 rounded-lg">
              <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="p-6 space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('common.name') }}</label>
              <input v-model="newPolicy.name" type="text" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500" />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('policies.form.backupTask') }}</label>
              <select v-model="newPolicy.backup_task" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500">
                <option :value="undefined">Select Task</option>
                <option v-for="task in backupTasks" :key="task.id" :value="task.id">{{ task.name }}</option>
              </select>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('policies.form.scheduleType') }}</label>
                <select v-model="newPolicy.schedule_type" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500">
                  <option value="hourly">{{ t('policies.scheduleTypes.hourly') }}</option>
                  <option value="daily">{{ t('policies.scheduleTypes.daily') }}</option>
                  <option value="weekly">{{ t('policies.scheduleTypes.weekly') }}</option>
                  <option value="monthly">{{ t('policies.scheduleTypes.monthly') }}</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('policies.form.retention') }}</label>
                <input v-model.number="newPolicy.retention_days" type="number" min="1" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500" />
              </div>
            </div>
            <div v-if="newPolicy.schedule_type === 'daily'">
              <label class="block text-sm font-medium text-slate-700 mb-1">{{ t('policies.form.time') }}</label>
              <input v-model="newPolicy.schedule_config!.time" type="time" class="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500" />
            </div>
          </div>
          <div class="px-6 py-4 border-t border-slate-100 flex justify-end gap-3">
            <button @click="showCreateModal = false" class="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50">
              {{ t('common.cancel') }}
            </button>
            <button @click="createPolicy" class="px-4 py-2 text-sm text-white bg-violet-600 rounded-lg hover:bg-violet-700">
              {{ t('common.create') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
