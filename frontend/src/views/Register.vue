<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '@/api'

const router = useRouter()
const { t, locale } = useI18n()

// Language switch
const currentLocale = computed(() => locale.value)

function toggleLanguage() {
  locale.value = locale.value === 'zh-CN' ? 'en' : 'zh-CN'
  localStorage.setItem('locale', locale.value)
}

// Form fields
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const firstName = ref('')
const lastName = ref('')
const captcha = ref('')
const agreeTerms = ref(false)
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const isLoading = ref(false)
const error = ref('')

// Captcha
const captchaUrl = ref('')
const captchaKey = ref('')

// Password strength
const passwordStrength = computed(() => {
  const pwd = password.value
  if (!pwd) return 0
  let strength = 0
  if (pwd.length >= 8) strength++
  if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) strength++
  if (/\d/.test(pwd)) strength++
  if (/[!@#$%^&*(),.?":{}|<>]/.test(pwd)) strength++
  return strength
})

const passwordStrengthText = computed(() => {
  const texts = ['', t('auth.weak'), t('auth.fair'), t('auth.good'), t('auth.strong')]
  return texts[passwordStrength.value]
})

const passwordStrengthColor = computed(() => {
  const colors = ['', 'bg-danger-500', 'bg-warning-500', 'bg-primary-500', 'bg-success-500']
  return colors[passwordStrength.value]
})

const isValid = computed(() => {
  return (
    email.value.length > 0 &&
    password.value.length >= 8 &&
    password.value === confirmPassword.value &&
    firstName.value.length > 0 &&
    captcha.value.length > 0 &&
    agreeTerms.value
  )
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

async function handleRegister() {
  if (!isValid.value) return

  if (password.value !== confirmPassword.value) {
    error.value = t('auth.passwordMismatch')
    return
  }

  isLoading.value = true
  error.value = ''

  try {
    await api.post('/accounts/register/', {
      email: email.value,
      password: password.value,
      first_name: firstName.value,
      last_name: lastName.value,
      captcha: captcha.value,
      captcha_key: captchaKey.value
    })
    
    // Redirect to login with success message
    router.push({ path: '/login', query: { registered: 'true' } })
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
  <div class="min-h-screen flex">
    <!-- Left Side - Branding -->
    <div class="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary-600 via-primary-700 to-primary-800 relative overflow-hidden">
      <!-- Background Pattern -->
      <div class="absolute inset-0 opacity-10">
        <svg class="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          <defs>
            <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
              <path d="M 10 0 L 0 0 0 10" fill="none" stroke="white" stroke-width="0.5"/>
            </pattern>
          </defs>
          <rect width="100" height="100" fill="url(#grid)"/>
        </svg>
      </div>
      
      <div class="relative z-10 flex flex-col justify-center items-center w-full p-12 text-white">
        <!-- Logo -->
        <div class="mb-8">
          <div class="w-24 h-24 bg-white/20 backdrop-blur-sm rounded-3xl flex items-center justify-center">
            <svg class="w-14 h-14 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
            </svg>
          </div>
        </div>
        
        <h1 class="text-4xl font-bold mb-4">HyperFileLens</h1>
        <p class="text-xl text-primary-100 text-center max-w-md mb-8">
          AI-Powered File Intelligence for Backup and Archive Data
        </p>
        
        <!-- Features -->
        <div class="space-y-4 text-primary-100">
          <div class="flex items-center gap-3">
            <svg class="w-5 h-5 text-primary-300" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <span>{{ t('auth.registerFeature1') }}</span>
          </div>
          <div class="flex items-center gap-3">
            <svg class="w-5 h-5 text-primary-300" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <span>{{ t('auth.registerFeature2') }}</span>
          </div>
          <div class="flex items-center gap-3">
            <svg class="w-5 h-5 text-primary-300" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <span>{{ t('auth.registerFeature3') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Side - Register Form -->
    <div class="w-full lg:w-1/2 flex flex-col bg-gray-50 overflow-y-auto">
      <!-- Language Switch Button -->
      <div class="flex justify-end p-4">
        <button
          @click="toggleLanguage"
          class="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-200 rounded-lg transition-colors"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"/>
          </svg>
          <span>{{ currentLocale === 'zh-CN' ? 'English' : '中文' }}</span>
        </button>
      </div>
      
      <div class="flex-1 flex items-center justify-center px-8 pb-8">
      <div class="max-w-md w-full py-8">
        <!-- Mobile Logo -->
        <div class="lg:hidden text-center mb-8">
          <div class="inline-flex items-center justify-center w-16 h-16 bg-primary-600 rounded-2xl mb-4">
            <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
            </svg>
          </div>
          <h1 class="text-2xl font-bold text-gray-900">HyperFileLens</h1>
        </div>

        <div class="text-center mb-8">
          <h2 class="text-2xl font-bold text-gray-900">{{ t('auth.createAccount') }}</h2>
          <p class="text-gray-600 mt-2">{{ t('auth.registerSubtitle') }}</p>
        </div>

        <!-- Register Form Card -->
        <div class="bg-white rounded-2xl shadow-xl p-8">
          <form @submit.prevent="handleRegister" class="space-y-4">
            <!-- Error Message -->
            <div v-if="error" class="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-xl flex items-center gap-2">
              <svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
              </svg>
              {{ error }}
            </div>

            <!-- Name Row -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label for="firstName" class="block text-sm font-medium text-gray-700 mb-1.5">
                  {{ t('auth.firstName') }}
                </label>
                <div class="relative">
                  <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                    <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                    </svg>
                  </div>
                  <input
                    id="firstName"
                    v-model="firstName"
                    type="text"
                    class="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                    :placeholder="t('auth.firstNamePlaceholder')"
                    required
                  />
                </div>
              </div>
              <div>
                <label for="lastName" class="block text-sm font-medium text-gray-700 mb-1.5">
                  {{ t('auth.lastName') }}
                </label>
                <div class="relative">
                  <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                    <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                    </svg>
                  </div>
                  <input
                    id="lastName"
                    v-model="lastName"
                    type="text"
                    class="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                    :placeholder="t('auth.lastNamePlaceholder')"
                    required
                  />
                </div>
              </div>
            </div>

            <!-- Email Input -->
            <div>
              <label for="email" class="block text-sm font-medium text-gray-700 mb-1.5">
                {{ t('auth.email') }}
              </label>
              <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                  </svg>
                </div>
                <input
                  id="email"
                  v-model="email"
                  type="email"
                  class="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                  :placeholder="t('auth.emailPlaceholder')"
                  required
                />
              </div>
            </div>

            <!-- Password Input -->
            <div>
              <label for="password" class="block text-sm font-medium text-gray-700 mb-1.5">
                {{ t('auth.password') }}
              </label>
              <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                  </svg>
                </div>
                <input
                  id="password"
                  v-model="password"
                  :type="showPassword ? 'text' : 'password'"
                  class="w-full pl-11 pr-12 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                  :placeholder="t('auth.passwordPlaceholder')"
                  required
                />
                <button
                  type="button"
                  @click="showPassword = !showPassword"
                  class="absolute inset-y-0 right-0 pr-3.5 flex items-center text-gray-400 hover:text-gray-600 transition-colors"
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
              <!-- Password Strength -->
              <div v-if="password" class="mt-2">
                <div class="flex gap-1 mb-1">
                  <div v-for="i in 4" :key="i" class="h-1 flex-1 rounded-full bg-gray-200">
                    <div v-if="i <= passwordStrength" class="h-full rounded-full transition-colors" :class="passwordStrengthColor"></div>
                  </div>
                </div>
                <p class="text-xs text-gray-500">{{ passwordStrengthText }}</p>
              </div>
            </div>

            <!-- Confirm Password Input -->
            <div>
              <label for="confirmPassword" class="block text-sm font-medium text-gray-700 mb-1.5">
                {{ t('auth.confirmPassword') }}
              </label>
              <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                  </svg>
                </div>
                <input
                  id="confirmPassword"
                  v-model="confirmPassword"
                  :type="showConfirmPassword ? 'text' : 'password'"
                  class="w-full pl-11 pr-12 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                  :class="{'border-danger-500 focus:ring-danger-500 focus:border-danger-500': confirmPassword && password !== confirmPassword}"
                  :placeholder="t('auth.confirmPasswordPlaceholder')"
                  required
                />
                <button
                  type="button"
                  @click="showConfirmPassword = !showConfirmPassword"
                  class="absolute inset-y-0 right-0 pr-3.5 flex items-center text-gray-400 hover:text-gray-600 transition-colors"
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
              <p v-if="confirmPassword && password !== confirmPassword" class="mt-1 text-xs text-danger-500">
                {{ t('auth.passwordMismatch') }}
              </p>
            </div>

            <!-- Captcha -->
            <div>
              <label for="captcha" class="block text-sm font-medium text-gray-700 mb-1.5">
                {{ t('auth.captcha') }}
              </label>
              <div class="flex gap-3">
                <div class="relative flex-1">
                  <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                    <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                    </svg>
                  </div>
                  <input
                    id="captcha"
                    v-model="captcha"
                    type="text"
                    maxlength="6"
                    class="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors uppercase tracking-widest"
                    :placeholder="t('auth.captchaPlaceholder')"
                    required
                  />
                </div>
                <div class="flex-shrink-0">
                  <img
                    :src="captchaUrl"
                    alt="Captcha"
                    class="h-12 w-28 rounded-lg border border-gray-300 cursor-pointer hover:opacity-80 transition-opacity object-cover bg-gray-100"
                    @click="refreshCaptcha"
                    :title="t('auth.refreshCaptcha')"
                  />
                </div>
              </div>
            </div>

            <!-- Terms -->
            <div class="flex items-start">
              <input
                id="terms"
                v-model="agreeTerms"
                type="checkbox"
                class="mt-1 w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <label for="terms" class="ml-2 text-sm text-gray-600">
                {{ t('auth.agreeTermsPrefix') }}
                <a href="#" class="text-primary-600 hover:text-primary-700">{{ t('auth.termsOfService') }}</a>
                {{ t('auth.and') }}
                <a href="#" class="text-primary-600 hover:text-primary-700">{{ t('auth.privacyPolicy') }}</a>
              </label>
            </div>

            <!-- Submit Button -->
            <button
              type="submit"
              class="w-full py-3 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-xl shadow-lg shadow-primary-500/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              :disabled="!isValid || isLoading"
            >
              <svg v-if="isLoading" class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              {{ isLoading ? t('auth.registering') : t('auth.register') }}
            </button>
          </form>

          <!-- Divider -->
          <div class="relative my-6">
            <div class="absolute inset-0 flex items-center">
              <div class="w-full border-t border-gray-200"></div>
            </div>
            <div class="relative flex justify-center text-sm">
              <span class="px-4 bg-white text-gray-500">{{ t('auth.or') }}</span>
            </div>
          </div>

          <!-- Login Link -->
          <div class="text-center">
            <p class="text-sm text-gray-600">
              {{ t('auth.haveAccount') }}
              <router-link to="/login" class="text-primary-600 hover:text-primary-700 font-medium">
                {{ t('auth.loginNow') }}
              </router-link>
            </p>
          </div>
        </div>

        <!-- Footer -->
        <div class="mt-8 text-center text-sm text-gray-500">
          <p>&copy; 2024 HyperFileLens. All rights reserved.</p>
        </div>
      </div>
    </div>
  </div>
</template>
