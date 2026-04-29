<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="sm:flex sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900 dark:text-white">{{ t('users.title') }}</h1>
        <p class="mt-2 text-sm text-gray-700 dark:text-gray-300">
          {{ t('users.description') }}
        </p>
      </div>
      <div class="mt-4 sm:mt-0 flex gap-3">
        <button
          type="button"
          class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:ring-gray-600 dark:hover:bg-gray-600"
          @click="openInviteDialog"
        >
          <EnvelopeIcon class="-ml-0.5 mr-1.5 h-5 w-5" aria-hidden="true" />
          {{ t('users.inviteUser') }}
        </button>
        <button
          type="button"
          class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
          @click="openCreateDialog"
        >
          <PlusIcon class="-ml-0.5 mr-1.5 h-5 w-5" aria-hidden="true" />
          {{ t('users.createUser') }}
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white dark:bg-gray-800 shadow rounded-lg p-4">
      <div class="flex flex-wrap gap-4">
        <div class="flex-1 min-w-0">
          <div class="relative">
            <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="t('common.search')"
              class="block w-full rounded-md border-0 py-1.5 pl-10 pr-3 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
              @input="debouncedSearch"
            />
          </div>
        </div>
        <div class="flex items-center gap-2">
          <select
            v-model="roleFilter"
            class="rounded-md border-0 py-1.5 pl-3 pr-8 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
            @change="fetchUsers"
          >
            <option value="">{{ t('common.all') }}</option>
            <option value="admin">{{ t('users.roles.admin') }}</option>
            <option value="member">{{ t('users.roles.member') }}</option>
          </select>
          <select
            v-model="statusFilter"
            class="rounded-md border-0 py-1.5 pl-3 pr-8 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
            @change="fetchUsers"
          >
            <option value="">{{ t('common.all') }}</option>
            <option value="active">{{ t('users.active') }}</option>
            <option value="inactive">{{ t('users.inactive') }}</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Users Table -->
    <div class="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
      <div v-if="loading" class="p-8 text-center">
        <svg class="animate-spin h-8 w-8 text-indigo-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">{{ t('common.loading') }}</p>
      </div>

      <table v-else class="min-w-full divide-y divide-gray-300 dark:divide-gray-700">
        <thead class="bg-gray-50 dark:bg-gray-900">
          <tr>
            <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 dark:text-white sm:pl-6">{{ t('users.user') }}</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('users.role') }}</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('users.status') }}</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('users.lastLogin') }}</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">{{ t('users.createdAt') }}</th>
            <th scope="col" class="relative py-3.5 pl-3 pr-4 sm:pr-6">
              <span class="sr-only">{{ t('common.actions') }}</span>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
          <tr v-for="user in users" :key="user.id" class="hover:bg-gray-50 dark:hover:bg-gray-700/50">
            <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm sm:pl-6">
              <div class="flex items-center">
                <div class="h-10 w-10 flex-shrink-0 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center">
                  <span class="text-indigo-600 dark:text-indigo-400 font-medium text-sm">
                    {{ getInitials(user) }}
                  </span>
                </div>
                <div class="ml-4">
                  <div class="font-medium text-gray-900 dark:text-white">{{ user.full_name || user.email }}</div>
                  <div class="text-gray-500 dark:text-gray-400">{{ user.email }}</div>
                </div>
              </div>
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm">
              <span :class="getRoleClass(user.tenant_role)" class="inline-flex rounded-full px-2 py-1 text-xs font-semibold">
                {{ t(`users.roles.${user.tenant_role}`) }}
              </span>
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm">
              <span :class="user.is_active ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'" class="inline-flex rounded-full px-2 py-1 text-xs font-semibold">
                {{ user.is_active ? t('users.active') : t('users.inactive') }}
              </span>
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
              {{ user.last_login_at ? formatDate(user.last_login_at) : '-' }}
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
              {{ formatDate(user.date_joined || '') }}
            </td>
            <td class="whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
              <Menu as="div" class="relative inline-block text-left">
                <MenuButton class="flex items-center rounded-full bg-white dark:bg-gray-700 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  <EllipsisVerticalIcon class="h-5 w-5" aria-hidden="true" />
                </MenuButton>
                <transition enter-active-class="transition ease-out duration-100" enter-from-class="transform opacity-0 scale-95" enter-to-class="transform opacity-100 scale-100" leave-active-class="transition ease-in duration-75" leave-from-class="transform opacity-100 scale-100" leave-to-class="transform opacity-0 scale-95">
                  <MenuItems class="absolute right-0 z-50 mt-2 w-48 origin-top-right rounded-md bg-white dark:bg-gray-700 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                    <div class="py-1">
                      <MenuItem v-if="user.is_active" v-slot="{ active }">
                        <button @click="toggleUserStatus(user, false)" :class="[active ? 'bg-gray-100 dark:bg-gray-600 text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-200', 'block w-full px-4 py-2 text-left text-sm']">
                          {{ t('users.disableUser') }}
                        </button>
                      </MenuItem>
                      <MenuItem v-else v-slot="{ active }">
                        <button @click="toggleUserStatus(user, true)" :class="[active ? 'bg-gray-100 dark:bg-gray-600 text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-200', 'block w-full px-4 py-2 text-left text-sm']">
                          {{ t('users.enableUser') }}
                        </button>
                      </MenuItem>
                      <MenuItem v-slot="{ active }">
                        <button @click="openChangeRoleDialog(user)" :class="[active ? 'bg-gray-100 dark:bg-gray-600 text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-200', 'block w-full px-4 py-2 text-left text-sm']">
                          {{ t('users.changeRole') }}
                        </button>
                      </MenuItem>
                    </div>
                  </MenuItems>
                </transition>
              </Menu>
            </td>
          </tr>
          <tr v-if="users.length === 0">
            <td colspan="6" class="px-3 py-12 text-center text-gray-500 dark:text-gray-400">
              {{ t('common.noData') }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create User Dialog -->
    <Teleport to="body">
      <div v-if="showCreateDialog" class="fixed inset-0 z-50 overflow-y-auto">
        <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="closeCreateDialog"></div>
          <div class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
            <div>
              <div class="mt-3 text-center sm:mt-5">
                <h3 class="text-base font-semibold leading-6 text-gray-900 dark:text-white">
                  {{ t('users.createUser') }}
                </h3>
                <div class="mt-4 space-y-4 text-left">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('users.email') }}</label>
                    <input
                      v-model="createForm.email"
                      type="email"
                      class="mt-1 block w-full rounded-md border-0 px-3 py-1.5 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
                      :placeholder="t('users.emailPlaceholder')"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('users.password') }}</label>
                    <input
                      v-model="createForm.password"
                      type="password"
                      class="mt-1 block w-full rounded-md border-0 px-3 py-1.5 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
                      :placeholder="t('users.passwordPlaceholder')"
                    />
                  </div>
                  <div class="grid grid-cols-2 gap-4">
                    <div>
                      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('users.firstName') }}</label>
                      <input
                        v-model="createForm.first_name"
                        type="text"
                        class="mt-1 block w-full rounded-md border-0 px-3 py-1.5 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
                      />
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('users.lastName') }}</label>
                      <input
                        v-model="createForm.last_name"
                        type="text"
                        class="mt-1 block w-full rounded-md border-0 px-3 py-1.5 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
                      />
                    </div>
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('users.role') }}</label>
                    <select
                      v-model="createForm.tenant_role"
                      class="mt-1 block w-full rounded-md border-0 px-3 py-1.5 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
                    >
                      <option value="admin">{{ t('users.roles.admin') }}</option>
                      <option value="member">{{ t('users.roles.member') }}</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
            <div class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
              <button
                type="button"
                class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 sm:col-start-2"
                @click="createUser"
                :disabled="creating"
              >
                {{ creating ? t('common.saving') : t('common.save') }}
              </button>
              <button
                type="button"
                class="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:ring-gray-600 dark:hover:bg-gray-600 sm:col-start-1 sm:mt-0"
                @click="closeCreateDialog"
              >
                {{ t('common.cancel') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Invite User Dialog -->
    <Teleport to="body">
      <div v-if="showInviteDialog" class="fixed inset-0 z-50 overflow-y-auto">
        <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="closeInviteDialog"></div>
          <div class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
            <div>
              <div class="mt-3 text-center sm:mt-5">
                <h3 class="text-base font-semibold leading-6 text-gray-900 dark:text-white">
                  {{ t('users.inviteUser') }}
                </h3>
                <div class="mt-4 space-y-4 text-left">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('users.email') }}</label>
                    <input
                      v-model="inviteForm.email"
                      type="email"
                      class="mt-1 block w-full rounded-md border-0 px-3 py-1.5 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
                      :placeholder="t('users.emailPlaceholder')"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('users.role') }}</label>
                    <select
                      v-model="inviteForm.role"
                      class="mt-1 block w-full rounded-md border-0 px-3 py-1.5 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
                    >
                      <option value="admin">{{ t('users.roles.admin') }}</option>
                      <option value="member">{{ t('users.roles.member') }}</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
            <div class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
              <button
                type="button"
                class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 sm:col-start-2"
                @click="sendInvite"
                :disabled="inviting"
              >
                {{ inviting ? t('users.sending') : t('users.sendInvite') }}
              </button>
              <button
                type="button"
                class="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:ring-gray-600 dark:hover:bg-gray-600 sm:col-start-1 sm:mt-0"
                @click="closeInviteDialog"
              >
                {{ t('common.cancel') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Change Role Dialog -->
    <Teleport to="body">
      <div v-if="showRoleDialog" class="fixed inset-0 z-50 overflow-y-auto">
        <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="closeRoleDialog"></div>
          <div class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
            <div>
              <div class="mt-3 text-center sm:mt-5">
                <h3 class="text-base font-semibold leading-6 text-gray-900 dark:text-white">
                  {{ t('users.changeRole') }}
                </h3>
                <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  {{ t('users.changeRoleHint', { user: selectedUser?.full_name || selectedUser?.email }) }}
                </p>
                <div class="mt-4 text-left">
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">{{ t('users.role') }}</label>
                  <select
                    v-model="selectedRole"
                    class="mt-1 block w-full rounded-md border-0 px-3 py-1.5 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 dark:bg-gray-700 dark:text-white sm:text-sm sm:leading-6"
                  >
                    <option value="admin">{{ t('users.roles.admin') }}</option>
                    <option value="member">{{ t('users.roles.member') }}</option>
                  </select>
                </div>
              </div>
            </div>
            <div class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
              <button
                type="button"
                class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 sm:col-start-2"
                @click="changeRole"
                :disabled="changingRole"
              >
                {{ changingRole ? t('common.saving') : t('common.save') }}
              </button>
              <button
                type="button"
                class="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:ring-gray-600 dark:hover:bg-gray-600 sm:col-start-1 sm:mt-0"
                @click="closeRoleDialog"
              >
                {{ t('common.cancel') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue'
import { PlusIcon, EllipsisVerticalIcon, EnvelopeIcon, MagnifyingGlassIcon } from '@heroicons/vue/24/outline'
import { useAppStore } from '@/stores/app'
import api from '@/api'

const { t } = useI18n()
const appStore = useAppStore()

interface User {
  id: string
  email: string
  full_name?: string
  first_name?: string
  last_name?: string
  tenant_role: string
  is_active: boolean
  last_login_at?: string
  date_joined?: string
}

const loading = ref(false)
const users = ref<User[]>([])
const searchQuery = ref('')
const roleFilter = ref('')
const statusFilter = ref('')

// Create dialog
const showCreateDialog = ref(false)
const creating = ref(false)
const createForm = ref({
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  tenant_role: 'member'
})

// Invite dialog
const showInviteDialog = ref(false)
const inviting = ref(false)
const inviteForm = ref({
  email: '',
  role: 'member'
})

// Role dialog
const showRoleDialog = ref(false)
const changingRole = ref(false)
const selectedUser = ref<User | null>(null)
const selectedRole = ref('')

// Debounce
let searchTimeout: ReturnType<typeof setTimeout> | null = null
const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(fetchUsers, 300)
}

async function fetchUsers() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (searchQuery.value) params.append('search', searchQuery.value)
    if (roleFilter.value) params.append('tenant_role', roleFilter.value)
    if (statusFilter.value) params.append('is_active', statusFilter.value === 'active' ? 'true' : 'false')

    const response = await api.get(`/accounts/users/?${params}`)
    users.value = response.data.results || response.data
  } catch (error: unknown) {
    console.error('Failed to fetch users:', error)
    appStore.showToast({ type: 'error', title: t('common.error') })
  } finally {
    loading.value = false
  }
}

function getInitials(user: User) {
  if (user.full_name) {
    return user.full_name.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2)
  }
  if (user.first_name && user.last_name) {
    return (user.first_name[0] + user.last_name[0]).toUpperCase()
  }
  return user.email.slice(0, 2).toUpperCase()
}

