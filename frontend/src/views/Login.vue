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

// Language switch
function toggleLanguage() {
  const newLocale = locale.value === 'zh-CN' ? 'en' : 'zh-CN'
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
}

// Form fields
const email = ref('')
const password = ref('')
const captcha = ref('')
const rememberMe = ref(false)
const showPassword = ref(false)
const isLoading = ref(false)
const error = ref('')

// Captcha
const captchaUrl = ref('')
const captchaKey = ref('')

// MFA
const showMfaDialog = ref(false)
const mfaCode = ref('')
const mfaMethod = ref<'email' | 'totp'>('email')
const pendingUserId = ref('')
const loginToken = ref('')

const isValid = computed(() => {
  return email.value.length > 0 && password.value.length > 0 && captcha.value.length > 0
})

// Fetch captcha image
async function refreshCaptcha() {
  try {
    const response = await api.get('/accounts/captcha/', { responseType: 'blob' })
    captchaUrl.value = URL.createObjectURL(response.data)
    captchaKey.value = response.headers['x-captcha-key'] || ''
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
        await api.post('/accounts/mfa/send/', { user_id: pendingUserId.value, login_token: loginToken.value })
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
  <div class="min-h-screen flex bg-gradient-to-br from-slate-50 to-slate-100">
    <!-- Left Side - Branding -->
    <div class="hidden lg:flex lg:w-1/2 relative overflow-hidden">
      <!-- Gradient Background -->
      <div class="absolute inset-0 bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500"></div>
      
      <!-- Animated Background Shapes -->
      <div class="absolute inset-0 overflow-hidden">
        <div class="absolute -top-40 -right-40 w-80 h-80 bg-white/10 rounded-full blur-3xl"></div>
        <div class="absolute top-1/2 -left-20 w-60 h-60 bg-white/10 rounded-full blur-3xl"></div>
        <div class="absolute bottom-20 right-20 w-40 h-40 bg-white/10 rounded-full blur-2xl"></div>
      </div>
      
      <!-- Content -->
      <div class="relative z-10 flex flex-col justify-center items-center w-full p-16 text-white">
        <!-- Logo -->
        <div class="mb-10">
          <div class="w-20 h-20 bg-white/20 backdrop-blur-xl rounded-2xl flex items-center justify-center shadow-2xl">
            <svg class="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
            </svg>
          </div>
        </div>
        
        <h1 class="text-5xl font-bold mb-4 tracking-tight">HyperFileLens</h1>
        <p class="text-xl text-white/80 text-center max-w-md mb-12 leading-relaxed">
          AI-Powered File Intelligence Platform
        </p>
        
        <!-- Features -->
        <div class="space-y-5">
          <div class="flex items-center gap-4 bg-white/10 backdrop-blur-sm rounded-xl px-5 py-3">
            <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
            </div>
            <span class="text-white/90 font-medium">{{ t('auth.feature1') }}</span>
          </div>
          <div class="flex items-center gap-4 bg-white/10 backdrop-blur-sm rounded-xl px-5 py-3">
            <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
            </div>
            <span class="text-white/90 font-medium">{{ t('auth.feature2') }}</span>
          </div>
          <div class="flex items-center gap-4 bg-white/10 backdrop-blur-sm rounded-xl px-5 py-3">
            <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              </svg>
            </div>
            <span class="text-white/90 font-medium">{{ t('auth.feature3') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Side - Login Form -->
    <div class="w-full lg:w-1/2 flex flex-col relative">
      <!-- Language Switch Button -->
      <div class="absolute top-6 right-6 z-10">
        <button
          @click="toggleLanguage"
          class="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl shadow-sm text-slate-600 hover:text-indigo-600 hover:border-indigo-300 hover:shadow-md transition-all duration-200"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"/>
          </svg>
          <span class="font-medium">{{ locale === 'zh-CN' ? 'English' : '中文' }}</span>
        </button>
      </div>
      
      <div class="flex-1 flex items-center justify-center px-8 py-12">
        <div class="w-full max-w-md">
          <!-- Mobile Logo -->
          <div class="lg:hidden text-center mb-10">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl shadow-lg mb-4">
              <svg class="w-9 h-9 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
              </svg>
            </div>
            <h1 class="text-2xl font-bold text-slate-800">HyperFileLens</h1>
          </div>

          <!-- Header -->
          <div class="mb-8">
            <h2 class="text-3xl font-bold text-slate-900">{{ t('auth.welcomeBack') }}</h2>
            <p class="text-slate-500 mt-2">{{ t('auth.loginSubtitle') }}</p>
          </div>

          <!-- Login Form Card -->
          <div class="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-8">
            <form @submit.prevent="handleLogin" class="space-y-5">
              <!-- Error Message -->
              <Transition
                enter-active-class="transition duration-200 ease-out"
                enter-from-class="opacity-0 -translate-y-1"
                enter-to-class="opacity-100 translate-y-0"
              >
                <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl flex items-center gap-3">
                  <svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                  </svg>
                  <span class="text-sm font-medium">{{ error }}</span>
                </div>
              </Transition>

              <!-- Email Input -->
              <div>
                <label for="email" class="block text-sm font-medium text-slate-700 mb-2">
                  {{ t('auth.email') }}
                </label>
                <div class="relative group">
                  <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none transition-colors group-focus-within:text-indigo-500">
                    <svg class="h-5 w-5 text-slate-400 group-focus-within:text-indigo-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                    </svg>
                  </div>
                  <input
                    id="email"
                    v-model="email"
                    type="email"
                    class="w-full pl-12 pr-4 py-3.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-200 placeholder:text-slate-400"
                    :placeholder="t('auth.emailPlaceholder')"
                    required
                    autofocus
                  />
                </div>
              </div>

              <!-- Password Input -->
              <div>
                <label for="password" class="block text-sm font-medium text-slate-700 mb-2">
                  {{ t('auth.password') }}
                </label>
                <div class="relative group">
                  <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg class="h-5 w-5 text-slate-400 group-focus-within:text-indigo-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                    </svg>
                  </div>
                  <input
                    id="password"
                    v-model="password"
                    :type="showPassword ? 'text' : 'password'"
                    class="w-full pl-12 pr-12 py-3.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-200 placeholder:text-slate-400"
                    :placeholder="t('auth.passwordPlaceholder')"
                    required
                  />
                  <button
                    type="button"
                    @click="showPassword = !showPassword"
                    class="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    <svg v-if="!showPassword" class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                    </svg>
                    <svg v-else class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                    </svg>
                  </button>
                </div>
              </div>

              <!-- Captcha -->
              <div>
                <label for="captcha" class="block text-sm font-medium text-slate-700 mb-2">
                  {{ t('auth.captcha') }}
                </label>
                <div class="flex gap-3">
                  <div class="relative group flex-1">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <svg class="h-5 w-5 text-slate-400 group-focus-within:text-indigo-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                      </svg>
                    </div>
                    <input
                      id="captcha"
                      v-model="captcha"
                      type="text"
                      maxlength="6"
                      class="w-full pl-12 pr-4 py-3.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-200 uppercase tracking-[0.3em] text-center font-mono text-lg"
                      :placeholder="t('auth.captchaPlaceholder')"
                      required
                    />
                  </div>
                  <button
                    type="button"
                    @click="refreshCaptcha"
                    class="flex-shrink-0 relative"
                  >
                    <img
                      :src="captchaUrl"
                      alt="Captcha"
                      class="h-[50px] w-[120px] rounded-xl border border-slate-200 cursor-pointer hover:opacity-80 transition-all duration-200 object-cover bg-slate-100"
                      :title="t('auth.refreshCaptcha')"
                    />
                    <div class="absolute inset-0 flex items-center justify-center bg-black/5 rounded-xl opacity-0 hover:opacity-100 transition-opacity">
                      <svg class="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                      </svg>
                    </div>
                  </button>
                </div>
              </div>

              <!-- Remember & Forgot -->
              <div class="flex items-center justify-between pt-1">
                <label class="flex items-center cursor-pointer group">
                  <input
                    v-model="rememberMe"
                    type="checkbox"
                    class="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                  />
                  <span class="ml-2.5 text-sm text-slate-600 group-hover:text-slate-800 transition-colors">{{ t('auth.rememberMe') }}</span>
                </label>
                <router-link to="/forgot-password" class="text-sm text-indigo-600 hover:text-indigo-700 font-medium transition-colors">
                  {{ t('auth.forgotPassword') }}
                </router-link>
              </div>

              <!-- Submit Button -->
              <button
                type="submit"
                class="w-full py-3.5 px-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-medium rounded-xl shadow-lg shadow-indigo-500/25 hover:shadow-xl hover:shadow-indigo-500/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-lg flex items-center justify-center gap-2 mt-6"
                :disabled="!isValid || isLoading"
              >
                <svg v-if="isLoading" class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>{{ isLoading ? t('auth.loggingIn') : t('auth.login') }}</span>
              </button>
            </form>

            <!-- Divider -->
            <div class="relative my-7">
              <div class="absolute inset-0 flex items-center">
                <div class="w-full border-t border-slate-200"></div>
              </div>
              <div class="relative flex justify-center text-sm">
                <span class="px-4 bg-white text-slate-400">{{ t('auth.or') }}</span>
              </div>
            </div>

            <!-- Register Link -->
            <div class="text-center">
              <p class="text-sm text-slate-500">
                {{ t('auth.noAccount') }}
                <router-link to="/register" class="text-indigo-600 hover:text-indigo-700 font-semibold transition-colors">
                  {{ t('auth.registerNow') }}
                </router-link>
              </p>
            </div>
          </div>

          <!-- Footer -->
          <div class="mt-8 text-center text-sm text-slate-400">
            <p>&copy; 2024 HyperFileLens. All rights reserved.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- MFA Dialog -->
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="showMfaDialog" class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <Transition
          enter-active-class="transition duration-200 ease-out"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
        >
          <div class="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full">
            <div class="text-center mb-6">
              <div class="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                </svg>
              </div>
              <h3 class="text-xl font-semibold text-slate-900">{{ t('auth.mfaRequired') }}</h3>
              <p class="text-slate-500 mt-2">{{ t('auth.mfaCodeSent') }}</p>
            </div>

            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-2">
                  {{ t('auth.mfaCode') }}
                </label>
                <input
                  v-model="mfaCode"
                  type="text"
                  maxlength="6"
                  class="w-full px-4 py-3.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-center text-2xl tracking-[0.5em] uppercase font-mono"
                  :placeholder="t('auth.mfaCodePlaceholder')"
                />
              </div>

              <div class="flex gap-3 pt-2">
                <button
                  @click="showMfaDialog = false"
                  class="flex-1 py-3 px-4 border border-slate-200 text-slate-700 font-medium rounded-xl hover:bg-slate-50 transition-colors"
                >
                  {{ t('common.cancel') }}
                </button>
                <button
                  @click="handleVerifyMfa"
                  :disabled="!mfaCode || isLoading"
                  class="flex-1 py-3 px-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-medium rounded-xl disabled:opacity-50 transition-all"
                >
                  {{ t('auth.verify') }}
                </button>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </div>
</template>
