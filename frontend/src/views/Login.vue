<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'
import api from '@/api'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const { t, locale } = useI18n()

function toggleLanguage() {
  const newLocale = locale.value === 'zh-CN' ? 'en' : 'zh-CN'
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
}

const email = ref('')
const password = ref('')
const captcha = ref('')
const rememberMe = ref(false)
const showPassword = ref(false)
const isLoading = ref(false)
const error = ref('')

const captchaUrl = ref('')
const captchaKey = ref('')

const showMfaDialog = ref(false)
const mfaCode = ref('')
const mfaMethod = ref<'email' | 'totp'>('email')
const pendingUserId = ref('')
const loginToken = ref('')

const isValid = computed(() => {
  return email.value.length > 0 && password.value.length > 0 && captcha.value.length > 0
})

async function refreshCaptcha() {
  try {
    const response = await api.get('/api/v1/accounts/captcha/')
    captchaUrl.value = response.data.image
    captchaKey.value = response.data.key
  } catch (err) {
    console.error('Failed to fetch captcha:', err)
  }
}

async function handleLogin() {
  if (!isValid.value) return
  isLoading.value = true
  error.value = ''

  try {
    const response = await authStore.login({
      email: email.value,
      password: password.value,
      captcha_code: captcha.value,
      captcha_key: captchaKey.value
    })
    
    if (response.mfa_required) {
      pendingUserId.value = response.user_id || ''
      mfaMethod.value = response.mfa_method || 'email'
      loginToken.value = response.login_token || ''
      showMfaDialog.value = true
      if (mfaMethod.value === 'email') {
        await api.post('/api/v1/accounts/mfa/send/', { user_id: pendingUserId.value, login_token: loginToken.value })
      }
    } else {
      router.push(route.query.redirect as string || '/')
    }
  } catch (err: any) {
    error.value = err.response?.data?.error || t('auth.invalidCredentials')
    refreshCaptcha()
    captcha.value = ''
  } finally {
    isLoading.value = false
  }
}

async function handleVerifyMfa() {
  if (!mfaCode.value) return
  try {
    isLoading.value = true
    await authStore.verifyMfa(pendingUserId.value, mfaCode.value, loginToken.value)
    router.push(route.query.redirect as string || '/')
  } catch (err: any) {
    error.value = err.response?.data?.error || t('auth.invalidMfaCode')
    mfaCode.value = ''
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  refreshCaptcha()
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-100 p-4">
    <!-- Language Switch -->
    <button
      @click="toggleLanguage"
      class="fixed top-4 right-4 flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"/>
      </svg>
      {{ locale === 'zh-CN' ? 'EN' : '中文' }}
    </button>

    <div class="w-full max-w-sm">
      <!-- Logo & Title -->
      <div class="text-center mb-6">
        <div class="inline-flex items-center justify-center w-10 h-10 bg-indigo-600 rounded-lg mb-3">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
          </svg>
        </div>
        <h1 class="text-xl font-semibold text-slate-900">HyperFileLens</h1>
        <p class="text-sm text-slate-500 mt-1">{{ t('auth.loginSubtitle') }}</p>
      </div>

      <!-- Login Card -->
      <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
        <form @submit.prevent="handleLogin" class="space-y-4">
          <!-- Error -->
          <div v-if="error" class="bg-red-50 border border-red-200 text-red-600 text-sm px-3 py-2 rounded-lg">
            {{ error }}
          </div>

          <!-- Email -->
          <div>
            <label class="block text-sm text-slate-600 mb-1">{{ t('auth.email') }}</label>
            <input
              v-model="email"
              type="email"
              class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              :placeholder="t('auth.emailPlaceholder')"
              required
              autofocus
            />
          </div>

          <!-- Password -->
          <div>
            <label class="block text-sm text-slate-600 mb-1">{{ t('auth.password') }}</label>
            <div class="relative">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                class="w-full px-3 py-2 pr-9 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                :placeholder="t('auth.passwordPlaceholder')"
                required
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <svg v-if="!showPassword" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- Captcha -->
          <div>
            <label class="block text-sm text-slate-600 mb-1">{{ t('auth.captcha') }}</label>
            <div class="flex gap-2">
              <input
                v-model="captcha"
                type="text"
                maxlength="6"
                class="flex-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent uppercase tracking-wider text-center"
                :placeholder="t('auth.captchaPlaceholder')"
                required
              />
              <img
                :src="captchaUrl"
                alt="Captcha"
                class="h-9 w-24 rounded-lg border border-slate-200 cursor-pointer hover:opacity-80 transition-opacity bg-slate-50"
                @click="refreshCaptcha"
                :title="t('auth.refreshCaptcha')"
              />
            </div>
          </div>

          <!-- Remember & Forgot -->
          <div class="flex items-center justify-between text-sm">
            <label class="flex items-center gap-1.5 cursor-pointer">
              <input v-model="rememberMe" type="checkbox" class="w-3.5 h-3.5 rounded border-slate-300 text-indigo-600" />
              <span class="text-slate-600">{{ t('auth.rememberMe') }}</span>
            </label>
            <router-link to="/forgot-password" class="text-indigo-600 hover:text-indigo-700">
              {{ t('auth.forgotPassword') }}
            </router-link>
          </div>

          <!-- Submit -->
          <button
            type="submit"
            class="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="!isValid || isLoading"
          >
            {{ isLoading ? t('auth.loggingIn') : t('auth.login') }}
          </button>
        </form>

        <!-- Divider -->
        <div class="relative my-4">
          <div class="absolute inset-0 flex items-center">
            <div class="w-full border-t border-slate-200"></div>
          </div>
          <div class="relative flex justify-center text-xs">
            <span class="px-2 bg-white text-slate-400">{{ t('auth.or') }}</span>
          </div>
        </div>

        <!-- Register Link -->
        <p class="text-center text-sm text-slate-500">
          {{ t('auth.noAccount') }}
          <router-link to="/register" class="text-indigo-600 hover:text-indigo-700 font-medium">
            {{ t('auth.registerNow') }}
          </router-link>
        </p>
      </div>

      <!-- Footer -->
      <p class="text-center text-xs text-slate-400 mt-4">
        &copy; 2024 HyperFileLens
      </p>
    </div>

    <!-- MFA Dialog -->
    <div v-if="showMfaDialog" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl shadow-xl p-5 w-full max-w-xs">
        <h3 class="text-lg font-medium text-slate-900 text-center mb-1">{{ t('auth.mfaRequired') }}</h3>
        <p class="text-sm text-slate-500 text-center mb-4">{{ t('auth.mfaCodeSent') }}</p>
        
        <input
          v-model="mfaCode"
          type="text"
          maxlength="6"
          class="w-full px-3 py-2 text-center text-xl tracking-widest border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 mb-4"
          :placeholder="t('auth.mfaCodePlaceholder')"
        />
        
        <div class="flex gap-2">
          <button
            @click="showMfaDialog = false"
            class="flex-1 py-2 border border-slate-200 text-slate-600 text-sm rounded-lg hover:bg-slate-50"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            @click="handleVerifyMfa"
            :disabled="!mfaCode || isLoading"
            class="flex-1 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {{ t('auth.verify') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
