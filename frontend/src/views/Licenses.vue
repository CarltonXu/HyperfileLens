<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="sm:flex sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900 dark:text-white">{{ t('licenses.title') }}</h1>
        <p class="mt-2 text-sm text-gray-700 dark:text-gray-300">
          {{ t('licenses.description') || 'Manage product licenses and authorization' }}
        </p>
      </div>
      <div class="mt-4 sm:mt-0 flex gap-2">
        <button
          type="button"
          class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
          @click="showMachineCodeDialog = true"
        >
          <ComputerDesktopIcon class="-ml-0.5 mr-1.5 h-5 w-5 text-gray-400" aria-hidden="true" />
          {{ t('licenses.exportMachineCode') || 'Export Machine Code' }}
        </button>
        <button
          type="button"
          class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
          @click="showActivateDialog = true"
        >
          <KeyIcon class="-ml-0.5 mr-1.5 h-5 w-5 text-white" aria-hidden="true" />
          {{ t('licenses.activateLicense') || 'Activate License' }}
        </button>
      </div>
    </div>

    <!-- Current License Status -->
    <div v-if="currentLicense" class="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
      <div class="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">
              {{ t('licenses.currentLicense') || 'Current License' }}
            </h3>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {{ currentLicense.license_key }}
            </p>
          </div>
          <div class="flex items-center gap-2">
            <span 
              class="inline-flex items-center rounded-full px-3 py-1 text-sm font-medium"
              :class="currentLicense.is_valid ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'"
            >
              {{ currentLicense.is_valid ? (t('licenses.active') || 'Active') : (t('licenses.expired') || 'Expired') }}
            </span>
          </div>
        </div>
      </div>
      
      <!-- License Details -->
      <div class="px-6 py-4">
        <dl class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">{{ t('licenses.tenant') || 'Tenant' }}</dt>
            <dd class="mt-1 text-sm text-gray-900 dark:text-white">{{ currentLicense.tenant_name }}</dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">{{ t('licenses.issuedAt') || 'Issued At' }}</dt>
            <dd class="mt-1 text-sm text-gray-900 dark:text-white">{{ formatDate(currentLicense.issued_at) }}</dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">{{ t('licenses.expiresAt') || 'Expires At' }}</dt>
            <dd class="mt-1 text-sm text-gray-900 dark:text-white">
              {{ currentLicense.is_perpetual ? (t('common.unlimited') || 'Perpetual') : formatDate(currentLicense.expires_at || '') }}
              <span v-if="!currentLicense.is_perpetual && currentLicense.days_until_expiry >= 0" class="text-gray-500 dark:text-gray-400 ml-1">
                ({{ t('licenses.daysRemaining', { n: currentLicense.days_until_expiry }) || `${currentLicense.days_until_expiry} days left` }})
              </span>
            </dd>
          </div>
          <div>
            <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">{{ t('licenses.machineId') || 'Machine Code' }}</dt>
            <dd class="mt-1 text-sm text-gray-900 dark:text-white font-mono">{{ currentLicense.machine_code }}</dd>
          </div>
        </dl>
      </div>

      <!-- Limits & Usage -->
      <div class="border-t border-gray-200 dark:border-gray-700 px-6 py-4">
        <h4 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{{ t('licenses.limitsAndUsage') || 'Limits & Usage' }}</h4>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div v-for="(limit, key) in limitItems" :key="key" class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
            <div class="flex justify-between items-center mb-1">
              <span class="text-xs font-medium text-gray-500 dark:text-gray-400">{{ limit.label }}</span>
              <span class="text-xs text-gray-500 dark:text-gray-400">
                {{ usage && limit.usageKey in usage ? usage[limit.usageKey as keyof typeof usage] : 0 }} / {{ (currentLicense as Record<string, unknown>)[limit.limitKey] }}
              </span>
            </div>
            <div class="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
              <div 
                class="h-2 rounded-full transition-all"
                :class="getUsageColor(usage && limit.usageKey in usage ? usage[limit.usageKey as keyof typeof usage] : 0, (currentLicense as Record<string, unknown>)[limit.limitKey] as number)"
                :style="{ width: `${Math.min(100, ((usage && limit.usageKey in usage ? usage[limit.usageKey as keyof typeof usage] : 0) / ((currentLicense as Record<string, unknown>)[limit.limitKey] as number)) * 100)}%` }"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- No License Card -->
    <div v-else class="bg-white dark:bg-gray-800 shadow rounded-lg p-8 text-center">
      <KeyIcon class="mx-auto h-12 w-12 text-gray-400" />
      <h3 class="mt-4 text-lg font-medium text-gray-900 dark:text-white">{{ t('licenses.noLicense') || 'No Active License' }}</h3>
      <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
        {{ t('licenses.noLicenseDescription') || 'Please activate a license to use this product.' }}
      </p>
      <div class="mt-6 flex justify-center gap-3">
        <button
          type="button"
          class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
          @click="showMachineCodeDialog = true"
        >
          {{ t('licenses.exportMachineCode') || 'Export Machine Code' }}
        </button>
        <button
          type="button"
          class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
          @click="showActivateDialog = true"
        >
          {{ t('licenses.activateLicense') || 'Activate License' }}
        </button>
      </div>
    </div>

    <!-- Machine Code Dialog -->
    <Teleport to="body">
      <div v-if="showMachineCodeDialog" class="fixed inset-0 z-50 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4">
          <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity" @click="showMachineCodeDialog = false"></div>
          
          <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full">
            <!-- Header -->
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 class="text-lg font-medium text-gray-900 dark:text-white">
                {{ t('licenses.machineCodeTitle') || 'Machine Code' }}
              </h3>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {{ t('licenses.machineCodeDescription') || 'Send this code to the sales team to get your activation code.' }}
              </p>
            </div>
            
            <!-- Content -->
            <div class="px-6 py-4">
              <div v-if="machineCodeLoading" class="flex justify-center py-8">
                <svg class="animate-spin h-8 w-8 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              <div v-else-if="machineCode">
                <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div class="flex items-center justify-between">
                    <code class="text-sm font-mono text-gray-900 dark:text-white break-all">{{ machineCode }}</code>
                    <button
                      type="button"
                      class="ml-2 text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
                      @click="copyMachineCode"
                    >
                      <ClipboardDocumentIcon class="h-5 w-5" />
                    </button>
                  </div>
                </div>
                <p class="mt-3 text-sm text-gray-500 dark:text-gray-400">
                  {{ t('licenses.machineCodeInstructions') || 'This code is unique to your environment. The activation code generated from this code can only be used here.' }}
                </p>
              </div>
              <div v-else class="text-center py-4 text-gray-500 dark:text-gray-400">
                {{ t('licenses.clickToGenerate') || 'Click the button below to generate machine code' }}
              </div>
            </div>
            
            <!-- Footer -->
            <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                type="button"
                class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600"
                @click="showMachineCodeDialog = false"
              >
                {{ t('common.close') || 'Close' }}
              </button>
              <button
                v-if="!machineCode"
                type="button"
                :disabled="machineCodeLoading"
                class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 disabled:opacity-50"
                @click="generateMachineCode"
              >
                {{ t('licenses.generateMachineCode') || 'Generate Machine Code' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Activate License Dialog -->
    <Teleport to="body">
      <div v-if="showActivateDialog" class="fixed inset-0 z-50 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4">
          <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity" @click="showActivateDialog = false"></div>
          
          <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full">
            <!-- Header -->
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 class="text-lg font-medium text-gray-900 dark:text-white">
                {{ t('licenses.activateLicense') || 'Activate License' }}
              </h3>
              <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {{ t('licenses.activateDescription') || 'Enter the activation code you received from the sales team.' }}
              </p>
            </div>
            
            <!-- Content -->
            <div class="px-6 py-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {{ t('licenses.activationCode') || 'Activation Code' }}
                </label>
                <textarea
                  v-model="activationCode"
                  rows="4"
                  class="block w-full rounded-lg border-0 py-2 px-3 text-slate-900 dark:text-white shadow-sm ring-1 ring-inset ring-slate-200 dark:ring-gray-600 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm dark:bg-gray-700 font-mono text-xs"
                  :placeholder="'HFL-ACT-...'"
                />
              </div>
              
              <!-- Error Message -->
              <div v-if="activateError" class="mt-3 rounded-md bg-red-50 dark:bg-red-900/20 p-3">
                <p class="text-sm text-red-700 dark:text-red-400">{{ activateError }}</p>
              </div>
            </div>
            
            <!-- Footer -->
            <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                type="button"
                class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600"
                @click="showActivateDialog = false"
              >
                {{ t('common.cancel') || 'Cancel' }}
              </button>
              <button
                type="button"
                :disabled="activating || !activationCode.trim()"
                class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                @click="activateLicense"
              >
                {{ activating ? (t('licenses.activating') || 'Activating...') : (t('licenses.activate') || 'Activate') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { 
  ComputerDesktopIcon, 
  KeyIcon,
  ClipboardDocumentIcon,
} from '@heroicons/vue/24/outline'
import { licensesApi } from '@/api'
import { useToast } from '@/composables/useToast'
import type { License } from '@/types/license'

const { t } = useI18n()
const { showToast } = useToast()

// State
const currentLicense = ref<License | null>(null)
const usage = ref<Record<string, number>>({})
const loading = ref(true)
const showMachineCodeDialog = ref(false)
const showActivateDialog = ref(false)
const machineCode = ref('')
const machineCodeLoading = ref(false)
const activationCode = ref('')
const activating = ref(false)
const activateError = ref('')

// Limit items for display
const limitItems = computed(() => [
  { label: t('licenses.maxUsers') || 'Users', limitKey: 'max_users', usageKey: 'users_count' },
  { label: t('licenses.maxProxies') || 'Proxies', limitKey: 'max_proxies', usageKey: 'proxies_count' },
  { label: t('licenses.maxStorage') || 'Storage (GB)', limitKey: 'max_storage_gb', usageKey: 'storage_used_gb' },
  { label: t('licenses.maxGateways') || 'Gateways', limitKey: 'max_gateways', usageKey: 'gateways_count' },
  { label: t('licenses.maxBackupTasks') || 'Backup Tasks', limitKey: 'max_backup_tasks', usageKey: 'backup_tasks_count' },
  { label: t('licenses.maxRecoveryTasks') || 'Recovery Tasks', limitKey: 'max_recovery_tasks', usageKey: 'recovery_tasks_count' },
  { label: t('licenses.maxSourceResources') || 'Source Resources', limitKey: 'max_source_resources', usageKey: 'source_resources_count' },
  { label: t('licenses.maxPolicies') || 'Policies', limitKey: 'max_policies', usageKey: 'policies_count' },
])

// Methods
const fetchCurrentLicense = async () => {
  loading.value = true
  try {
    const response = await licensesApi.current()
    if (response.data.is_valid) {
      currentLicense.value = response.data.license
      usage.value = response.data.usage || {}
    }
  } catch (error) {
    console.log('No active license')
  } finally {
    loading.value = false
  }
}

const generateMachineCode = async () => {
  machineCodeLoading.value = true
  try {
    const response = await licensesApi.machineCode()
    machineCode.value = response.data.machine_code
    showToast(t('licenses.machineCodeGenerated') || 'Machine code generated', 'success')
  } catch (error: any) {
    showToast(error.response?.data?.message || 'Failed to generate machine code', 'error')
  } finally {
    machineCodeLoading.value = false
  }
}

const copyMachineCode = async () => {
  try {
    await navigator.clipboard.writeText(machineCode.value)
    showToast(t('common.copied') || 'Copied to clipboard', 'success')
  } catch (error) {
    showToast('Failed to copy', 'error')
  }
}

const activateLicense = async () => {
  activating.value = true
  activateError.value = ''
  
  try {
    await licensesApi.activate({ activation_code: activationCode.value })
    showToast(t('licenses.activateSuccess') || 'License activated successfully', 'success')
    showActivateDialog.value = false
    activationCode.value = ''
    await fetchCurrentLicense()
  } catch (error: any) {
    const errorData = error.response?.data
    activateError.value = errorData?.message || errorData?.error || 'Activation failed'
  } finally {
    activating.value = false
  }
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString()
}

const getUsageColor = (current: number, max: number) => {
  const percentage = (current / max) * 100
  if (percentage >= 90) return 'bg-red-500'
  if (percentage >= 70) return 'bg-yellow-500'
  return 'bg-green-500'
}

onMounted(() => {
  fetchCurrentLicense()
})
</script>
