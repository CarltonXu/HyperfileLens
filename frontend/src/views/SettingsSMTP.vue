<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
          {{ t('settings.smtp.title') }}
        </h1>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {{ t('settings.smtp.description') }}
        </p>
      </div>
      <button
        @click="openCreateDialog"
        class="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
      >
        <PlusIcon class="w-5 h-5 mr-2" />
        {{ t('settings.smtp.addConfig') }}
      </button>
    </div>

    <!-- SMTP Configurations List -->
    <div class="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
      <div v-if="loading" class="p-8 text-center">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
      </div>
      
      <div v-else-if="smtpConfigs.length === 0" class="p-8 text-center">
        <EnvelopeIcon class="mx-auto h-12 w-12 text-gray-400" />
        <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">
          {{ t('settings.smtp.noConfigs') }}
        </h3>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {{ t('settings.smtp.noConfigsDesc') }}
        </p>
      </div>
      
      <table v-else class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead class="bg-gray-50 dark:bg-gray-900/50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              {{ t('settings.smtp.name') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              {{ t('settings.smtp.server') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              {{ t('settings.smtp.fromEmail') }}
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              {{ t('common.status') }}
            </th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              {{ t('common.actions') }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
          <tr v-for="config in smtpConfigs" :key="config.id" class="hover:bg-gray-50 dark:hover:bg-gray-700/50">
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="flex items-center">
                <span class="text-sm font-medium text-gray-900 dark:text-white">{{ config.name }}</span>
                <span v-if="config.is_default" class="ml-2 px-2 py-0.5 text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900/50 dark:text-indigo-300 rounded">
                  {{ t('common.default') }}
                </span>
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
              {{ config.host }}:{{ config.port }}
              <span v-if="config.use_tls" class="ml-1 text-green-600">(TLS)</span>
              <span v-else-if="config.use_ssl" class="ml-1 text-green-600">(SSL)</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
              {{ config.from_name }} &lt;{{ config.from_email }}&gt;
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span :class="config.is_active ? 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'" class="px-2 py-1 text-xs font-medium rounded">
                {{ config.is_active ? t('common.active') : t('common.inactive') }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
              <button @click="testConnection(config)" class="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400">
                {{ t('settings.smtp.testConnection') }}
              </button>
              <button @click="setDefault(config)" v-if="!config.is_default" class="text-green-600 hover:text-green-900 dark:text-green-400">
                {{ t('settings.smtp.setDefault') }}
              </button>
              <button @click="openEditDialog(config)" class="text-gray-600 hover:text-gray-900 dark:text-gray-400">
                {{ t('common.edit') }}
              </button>
              <button @click="deleteConfig(config)" class="text-red-600 hover:text-red-900 dark:text-red-400">
                {{ t('common.delete') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create/Edit Dialog -->
    <div v-if="showDialog" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-screen items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/50" @click="closeDialog"></div>
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full p-6">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
            {{ editing ? t('settings.smtp.editConfig') : t('settings.smtp.addConfig') }}
          </h3>
          
          <form @submit.prevent="saveConfig" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('settings.smtp.name') }}</label>
              <input v-model="form.name" type="text" required class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border" />
            </div>
            
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('settings.smtp.host') }}</label>
                <input v-model="form.host" type="text" required class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border" placeholder="smtp.example.com" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('settings.smtp.port') }}</label>
                <input v-model.number="form.port" type="number" required class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border" placeholder="587" />
              </div>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('settings.smtp.username') }}</label>
                <input v-model="form.username" type="text" class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('settings.smtp.password') }}</label>
                <input v-model="form.password" type="password" class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border" :placeholder="editing ? '••••••••' : ''" />
              </div>
            </div>
            
            <div class="flex items-center space-x-6">
              <label class="flex items-center">
                <input v-model="form.use_tls" type="checkbox" class="rounded border-gray-300 dark:border-gray-600 text-indigo-600 focus:ring-indigo-500" />
                <span class="ml-2 text-sm text-gray-700 dark:text-gray-300">TLS</span>
              </label>
              <label class="flex items-center">
                <input v-model="form.use_ssl" type="checkbox" class="rounded border-gray-300 dark:border-gray-600 text-indigo-600 focus:ring-indigo-500" />
                <span class="ml-2 text-sm text-gray-700 dark:text-gray-300">SSL</span>
              </label>
              <label class="flex items-center">
                <input v-model="form.is_active" type="checkbox" class="rounded border-gray-300 dark:border-gray-600 text-indigo-600 focus:ring-indigo-500" />
                <span class="ml-2 text-sm text-gray-700 dark:text-gray-300">{{ t('common.active') }}</span>
              </label>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('settings.smtp.fromEmail') }}</label>
                <input v-model="form.from_email" type="email" required class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('settings.smtp.fromName') }}</label>
                <input v-model="form.from_name" type="text" required class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border" />
              </div>
            </div>
            
            <div class="flex justify-end space-x-3 pt-4 border-t dark:border-gray-700">
              <button type="button" @click="closeDialog" class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600">
                {{ t('common.cancel') }}
              </button>
              <button type="submit" class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg">
                {{ t('common.save') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Test Email Dialog -->
    <div v-if="showTestDialog" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-screen items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/50" @click="showTestDialog = false"></div>
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
            {{ t('settings.smtp.sendTestEmail') }}
          </h3>
          
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('settings.smtp.testEmailTo') }}</label>
              <input v-model="testEmail" type="email" required class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border" placeholder="user@example.com" />
            </div>
            
            <div class="flex justify-end space-x-3">
              <button type="button" @click="showTestDialog = false" class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600">
                {{ t('common.cancel') }}
              </button>
              <button @click="sendTestEmail" class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg">
                {{ t('settings.smtp.sendTest') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { PlusIcon, EnvelopeIcon } from '@heroicons/vue/24/outline'
import { smtpApi, type SMTPConfig } from '@/api'
import { useAppStore } from '@/stores/app'

const { t } = useI18n()
const appStore = useAppStore()

const loading = ref(true)
const smtpConfigs = ref<SMTPConfig[]>([])
const showDialog = ref(false)
const showTestDialog = ref(false)
const editing = ref(false)
const editingId = ref<string | null>(null)
const testingConfig = ref<SMTPConfig | null>(null)
const testEmail = ref('')

const form = reactive({
  name: 'Default',
  host: '',
  port: 587,
  username: '',
  password: '',
  use_tls: true,
  use_ssl: false,
  from_email: 'noreply@hyperfilelens.com',
  from_name: 'HyperFileLens',
  is_active: true,
})

const fetchConfigs = async () => {
  loading.value = true
  try {
    const response = await smtpApi.list()
    smtpConfigs.value = response.data
  } catch (error) {
    console.error('Failed to fetch SMTP configs:', error)
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  editing.value = false
  editingId.value = null
  Object.assign(form, {
    name: 'Default',
    host: '',
    port: 587,
    username: '',
    password: '',
    use_tls: true,
    use_ssl: false,
    from_email: 'noreply@hyperfilelens.com',
    from_name: 'HyperFileLens',
    is_active: true,
  })
  showDialog.value = true
}

const openEditDialog = (config: SMTPConfig) => {
  editing.value = true
  editingId.value = config.id
  Object.assign(form, {
    name: config.name,
    host: config.host,
    port: config.port,
    username: config.username,
    password: '',
    use_tls: config.use_tls,
    use_ssl: config.use_ssl,
    from_email: config.from_email,
    from_name: config.from_name,
    is_active: config.is_active,
  })
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveConfig = async () => {
  try {
    const data = { ...form }
    if (editing.value && editingId.value) {
      if (!data.password) delete (data as Record<string, unknown>).password
      await smtpApi.update(editingId.value, data)
      appStore.showToast({ type: 'success', title: t('common.updateSuccess') })
    } else {
      await smtpApi.create(data)
      appStore.showToast({ type: 'success', title: t('common.createSuccess') })
    }
    closeDialog()
    fetchConfigs()
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } }
    appStore.showToast({ type: 'error', title: err.response?.data?.error || t('common.error') })
  }
}

const testConnection = async (config: SMTPConfig) => {
  try {
    const response = await smtpApi.testConnection(config.id)
    appStore.showToast({ type: response.data.success ? 'success' : 'error', title: response.data.message })
  } catch (error: unknown) {
    const err = error as { response?: { data?: { message?: string } } }
    appStore.showToast({ type: 'error', title: err.response?.data?.message || t('common.error') })
  }
}

const setDefault = async (config: SMTPConfig) => {
  try {
    await smtpApi.setDefault(config.id)
    appStore.showToast({ type: 'success', title: t('settings.smtp.setDefaultSuccess') })
    fetchConfigs()
  } catch (error) {
    appStore.showToast({ type: 'error', title: t('common.error') })
  }
}

const deleteConfig = async (config: SMTPConfig) => {
  if (!confirm(t('settings.smtp.confirmDelete'))) return
  
  try {
    await smtpApi.delete(config.id)
    appStore.showToast({ type: 'success', title: t('common.deleteSuccess') })
    fetchConfigs()
  } catch (error) {
    appStore.showToast({ type: 'error', title: t('common.error') })
  }
}

const sendTestEmail = async () => {
  if (!testingConfig.value) return
  
  try {
    const response = await smtpApi.sendTestEmail(testingConfig.value.id, testEmail.value)
    appStore.showToast({ type: response.data.success ? 'success' : 'error', title: response.data.message })
    showTestDialog.value = false
  } catch (error: unknown) {
    const err = error as { response?: { data?: { message?: string } } }
    appStore.showToast({ type: 'error', title: err.response?.data?.message || t('common.error') })
  }
}

onMounted(() => {
  fetchConfigs()
})
</script>
