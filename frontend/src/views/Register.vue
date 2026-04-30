<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import api from '@/api'

const router = useRouter()
const { t, locale } = useI18n()
const appStore = useAppStore()

function toggleLanguage() {
  const newLocale = locale.value === 'zh-CN' ? 'en' : 'zh-CN'
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
}

const firstName = ref('')
const lastName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const captcha = ref('')
const agreedToTerms = ref(false)
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const isLoading = ref(false)
const error = ref('')

const captchaUrl = ref('')
const captchaKey = ref('')
const captchaLoading = ref(false)

const passwordStrength = computed(() => {
  const pwd = password.value
  if (!pwd) return { score: 0, text: '', color: '' }
  
  let score = 0
  if (pwd.length >= 8) score++
  if (/[A-Z]/.test(pwd)) score++
  if (/[a-z]/.test(pwd)) score++
  if (/[0-9]/.test(pwd)) score++
  if (/[^A-Za-z0-9]/.test(pwd)) score++
  
  const levels = [
    { text: t('auth.veryWeak'), color: 'bg-red-500' },
    { text: t('auth.weak'), color: 'bg-orange-500' },
    { text: t('auth.fair'), color: 'bg-yellow-500' },
    { text: t('auth.good'), color: 'bg-lime-500' },
    { text: t('auth.strong'), color: 'bg-green-500' },
    { text: t('auth.veryStrong'), color: 'bg-emerald-500' }
  ]
  
  return { score, ...levels[score] }
})

const isValid = computed(() => {
  return (
    firstName.value.length > 0 &&
    lastName.value.length > 0 &&
    email.value.length > 0 &&
    password.value.length >= 6 &&
    password.value === confirmPassword.value &&
    captcha.value.length > 0 &&
    agreedToTerms.value
  )
})

async function refreshCaptcha() {
  captchaLoading.value = true
  try {
    const response = await api.get('/api/v1/accounts/captcha/')
    captchaUrl.value = response.data.image
    captchaKey.value = response.data.key
  } catch (err) {
    console.error('Failed to fetch captcha:', err)
  } finally {
    captchaLoading.value = false
  }
}