function getRoleClass(role: string) {
  const classes: Record<string, string> = {
    admin: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
    member: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
  }
  return classes[role] || classes.member
}

function formatDate(date: string) {
  if (!date) return '-'
  return new Date(date).toLocaleDateString()
}

function openCreateDialog() {
  createForm.value = { email: '', password: '', first_name: '', last_name: '', tenant_role: 'member' }
  showCreateDialog.value = true
}

function closeCreateDialog() {
  showCreateDialog.value = false
}

async function createUser() {
  creating.value = true
  try {
    await api.post('/accounts/users/', createForm.value)
    appStore.showToast({ type: 'success', title: t('users.createSuccess') })
    closeCreateDialog()
    fetchUsers()
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } }
    appStore.showToast({ type: 'error', title: err.response?.data?.error || t('users.createFailed') })
  } finally {
    creating.value = false
  }
}

function openInviteDialog() {
  inviteForm.value = { email: '', role: 'member' }
  showInviteDialog.value = true
}

function closeInviteDialog() {
  showInviteDialog.value = false
}

async function sendInvite() {
  inviting.value = true
  try {
    await api.post('/tenants/invitations/', inviteForm.value)
    appStore.showToast({ type: 'success', title: t('users.inviteSuccess') })
    closeInviteDialog()
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } }
    appStore.showToast({ type: 'error', title: err.response?.data?.error || t('users.inviteFailed') })
  } finally {
    inviting.value = false
  }
}

function openChangeRoleDialog(user: User) {
  selectedUser.value = user
  selectedRole.value = user.tenant_role
  showRoleDialog.value = true
}

function closeRoleDialog() {
  showRoleDialog.value = false
  selectedUser.value = null
}

async function changeRole() {
  if (!selectedUser.value) return
  changingRole.value = true
  try {
    await api.post(`/accounts/users/${selectedUser.value.id}/change_role/`, { role: selectedRole.value })
    appStore.showToast({ type: 'success', title: t('users.roleChangeSuccess') })
    closeRoleDialog()
    fetchUsers()
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } }
    appStore.showToast({ type: 'error', title: err.response?.data?.error || t('users.roleChangeFailed') })
  } finally {
    changingRole.value = false
  }
}

async function toggleUserStatus(user: User, active: boolean) {
  try {
    const action = active ? 'enable' : 'disable'
    await api.post(`/accounts/users/${user.id}/${action}/`)
    appStore.showToast({ type: 'success', title: active ? t('users.enableSuccess') : t('users.disableSuccess') })
    fetchUsers()
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } }
    appStore.showToast({ type: 'error', title: err.response?.data?.error || t('common.error') })
  }
}

onMounted(() => {
  fetchUsers()
})
</script>
