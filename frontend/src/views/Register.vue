<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '@/stores/app'
import api from '@/api'

const router = useRouter()
const { t, locale } = useI18n()
const appStore = useAppStore()

// Language switch
function toggleLanguage() {
  const newLocale = locale.value === 'zh-CN' ? 'en' : 'zh-CN'
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
}

// Form fields
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

// Captcha
const captchaUrl = ref('')
const captchaKey = ref('')

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
  try {
    const response = await api.get('/accounts/captcha/', { responseType: 'blob' })
    captchaUrl.value = URL.createObjectURL(response.data)
    captchaKey.value = response.headers['x-captcha-key'] || ''
  } catch (err) {
    console.error('Failed to fetch captcha:', err)
  }
}

async function handleRegister() {
  if (!isValid.value) return
  
  isLoading.value = true
  error.value = ''

  try {
    await api.post('/accounts/register/', {
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
  <div class="min-h-screen flex bg-gradient-to-br from-slate-50 to-slate-100">
    <!-- Left Side - Branding -->
    <div class="hidden lg:flex lg:w-1/2 relative overflow-hidden">
      <!-- Gradient Background -->
      <div class="absolute inset-0 bg-gradient-to-br from-emerald-600 via-teal-600 to-cyan-500"></div>
      
      <!-- Animated Background Shapes -->
      <div class="absolute inset-0 overflow-hidden">
        <div class="absolute -top-40 -left-40 w-80 h-80 bg-white/10 rounded-full blur-3xl"></div>
        <div class="absolute top-1/3 -right-20 w-60 h-60 bg-white/10 rounded-full blur-3xl"></div>
        <div class="absolute bottom-20 left-20 w-40 h-40 bg-white/10 rounded-full blur-2xl"></div>
      </div>
      
      <!-- Content -->
      <div class="relative z-10 flex flex-col justify-center items-center w-full p-16 text-white">
        <!-- Logo -->
        <div class="mb-10">
          <div class="w-20 h-20 bg-white/20 backdrop-blur-xl rounded-2xl flex items-center justify-center shadow-2xl">
            <svg class="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
          </div>
        </div>
        
        <h1 class="text-5xl font-bold mb-4 tracking-tight">{{ t('auth.createAccount') }}</h1>
        <p class="text-xl text-white/80 text-center max-w-md mb-12 leading-relaxed">
          {{ t('auth.registerSubtitle') }}
        </p>
        
        <!-- Benefits -->
        <div class="space-y-5">
          <div class="flex items-center gap-4 bg-white/10 backdrop-blur-sm rounded-xl px-5 py-3">
            <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
            </div>
            <span class="text-white/90 font-medium">{{ t('auth.benefit1') }}</span>
          </div>
          <div class="flex items-center gap-4 bg-white/10 backdrop-blur-sm rounded-xl px-5 py-3">
            <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
              </svg>
            </div>
            <span class="text-white/90 font-medium">{{ t('auth.benefit2') }}</span>
          </div>
          <div class="flex items-center gap-4 bg-white/10 backdrop-blur-sm rounded-xl px-5 py-3">
            <div class="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
              </svg>
            </div>
            <span class="text-white/90 font-medium">{{ t('auth.benefit3') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Side - Register Form -->
    <div class="w-full lg:w-1/2 flex flex-col relative">
      <!-- Language Switch Button -->
      <div class="absolute top-6 right-6 z-10">
        <button
          @click="toggleLanguage"
          class="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl shadow-sm text-slate-600 hover:text-emerald-600 hover:border-emerald-300 hover:shadow-md transition-all duration-200"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"/>
          </svg>
          <span class="font-medium">{{ locale === 'zh-CN' ? 'English' : '中文' }}</span>
        </button>
      </div>
      
      <div class="flex-1 flex items-center justify-center px-8 py-12 overflow-y-auto">
        <div class="w-full max-w-md">
          <!-- Mobile Logo -->
          <div class="lg:hidden text-center mb-10">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl shadow-lg mb-4">
              <svg class="w-9 h-9 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
              </svg>
            </div>
            <h1 class="text-2xl font-bold text-slate-800">HyperFileLens</h1>
          </div>

          <!-- Header -->
          <div class="mb-8">
            <h2 class="text-3xl font-bold text-slate-900">{{ t('auth.getStarted') }}</h2>
            <p class="text-slate-500 mt-2">{{ t('auth.registerSubtitle') }}</p>
          </div>

          <!-- Register Form Card -->
          <div class="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-8">
            <form @submit.prevent="handleRegister" class="space-y-4">
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

              <!-- Name Fields -->
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label for="firstName" class="block text-sm font-medium text-slate-700 mb-2">
                    {{ t('auth.firstName') }}
                  </label>
                  <div class="relative group">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <svg class="h-5 w-5 text-slate-400 group-focus-within:text-emerald-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                      </svg>
                    </div>
                    <input
                      id="firstName"
                      v-model="firstName"
                      type="text"
                      class="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200 placeholder:text-slate-400"
                      :placeholder="t('auth.firstNamePlaceholder')"
                      required
                    />
                  </div>
                </div>
                <div>
                  <label for="lastName" class="block text-sm font-medium text-slate-700 mb-2">
                    {{ t('auth.lastName') }}
                  </label>
                  <div class="relative group">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <svg class="h-5 w-5 text-slate-400 group-focus-within:text-emerald-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                      </svg>
                    </div>
                    <input
                      id="lastName"
                      v-model="lastName"
                      type="text"
                      class="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200 placeholder:text-slate-400"
                      :placeholder="t('auth.lastNamePlaceholder')"
                      required
                    />
                  </div>
                </div>
              </div>

              <!-- Email Input -->
              <div>
                <label for="email" class="block text-sm font-medium text-slate-700 mb-2">
                  {{ t('auth.email') }}
                </label>
                <div class="relative group">
                  <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg class="h-5 w-5 text-slate-400 group-focus-within:text-emerald-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                    </svg>
                  </div>
                  <input
                    id="email"
                    v-model="email"
                    type="email"
                    class="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200 placeholder:text-slate-400"
                    :placeholder="t('auth.emailPlaceholder')"
                    required
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
                    <svg class="h-5 w-5 text-slate-400 group-focus-within:text-emerald-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                    </svg>
                  </div>
                  <input
                    id="password"
                    v-model="password"
                    :type="showPassword ? 'text' : 'password'"
                    class="w-full pl-12 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200 placeholder:text-slate-400"
                    :placeholder="t('auth.passwordPlaceholder')"
                    required
                    minlength="6"
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
                <!-- Password Strength Indicator -->
                <div v-if="password" class="mt-2">
                  <div class="flex items-center gap-2">
                    <div class="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                      <div 
                        :class="passwordStrength.color"
                        class="h-full transition-all duration-300"
                        :style="{ width: `${(passwordStrength.score / 5) * 100}%` }"
                      ></div>
                    </div>
                    <span class="text-xs text-slate-500 w-12">{{ passwordStrength.text }}</span>
                  </div>
                </div>
              </div>

              <!-- Confirm Password Input -->
              <div>
                <label for="confirmPassword" class="block text-sm font-medium text-slate-700 mb-2">
                  {{ t('auth.confirmPassword') }}
                </label>
                <div class="relative group">
                  <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg class="h-5 w-5 text-slate-400 group-focus-within:text-emerald-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                    </svg>
                  </div>
                  <input
                    id="confirmPassword"
                    v-model="confirmPassword"
                    :type="showConfirmPassword ? 'text' : 'password'"
                    class="w-full pl-12 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200 placeholder:text-slate-400"
                    :class="{ 'border-red-300 focus:ring-red-500': confirmPassword && password !== confirmPassword }"
                    :placeholder="t('auth.confirmPasswordPlaceholder')"
                    required
                  />
                  <button
                    type="button"
                    @click="showConfirmPassword = !showConfirmPassword"
                    class="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    <svg v-if="!showConfirmPassword" class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                    </svg>
                    <svg v-else class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                    </svg>
                  </button>
                </div>
                <p v-if="confirmPassword && password !== confirmPassword" class="mt-1 text-sm text-red-500">
                  {{ t('auth.passwordMismatch') }}
                </p>
              </div>

              <!-- Captcha -->
              <div>
                <label for="captcha" class="block text-sm font-medium text-slate-700 mb-2">
                  {{ t('auth.captcha') }}
                </label>
                <div class="flex gap-3">
                  <div class="relative group flex-1">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <svg class="h-5 w-5 text-slate-400 group-focus-within:text-emerald-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                      </svg>
                    </div>
                    <input
                      id="captcha"
                      v-model="captcha"
                      type="text"
                      maxlength="6"
                      class="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200 uppercase tracking-[0.3em] text-center font-mono text-lg"
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

              <!-- Terms -->
              <div class="flex items-start gap-3 pt-1">
                <input
                  id="terms"
                  v-model="agreedToTerms"
                  type="checkbox"
                  class="mt-0.5 w-4 h-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                />
                <label for="terms" class="text-sm text-slate-600 cursor-pointer">
                  {{ t('auth.agreeToTerms') }}
                  <a href="#" class="text-emerald-600 hover:text-emerald-700 font-medium">{{ t('auth.termsOfService') }}</a>
                  {{ t('auth.and') }}
                  <a href="#" class="text-emerald-600 hover:text-emerald-700 font-medium">{{ t('auth.privacyPolicy') }}</a>
                </label>
              </div>

              <!-- Submit Button -->
              <button
                type="submit"
                class="w-full py-3.5 px-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-medium rounded-xl shadow-lg shadow-emerald-500/25 hover:shadow-xl hover:shadow-emerald-500/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-lg flex items-center justify-center gap-2 mt-6"
                :disabled="!isValid || isLoading"
              >
                <svg v-if="isLoading" class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>{{ isLoading ? t('auth.creatingAccount') : t('auth.createAccount') }}</span>
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

            <!-- Login Link -->
            <div class="text-center">
              <p class="text-sm text-slate-500">
                {{ t('auth.alreadyHaveAccount') }}
                <router-link to="/login" class="text-emerald-600 hover:text-emerald-700 font-semibold transition-colors">
                  {{ t('auth.loginNow') }}
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
  </div>
</template>