async function handleRegister() {
  if (!isValid.value) return
  isLoading.value = true
  error.value = ''

  try {
    await api.post('/api/v1/accounts/register-v2/', {
      email: email.value,
      password: password.value,
      first_name: firstName.value,
      last_name: lastName.value,
      captcha_code: captcha.value,
      captcha_key: captchaKey.value
    })
    
    appStore.showToast({
      type: 'success',
      title: t('auth.registerSuccess'),
      message: t('auth.canNowLogin')
    })
    
    router.push('/login')
  } catch (err: any) {
    error.value = err.response?.data?.error || t('auth.registerFailed')
    refreshCaptcha()
    captcha.value = ''
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  refreshCaptcha()
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4">
    <!-- Animated Background -->
    <div class="absolute inset-0 overflow-hidden">
      <!-- Grid Pattern -->
      <div class="absolute inset-0 opacity-20" style="background-image: linear-gradient(rgba(16, 185, 129, 0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(16, 185, 129, 0.3) 1px, transparent 1px); background-size: 50px 50px;"></div>
      
      <!-- Floating Particles -->
      <div class="absolute top-1/4 left-1/4 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl animate-pulse"></div>
      <div class="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" style="animation-delay: 1s;"></div>
      <div class="absolute top-1/2 right-1/3 w-48 h-48 bg-teal-500/10 rounded-full blur-3xl animate-pulse" style="animation-delay: 2s;"></div>
      
      <!-- Data Stream Lines -->
      <svg class="absolute inset-0 w-full h-full opacity-10" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#10b981;stop-opacity:0" />
            <stop offset="50%" style="stop-color:#10b981;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#10b981;stop-opacity:0" />
          </linearGradient>
        </defs>
        <line x1="0" y1="15%" x2="100%" y2="20%" stroke="url(#lineGradient)" stroke-width="1" class="animate-pulse" />
        <line x1="0" y1="50%" x2="100%" y2="45%" stroke="url(#lineGradient)" stroke-width="1" class="animate-pulse" style="animation-delay: 0.5s;" />
        <line x1="0" y1="85%" x2="100%" y2="80%" stroke="url(#lineGradient)" stroke-width="1" class="animate-pulse" style="animation-delay: 1s;" />
      </svg>
    </div>

    <!-- Language Switch -->
    <button
      @click="toggleLanguage"
      class="fixed top-4 right-4 flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-400 hover:text-white transition-colors bg-slate-800/50 backdrop-blur-sm rounded-lg border border-slate-700/50"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"/>
      </svg>
      {{ locale === 'zh-CN' ? 'EN' : '中文' }}
    </button>

    <div class="w-full max-w-sm relative z-10">
      <!-- Logo & Title -->
      <div class="text-center mb-6">
        <div class="inline-flex items-center justify-center w-12 h-12 bg-gradient-to-br from-emerald-500 to-cyan-600 rounded-xl mb-3 shadow-lg shadow-emerald-500/25">
          <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
          </svg>
        </div>
        <h1 class="text-xl font-bold text-white tracking-tight">{{ t('auth.createAccount') }}</h1>
        <p class="text-sm text-slate-400 mt-1">{{ t('auth.registerSubtitle') }}</p>
      </div>

      <!-- Register Card -->
      <div class="bg-slate-800/60 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-700/50 p-5">
        <form @submit.prevent="handleRegister" class="space-y-3.5">
          <!-- Error -->
          <div v-if="error" class="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-3 py-2 rounded-lg">
            {{ error }}
          </div>

          <!-- Name -->
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm text-slate-400 mb-1">{{ t('auth.firstName') }}</label>
              <input
                v-model="firstName"
                type="text"
                class="w-full px-3 py-2 text-sm bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50"
                :placeholder="t('auth.firstNamePlaceholder')"
                required
              />
            </div>
            <div>
              <label class="block text-sm text-slate-400 mb-1">{{ t('auth.lastName') }}</label>
              <input
                v-model="lastName"
                type="text"
                class="w-full px-3 py-2 text-sm bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50"
                :placeholder="t('auth.lastNamePlaceholder')"
                required
              />
            </div>
          </div>

          <!-- Email -->
          <div>
            <label class="block text-sm text-slate-400 mb-1">{{ t('auth.email') }}</label>
            <div class="relative">
              <div class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <input
                v-model="email"
                type="email"
                class="w-full pl-9 pr-3 py-2 text-sm bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50"
                :placeholder="t('auth.emailPlaceholder')"
                required
              />
            </div>
          </div>

          <!-- Password -->
          <div>
            <label class="block text-sm text-slate-400 mb-1">{{ t('auth.password') }}</label>
            <div class="relative">
              <div class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                class="w-full pl-9 pr-9 py-2 text-sm bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50"
                :placeholder="t('auth.passwordPlaceholder')"
                required
                minlength="6"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
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
            <!-- Password Strength -->
            <div v-if="password" class="flex items-center gap-2 mt-1.5">
              <div class="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
                <div 
                  :class="passwordStrength.color"
                  class="h-full transition-all duration-300"
                  :style="{ width: `${(passwordStrength.score / 5) * 100}%` }"
                ></div>
              </div>
              <span class="text-xs text-slate-500 w-12">{{ passwordStrength.text }}</span>
            </div>
          </div>

          <!-- Confirm Password -->
          <div>
            <label class="block text-sm text-slate-400 mb-1">{{ t('auth.confirmPassword') }}</label>
            <div class="relative">
              <div class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <input
                v-model="confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                class="w-full pl-9 pr-9 py-2 text-sm bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50"
                :class="{ 'border-red-500/50 focus:ring-red-500/50': confirmPassword && password !== confirmPassword }"
                :placeholder="t('auth.confirmPasswordPlaceholder')"
                required
              />
              <button
                type="button"
                @click="showConfirmPassword = !showConfirmPassword"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
              >
                <svg v-if="!showConfirmPassword" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                </svg>
              </button>
            </div>
            <p v-if="confirmPassword && password !== confirmPassword" class="text-xs text-red-400 mt-1">
              {{ t('auth.passwordMismatch') }}
            </p>
          </div>

          <!-- Captcha -->
          <div>
            <label class="block text-sm text-slate-400 mb-1">{{ t('auth.captcha') }}</label>
            <div class="flex gap-2">
              <div class="relative flex-1">
                <div class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <input
                  v-model="captcha"
                  type="text"
                  maxlength="6"
                  class="w-full pl-9 pr-3 py-2 text-sm bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 uppercase tracking-wider text-center"
                  :placeholder="t('auth.captchaPlaceholder')"
                  required
                />
              </div>
              <div class="relative h-9 w-24 rounded-lg border border-slate-700 bg-slate-900/50 cursor-pointer overflow-hidden hover:border-emerald-500/50 transition-colors" @click="refreshCaptcha" :title="t('auth.refreshCaptcha')">
                <img
                  v-if="captchaUrl"
                  :src="captchaUrl"
                  alt="Captcha"
                  class="h-full w-full object-cover"
                />
                <div v-if="captchaLoading" class="absolute inset-0 bg-slate-900/80 flex items-center justify-center">
                  <svg class="w-4 h-4 text-emerald-400 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
                <div v-if="!captchaUrl && !captchaLoading" class="h-full w-full flex items-center justify-center text-slate-500">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </div>
              </div>
            </div>
          </div>

          <!-- Terms -->
          <label class="flex items-start gap-2 cursor-pointer">
            <input
              v-model="agreedToTerms"
              type="checkbox"
              class="mt-0.5 w-3.5 h-3.5 rounded border-slate-600 bg-slate-700 text-emerald-500 focus:ring-emerald-500/50"
            />
            <span class="text-xs text-slate-400">
              {{ t('auth.agreeToTerms') }}
              <a href="#" class="text-emerald-400 hover:text-emerald-300">{{ t('auth.termsOfService') }}</a>
              {{ t('auth.and') }}
              <a href="#" class="text-emerald-400 hover:text-emerald-300">{{ t('auth.privacyPolicy') }}</a>
            </span>
          </label>

          <!-- Submit -->
          <button
            type="submit"
            class="w-full py-2.5 bg-gradient-to-r from-emerald-500 to-cyan-600 hover:from-emerald-600 hover:to-cyan-700 text-white text-sm font-medium rounded-lg transition-all shadow-lg shadow-emerald-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="!isValid || isLoading"
          >
            <span v-if="isLoading" class="flex items-center justify-center gap-2">
              <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ t('auth.creatingAccount') }}
            </span>
            <span v-else>{{ t('auth.createAccount') }}</span>
          </button>
        </form>

        <!-- Divider -->
        <div class="relative my-4">
          <div class="absolute inset-0 flex items-center">
            <div class="w-full border-t border-slate-700"></div>
          </div>
          <div class="relative flex justify-center text-xs">
            <span class="px-2 bg-slate-800/60 text-slate-500">{{ t('auth.or') }}</span>
          </div>
        </div>

        <!-- Login Link -->
        <p class="text-center text-sm text-slate-400">
          {{ t('auth.alreadyHaveAccount') }}
          <router-link to="/login" class="text-emerald-400 hover:text-emerald-300 font-medium transition-colors">
            {{ t('auth.loginNow') }}
          </router-link>
        </p>
      </div>

      <!-- Footer -->
      <p class="text-center text-xs text-slate-500 mt-4">
        &copy; 2024 HyperFileLens · AI-Powered Backup Intelligence
      </p>
    </div>
  </div>
</template>
