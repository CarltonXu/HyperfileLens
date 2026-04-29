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
          {{ t('licenses.getMachineCode') || 'Get Machine Code' }}
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
            <dd class="mt-1 text-sm text-gray-900 dark:text-white font-mono text-xs break-all">{{ currentLicense.machine_code }}</dd>
          </div>
        </dl>
      </div>

      <!-- Limits & Usage -->
      <div class="border-t border-gray-200 dark:border-gray-700 px-6 py-4">
        <h4 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{{ t('licenses.limitsAndUsage') || 'Limits & Usage' }}</h4>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5">
          <div v-for="(limit, key) in limitItems" :key="key" class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
            <div class="flex justify-between items-center mb-1">
              <span class="text-xs font-medium text-gray-500 dark:text-gray-400">{{ limit.label }}</span>
              <span class="text-xs text-gray-500 dark:text-gray-400">
                {{ getUsage(limit.usageKey) }} / {{ getLimit(limit.limitKey) }}
              </span>
            </div>
            <div class="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
              <div 
                class="h-2 rounded-full transition-all"
                :class="getUsageColor(getUsage(limit.usageKey), getLimit(limit.limitKey))"
                :style="{ width: `${getUsagePercent(getUsage(limit.usageKey), getLimit(limit.limitKey))}%` }"
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
      <div class="mt-6">
        <button
          type="button"
          class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
          @click="showActivateDialog = true"
        >
          {{ t('licenses.activateLicense') || 'Activate License' }}
        </button>
      </div>
    </div>

    <!-- License History -->
    <div v-if="licenseHistory.length > 0" class="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">
          {{ t('licenses.history') || 'License History' }}
        </h3>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-300 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th class="py-3.5 pl-6 pr-3 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('licenses.changeType') || 'Change Type' }}</th>
              <th class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('licenses.licenseKey') || 'License Key' }}</th>
              <th class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('licenses.changedAt') || 'Changed At' }}</th>
              <th class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('licenses.previousExpiry') || 'Expiry Date' }}</th>
              <th class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('licenses.reason') || 'Reason' }}</th>
              <th class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('common.actions') || 'Actions' }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <template v-for="history in licenseHistory" :key="history.id">
              <tr class="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer" @click="toggleHistoryDetail(history.id)">
                <td class="whitespace-nowrap py-4 pl-6 pr-3 text-sm">
                  <span :class="getChangeTypeClass(history.change_type)">
                    {{ getChangeTypeLabel(history.change_type) }}
                  </span>
                </td>
                <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400 font-mono">
                  <span :title="history.license_key">{{ history.license_key?.substring(0, 25) }}...</span>
                </td>
                <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                  {{ formatDate(history.archived_at) }}
                </td>
                <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                  {{ history.expires_at ? formatDate(history.expires_at) : (history.is_perpetual ? (t('licenses.perpetual') || 'Perpetual') : '-') }}
                </td>
                <td class="px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                  {{ history.change_reason || '-' }}
                </td>
                <td class="px-3 py-4 text-sm">
                  <button class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">
                    {{ expandedHistoryId === history.id ? (t('common.hide') || 'Hide') : (t('common.viewDetails') || 'Details') }}
                  </button>
                </td>
              </tr>
              <!-- Expanded Details Row -->
              <tr v-if="expandedHistoryId === history.id" class="bg-gray-50 dark:bg-gray-900">
                <td colspan="6" class="px-6 py-4">
                  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.maxTenants') || 'Max Tenants' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400">{{ history.max_tenants || '-' }}</dd>
                    </div>
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.maxUsers') || 'Max Users' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400">{{ history.max_users || '-' }}</dd>
                    </div>
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.maxProxies') || 'Max Proxies' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400">{{ history.max_proxies || '-' }}</dd>
                    </div>
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.maxStorage') || 'Max Storage (GB)' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400">{{ history.max_storage_gb || '-' }}</dd>
                    </div>
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.maxGateways') || 'Max Gateways' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400">{{ history.max_gateways || '-' }}</dd>
                    </div>
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.aiInsightsQuota') || 'AI Insights Quota' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400">{{ history.ai_insights_quota || '-' }}</dd>
                    </div>
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.maxBackupTasks') || 'Max Backup Tasks' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400">{{ history.max_backup_tasks || '-' }}</dd>
                    </div>
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.maxRecoveryTasks') || 'Max Recovery Tasks' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400">{{ history.max_recovery_tasks || '-' }}</dd>
                    </div>
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.maxSourceResources') || 'Max Source Resources' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400">{{ history.max_source_resources || '-' }}</dd>
                    </div>
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.maxPolicies') || 'Max Policies' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400">{{ history.max_policies || '-' }}</dd>
                    </div>
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.maxRepositories') || 'Max Repositories' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400">{{ history.max_repositories || '-' }}</dd>
                    </div>
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.issuedAt') || 'Issued At' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400">{{ formatDate(history.issued_at) }}</dd>
                    </div>
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.activatedAt') || 'Activated At' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400">{{ formatDate(history.activated_at) }}</dd>
                    </div>
                    <div>
                      <dt class="font-medium text-gray-900 dark:text-white">{{ t('licenses.machineCode') || 'Machine Code' }}</dt>
                      <dd class="text-gray-500 dark:text-gray-400 font-mono text-xs">{{ history.machine_code?.substring(0, 30) }}...</dd>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
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
                {{ t('licenses.machineCodeDescription') || 'Unique identifier for this environment' }}
              </p>
            </div>
            
            <!-- Content -->
            <div class="px-6 py-4 space-y-4">
              <!-- Info Box -->
              <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                <div class="flex items-start gap-3">
                  <InformationCircleIcon class="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                  <div class="text-sm text-blue-700 dark:text-blue-300">
                    <p class="font-medium">{{ t('licenses.howToActivate') || 'How to activate:' }}</p>
                    <ol class="mt-2 list-decimal list-inside space-y-1">
                      <li>{{ t('licenses.step1CopyCode') || 'Copy the machine code below' }}</li>
                      <li>{{ t('licenses.step2SendToSales') || 'Send it to our sales team' }}</li>
                      <li>{{ t('licenses.step3ReceiveActivation') || 'Receive your activation code' }}</li>
                      <li>{{ t('licenses.step4Activate') || 'Click "Activate License" to enter the code' }}</li>
                    </ol>
                  </div>
                </div>
              </div>
              
              <!-- Machine Code Display -->
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {{ t('licenses.yourMachineCode') || 'Your Machine Code' }}
                </label>
                <div class="relative">
                  <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
                    <code class="text-sm font-mono text-gray-900 dark:text-white break-all">{{ machineCode }}</code>
                  </div>
                  <button
                    type="button"
                    class="absolute top-2 right-2 p-2 rounded-md bg-white dark:bg-gray-600 shadow-sm border border-gray-200 dark:border-gray-500 hover:bg-gray-50 dark:hover:bg-gray-500"
                    @click="copyMachineCodeFromDialog"
                  >
                    <ClipboardDocumentCheckIcon v-if="copied" class="h-5 w-5 text-green-500" />
                    <ClipboardDocumentIcon v-else class="h-5 w-5 text-gray-400" />
                  </button>
                </div>
                <p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  {{ t('licenses.machineCodeNote') || 'This code is uniquely generated for your environment and tenant. It will not change unless you reinstall the system.' }}
                </p>
              </div>
            </div>
            
            <!-- Footer -->
            <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                type="button"
                class="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                @click="showMachineCodeDialog = false"
              >
                {{ t('common.close') || 'Close' }}
              </button>
              <button
                type="button"
                class="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
                @click="copyMachineCodeFromDialog"
              >
                {{ t('common.copy') || 'Copy Code' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Activate Dialog -->
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
                {{ t('licenses.enterActivationCode') || 'Enter the activation code provided by the sales team' }}
              </p>
            </div>
            
            <!-- Content -->
            <div class="px-6 py-4">
              <!-- Error Message -->
              <div v-if="activateError" class="mb-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-md">
                <p class="text-sm text-red-600 dark:text-red-400">{{ activateError }}</p>
              </div>
              
              <!-- Activation Code Input -->
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {{ t('licenses.activationCode') || 'Activation Code' }}
                </label>
                <textarea
                  v-model="activationCode"
                  rows="3"
                  class="block w-full rounded-md border-0 p-3 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:bg-gray-700 sm:text-sm sm:leading-6 font-mono text-xs break-all"
                  :placeholder="t('licenses.activationCodePlaceholder') || 'HFL-ACT-...'"
                ></textarea>
              </div>
            </div>
            
            <!-- Footer -->
            <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                type="button"
                class="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                @click="showActivateDialog = false"
              >
                {{ t('common.cancel') || 'Cancel' }}
              </button>
              <button
                type="button"
                :disabled="activating || !activationCode.trim()"
                class="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
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
  KeyIcon,
  ClipboardDocumentIcon,
  ClipboardDocumentCheckIcon,
  InformationCircleIcon,
  ComputerDesktopIcon,
} from '@heroicons/vue/24/outline'
import { licensesApi } from '@/api'
import { useToast } from '@/composables/useToast'
import type { License, LicenseHistory } from '@/types/license'

const { t } = useI18n()
const { showToast } = useToast()

// State
const currentLicense = ref<License | null>(null)
const usage = ref<Record<string, number>>({})
const loading = ref(true)
const showMachineCodeDialog = ref(false)
const showActivateDialog = ref(false)
const machineCode = ref('')
const activationCode = ref('')
const activating = ref(false)
const activateError = ref('')
const licenseHistory = ref<LicenseHistory[]>([])
const copied = ref(false)
const expandedHistoryId = ref<string | null>(null)

// Limit items for display - 完整的配额列表
const limitItems = computed(() => [
  { label: t('licenses.maxTenants') || 'Tenants', limitKey: 'max_tenants', usageKey: 'tenants_count' },
  { label: t('licenses.maxUsers') || 'Users', limitKey: 'max_users', usageKey: 'users_count' },
  { label: t('licenses.maxProxies') || 'Proxies', limitKey: 'max_proxies', usageKey: 'proxies_count' },
  { label: t('licenses.maxStorage') || 'Storage (GB)', limitKey: 'max_storage_gb', usageKey: 'storage_used_gb' },
  { label: t('licenses.maxGateways') || 'Gateways', limitKey: 'max_gateways', usageKey: 'gateways_count' },
  { label: t('licenses.aiInsightsQuota') || 'AI Insights', limitKey: 'ai_insights_quota', usageKey: 'ai_insights_used' },
  { label: t('licenses.maxBackupTasks') || 'Backup Tasks', limitKey: 'max_backup_tasks', usageKey: 'backup_tasks_count' },
  { label: t('licenses.maxRecoveryTasks') || 'Recovery Tasks', limitKey: 'max_recovery_tasks', usageKey: 'recovery_tasks_count' },
  { label: t('licenses.maxSourceResources') || 'Source Resources', limitKey: 'max_source_resources', usageKey: 'source_resources_count' },
  { label: t('licenses.maxPolicies') || 'Policies', limitKey: 'max_policies', usageKey: 'policies_count' },
  { label: t('licenses.maxRepositories') || 'Repositories', limitKey: 'max_repositories', usageKey: 'repositories_count' },
])

// Helper methods
const getLimit = (key: string): number => {
  if (!currentLicense.value) return 0
  return (currentLicense.value as Record<string, unknown>)[key] as number || 0
}

const getUsage = (key: string): number => {
  return usage.value[key] || 0
}

const getUsagePercent = (current: number, max: number): number => {
  if (max === 0) return 0
  return Math.min(100, (current / max) * 100)
}

// Methods
const fetchCurrentLicense = async () => {
  loading.value = true
  try {
    const response = await licensesApi.current()
    if (response.data.is_valid) {
      currentLicense.value = response.data.license
      usage.value = response.data.usage || {}
    }
    // Machine code is auto-generated and returned
    if (response.data.machine_code) {
      machineCode.value = response.data.machine_code
    }
  } catch (error) {
    console.log('No active license')
  } finally {
    loading.value = false
  }
}

const fetchLicenseHistory = async () => {
  try {
    const response = await licensesApi.history()
    licenseHistory.value = response.data.results || []
  } catch (error) {
    console.log('No license history')
  }
}

const copyMachineCodeFromDialog = async () => {
  try {
    await navigator.clipboard.writeText(machineCode.value)
    copied.value = true
    showToast(t('common.copied') || 'Copied to clipboard', 'success')
    setTimeout(() => {
      copied.value = false
    }, 2000)
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
    await fetchLicenseHistory()
  } catch (error: any) {
    const errorData = error.response?.data
    activateError.value = errorData?.message || errorData?.error || 'Activation failed'
  } finally {
    activating.value = false
  }
}

const formatDate = (date: string | null | undefined) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString()
}

const getUsageColor = (current: number, max: number) => {
  const percentage = getUsagePercent(current, max)
  if (percentage >= 90) return 'bg-red-500'
  if (percentage >= 70) return 'bg-yellow-500'
  return 'bg-green-500'
}

const getChangeTypeClass = (type: string) => {
  const classes: Record<string, string> = {
    'initial': 'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    'renewal': 'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    'upgrade': 'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    'downgrade': 'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    'expired': 'inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  }
  return classes[type] || classes['initial']
}

const toggleHistoryDetail = (id: string) => {
  expandedHistoryId.value = expandedHistoryId.value === id ? null : id
}

const getChangeTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    'initial': t('licenses.changeInitial') || 'Initial',
    'renewal': t('licenses.changeRenewal') || 'Renewal',
    'upgrade': t('licenses.changeUpgrade') || 'Upgrade',
    'downgrade': t('licenses.changeDowngrade') || 'Downgrade',
    'expired': t('licenses.changeExpired') || 'Expired',
  }
  return labels[type] || type
}

onMounted(() => {
  fetchCurrentLicense()
  fetchLicenseHistory()
})
</script>
