<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const authStore = useAuthStore()
const { t } = useI18n()

const isLoading = ref(false)
const email = ref('')
const password = ref('')
const error = ref('')

const isValid = computed(() => {
  return email.value.length > 0 && password.value.length > 0
})

async function handleLogin() {
  if (!isValid.value) return

  isLoading.value = true
  error.value = ''

  try {
    await authStore.login({
      email: email.value,
      password: password.value
    })
    router.push('/')
  } catch (err: any) {
    error.value = err.response?.data?.error || t('auth.invalidCredentials')
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100 py-12 px-4">
    <div class="max-w-md w-full">
      <!-- Logo and Title -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-primary-600 rounded-2xl mb-4">
          <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
          </svg>
        </div>
        <h1 class="text-3xl font-bold text-gray-900">HyperFileLens</h1>
        <p class="text-gray-600 mt-2">{{ t('auth.loginSubtitle') }}</p>
      </div>

      <!-- Login Form -->
      <div class="card p-8">
        <form @submit.prevent="handleLogin" class="space-y-6">
          <!-- Error Message -->
          <div v-if="error" class="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-lg">
            {{ error }}
          </div>

          <!-- Email -->
          <div>
            <label for="email" class="label">{{ t('auth.email') }}</label>
            <input
              id="email"
              v-model="email"
              type="email"
              class="input"
              :placeholder="t('auth.email')"
              required
              autofocus
            />
          </div>

          <!-- Password -->
          <div>
            <label for="password" class="label">{{ t('auth.password') }}</label>
            <input
              id="password"
              v-model="password"
              type="password"
              class="input"
              :placeholder="t('auth.password')"
              required
            />
          </div>

          <!-- Remember & Forgot -->
          <div class="flex items-center justify-between">
            <label class="flex items-center">
              <input type="checkbox" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
              <span class="ml-2 text-sm text-gray-600">{{ t('auth.rememberMe') }}</span>
            </label>
            <a href="#" class="text-sm text-primary-600 hover:text-primary-700">
              {{ t('auth.forgotPassword') }}
            </a>
          </div>

          <!-- Submit -->
          <button
            type="submit"
            class="btn-primary w-full py-3"
            :disabled="!isValid || isLoading"
          >
            <span v-if="isLoading" class="spinner-sm mr-2"></span>
            {{ t('auth.login') }}
          </button>
        </form>

        <!-- Register Link -->
        <div class="mt-6 text-center">
          <p class="text-sm text-gray-600">
            {{ $t('auth.createAccount') }}
            <router-link to="/register" class="text-primary-600 hover:text-primary-700 font-medium">
              {{ $t('auth.register') }}
            </router-link>
          </p>
        </div>
      </div>

      <!-- Footer -->
      <div class="mt-8 text-center text-sm text-gray-500">
        <p>AI-Powered File Intelligence for Backup and Archive Data</p>
      </div>
    </div>
  </div>
</template>
